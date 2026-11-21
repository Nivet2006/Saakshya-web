"""Conversation workflow state machine, spoken read-back, corrections & escalation.

Implements Phase 2's deterministic workflow controller for the ASHA Voice Field
Register:

    IDLE -> GATHERING_NOTES -> EXTRACTING_FIELDS
         -> CLARIFICATION_REQUIRED (if missing/ambiguous required fields)
         -> READ_BACK_CONFIRMATION -> READY_TO_CONFIRM
         -> CORRECTION_PATCH -> READ_BACK_CONFIRMATION (on field corrections)
         -> confirmed + persistence_requested -> COMMITTED (only after ack)

    ANY STATE -> DANGER_ESCALATION (immediate high-priority interrupt)

Design invariants:
- No unconfirmed draft can ever transition to COMMITTED.
- Persistence is separated from worker confirmation: `COMMITTED` requires
  `handle_persistence_result(accepted=True)`.
- Danger alerts are strictly append-only and preserved across interruptions,
  corrections, resuming, or visit abandonment.
- Never diagnose, prescribe, suggest home remedies, or invent PHC details.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from app.conversation.models import (
    ActionType,
    ClarificationRequest,
    ConversationState,
    DangerAlertInput,
    DangerAlertRecord,
    ExtractionUpdate,
    StateMachineAction,
    TransitionResult,
    VisitRecordState,
    VisitStatus,
    VisitType,
    normalize_language,
    utc_now_iso,
)


class InvalidTransitionError(ValueError):
    """Raised when an operation violates a safety or confirmation invariant."""


# ---------------------------------------------------------------------------
# Confirmation / Rejection Intent Detection
# ---------------------------------------------------------------------------

_NEGATION_LATIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(no|nope|not|nah|nahi|nahin|na|mat|galat|wrong|cancel|change|incorrect|badlo|badalna|illa|illai|beda|venda|vendam)\b", re.IGNORECASE),
)
_NEGATION_INDIC_SUBSTRINGS: tuple[str, ...] = (
    "नहीं",
    "नही",
    "गलत",
    "बदलो",
    "कैंसल",
    "ಇಲ್ಲ",
    "ಬೇಡ",
    "ತಪ್ಪು",
    "இல்லை",
    "வேண்டாம்",
    "தவறு",
)

_AFFIRMATIVE_LATIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(yes|yeah|yep|confirm|confirmed|correct|right|ok|okay|haan|haa|han|houdu|howdu|aama|aamam|aamaam|sari|seri)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(theek\s+hai|thik\s+hai|sahi\s+hai|haan\s+ji|han\s+ji|hanji|go\s+ahead|save\s+it|confirm\s+karo|confirm\s+kar\s+do|save\s+kar\s+do|confirm\s+madi|confirm\s+pannunga)\b",
        re.IGNORECASE,
    ),
)
_AFFIRMATIVE_INDIC_SUBSTRINGS: tuple[str, ...] = (
    "हाँ",
    "हां",
    "ठीक है",
    "सही है",
    "कन्फर्म",
    "ಹೌದು",
    "ಸರಿ",
    "ದೃಢೀಕರಿಸಿ",
    "ஆமா",
    "ஆமாம்",
    "சரி",
    "உறுதி",
)

# Lightweight fallback patterns for inline voice corrections when caller did not
# already pass a structured ExtractionUpdate patch from 1C.
_WEIGHT_CORRECTION_RE = re.compile(
    r"(?:weight|wajan|vajan|वज़न|वजन|ತೂಕ|எடை)?\s*(?:is|hai|है|:)?\s*(\d+(?:\.\d+)?)\s*(?:kg|kgs|kilo|kilos|kilogram|kilograms|किलो|ಕೆಜಿ|கிலோ)\b",
    re.IGNORECASE,
)
_NEXT_VISIT_CORRECTION_RE = re.compile(
    r"(?:next\s+visit(?:\s+date)?|agli\s+visit|अगली\s+विज़िट(?:\s+की\s+तारीख)?)\s*(?:is|on|ko|hai|को|है|:)?\s*([0-9]{4}-[0-9]{2}-[0-9]{2}|\d{1,2}\s+[A-Za-z]+(?:\s+\d{4})?|[A-Za-z]+\s+\d{1,2}(?:,?\s+\d{4})?)",
    re.IGNORECASE,
)
_VISIT_TYPE_CORRECTION_RE = re.compile(
    r"(?:visit\s+type|visit)\s*(?:is|hai|:)?\s*\b(ANC|PNC|Newborn|Immunisation|Immunization)\b",
    re.IGNORECASE,
)


def classify_confirmation_intent(utterance: str) -> str:
    """Classify a confirmation-phase utterance as 'confirm', 'reject', or 'unclear'.

    Negation/correction cues always take precedence so utterances like
    'No, correct weight is 2.8 kilo' are NEVER misclassified as 'confirm'.
    """
    text = utterance.strip()
    if not text:
        return "unclear"

    for pat in _NEGATION_LATIN_PATTERNS:
        if pat.search(text):
            return "reject"
    for sub in _NEGATION_INDIC_SUBSTRINGS:
        if sub in text:
            return "reject"

    for pat in _AFFIRMATIVE_LATIN_PATTERNS:
        if pat.search(text):
            return "confirm"
    for sub in _AFFIRMATIVE_INDIC_SUBSTRINGS:
        if sub in text:
            return "confirm"

    return "unclear"


def extract_fallback_correction_patch(utterance: str) -> ExtractionUpdate | None:
    """Best-effort parser for simple direct voice corrections if 1C patch wasn't supplied."""
    text = utterance.strip()
    if not text:
        return None

    kwargs: dict[str, Any] = {}
    explicit: set[str] = set()

    m_weight = _WEIGHT_CORRECTION_RE.search(text)
    if m_weight:
        val = float(m_weight.group(1))
        if 0 < val <= 250:
            kwargs["weight_kg"] = val
            explicit.add("weight_kg")

    m_date = _NEXT_VISIT_CORRECTION_RE.search(text)
    if m_date:
        kwargs["next_visit_date"] = m_date.group(1).strip().rstrip(".,")
        explicit.add("next_visit_date")

    m_vtype = _VISIT_TYPE_CORRECTION_RE.search(text)
    if m_vtype:
        kwargs["visit_type"] = m_vtype.group(1)
        explicit.add("visit_type")

    if not explicit:
        return None
    return ExtractionUpdate(**kwargs, explicit_fields=explicit)


# ---------------------------------------------------------------------------
# Localized Speech Templates (hi-IN, en-IN, kn-IN, ta-IN)
# Safety rule: NO diagnosis, NO treatment/medicine/home remedies,
# NO fabricated PHC locations or phone numbers.
# ---------------------------------------------------------------------------

def _format_weight(weight_kg: float) -> str:
    return f"{weight_kg:.2f}".rstrip("0").rstrip(".")


def _join_list(items: list[str]) -> str:
    return ", ".join(items)


_URGENT_REFERRAL_MESSAGES: dict[str, str] = {
    "en-IN": (
        "Urgent alert! A danger sign has been detected. "
        "Please refer the beneficiary to the nearest PHC immediately. "
        "Do not delay referral."
    ),
    "hi-IN": (
        "तत्काल चेतावनी! खतरे का लक्षण पाया गया है। "
        "कृपया लाभार्थी को तुरंत नज़दीकी पीएचसी में रेफर करें। "
        "रेफर करने में देरी न करें।"
    ),
    "kn-IN": (
        "ತುರ್ತು ಎಚ್ಚರಿಕೆ! ಅಪಾಯದ ಲಕ್ಷಣ ಕಂಡುಬಂದಿದೆ. "
        "ದಯವಿಟ್ಟು ಫಲಾನುಭವಿಯನ್ನು ತಕ್ಷಣ ಹತ್ತಿರದ ಪಿಎಚ್‌ಸಿಗೆ ಕಳುಹಿಸಿ. "
        "ತಡ ಮಾಡಬೇಡಿ."
    ),
    "ta-IN": (
        "அவசர எச்சரிக்கை! அபாய அறிகுறி கண்டறியப்பட்டுள்ளது. "
        "தயவுசெய்து பயனாளியை உடனடியாக அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்திற்கு அனுப்பவும். "
        "தாமதிக்க வேண்டாம்."
    ),
}

_CONFIRMATION_PENDING_MESSAGES: dict[str, str] = {
    "en-IN": "Record confirmed. Saving the visit record now.",
    "hi-IN": "रिकॉर्ड कन्फर्म हो गया है। अब विज़िट रिकॉर्ड सेव किया जा रहा है।",
    "kn-IN": "ದಾಖಲೆ ದೃಢೀಕರಿಸಲಾಗಿದೆ. ಈಗ ಭೇಟಿಯ ದಾಖಲೆಯನ್ನು ಉಳಿಸಲಾಗುತ್ತಿದೆ.",
    "ta-IN": "பதிவு உறுதிப்படுத்தப்பட்டது. இப்போது பார்வை பதிவு சேமிக்கப்படுகிறது.",
}

_COMMITTED_MESSAGES: dict[str, str] = {
    "en-IN": "Visit record has been saved successfully.",
    "hi-IN": "विज़िट रिकॉर्ड सफलतापूर्वक सेव हो गया है।",
    "kn-IN": "ಭೇಟಿಯ ದಾಖಲೆಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ.",
    "ta-IN": "பார்வை பதிவு வெற்றிகரமாக சேமிக்கப்பட்டது.",
}

_PERSISTENCE_FAILED_MESSAGES: dict[str, str] = {
    "en-IN": (
        "Your record is confirmed locally, but it could not be saved to the server yet. "
        "Please retry saving when connectivity is available."
    ),
    "hi-IN": (
        "यह रिकॉर्ड लोकल रूप से कन्फर्म हो गया है, लेकिन अभी सर्वर पर सेव नहीं हो सका है। "
        "कृपया नेटवर्क मिलने पर दोबारा सेव करें।"
    ),
    "kn-IN": (
        "ಈ ದಾಖಲೆ ಸ್ಥಳೀಯವಾಗಿ ದೃಢೀಕರಿಸಲಾಗಿದೆ, ಆದರೆ ಇನ್ನೂ ಸರ್ವರ್‌ನಲ್ಲಿ ಉಳಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. "
        "ದಯವಿಟ್ಟು ಸಂಪರ್ಕ ಲಭ್ಯವಾದಾಗ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."
    ),
    "ta-IN": (
        "இந்தப் பதிவு உள்ளூரில் உறுதிப்படுத்தப்பட்டுள்ளது, ஆனால் இன்னும் சர்வரில் சேமிக்க முடியவில்லை. "
        "தயவுசெய்து இணைப்பு கிடைத்ததும் மீண்டும் முயற்சிக்கவும்."
    ),
}

_REJECT_WITHOUT_FIELD_MESSAGES: dict[str, str] = {
    "en-IN": "Okay, I have not confirmed the record. Which detail would you like to change?",
    "hi-IN": "ठीक है, रिकॉर्ड कन्फर्म नहीं किया गया है। आप कौन सी जानकारी बदलना चाहती हैं?",
    "kn-IN": "ಸರಿ, ದಾಖಲೆಯನ್ನು ದೃಢೀಕರಿಸಿಲ್ಲ. ಯಾವ ಮಾಹಿತಿಯನ್ನು ಬದಲಾಯಿಸಬೇಕು?",
    "ta-IN": "சரி, பதிவை உறுதிப்படுத்தவில்லை. எந்தத் தகவலை மாற்ற வேண்டும்?",
}

_UNCLEAR_CONFIRMATION_MESSAGES: dict[str, str] = {
    "en-IN": "Please say confirm to save this record, or tell me which field to change.",
    "hi-IN": "कृपया रिकॉर्ड सेव करने के लिए कन्फर्म बोलें, या बताएं कौन सी जानकारी बदलनी है।",
    "kn-IN": "ಈ ದಾಖಲೆಯನ್ನು ಉಳಿಸಲು ಹೌದು ಎಂದು ಹೇಳಿ, ಅಥವಾ ಯಾವ ಮಾಹಿತಿಯನ್ನು ಬದಲಾಯಿಸಬೇಕು ಎಂದು ತಿಳಿಸಿ.",
    "ta-IN": "இந்தப் பதிவை சேமிக்க சரி என்று சொல்லுங்கள், அல்லது எந்தத் தகவலை மாற்ற வேண்டும் என்று கூறுங்கள்.",
}

_CLARIFICATION_TEMPLATES: dict[str, dict[str, str]] = {
    "en-IN": {
        "beneficiary_id": "Could you please confirm the beneficiary name or ID?",
        "visit_type": "What is the visit type: ANC, PNC, Newborn, or Immunisation?",
        "clinical_observation": "Please share at least one visit detail such as weight, vaccinations, or next visit date.",
        "weight_kg": "Could you please confirm the weight in kilograms?",
        "next_visit_date": "Could you please clarify the next visit date?",
        "vaccinations_due": "Which vaccinations are due?",
        "default": "Could you please clarify the {field}?",
    },
    "hi-IN": {
        "beneficiary_id": "कृपया लाभार्थी का नाम या आईडी बताएं।",
        "visit_type": "यह विज़िट किस प्रकार की है: ANC, PNC, Newborn, या Immunisation?",
        "clinical_observation": "कृपया विज़िट की कम से कम एक जानकारी बताएं, जैसे वज़न, टीकाकरण या अगली विज़िट की तारीख।",
        "weight_kg": "कृपया वज़न किलो में स्पष्ट करें।",
        "next_visit_date": "कृपया अगली विज़िट की तारीख स्पष्ट करें।",
        "vaccinations_due": "कौन से टीके बाकी हैं?",
        "default": "कृपया {field} स्पष्ट करें।",
    },
    "kn-IN": {
        "beneficiary_id": "ದಯವಿಟ್ಟು ಫಲಾನುಭವಿಯ ಹೆಸರು ಅಥವಾ ಐಡಿ ತಿಳಿಸಿ.",
        "visit_type": "ಭೇಟಿಯ ವಿಧ ಯಾವುದು: ANC, PNC, Newborn, ಅಥವಾ Immunisation?",
        "clinical_observation": "ದಯವಿಟ್ಟು ತೂಕ, ಲಸಿಕೆ ಅಥವಾ ಮುಂದಿನ ಭೇಟಿಯ ದಿನಾಂಕದಂತಹ ಕನಿಷ್ಠ ಒಂದು ಮಾಹಿತಿಯನ್ನು ತಿಳಿಸಿ.",
        "weight_kg": "ದಯವಿಟ್ಟು ತೂಕವನ್ನು ಕೆಜಿಯಲ್ಲಿ ದೃಢೀಕರಿಸಿ.",
        "next_visit_date": "ದಯವಿಟ್ಟು ಮುಂದಿನ ಭೇಟಿಯ ದಿನಾಂಕವನ್ನು ಸ್ಪಷ್ಟಪಡಿಸಿ.",
        "vaccinations_due": "ಯಾವ ಲಸಿಕೆಗಳು ಬಾಕಿ ಇವೆ?",
        "default": "ದಯವಿಟ್ಟು {field} ಮಾಹಿತಿಯನ್ನು ಸ್ಪಷ್ಟಪಡಿಸಿ.",
    },
    "ta-IN": {
        "beneficiary_id": "தயவுசெய்து பயனாளியின் பெயர் அல்லது ஐடியைக் கூறுங்கள்.",
        "visit_type": "பார்வை வகை என்ன: ANC, PNC, Newborn, அல்லது Immunisation?",
        "clinical_observation": "தயவுசெய்து எடை, தடுப்பூசி அல்லது அடுத்த பார்வை தேதி போன்ற குறைந்தது ஒரு விவரத்தைக் கூறுங்கள்.",
        "weight_kg": "தயவுசெய்து எடையை கிலோவில் உறுதிப்படுத்தவும்.",
        "next_visit_date": "தயவுசெய்து அடுத்த பார்வை தேதியைத் தெளிவுபடுத்தவும்.",
        "vaccinations_due": "எந்தத் தடுப்பூசிகள் நிலுவையில் உள்ளன?",
        "default": "தயவுசெய்து {field} விவரத்தைத் தெளிவுபடுத்தவும்.",
    },
}


def generate_urgent_referral_text(language: str, alert: DangerAlertInput | None = None) -> str:
    """Return a safe, localized urgent PHC referral message."""
    lang = normalize_language(language)
    if alert is not None and alert.escalation_message and alert.escalation_message.strip():
        return alert.escalation_message.strip()
    return _URGENT_REFERRAL_MESSAGES[lang]


def generate_read_back_text(visit: VisitRecordState, language: str) -> str:
    """Generate natural spoken read-back text in hi-IN, en-IN, kn-IN, or ta-IN."""
    lang = normalize_language(language)
    parts: list[str] = []

    ben_id = visit.beneficiary_id or "unknown"
    ben_name = visit.beneficiary_name
    vtype = visit.visit_type.value if visit.visit_type else "unknown"
    weight_str = _format_weight(visit.weight_kg) if visit.weight_kg is not None else None
    signs_str = _join_list(visit.danger_signs) if visit.danger_signs else ""

    if lang == "hi-IN":
        parts.append("मैं इस विज़िट का रिकॉर्ड पढ़कर सुना रही हूँ।")
        if ben_name:
            parts.append(f"लाभार्थी {ben_name}, आईडी {ben_id}।")
        else:
            parts.append(f"लाभार्थी आईडी {ben_id}।")
        parts.append(f"विज़िट का प्रकार: {vtype}।")
        if weight_str is not None:
            parts.append(f"वज़न: {weight_str} किलो।")
        if visit.vaccinations_completed:
            parts.append(f"पूरे हुए टीके: {_join_list(visit.vaccinations_completed)}।")
        if visit.vaccinations_due:
            parts.append(f"बाकी टीके: {_join_list(visit.vaccinations_due)}।")
        if visit.follow_up_actions:
            parts.append(f"फ़ॉलो-अप कार्य: {_join_list(visit.follow_up_actions)}।")
        if visit.next_visit_date:
            parts.append(f"अगली विज़िट की तारीख: {visit.next_visit_date}।")
        if visit.danger_sign_flagged:
            flag_detail = f" ({signs_str})" if signs_str else ""
            parts.append(
                f"चेतावनी: खतरे का लक्षण दर्ज है{flag_detail}। तुरंत नज़दीकी पीएचसी में रेफर करें।"
            )
        parts.append("क्या मैं यह रिकॉर्ड कन्फर्म कर दूँ?")

    elif lang == "kn-IN":
        parts.append("ಭೇಟಿಯ ದಾಖಲೆಯನ್ನು ಓದಿ ಹೇಳುತ್ತಿದ್ದೇನೆ.")
        if ben_name:
            parts.append(f"ಫಲಾನುಭವಿ {ben_name}, ಐಡಿ {ben_id}.")
        else:
            parts.append(f"ಫಲಾನುಭವಿ ಐಡಿ {ben_id}.")
        parts.append(f"ಭೇಟಿಯ ವಿಧ: {vtype}.")
        if weight_str is not None:
            parts.append(f"ತೂಕ: {weight_str} ಕೆಜಿ.")
        if visit.vaccinations_completed:
            parts.append(f"ಪೂರ್ಣಗೊಂಡ ಲಸಿಕೆಗಳು: {_join_list(visit.vaccinations_completed)}.")
        if visit.vaccinations_due:
            parts.append(f"ಬಾಕಿ ಇರುವ ಲಸಿಕೆಗಳು: {_join_list(visit.vaccinations_due)}.")
        if visit.follow_up_actions:
            parts.append(f"ಮುಂದಿನ ಕ್ರಮಗಳು: {_join_list(visit.follow_up_actions)}.")
        if visit.next_visit_date:
            parts.append(f"ಮುಂದಿನ ಭೇಟಿಯ ದಿನಾಂಕ: {visit.next_visit_date}.")
        if visit.danger_sign_flagged:
            flag_detail = f" ({signs_str})" if signs_str else ""
            parts.append(
                f"ಎಚ್ಚರಿಕೆ: ಅಪಾಯದ ಲಕ್ಷಣ ಗುರುತಿಸಲಾಗಿದೆ{flag_detail}. ತಕ್ಷಣ ಹತ್ತಿರದ ಪಿಎಚ್‌ಸಿಗೆ ಕಳುಹಿಸಿ."
            )
        parts.append("ಈ ದಾಖಲೆಯನ್ನು ದೃಢೀಕರಿಸಲೇ?")

    elif lang == "ta-IN":
        parts.append("பார்வை பதிவை படித்துக் காட்டுகிறேன்.")
        if ben_name:
            parts.append(f"பயனாளி {ben_name}, ஐடி {ben_id}.")
        else:
            parts.append(f"பயனாளி ஐடி {ben_id}.")
        parts.append(f"பார்வை வகை: {vtype}.")
        if weight_str is not None:
            parts.append(f"எடை: {weight_str} கிலோ.")
        if visit.vaccinations_completed:
            parts.append(f"முடிந்த தடுப்பூசிகள்: {_join_list(visit.vaccinations_completed)}.")
        if visit.vaccinations_due:
            parts.append(f"நிலுவை தடுப்பூசிகள்: {_join_list(visit.vaccinations_due)}.")
        if visit.follow_up_actions:
            parts.append(f"தொடர் நடவடிக்கைகள்: {_join_list(visit.follow_up_actions)}.")
        if visit.next_visit_date:
            parts.append(f"அடுத்த பார்வை தேதி: {visit.next_visit_date}.")
        if visit.danger_sign_flagged:
            flag_detail = f" ({signs_str})" if signs_str else ""
            parts.append(
                f"எச்சரிக்கை: அபாய அறிகுறி பதிவாகியுள்ளது{flag_detail}. "
                "உடனடியாக அருகிலுள்ள ஆரம்ப சுகாதார நிலையத்திற்கு அனுப்பவும்."
            )
        parts.append("இந்தப் பதிவை உறுதிப்படுத்தலாமா?")

    else:  # en-IN
        parts.append("Let me read back the visit record.")
        if ben_name:
            parts.append(f"Beneficiary {ben_name}, ID {ben_id}.")
        else:
            parts.append(f"Beneficiary ID {ben_id}.")
        parts.append(f"Visit type: {vtype}.")
        if weight_str is not None:
            parts.append(f"Weight: {weight_str} kg.")
        if visit.vaccinations_completed:
            parts.append(f"Vaccinations completed: {_join_list(visit.vaccinations_completed)}.")
        if visit.vaccinations_due:
            parts.append(f"Vaccinations due: {_join_list(visit.vaccinations_due)}.")
        if visit.follow_up_actions:
            parts.append(f"Follow-up actions: {_join_list(visit.follow_up_actions)}.")
        if visit.next_visit_date:
            parts.append(f"Next visit date: {visit.next_visit_date}.")
        if visit.danger_sign_flagged:
            flag_detail = f" ({signs_str})" if signs_str else ""
            parts.append(
                f"Alert: Danger sign flagged{flag_detail}. "
                "Immediate referral to the nearest PHC is required."
            )
        parts.append("Should I confirm this record?")

    return " ".join(parts)


def generate_clarification_text(
    clarifications: list[ClarificationRequest],
    language: str,
) -> str:
    """Generate a concise localized prompt asking ONLY for missing/ambiguous fields."""
    lang = normalize_language(language)
    templates = _CLARIFICATION_TEMPLATES[lang]
    prompts: list[str] = []

    for req in clarifications:
        if lang == "en-IN" and req.question and req.question.strip():
            prompt = req.question.strip()
        elif req.field in templates:
            prompt = templates[req.field].format(field=req.field)
        elif req.question and req.question.strip():
            prompt = req.question.strip()
        else:
            prompt = templates["default"].format(field=req.field)
        if req.candidates:
            options_str = ", ".join(req.candidates)
            if lang == "hi-IN":
                prompt = f"{prompt} विकल्प: {options_str}।"
            elif lang == "kn-IN":
                prompt = f"{prompt} ಆಯ್ಕೆಗಳು: {options_str}."
            elif lang == "ta-IN":
                prompt = f"{prompt} விருப்பங்கள்: {options_str}."
            else:
                prompt = f"{prompt} Options: {options_str}."
        prompts.append(prompt)

    return " ".join(prompts)


# ---------------------------------------------------------------------------
# Conversation State Machine
# ---------------------------------------------------------------------------

class ConversationStateMachine:
    """Per-session visit workflow state machine with safety-first escalation."""

    def __init__(
        self,
        *,
        session_id: str | None = None,
        language: str = "hi-IN",
        beneficiary_id: str | None = None,
        beneficiary_name: str | None = None,
        visit_draft_id: str | None = None,
    ) -> None:
        self.session_id: str = session_id or f"sess_{uuid.uuid4().hex[:12]}"
        self.active_language: str = normalize_language(language)
        self.state: ConversationState = ConversationState.IDLE
        self.return_state: ConversationState | None = None

        visit_kwargs: dict[str, Any] = {}
        if visit_draft_id:
            visit_kwargs["visit_draft_id"] = visit_draft_id
        if beneficiary_id:
            visit_kwargs["beneficiary_id"] = beneficiary_id
        if beneficiary_name:
            visit_kwargs["beneficiary_name"] = beneficiary_name
        self.visit: VisitRecordState = VisitRecordState(**visit_kwargs)

        self.confirmed_fields: set[str] = set()
        if beneficiary_id:
            self.confirmed_fields.add("beneficiary_id")
        if beneficiary_name:
            self.confirmed_fields.add("beneficiary_name")

        self.pending_clarifications: list[ClarificationRequest] = []
        self._danger_alerts: list[DangerAlertRecord] = []
        self._danger_index_by_canonical: dict[str, int] = {}

        self.last_read_back_text: str | None = None
        self.awaiting_persistence: bool = False
        self.persistence_error: str | None = None
        self.abandoned: bool = False
        self.transition_history: list[tuple[ConversationState, ConversationState, str]] = []

    @property
    def danger_alerts(self) -> list[DangerAlertRecord]:
        """Return defensive copies of immutable session danger alerts."""
        return [a.model_copy(deep=True) for a in self._danger_alerts]

    def set_language(self, language: str) -> str:
        """Update the active response language to a supported BCP-47 tag."""
        self.active_language = normalize_language(language, default=self.active_language)
        return self.active_language

    # -- Internal helpers ----------------------------------------------------

    def _transition(
        self,
        new_state: ConversationState,
        reason: str,
        actions: list[StateMachineAction],
        *,
        priority: str = "normal",
    ) -> None:
        old_state = self.state
        if old_state != new_state:
            self.state = new_state
            self.transition_history.append((old_state, new_state, reason))
            actions.append(
                StateMachineAction(
                    action_type=ActionType.STATE_CHANGED,
                    priority=priority,
                    payload={
                        "previous_state": old_state.value,
                        "current_state": new_state.value,
                        "reason": reason,
                    },
                )
            )

    def _result(
        self,
        previous_state: ConversationState,
        actions: list[StateMachineAction],
        *,
        spoken_text: str | None = None,
        is_urgent: bool = False,
        interrupt_speech: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> TransitionResult:
        return TransitionResult(
            previous_state=previous_state,
            current_state=self.state,
            spoken_text=spoken_text,
            spoken_language=self.active_language,
            is_urgent=is_urgent,
            interrupt_speech=interrupt_speech,
            actions=actions,
            visit_record=self.visit.model_copy(deep=True),
            danger_alerts=self.danger_alerts,
            pending_clarifications=[c.model_copy(deep=True) for c in self.pending_clarifications],
            metadata=metadata or {},
        )

    def _merge_unique_list(self, existing: list[str], additions: list[str]) -> list[str]:
        seen = {item.strip().lower() for item in existing}
        merged = list(existing)
        for item in additions:
            cleaned = item.strip()
            if cleaned and cleaned.lower() not in seen:
                merged.append(cleaned)
                seen.add(cleaned.lower())
        return merged

    def _backfill_alert_beneficiary(self) -> None:
        if not self.visit.beneficiary_id:
            return
        for idx, alert in enumerate(self._danger_alerts):
            if alert.beneficiary_id is None:
                self._danger_alerts[idx] = alert.model_copy(
                    update={"beneficiary_id": self.visit.beneficiary_id}
                )

    def _compute_clarifications(self) -> list[ClarificationRequest]:
        """Determine unresolved ambiguities + missing minimum required fields.

        Never includes fields that are already confirmed.
        """
        by_field: dict[str, ClarificationRequest] = {}

        # 1. Retain active ambiguities/clarifications that have NOT been confirmed yet
        for req in self.pending_clarifications:
            if req.field == "clinical_observation" and self.visit.has_clinical_observation():
                continue
            if req.field in self.confirmed_fields and req.reason == "missing":
                continue
            if req.field == "beneficiary_id" and self.visit.beneficiary_id is not None and req.reason != "ambiguous":
                continue
            if req.field == "visit_type" and self.visit.visit_type is not None and req.reason != "ambiguous":
                continue
            if req.field in self.confirmed_fields and req.reason == "ambiguous":
                continue
            by_field[req.field] = req

        # 2. Check minimum required fields before read-back
        if self.visit.beneficiary_id is None and "beneficiary_id" not in by_field:
            by_field["beneficiary_id"] = ClarificationRequest(
                field="beneficiary_id", reason="missing"
            )
        if self.visit.visit_type is None and "visit_type" not in by_field:
            by_field["visit_type"] = ClarificationRequest(
                field="visit_type", reason="missing"
            )
        if not self.visit.has_clinical_observation() and "clinical_observation" not in by_field:
            by_field["clinical_observation"] = ClarificationRequest(
                field="clinical_observation", reason="missing"
            )

        # Deterministic ordering: explicit ambiguities first, then required fields
        ordered: list[ClarificationRequest] = []
        priority_order = ("beneficiary_id", "visit_type", "clinical_observation")
        for key, req in by_field.items():
            if req.reason != "missing":
                ordered.append(req)
        for key in priority_order:
            if key in by_field and by_field[key].reason == "missing":
                ordered.append(by_field[key])
        for key, req in by_field.items():
            if req.reason == "missing" and key not in priority_order:
                ordered.append(req)
        return ordered

    def _apply_update_fields(
        self, update: ExtractionUpdate, *, is_patch: bool
    ) -> list[str]:
        """Apply extraction/patch fields to `self.visit` without touching danger state."""
        fields = update.specified_fields()
        changed: list[str] = []

        if "beneficiary_id" in fields and update.beneficiary_id is not None:
            self.visit.beneficiary_id = update.beneficiary_id
            self.confirmed_fields.add("beneficiary_id")
            self._backfill_alert_beneficiary()
            changed.append("beneficiary_id")

        if "beneficiary_name" in fields and update.beneficiary_name is not None:
            self.visit.beneficiary_name = update.beneficiary_name
            self.confirmed_fields.add("beneficiary_name")
            changed.append("beneficiary_name")

        if "visit_type" in fields and update.visit_type is not None:
            self.visit.visit_type = update.visit_type
            self.confirmed_fields.add("visit_type")
            changed.append("visit_type")

        if "weight_kg" in fields and update.weight_kg is not None:
            self.visit.weight_kg = update.weight_kg
            self.confirmed_fields.add("weight_kg")
            changed.append("weight_kg")

        if "vaccinations_completed" in fields and update.vaccinations_completed is not None:
            if is_patch:
                self.visit.vaccinations_completed = [
                    v.strip() for v in update.vaccinations_completed if v.strip()
                ]
            else:
                self.visit.vaccinations_completed = self._merge_unique_list(
                    self.visit.vaccinations_completed, update.vaccinations_completed
                )
            self.confirmed_fields.add("vaccinations_completed")
            changed.append("vaccinations_completed")

        if "vaccinations_due" in fields and update.vaccinations_due is not None:
            if is_patch:
                self.visit.vaccinations_due = [
                    v.strip() for v in update.vaccinations_due if v.strip()
                ]
            else:
                self.visit.vaccinations_due = self._merge_unique_list(
                    self.visit.vaccinations_due, update.vaccinations_due
                )
            self.confirmed_fields.add("vaccinations_due")
            changed.append("vaccinations_due")

        if "next_visit_date" in fields and update.next_visit_date is not None:
            self.visit.next_visit_date = update.next_visit_date.strip()
            self.confirmed_fields.add("next_visit_date")
            changed.append("next_visit_date")

        if "follow_up_actions" in fields and update.follow_up_actions is not None:
            if is_patch:
                self.visit.follow_up_actions = [
                    a.strip() for a in update.follow_up_actions if a.strip()
                ]
            else:
                self.visit.follow_up_actions = self._merge_unique_list(
                    self.visit.follow_up_actions, update.follow_up_actions
                )
            self.confirmed_fields.add("follow_up_actions")
            changed.append("follow_up_actions")

        # Clear any pending clarifications for fields that just received concrete values
        if changed:
            changed_set = set(changed)
            self.pending_clarifications = [
                c for c in self.pending_clarifications if c.field not in changed_set
            ]
            self.visit.updated_at = utc_now_iso()

        # Merge newly reported clarifications (ignoring fields resolved in this same update
        # or already confirmed unless the value is still unknown).
        for clar in update.clarifications:
            if clar.field in changed:
                continue
            if clar.field in self.confirmed_fields and getattr(self.visit, clar.field, None) is not None:
                continue
            self.pending_clarifications = [
                c for c in self.pending_clarifications if c.field != clar.field
            ]
            self.pending_clarifications.append(clar)

        return changed

    def _enter_read_back(
        self,
        actions: list[StateMachineAction],
        *,
        reason: str,
    ) -> str:
        self.pending_clarifications = []
        self._transition(ConversationState.READ_BACK_CONFIRMATION, reason, actions)
        read_back = generate_read_back_text(self.visit, self.active_language)
        self.last_read_back_text = read_back
        actions.append(
            StateMachineAction(
                action_type=ActionType.READ_BACK_STARTED,
                payload={
                    "visit_draft_id": self.visit.visit_draft_id,
                    "language": self.active_language,
                    "text": read_back,
                },
            )
        )
        actions.append(
            StateMachineAction(
                action_type=ActionType.SPEAK,
                payload={"text": read_back, "language": self.active_language},
            )
        )
        return read_back

    # -- Public Workflow API -------------------------------------------------

    def start_gathering(self, *, language: str | None = None) -> TransitionResult:
        """Transition from IDLE into GATHERING_NOTES when the worker begins speaking."""
        previous = self.state
        if language:
            self.set_language(language)
        actions: list[StateMachineAction] = []
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError(
                "Visit record is already committed; start a new session for another visit."
            )
        if self.state == ConversationState.IDLE:
            self._transition(
                ConversationState.GATHERING_NOTES, "worker_started_visit_notes", actions
            )
        return self._result(previous, actions)

    def begin_extraction(self, *, language: str | None = None) -> TransitionResult:
        """Transition into EXTRACTING_FIELDS while the extraction layer parses notes."""
        previous = self.state
        if language:
            self.set_language(language)
        actions: list[StateMachineAction] = []
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Cannot extract fields into a committed visit.")
        if self.state == ConversationState.IDLE:
            self._transition(
                ConversationState.GATHERING_NOTES, "worker_started_visit_notes", actions
            )
        if self.state in (
            ConversationState.GATHERING_NOTES,
            ConversationState.CLARIFICATION_REQUIRED,
            ConversationState.DANGER_ESCALATION,
        ):
            self._transition(
                ConversationState.EXTRACTING_FIELDS, "extraction_started", actions
            )
        return self._result(previous, actions)

    def apply_extraction(
        self,
        update: ExtractionUpdate,
        *,
        language: str | None = None,
    ) -> TransitionResult:
        """Apply extracted structured fields and route to clarification or read-back."""
        previous = self.state
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Cannot modify a committed visit record.")

        if language:
            self.set_language(language)
        elif update.detected_language:
            self.set_language(update.detected_language)

        actions: list[StateMachineAction] = []

        # Ensure explicit progression IDLE -> GATHERING_NOTES -> EXTRACTING_FIELDS
        if self.state == ConversationState.IDLE:
            self._transition(
                ConversationState.GATHERING_NOTES, "worker_started_visit_notes", actions
            )
        if self.state != ConversationState.EXTRACTING_FIELDS:
            self._transition(
                ConversationState.EXTRACTING_FIELDS, "extraction_started", actions
            )

        changed = self._apply_update_fields(update, is_patch=False)
        actions.append(
            StateMachineAction(
                action_type=ActionType.DRAFT_UPDATED,
                payload={
                    "changed_fields": changed,
                    "visit_record": self.visit.to_contract_payload(),
                },
            )
        )

        clarifications = self._compute_clarifications()
        if clarifications:
            self.pending_clarifications = clarifications
            self._transition(
                ConversationState.CLARIFICATION_REQUIRED,
                "missing_or_ambiguous_fields",
                actions,
            )
            prompt = generate_clarification_text(clarifications, self.active_language)
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [c.model_dump(mode="json") for c in clarifications],
                        "language": self.active_language,
                        "text": prompt,
                    },
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": prompt, "language": self.active_language},
                )
            )
            return self._result(previous, actions, spoken_text=prompt)

        read_back = self._enter_read_back(actions, reason="required_fields_complete")
        return self._result(previous, actions, spoken_text=read_back)

    def on_read_back_completed(self) -> TransitionResult:
        """Mark spoken read-back complete -> transition into READY_TO_CONFIRM."""
        previous = self.state
        actions: list[StateMachineAction] = []
        if self.state == ConversationState.READ_BACK_CONFIRMATION:
            self._transition(
                ConversationState.READY_TO_CONFIRM, "read_back_completed", actions
            )
        return self._result(previous, actions)

    def apply_correction_patch(
        self,
        patch: ExtractionUpdate,
        *,
        language: str | None = None,
    ) -> TransitionResult:
        """Patch ONLY specified fields, preserve all others + danger alerts, and re-read."""
        previous = self.state
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Cannot patch a committed visit record.")

        if language:
            self.set_language(language)
        elif patch.detected_language:
            self.set_language(patch.detected_language)

        actions: list[StateMachineAction] = []
        self._transition(
            ConversationState.CORRECTION_PATCH, "worker_correction_received", actions
        )

        # Any correction invalidates prior confirmation until re-read & re-confirmed
        self.visit.status = VisitStatus.DRAFT
        self.awaiting_persistence = False
        self.persistence_error = None

        patched_fields = self._apply_update_fields(patch, is_patch=True)
        actions.append(
            StateMachineAction(
                action_type=ActionType.CORRECTION_APPLIED,
                payload={
                    "patched_fields": patched_fields,
                    "visit_record": self.visit.to_contract_payload(),
                },
            )
        )
        actions.append(
            StateMachineAction(
                action_type=ActionType.DRAFT_UPDATED,
                payload={
                    "changed_fields": patched_fields,
                    "visit_record": self.visit.to_contract_payload(),
                },
            )
        )

        clarifications = self._compute_clarifications()
        if clarifications:
            self.pending_clarifications = clarifications
            self._transition(
                ConversationState.CLARIFICATION_REQUIRED,
                "clarification_needed_after_patch",
                actions,
            )
            prompt = generate_clarification_text(clarifications, self.active_language)
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [c.model_dump(mode="json") for c in clarifications],
                        "language": self.active_language,
                        "text": prompt,
                    },
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": prompt, "language": self.active_language},
                )
            )
            return self._result(
                previous,
                actions,
                spoken_text=prompt,
                metadata={"patched_fields": patched_fields},
            )

        read_back = self._enter_read_back(actions, reason="re_read_after_correction")
        return self._result(
            previous,
            actions,
            spoken_text=read_back,
            metadata={"patched_fields": patched_fields},
        )

    def handle_confirmation_response(
        self,
        utterance: str,
        *,
        correction_patch: ExtractionUpdate | None = None,
        language: str | None = None,
    ) -> TransitionResult:
        """Handle worker reply during READ_BACK_CONFIRMATION or READY_TO_CONFIRM.

        - If `correction_patch` has fields (or utterance contains a clear inline
          correction), applies CORRECTION_PATCH and re-reads.
        - If explicit affirmative confirmation (ONLY in READ_BACK_CONFIRMATION or
          READY_TO_CONFIRM), marks `status='confirmed'` and emits
          `persistence_requested` (does NOT mark COMMITTED yet).
        - If explicit rejection without a correction field, asks which field to change.
        """
        previous = self.state
        if language:
            self.set_language(language)

        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Visit record is already committed.")

        # 1. Explicit structured correction patch takes priority
        if correction_patch is not None and (
            correction_patch.specified_fields() or correction_patch.clarifications
        ):
            return self.apply_correction_patch(correction_patch)

        # 2. Fallback inline correction parsing (e.g. "No, weight is 2.8 kilo")
        if self.state in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
            ConversationState.CLARIFICATION_REQUIRED,
        ):
            inferred_patch = extract_fallback_correction_patch(utterance)
            if inferred_patch is not None:
                return self.apply_correction_patch(inferred_patch)

        intent = classify_confirmation_intent(utterance)
        actions: list[StateMachineAction] = []

        # 3. Affirmative confirmation is ONLY honoured in READ_BACK_CONFIRMATION / READY_TO_CONFIRM
        if intent == "confirm":
            if self.state not in (
                ConversationState.READ_BACK_CONFIRMATION,
                ConversationState.READY_TO_CONFIRM,
            ):
                raise InvalidTransitionError(
                    f"Explicit confirmation is only allowed in READ_BACK_CONFIRMATION or "
                    f"READY_TO_CONFIRM (current state: {self.state.value})."
                )
            if self.state == ConversationState.READ_BACK_CONFIRMATION:
                self._transition(
                    ConversationState.READY_TO_CONFIRM,
                    "worker_confirmed_during_read_back",
                    actions,
                )

            self.visit.status = VisitStatus.CONFIRMED
            self.visit.updated_at = utc_now_iso()
            self.awaiting_persistence = True
            self.persistence_error = None

            payload = self.visit.to_contract_payload()
            actions.append(
                StateMachineAction(
                    action_type=ActionType.WORKER_CONFIRMED,
                    payload={"visit_record": payload},
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.PERSISTENCE_REQUESTED,
                    priority="high",
                    payload={
                        "session_id": self.session_id,
                        "visit_record": payload,
                        "danger_alerts": [a.model_dump(mode="json") for a in self._danger_alerts],
                    },
                )
            )
            spoken = _CONFIRMATION_PENDING_MESSAGES[self.active_language]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": spoken, "language": self.active_language},
                )
            )
            return self._result(
                previous,
                actions,
                spoken_text=spoken,
                metadata={"intent": "confirm", "awaiting_persistence": True},
            )

        # 4. Explicit rejection without a correction field -> ask which field to change
        if intent == "reject":
            self.visit.status = VisitStatus.DRAFT
            self.awaiting_persistence = False
            self._transition(
                ConversationState.CLARIFICATION_REQUIRED,
                "worker_rejected_without_field",
                actions,
            )
            spoken = _REJECT_WITHOUT_FIELD_MESSAGES[self.active_language]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [
                            {"field": "unspecified", "reason": "correction_requested"}
                        ],
                        "language": self.active_language,
                        "text": spoken,
                    },
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": spoken, "language": self.active_language},
                )
            )
            return self._result(
                previous,
                actions,
                spoken_text=spoken,
                metadata={"intent": "reject"},
            )

        # 5. Unclear response -> never confirm; re-prompt politely
        spoken = _UNCLEAR_CONFIRMATION_MESSAGES[self.active_language]
        actions.append(
            StateMachineAction(
                action_type=ActionType.SPEAK,
                payload={"text": spoken, "language": self.active_language},
            )
        )
        return self._result(
            previous,
            actions,
            spoken_text=spoken,
            metadata={"intent": "unclear"},
        )

    def handle_persistence_result(
        self,
        *,
        accepted: bool,
        record_id: str | None = None,
        error: str | None = None,
    ) -> TransitionResult:
        """Process durable persistence acknowledgement from Agent 3 / storage layer.

        - Requires `visit.status == VisitStatus.CONFIRMED` (never commits an
          unconfirmed draft).
        - Transitions to `COMMITTED` ONLY when `accepted=True`.
        - When `accepted=False`, keeps `status='confirmed'` and stays out of
          `COMMITTED`, informing the worker honestly.
        """
        previous = self.state
        if self.visit.status != VisitStatus.CONFIRMED:
            raise InvalidTransitionError(
                "Cannot process persistence result for an unconfirmed visit draft "
                f"(status={self.visit.status.value}, state={self.state.value})."
            )

        actions: list[StateMachineAction] = []
        self.awaiting_persistence = False

        if accepted:
            self.visit.status = VisitStatus.COMMITTED
            self.visit.record_id = record_id or self.visit.record_id or f"rec_{uuid.uuid4().hex[:12]}"
            self.visit.updated_at = utc_now_iso()
            self.persistence_error = None
            self._transition(
                ConversationState.COMMITTED, "persistence_accepted", actions
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.VISIT_COMMITTED,
                    payload={
                        "record_id": self.visit.record_id,
                        "visit_record": self.visit.to_contract_payload(),
                    },
                )
            )
            spoken = _COMMITTED_MESSAGES[self.active_language]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": spoken, "language": self.active_language},
                )
            )
            return self._result(
                previous,
                actions,
                spoken_text=spoken,
                metadata={"persisted": True, "record_id": self.visit.record_id},
            )

        # Persistence rejected / failed: keep status='confirmed', stay out of COMMITTED
        self.persistence_error = error or "Persistence layer did not acknowledge save."
        actions.append(
            StateMachineAction(
                action_type=ActionType.PERSISTENCE_REJECTED,
                priority="high",
                payload={
                    "visit_draft_id": self.visit.visit_draft_id,
                    "status": self.visit.status.value,
                    "error": self.persistence_error,
                    "retryable": True,
                },
            )
        )
        spoken = _PERSISTENCE_FAILED_MESSAGES[self.active_language]
        actions.append(
            StateMachineAction(
                action_type=ActionType.SPEAK,
                payload={"text": spoken, "language": self.active_language},
            )
        )
        return self._result(
            previous,
            actions,
            spoken_text=spoken,
            metadata={"persisted": False, "error": self.persistence_error},
        )

    def retry_persistence(self) -> TransitionResult:
        """Re-emit `persistence_requested` for an already-confirmed unsaved draft."""
        previous = self.state
        if self.visit.status != VisitStatus.CONFIRMED:
            raise InvalidTransitionError(
                "Only a worker-confirmed record can retry persistence."
            )
        self.awaiting_persistence = True
        actions = [
            StateMachineAction(
                action_type=ActionType.PERSISTENCE_REQUESTED,
                priority="high",
                payload={
                    "session_id": self.session_id,
                    "visit_record": self.visit.to_contract_payload(),
                    "danger_alerts": [a.model_dump(mode="json") for a in self._danger_alerts],
                    "is_retry": True,
                },
            )
        ]
        return self._result(previous, actions, metadata={"is_retry": True})

    # -- Safety-Critical Danger Sign Interrupt -------------------------------

    def handle_danger_detection(
        self,
        detection: DangerAlertInput | list[DangerAlertInput],
        *,
        language: str | None = None,
    ) -> TransitionResult:
        """High-priority interrupt reachable from ANY active state.

        - Immediately transitions to DANGER_ESCALATION (saving `return_state`).
        - Emits critical `danger_alert` + urgent PHC referral speech.
        - Idempotent per `canonical_id` within a session: duplicate partial/final
          detections update evidence without spamming duplicate alerts or speech.
        """
        previous = self.state
        detections = detection if isinstance(detection, list) else [detection]
        if not detections:
            return self._result(previous, [], metadata={"deduplicated": True})

        if language:
            self.set_language(language)
        elif detections[0].language:
            self.set_language(detections[0].language)

        actions: list[StateMachineAction] = []
        new_records: list[DangerAlertRecord] = []
        updated_existing: list[str] = []
        now = utc_now_iso()

        for item in detections:
            cid = item.canonical_id
            if cid in self._danger_index_by_canonical:
                idx = self._danger_index_by_canonical[cid]
                existing = self._danger_alerts[idx]
                phrase = item.matched_phrase.strip()
                new_history = list(existing.evidence_history)
                new_evidence = existing.evidence
                if phrase and phrase not in new_history:
                    new_history.append(phrase)
                    # Prefer final/richer phrase as primary evidence
                    if not item.is_partial or len(phrase) > len(new_evidence):
                        new_evidence = phrase
                ref = existing.guideline_reference or item.guideline_reference
                ben_id = existing.beneficiary_id or self.visit.beneficiary_id
                self._danger_alerts[idx] = existing.model_copy(
                    update={
                        "evidence": new_evidence,
                        "evidence_history": new_history,
                        "guideline_reference": ref,
                        "beneficiary_id": ben_id,
                        "updated_at": now,
                    }
                )
                updated_existing.append(cid)
                continue

            phrase = item.matched_phrase.strip()
            record = DangerAlertRecord(
                alert_id=item.alert_id or f"alert_{uuid.uuid4().hex[:12]}",
                session_id=self.session_id,
                visit_draft_id=self.visit.visit_draft_id,
                beneficiary_id=self.visit.beneficiary_id,
                canonical_id=cid,
                category=item.category,
                display_name=item.display_name or cid,
                evidence=phrase,
                evidence_history=[phrase] if phrase else [],
                guideline_reference=item.guideline_reference,
                severity=item.severity,
                detected_at=now,
                updated_at=now,
                escalation_language=self.active_language,
                danger_sign_flagged=True,
            )
            self._danger_index_by_canonical[cid] = len(self._danger_alerts)
            self._danger_alerts.append(record)
            new_records.append(record)

            # Danger sign state on the visit draft is strictly monotonic
            self.visit.danger_sign_flagged = True
            if cid not in self.visit.danger_signs:
                self.visit.danger_signs.append(cid)
            self.visit.follow_up_actions = self._merge_unique_list(
                self.visit.follow_up_actions,
                ["Immediate referral to nearest PHC"],
            )
            self.visit.updated_at = now

        # If every detection in this batch was already alerted -> idempotent no-spam return
        if not new_records:
            return self._result(
                previous,
                actions,
                is_urgent=False,
                interrupt_speech=False,
                metadata={
                    "deduplicated": True,
                    "updated_canonical_ids": updated_existing,
                },
            )

        # Save origin return_state (without overwriting if already inside DANGER_ESCALATION)
        if self.state != ConversationState.DANGER_ESCALATION:
            self.return_state = self.state

        self._transition(
            ConversationState.DANGER_ESCALATION,
            "verified_danger_sign_detected",
            actions,
            priority="critical",
        )

        for record in new_records:
            actions.append(
                StateMachineAction(
                    action_type=ActionType.DANGER_ALERT,
                    priority="critical",
                    payload=record.model_dump(mode="json"),
                )
            )

        actions.append(
            StateMachineAction(
                action_type=ActionType.DRAFT_UPDATED,
                priority="high",
                payload={
                    "changed_fields": ["danger_signs", "danger_sign_flagged", "follow_up_actions"],
                    "visit_record": self.visit.to_contract_payload(),
                },
            )
        )

        primary_input = next(
            (d for d in detections if d.canonical_id == new_records[0].canonical_id),
            detections[0],
        )
        urgent_text = generate_urgent_referral_text(self.active_language, primary_input)
        actions.append(
            StateMachineAction(
                action_type=ActionType.SPEAK_URGENT,
                priority="critical",
                payload={
                    "text": urgent_text,
                    "language": self.active_language,
                    "interrupt": True,
                    "canonical_ids": [r.canonical_id for r in new_records],
                },
            )
        )

        return self._result(
            previous,
            actions,
            spoken_text=urgent_text,
            is_urgent=True,
            interrupt_speech=True,
            metadata={
                "deduplicated": False,
                "new_alert_ids": [r.alert_id for r in new_records],
                "return_state": self.return_state.value if self.return_state else None,
            },
        )

    def acknowledge_danger_alert(self, alert_id: str | None = None) -> list[DangerAlertRecord]:
        """Mark one or all danger alerts acknowledged while preserving immutable history."""
        now = utc_now_iso()
        for idx, alert in enumerate(self._danger_alerts):
            if alert_id is None or alert.alert_id == alert_id:
                self._danger_alerts[idx] = alert.model_copy(
                    update={"acknowledged": True, "status": "acknowledged", "updated_at": now}
                )
        return self.danger_alerts

    def resume_after_danger(self) -> TransitionResult:
        """Resume the visit workflow after urgent danger escalation while preserving alerts."""
        previous = self.state
        actions: list[StateMachineAction] = []
        if self.state != ConversationState.DANGER_ESCALATION:
            return self._result(previous, actions)

        target = self.return_state or ConversationState.GATHERING_NOTES
        self.return_state = None

        if target in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
        ):
            # Re-read record so the newly set danger_sign_flagged is explicitly read aloud
            read_back = self._enter_read_back(actions, reason="resumed_after_danger_escalation")
            return self._result(previous, actions, spoken_text=read_back)

        if target == ConversationState.IDLE:
            target = ConversationState.GATHERING_NOTES

        self._transition(target, "resumed_after_danger_escalation", actions)

        if target == ConversationState.CLARIFICATION_REQUIRED and self.pending_clarifications:
            prompt = generate_clarification_text(self.pending_clarifications, self.active_language)
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": prompt, "language": self.active_language},
                )
            )
            return self._result(previous, actions, spoken_text=prompt)

        return self._result(previous, actions)

    def handle_barge_in(self) -> TransitionResult:
        """Handle worker barge-in without losing draft fields or danger alerts."""
        previous = self.state
        # Clear stale read-back text reference; keep workflow ready for interrupting turn
        self.last_read_back_text = None
        return self._result(previous, [], metadata={"barge_in_handled": True})

    def abandon_visit(self) -> TransitionResult:
        """Mark visit workflow abandoned while strictly preserving all danger alerts."""
        previous = self.state
        actions: list[StateMachineAction] = []
        self.abandoned = True
        self.awaiting_persistence = False
        if self.state != ConversationState.COMMITTED:
            self._transition(ConversationState.IDLE, "visit_abandoned", actions)
        return self._result(
            previous,
            actions,
            metadata={
                "abandoned": True,
                "danger_alerts_preserved": len(self._danger_alerts),
            },
        )
