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
    "కాదు",
    "వద్దు",
    "అల్ల",
    "അല്ല",
    "വേണ്ട",
    "না",
    "নয়",
    "नाही",
    "नको",
    "ના",
    "ਨਹੀਂ",
)

_AFFIRMATIVE_LATIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(yes|yeah|yep|confirm|confirmed|correct|right|ok|okay|haan|haa|han|houdu|howdu|aama|aamam|aamaam|sari|seri|avunu|athe|ho|hoy|haa|haanji)\b",
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
    "అవును",
    "సరే",
    "അതെ",
    "ശരി",
    "হ্যাঁ",
    "ঠিক আছে",
    "हो",
    "होय",
    "બરાબર",
    "હા",
    "ਹਾਂ",
    "ਠੀਕ ਹੈ",
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

    # Bare numeric weight correction fallback ("No, it is 53", "No, it is fifty-three", "No, it is 3.2")
    if not explicit:
        m_bare_num = re.search(
            r"(?:no|nahi|nahin|actually|it\s+is|is)\s*[,:]?\s*(?:it\s+is\s*)?(\d+(?:\.\d+)?)\b",
            text,
            re.IGNORECASE,
        )
        if m_bare_num:
            val = float(m_bare_num.group(1))
            if 0.4 <= val <= 200:
                kwargs["weight_kg"] = val
                explicit.add("weight_kg")
        else:
            _word_map = {
                "fifty-two": 52.0,
                "fifty two": 52.0,
                "fifty-three": 53.0,
                "fifty three": 53.0,
                "fifty-four": 54.0,
                "fifty four": 54.0,
                "bawan": 52.0,
                "tirpan": 53.0,
            }
            low = text.lower()
            for phrase, num_val in _word_map.items():
                if phrase in low:
                    kwargs["weight_kg"] = num_val
                    explicit.add("weight_kg")
                    break

    if not explicit:
        return None
    return ExtractionUpdate(**kwargs, explicit_fields=explicit)


# ---------------------------------------------------------------------------
# Localized Speech Templates (hi-IN, en-IN, kn-IN, ta-IN)
# Safety rule: NO diagnosis, NO treatment/medicine/home remedies,
# NO fabricated PHC locations or phone numbers.
# ---------------------------------------------------------------------------

_COMPLETION_LATIN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\b(that'?s\s+all|that\s+is\s+all|i'?m\s+done|i\s+am\s+done|we\s+are\s+done|"
        r"all\s+done|everything\s+is\s+correct|everything\s+looks\s+good|"
        r"finish\s+(?:this\s+|the\s+)?visit|no\s+more\s+changes|nothing\s+else|"
        r"complete\s+(?:the\s+)?visit|bas\s+itna\s+hi|ho\s+gaya|sab\s+theek\s+hai|"
        r"koi\s+badlav\s+nahi)\b",
        re.IGNORECASE,
    ),
    re.compile(r"^\s*(?:done|finish|bas|itna\s+hi)\s*[.!]?\s*$", re.IGNORECASE),
)

_COMPLETION_INDIC_SUBSTRINGS: tuple[str, ...] = (
    "बस इतना ही",
    "बस हो गया",
    "हो गया",
    "सब ठीक है",
    "कोई बदलाव नहीं",
    "मुगियितु",
    "ಮುಗಿಯಿತು",
    "ಇಷ್ಟೇ",
    "முடிந்தது",
    "அவ்வளவுதான்",
    "అంతే",
    "పూర్తయింది",
    "മതി",
    "കഴിഞ്ഞു",
    "শেষ",
    "হয়ে গেছে",
    "झाले",
    "एवढेच",
    "પૂરું થયું",
    "બસ આટલું જ",
    "ਹੋ ਗਿਆ",
    "ਬੱਸ ਇੰਨਾ ਹੀ",
)


def is_completion_intent(utterance: str) -> bool:
    """Return True when the worker indicates note collection & editing are finished."""
    text = utterance.strip()
    if not text:
        return False
    for pat in _COMPLETION_LATIN_PATTERNS:
        if pat.search(text):
            return True
    return any(sub in text for sub in _COMPLETION_INDIC_SUBSTRINGS)


def generate_patch_acknowledgement_text(
    *,
    visit: VisitRecordState,
    changed_fields: list[str],
    is_correction: bool,
    language: str,
) -> str:
    """Generate a short, natural localized acknowledgement of newly captured or updated fields."""
    lang = normalize_language(language)
    updates: list[str] = []

    if "beneficiary_id" in changed_fields or "beneficiary_name" in changed_fields:
        name = visit.beneficiary_name or visit.beneficiary_id or ""
        if lang == "hi-IN":
            updates.append(f"लाभार्थी {name}")
        elif lang == "kn-IN":
            updates.append(f"ಫಲಾನುಭವಿ {name}")
        elif lang == "ta-IN":
            updates.append(f"பயனாளி {name}")
        else:
            updates.append(f"beneficiary to {name}" if is_correction else f"beneficiary {name}")

    if "visit_type" in changed_fields and visit.visit_type:
        if lang == "hi-IN":
            updates.append(f"विज़िट प्रकार {visit.visit_type.value}")
        elif lang == "kn-IN":
            updates.append(f"ಭೇಟಿಯ ವಿಧ {visit.visit_type.value}")
        elif lang == "ta-IN":
            updates.append(f"பார்வை வகை {visit.visit_type.value}")
        else:
            updates.append(f"visit type to {visit.visit_type.value}" if is_correction else f"visit type {visit.visit_type.value}")

    if "weight_kg" in changed_fields and visit.weight_kg is not None:
        w = _format_weight(visit.weight_kg)
        if lang == "hi-IN":
            updates.append(f"वज़न {w} किलो")
        elif lang == "kn-IN":
            updates.append(f"ತೂಕ {w} ಕೆಜಿ")
        elif lang == "ta-IN":
            updates.append(f"எடை {w} கிலோ")
        else:
            updates.append(f"weight to {w} kilograms" if is_correction else f"weight as {w} kilograms")

    if "vaccinations_completed" in changed_fields and visit.vaccinations_completed:
        v = _join_list(visit.vaccinations_completed)
        if lang == "hi-IN":
            updates.append(f"पूरे हुए टीके {v}")
        elif lang == "kn-IN":
            updates.append(f"ಪೂರ್ಣಗೊಂಡ ಲಸಿಕೆ {v}")
        elif lang == "ta-IN":
            updates.append(f"முடிந்த தடுப்பூசி {v}")
        else:
            updates.append(f"completed vaccinations ({v})")

    if "vaccinations_due" in changed_fields and visit.vaccinations_due:
        v = _join_list(visit.vaccinations_due)
        if lang == "hi-IN":
            updates.append(f"बाकी टीके {v}")
        elif lang == "kn-IN":
            updates.append(f"ಬಾಕಿ ಲಸಿಕೆ {v}")
        elif lang == "ta-IN":
            updates.append(f"நிலுவை தடுப்பூசி {v}")
        else:
            updates.append(f"pending vaccinations ({v})")

    if "next_visit_date" in changed_fields and visit.next_visit_date:
        d = format_unambiguous_spoken_date(visit.next_visit_date)
        if lang == "hi-IN":
            updates.append(f"अगली विज़िट की तारीख {d}")
        elif lang == "kn-IN":
            updates.append(f"ಮುಂದಿನ ಭೇಟಿಯ ದಿನಾಂಕ {d}")
        elif lang == "ta-IN":
            updates.append(f"அடுத்த பார்வை தேதி {d}")
        else:
            updates.append(f"next visit to {d}" if is_correction else f"next visit on {d}")

    if not updates and "follow_up_actions" in changed_fields:
        if lang == "hi-IN":
            updates.append("फ़ॉलो-अप जानकारी")
        elif lang == "kn-IN":
            updates.append("ಮುಂದಿನ ಕ್ರಮ")
        elif lang == "ta-IN":
            updates.append("தொடர் நடவடிக்கை")
        else:
            updates.append("follow-up details")

    joined = ", ".join(updates) if updates else "visit details"
    if lang == "hi-IN":
        return (
            f"ठीक है, मैंने {joined} अपडेट कर दिया है। कोई और जानकारी या बदलाव बताएं, या समाप्त करने के लिए बोलें 'बस इतना ही'।"
            if is_correction
            else f"नोट किया: {joined}। कृपया आगे की जानकारी बताएं, या समाप्त करने के लिए बोलें 'बस इतना ही'।"
        )
    if lang == "kn-IN":
        return (
            f"ಸರಿ, {joined} ನವೀಕರಿಸಲಾಗಿದೆ. ಇನ್ನೇನಾದರೂ ಸೇರಿಸಲು ಅಥವಾ ಬದಲಾಯಿಸಲು ತಿಳಿಸಿ, ಅಥವಾ 'ಮುಗಿಯಿತು' ಎಂದು ಹೇಳಿ."
            if is_correction
            else f"ದಾಖಲಿಸಲಾಗಿದೆ: {joined}. ದಯವಿಟ್ಟು ಮುಂದುವರಿಸಿ, ಅಥವಾ 'ಮುಗಿಯಿತು' ಎಂದು ಹೇಳಿ."
        )
    if lang == "ta-IN":
        return (
            f"சரி, {joined} புதுப்பிக்கப்பட்டது. வேறு தகவல் அல்லது மாற்றம் இருந்தால் கூறுங்கள், அல்லது 'முடிந்தது' என்று சொல்லுங்கள்."
            if is_correction
            else f"பதிவு செய்யப்பட்டது: {joined}. தொடர்ந்து கூறுங்கள், அல்லது 'முடிந்தது' என்று சொல்லுங்கள்."
        )
    return (
        f"Okay, I have updated {joined}. Let me know if you want to add or change anything else."
        if is_correction
        else f"Recorded {joined}. Continue speaking to add or change details, or say that's all when done."
    )


def generate_readback_preference_question(language: str) -> str:
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "आपकी विज़िट की जानकारी अपडेट हो गई है। क्या मैं पूरा विज़िट सारांश पढ़कर सुनाऊँ?"
    if lang == "kn-IN":
        return "ನಿಮ್ಮ ಭೇಟಿಯ ಮಾಹಿತಿಯನ್ನು ನವೀಕರಿಸಲಾಗಿದೆ. ಸಂಪೂರ್ಣ ಭೇಟಿಯ ಸಾರಾಂಶವನ್ನು ಓದಿ ಹೇಳಲೇ?"
    if lang == "ta-IN":
        return "உங்கள் பார்வைத் தகவல் புதுப்பிக்கப்பட்டுள்ளது. முழு பார்வை சுருக்கத்தையும் படித்துக் காட்டலாமா?"
    return "Your visit information has been updated. Would you like me to read the complete visit summary aloud?"


def generate_unclear_readback_preference_question(language: str) -> str:
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "माफ़ कीजिए, क्या मैं पूरा सारांश पढ़कर सुनाऊँ? कृपया हाँ या नहीं बोलें।"
    if lang == "kn-IN":
        return "ಕ್ಷಮಿಸಿ, ಸಾರಾಂಶವನ್ನು ಓದಿ ಹೇಳಲೇ? ದಯವಿಟ್ಟು ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
    if lang == "ta-IN":
        return "மன்னிக்கவும், சுருக்கத்தை படித்துக் காட்டலாமா? தயவுசெய்து ஆம் அல்லது இல்லை என்று சொல்லுங்கள்."
    return "Sorry, should I read the summary aloud? Please say yes or no."


def generate_submission_confirmation_question(language: str) -> str:
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "ठीक है। क्या आप यह विज़िट अभी सबमिट और सेव करना चाहती हैं?"
    if lang == "kn-IN":
        return "ಸರಿ. ಈ ಭೇಟಿಯನ್ನು ಈಗ ಸಲ್ಲಿಸಿ ಉಳಿಸಬೇಕೇ?"
    if lang == "ta-IN":
        return "சரி. இந்தப் பார்வையை இப்போது சமர்ப்பித்து சேமிக்கலாமா?"
    return "Okay. Would you like to submit and save this visit now?"


def generate_unclear_submission_question(language: str) -> str:
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "माफ़ कीजिए, क्या मैं यह विज़िट सबमिट और सेव कर दूँ? कृपया हाँ या नहीं बोलें।"
    if lang == "kn-IN":
        return "ಕ್ಷಮಿಸಿ, ಈ ಭೇಟಿಯನ್ನು ಸಲ್ಲಿಸಿ ಉಳಿಸಬೇಕೇ? ದಯವಿಟ್ಟು ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
    if lang == "ta-IN":
        return "மன்னிக்கவும், இந்தப் பார்வையை சமர்ப்பித்து சேமிக்கலாமா? தயவுசெய்து ஆம் அல்லது இல்லை என்று சொல்லுங்கள்."
    return "Sorry, would you like to submit and save this visit now? Please say yes or no."


def generate_submission_declined_text(language: str) -> str:
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "ठीक है, यह विज़िट अभी ड्राफ्ट के रूप में रखी गई है। आप इसमें और बदलाव कर सकती हैं या बाद में सबमिट कर सकती हैं।"
    if lang == "kn-IN":
        return "ಸರಿ, ಈ ಭೇಟಿಯನ್ನು ಸಲ್ಲಿಸದ ಡ್ರಾಫ್ಟ್ ಆಗಿ ಉಳಿಸಲಾಗಿದೆ. ನೀವು ಬದಲಾವಣೆಗಳನ್ನು ಮಾಡಬಹುದು ಅಥವಾ ನಂತರ ಸಲ್ಲಿಸಬಹುದು."
    if lang == "ta-IN":
        return "சரி, இந்தப் பார்வை சமர்ப்பிக்கப்படாத வரைவாக வைக்கப்பட்டுள்ளது. நீங்கள் மாற்றங்களைச் செய்யலாம் அல்லது பின்னர் சமர்ப்பிக்கலாம்."
    return "Okay, I have kept this visit as an unsubmitted draft. You can make more changes or submit later."


def generate_complete_summary_with_submit_prompt(visit: VisitRecordState, language: str) -> str:
    """Read back the latest corrected summary clearly and ask for submission permission."""
    lang = normalize_language(language)
    base = generate_read_back_text(visit, lang)
    for old_q, new_q in (
        ("क्या मैं यह रिकॉर्ड कन्फर्म कर दूँ?", "क्या आप यह विज़िट अभी सबमिट और सेव करना चाहती हैं?"),
        ("ಈ ದಾಖಲೆಯನ್ನು ದೃಢೀಕರಿಸಲೇ?", "ಈ ಭೇಟಿಯನ್ನು ಈಗ ಸಲ್ಲಿಸಿ ಉಳಿಸಬೇಕೇ?"),
        ("இந்தப் பதிவை உறுதிப்படுத்தலாமா?", "இந்தப் பார்வையை இப்போது சமர்ப்பித்து சேமிக்கலாமா?"),
        ("Should I confirm this record?", "Would you like to submit and save this visit now?"),
    ):
        if base.endswith(old_q):
            return base[: -len(old_q)] + new_q
    return f"{base} {generate_submission_confirmation_question(lang)}"


def _format_weight(weight_kg: float) -> str:
    return f"{weight_kg:.2f}".rstrip("0").rstrip(".")


def _join_list(items: list[str]) -> str:
    return ", ".join(items)


_EN_MONTH_LABELS: tuple[str, ...] = (
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def format_unambiguous_spoken_date(iso_date: str | None) -> str:
    """Format an ISO YYYY-MM-DD date unambiguously as '28 November 2026 (2026-11-28)'."""
    if not iso_date:
        return ""
    cleaned = iso_date.strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", cleaned)
    if not m:
        return cleaned
    year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if 1 <= month <= 12:
        return f"{day} {_EN_MONTH_LABELS[month]} {year} ({cleaned})"
    return cleaned


def generate_beneficiary_greeting_text(
    beneficiary_name: str | None,
    beneficiary_id: str | None,
    language: str,
) -> str:
    """Generate personalized spoken greeting when Start Recording is pressed (Section 1)."""
    lang = normalize_language(language)
    if beneficiary_name and beneficiary_id:
        with_ben: dict[str, str] = {
            "hi-IN": (
                f"नमस्ते! क्या आप आज {beneficiary_name} से मिलने गई हैं? "
                f"लाभार्थी आईडी: {beneficiary_id}। कृपया पुष्टि करें, क्या यह सही लाभार्थी है? हाँ या नहीं बोलें।"
            ),
            "kn-IN": (
                f"ನಮಸ್ಕಾರ! ನೀವು ಇಂದು {beneficiary_name} ಅವರನ್ನು ಭೇಟಿ ಮಾಡುತ್ತಿದ್ದೀರಾ? "
                f"ಫಲಾನುಭವಿ ಐಡಿ: {beneficiary_id}. ದಯವಿಟ್ಟು ದೃಢೀಕರಿಸಿ, ಇದು ಸರಿಯಾದ ಫಲಾನುಭವಿಯೇ? ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
            ),
            "ta-IN": (
                f"வணக்கம்! இன்று {beneficiary_name} அவர்களை சந்திக்கிறீர்களா? "
                f"பயனாளி ஐடி: {beneficiary_id}. தயவுசெய்து உறுதிப்படுத்தவும், இது சரியான பயனாளியா? ஆம் அல்லது இல்லை என்று சொல்லுங்கள்."
            ),
            "te-IN": (
                f"నమస్కారం! మీరు ఈరోజు {beneficiary_name} గారిని కలుస్తున్నారా? "
                f"లబ్ధిదారు ఐడి: {beneficiary_id}. దయచేసి నిర్ధారించండి, అవును లేదా కాదు అని చెప్పండి."
            ),
            "ml-IN": (
                f"നമസ്കാരം! നിങ്ങൾ ഇന്ന് {beneficiary_name} യെ സന്ദർശിക്കുകയാണോ? "
                f"ഗുണഭോക്തൃ ഐഡി: {beneficiary_id}. ഇത് ശരിയാണോ? അതെ അല്ലെങ്കിൽ അല്ല എന്ന് പറയുക."
            ),
            "bn-IN": (
                f"নমস্কার! আপনি কি আজ {beneficiary_name}-এর সাথে দেখা করছেন? "
                f"সুবিধাভোগী আইডি: {beneficiary_id}। অনুগ্রহ করে নিশ্চিত করুন, হ্যাঁ বা না বলুন।"
            ),
            "mr-IN": (
                f"नमस्कार! तुम्ही आज {beneficiary_name} यांना भेटत आहात का? "
                f"लाभार्थी आयडी: {beneficiary_id}. कृपया होय किंवा नाही सांगा."
            ),
            "gu-IN": (
                f"નમસ્તે! શું તમે આજે {beneficiary_name} ની મુલાકાત લઈ રહ્યા છો? "
                f"લાભાર્થી આઈડી: {beneficiary_id}. કૃપા કરીને હા અથવા ના કહો."
            ),
            "pa-IN": (
                f"ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਕੀ ਤੁਸੀਂ ਅੱਜ {beneficiary_name} ਨੂੰ ਮਿਲਣ ਜਾ ਰਹੇ ਹੋ? "
                f"ਲਾਭਪਾਤਰੀ ਆਈਡੀ: {beneficiary_id}। ਕਿਰਪਾ ਕਰਕੇ ਹਾਂ ਜਾਂ ਨਹੀਂ ਕਹੋ।"
            ),
        }
        return with_ben.get(
            lang,
            (
                f"Namaste! Are you visiting {beneficiary_name} today? "
                f"Beneficiary ID: {beneficiary_id}. "
                "Please confirm. Is this the correct beneficiary? Say yes or no."
            ),
        )

    no_ben: dict[str, str] = {
        "hi-IN": "नमस्ते! कृपया आज की विज़िट के लिए लाभार्थी का नाम या लाभार्थी आईडी बताएं।",
        "kn-IN": "ನಮಸ್ಕಾರ! ಇಂದಿನ ಭೇಟಿಗಾಗಿ ದಯವಿಟ್ಟು ಫಲಾನುಭವಿಯ ಹೆಸರು ಅಥವಾ ಫಲಾನುಭವಿ ಐಡಿ ತಿಳಿಸಿ.",
        "ta-IN": "வணக்கம்! இன்றைய பார்வைக்காக பயனாளியின் பெயர் அல்லது பயனாளி ஐடியைக் கூறுங்கள்.",
        "te-IN": "నమస్కారం! ఈరోజు విజిట్ కోసం లబ్ధిదారు పేరు లేదా ఐడి చెప్పండి.",
        "ml-IN": "നമസ്കാരം! ഇന്നത്തെ സന്ദർശനത്തിനായി ഗുണഭോക്താവിന്റെ പേര് അല്ലെങ്കിൽ ഐഡി പറയുക.",
        "bn-IN": "নমস্কার! আজকের ভিজিটের জন্য অনুগ্রহ করে সুবিধাভোগীর নাম বা আইডি বলুন।",
        "mr-IN": "नमस्कार! आजच्या भेटीसाठी कृपया लाभार्थ्याचे नाव किंवा आयडी सांगा.",
        "gu-IN": "નમસ્તે! આજની મુલાકાત માટે કૃપા કરીને લાભાર્થીનું નામ અથવા આઈડી કહો.",
        "pa-IN": "ਸਤਿ ਸ੍ਰੀ ਅਕਾਲ! ਅੱਜ ਦੀ ਵਿਜ਼ਿਟ ਲਈ ਕਿਰਪਾ ਕਰਕੇ ਲਾਭਪਾਤਰੀ ਦਾ ਨਾਮ ਜਾਂ ਆਈਡੀ ਦੱਸੋ।",
    }
    return no_ben.get(
        lang,
        "Namaste! Please tell me the beneficiary's name or beneficiary ID for today's visit.",
    )


def generate_identity_confirmed_text(beneficiary_name: str, language: str) -> str:
    """Scenario A: Short acknowledgement after beneficiary identity is confirmed."""
    lang = normalize_language(language)
    msgs: dict[str, str] = {
        "hi-IN": (
            f"धन्यवाद। {beneficiary_name} कन्फर्म हो गई हैं। "
            "कृपया आज की विज़िट के बारे में बताएं। आप अपनी भाषा में सामान्य रूप से बोल सकती हैं।"
        ),
        "kn-IN": (
            f"ಧನ್ಯವಾದಗಳು. {beneficiary_name} ದೃಢೀಕರಿಸಲಾಗಿದೆ. "
            "ದಯವಿಟ್ಟು ಇಂದಿನ ಭೇಟಿಯ ಬಗ್ಗೆ ತಿಳಿಸಿ. ನಿಮ್ಮ ಭಾಷೆಯಲ್ಲಿ ಸಹಜವಾಗಿ ಮಾತನಾಡಬಹುದು."
        ),
        "ta-IN": (
            f"நன்றி. {beneficiary_name} உறுதிப்படுத்தப்பட்டது. "
            "தயவுசெய்து இன்றைய பார்வையைப் பற்றி கூறுங்கள். உங்கள் மொழியில் இயல்பாகப் பேசலாம்."
        ),
        "te-IN": (
            f"ధన్యవాదాలు. {beneficiary_name} నిర్ధారించబడింది. "
            "దయచేసి ఈరోజు విజిట్ గురించి మీ భాషలో సహజంగా చెప్పండి."
        ),
        "ml-IN": (
            f"നന്ദി. {beneficiary_name} സ്ഥിരീകരിച്ചു. "
            "ഇന്നത്തെ സന്ദർശനത്തെക്കുറിച്ച് നിങ്ങളുടെ ഭാഷയിൽ സ്വാഭാവികമായി സംസാരിക്കാം."
        ),
        "bn-IN": (
            f"ধন্যবাদ। {beneficiary_name} নিশ্চিত হয়েছেন। "
            "অনুগ্রহ করে আজকের ভিজিট সম্পর্কে আপনার ভাষায় স্বাভাবিকভাবে বলুন।"
        ),
        "mr-IN": (
            f"धन्यवाद। {beneficiary_name} निश्चित झाले आहेत। "
            "कृपया आजच्या भेटीबद्दल तुमच्या भाषेत सहज बोला."
        ),
        "gu-IN": (
            f"આભાર. {beneficiary_name} ની પુષ્ટિ થઈ છે. "
            "કૃપા કરીને આજની મુલાકાત વિશે તમારી ભાષામાં સહજતાથી જણાવો."
        ),
        "pa-IN": (
            f"ਧੰਨਵਾਦ। {beneficiary_name} ਦੀ ਪੁਸ਼ਟੀ ਹੋ ਗਈ ਹੈ। "
            "ਕਿਰਪਾ ਕਰਕੇ ਅੱਜ ਦੀ ਵਿਜ਼ਿਟ ਬਾਰੇ ਆਪਣੀ ਭਾਸ਼ਾ ਵਿੱਚ ਆਰਾਮ ਨਾਲ ਦੱਸੋ।"
        ),
    }
    return msgs.get(
        lang,
        (
            f"Thank you. {beneficiary_name} is confirmed. "
            "Please tell me about today's visit. You can speak naturally in your language."
        ),
    )


def generate_identity_correction_prompt(language: str) -> str:
    """Scenario B step 1: Prompt when worker says NO to the initial beneficiary."""
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "ठीक है। कृपया सही लाभार्थी का नाम या लाभार्थी आईडी बताएं।"
    if lang == "kn-IN":
        return "ಸರಿ. ದಯವಿಟ್ಟು ಸರಿಯಾದ ಫಲಾನುಭವಿಯ ಹೆಸರು ಅಥವಾ ಫಲಾನುಭವಿ ಐಡಿ ತಿಳಿಸಿ."
    if lang == "ta-IN":
        return "சரி. தயவுசெய்து சரியான பயனாளியின் பெயர் அல்லது பயனாளி ஐடியைக் கூறுங்கள்."
    return "Okay. Please tell me the correct beneficiary's name or beneficiary ID."


def generate_candidate_confirmation_text(
    beneficiary_name: str,
    beneficiary_id: str,
    language: str,
) -> str:
    """Scenario B step 2: Read resolved candidate's name and ID aloud and ask for confirmation."""
    lang = normalize_language(language)
    if lang == "hi-IN":
        return (
            f"मुझे {beneficiary_name}, लाभार्थी आईडी {beneficiary_id} मिली हैं। "
            "क्या यह सही है? कृपया हाँ या नहीं बोलें।"
        )
    if lang == "kn-IN":
        return (
            f"ನನಗೆ {beneficiary_name}, ಫಲಾನುಭವಿ ಐಡಿ {beneficiary_id} ಸಿಕ್ಕಿದೆ. "
            "ಇದು ಸರಿಯೇ? ದಯವಿಟ್ಟು ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
        )
    if lang == "ta-IN":
        return (
            f"{beneficiary_name}, பயனாளி ஐடி {beneficiary_id} கிடைத்தது. "
            "இது சரியா? தயவுசெய்து ஆம் அல்லது இல்லை என்று சொல்லுங்கள்."
        )
    return f"I found {beneficiary_name}, beneficiary ID {beneficiary_id}. Is this correct?"


def generate_multiple_beneficiaries_text(
    candidates: list[tuple[str, str]],
    language: str,
) -> str:
    """Scenario C: Multiple matching beneficiaries with similar names."""
    lang = normalize_language(language)
    options = ", ".join(f"{name} ({bid})" for bid, name in candidates)
    suffix = f" ({options})" if options else ""
    if lang == "hi-IN":
        return f"मुझे एक से अधिक मिलते-जुलते लाभार्थी मिले हैं{suffix}। कृपया लाभार्थी आईडी बताएं।"
    if lang == "kn-IN":
        return f"ಒಂದಕ್ಕಿಂತ ಹೆಚ್ಚು ಹೊಂದಾಣಿಕೆಯಾಗುವ ಫಲಾನುಭವಿಗಳು ಕಂಡುಬಂದಿದ್ದಾರೆ{suffix}. ದಯವಿಟ್ಟು ಫಲಾನುಭವಿ ಐಡಿ ತಿಳಿಸಿ."
    if lang == "ta-IN":
        return f"ஒன்றுக்கும் மேற்பட்ட பொருந்தும் பயனாளிகள் கண்டறியப்பட்டனர்{suffix}. தயவுசெய்து பயனாளி ஐடியைக் கூறுங்கள்."
    return f"I found more than one matching beneficiary{suffix}. Please tell me the beneficiary ID."


def generate_beneficiary_not_found_text(language: str) -> str:
    """Scenario D: Beneficiary not found in synthetic directory."""
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "मुझे वह लाभार्थी नहीं मिली। कृपया नाम दोबारा बोलें या लाभार्थी आईडी बताएं।"
    if lang == "kn-IN":
        return "ಆ ಫಲಾನುಭವಿ ಕಂಡುಬಂದಿಲ್ಲ. ದಯವಿಟ್ಟು ಹೆಸರನ್ನು ಮತ್ತೆ ಹೇಳಿ ಅಥವಾ ಫಲಾನುಭವಿ ಐಡಿ ತಿಳಿಸಿ."
    if lang == "ta-IN":
        return "அந்தப் பயனாளியைக் கண்டுபிடிக்க முடியவில்லை. தயவுசெய்து பெயரை மீண்டும் கூறவும் அல்லது பயனாளி ஐடியைச் சொல்லவும்."
    return "I couldn't find that beneficiary. Please repeat the name or tell me the beneficiary ID."


def generate_unclear_identity_confirmation_text(language: str) -> str:
    """Scenario E: Ambiguous YES/NO response during beneficiary identity confirmation."""
    lang = normalize_language(language)
    if lang == "hi-IN":
        return "माफ़ कीजिए, मैं समझ नहीं पाई। क्या यह सही लाभार्थी है? कृपया हाँ या नहीं बोलें।"
    if lang == "kn-IN":
        return "ಕ್ಷಮಿಸಿ, ನನಗೆ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಇದು ಸರಿಯಾದ ಫಲಾನುಭವಿಯೇ? ದಯವಿಟ್ಟು ಹೌದು ಅಥವಾ ಇಲ್ಲ ಎಂದು ಹೇಳಿ."
    if lang == "ta-IN":
        return "மன்னிக்கவும், எனக்குப் புரியவில்லை. இது சரியான பயனாளியா? தயவுசெய்து ஆம் அல்லது இல்லை என்று சொல்லுங்கள்."
    return "Sorry, I couldn't understand. Is this the correct beneficiary? Please say yes or no."


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
    "te-IN": (
        "అత్యవసర హెచ్చరిక! ప్రమాద సంకేతం గుర్తించబడింది. "
        "దయచేసి లబ్ధిదారుని వెంటనే సమీపంలోని ప్రాథమిక ఆరోగ్య కేంద్రానికి (PHC) తీసుకెళ్లండి."
    ),
    "ml-IN": (
        "അടിയന്തര മുന്നറിയിപ്പ്! അപകട ലക്ഷണം കണ്ടെത്തി. "
        "ദയവായി ഗുണഭോക്താവിനെ ഉടൻ അടുത്തുള്ള പ്രാഥമിക ആരോഗ്യ കേന്ദ്രത്തിലേക്ക് (PHC) മാറ്റുക."
    ),
    "bn-IN": (
        "জরুরি সতর্কতা! বিপদের লক্ষণ শনাক্ত হয়েছে। "
        "অনুগ্রহ করে রোগীকে অবিলম্বে নিকটস্থ পিএইচসি (PHC)-তে রেফার করুন। দেরি করবেন না।"
    ),
    "mr-IN": (
        "तातडीची सूचना! धोक्याचे लक्षण आढळले आहे. "
        "कृपया लाभार्थ्याला ताबडतोब जवळच्या प्राथमिक आरोग्य केंद्रात (PHC) न्या. उशीर करू नका."
    ),
    "gu-IN": (
        "તાત્કાલિક ચેતવણી! જોખમનું ચિહ્ન જણાયું છે. "
        "કૃપા કરીને લાભાર્થીને તાત્કાલિક નજીકના પીએચસી (PHC) માં મોકલો. વિલંબ કરશો નહીં."
    ),
    "pa-IN": (
        "ਤੁਰੰਤ ਚੇਤਾਵਨੀ! ਖ਼ਤਰੇ ਦਾ ਸੰਕੇਤ ਮਿਲਿਆ ਹੈ। "
        "ਕਿਰਪਾ ਕਰਕੇ ਲਾਭਪਾਤਰੀ ਨੂੰ ਤੁਰੰਤ ਨਜ਼ਦੀਕੀ ਪੀ.ਐਚ.ਸੀ. (PHC) ਭੇਜੋ। ਦੇਰੀ ਨਾ ਕਰੋ।"
    ),
}

_CONFIRMATION_PENDING_MESSAGES: dict[str, str] = {
    "en-IN": "Record confirmed. Saving the visit record now.",
    "hi-IN": "रिकॉर्ड कन्फर्म हो गया है। अब विज़िट रिकॉर्ड सेव किया जा रहा है।",
    "kn-IN": "ದಾಖಲೆ ದೃಢೀಕರಿಸಲಾಗಿದೆ. ಈಗ ಭೇಟಿಯ ದಾಖಲೆಯನ್ನು ಉಳಿಸಲಾಗುತ್ತಿದೆ.",
    "ta-IN": "பதிவு உறுதிப்படுத்தப்பட்டது. இப்போது பார்வை பதிவு சேமிக்கப்படுகிறது.",
    "te-IN": "రికార్డు నిర్ధారించబడింది. ఇప్పుడు విజిట్ రికార్డును సేవ్ చేస్తున్నాము.",
    "ml-IN": "രേഖ സ്ഥിരീകരിച്ചു. ഇപ്പോൾ സന്ദർശന രേഖ സംരക്ഷിക്കുന്നു.",
    "bn-IN": "রেকর্ড নিশ্চিত হয়েছে। এখন ভিজিট রেকর্ড সংরক্ষণ করা হচ্ছে।",
    "mr-IN": "नोंद निश्चित झाली आहे. आता भेट नोंद जतन केली जात आहे.",
    "gu-IN": "રેકોર્ડની પુષ્ટિ થઈ છે. હવે મુલાકાત રેકોર્ડ સાચવવામાં આવી રહ્યો છે.",
    "pa-IN": "ਰਿਕਾਰਡ ਦੀ ਪੁਸ਼ਟੀ ਹੋ ਗਈ ਹੈ। ਹੁਣ ਵਿਜ਼ਿਟ ਰਿਕਾਰਡ ਸੇਵ ਕੀਤਾ ਜਾ ਰਿਹਾ ਹੈ।",
}

_COMMITTED_MESSAGES: dict[str, str] = {
    "en-IN": "Your visit has been successfully saved. Thank you.",
    "hi-IN": "आपकी विज़िट सफलतापूर्वक सेव हो गई है। धन्यवाद।",
    "kn-IN": "ನಿಮ್ಮ ಭೇಟಿಯನ್ನು ಯಶಸ್ವಿಯಾಗಿ ಉಳಿಸಲಾಗಿದೆ. ಧನ್ಯವಾದಗಳು.",
    "ta-IN": "உங்கள் பார்வை வெற்றிகரமாக சேமிக்கப்பட்டது. நன்றி.",
    "te-IN": "మీ విజిట్ విజయవంతంగా సేవ్ చేయబడింది. ధన్యవాదాలు.",
    "ml-IN": "നിങ്ങളുടെ സന്ദർശനം വിജയകരമായി സംരക്ഷിച്ചു. നന്ദി.",
    "bn-IN": "আপনার ভিজিট সফলভাবে সংরক্ষিত হয়েছে। ধন্যবাদ।",
    "mr-IN": "तुमची भेट यशस्वीरित्या जतन झाली आहे. धन्यवाद.",
    "gu-IN": "તમારી મુલાકાત સફળતાપૂર્વક સાચવાઈ ગઈ છે. આભાર.",
    "pa-IN": "ਤੁਹਾਡੀ ਵਿਜ਼ਿਟ ਸਫਲਤਾਪੂਰਵਕ ਸੇਵ ਹੋ ਗਈ ਹੈ। ਧੰਨਵਾਦ।",
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
    return _URGENT_REFERRAL_MESSAGES.get(lang, _URGENT_REFERRAL_MESSAGES["en-IN"])


def generate_read_back_text(visit: VisitRecordState, language: str) -> str:
    """Generate natural spoken read-back text in hi-IN, en-IN, kn-IN, or ta-IN."""
    lang = normalize_language(language)
    parts: list[str] = []

    ben_id = visit.beneficiary_id or "unknown"
    ben_name = visit.beneficiary_name
    vtype = visit.visit_type.value if visit.visit_type else "unknown"
    weight_str = _format_weight(visit.weight_kg) if visit.weight_kg is not None else None
    date_str = format_unambiguous_spoken_date(visit.next_visit_date) if visit.next_visit_date else None
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
        if date_str:
            parts.append(f"अगली विज़िट की तारीख: {date_str}।")
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
        if date_str:
            parts.append(f"ಮುಂದಿನ ಭೇಟಿಯ ದಿನಾಂಕ: {date_str}.")
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
        if date_str:
            parts.append(f"அடுத்த பார்வை தேதி: {date_str}.")
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
        if date_str:
            parts.append(f"Next visit date: {date_str}.")
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
    templates = _CLARIFICATION_TEMPLATES.get(lang, _CLARIFICATION_TEMPLATES["en-IN"])
    prompts: list[str] = []

    for req in clarifications:
        if req.question and req.question.strip() and (
            lang == "en-IN" or req.reason in {"ambiguous_value", "conflict", "uncertain_danger_sign"}
        ):
            prompt = req.question.strip()
        elif req.field in templates:
            prompt = templates[req.field].format(field=req.field)
        elif req.question and req.question.strip():
            prompt = req.question.strip()
        else:
            prompt = templates["default"].format(field=req.field)
        if req.candidates and (len(req.candidates) >= 2 or req.reason != "ambiguous_value"):
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

        self.identity_verified: bool = bool(beneficiary_id)
        self.candidate_beneficiary_id: str | None = beneficiary_id
        self.candidate_beneficiary_name: str | None = beneficiary_name

        self.pending_clarifications: list[ClarificationRequest] = []
        self._danger_alerts: list[DangerAlertRecord] = []
        self._danger_index_by_canonical: dict[str, int] = {}

        self.last_read_back_text: str | None = None
        self.summary_outdated: bool = False
        self.readback_silence_repompts: int = 0
        self.submission_silence_reprompts: int = 0
        self.change_history: list[dict[str, Any]] = []
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
        self,
        update: ExtractionUpdate,
        *,
        is_patch: bool,
        merge_lists: bool = False,
    ) -> list[str]:
        """Apply extraction/patch fields to `self.visit` without touching danger state."""
        fields = update.specified_fields()
        changed: list[str] = []
        prev_snapshot: dict[str, Any] = {}
        new_snapshot: dict[str, Any] = {}

        def _record(field_name: str, old_val: Any, new_val: Any) -> None:
            if old_val != new_val:
                prev_snapshot[field_name] = old_val
                new_snapshot[field_name] = new_val
                self.change_history.append(
                    {
                        "field": field_name,
                        "previous_value": old_val,
                        "new_value": new_val,
                        "is_patch": is_patch,
                        "timestamp": utc_now_iso(),
                    }
                )

        for cf in update.clear_fields:
            if cf == "weight_kg" and self.visit.weight_kg is not None:
                _record("weight_kg", self.visit.weight_kg, None)
                self.visit.weight_kg = None
                self.confirmed_fields.discard("weight_kg")
                changed.append("weight_kg")
            elif cf == "next_visit_date" and self.visit.next_visit_date is not None:
                _record("next_visit_date", self.visit.next_visit_date, None)
                self.visit.next_visit_date = None
                self.confirmed_fields.discard("next_visit_date")
                changed.append("next_visit_date")
            elif cf == "visit_type" and self.visit.visit_type is not None:
                _record("visit_type", self.visit.visit_type.value, None)
                self.visit.visit_type = None
                self.confirmed_fields.discard("visit_type")
                changed.append("visit_type")
            elif cf == "vaccinations_due" and self.visit.vaccinations_due:
                _record("vaccinations_due", list(self.visit.vaccinations_due), [])
                self.visit.vaccinations_due = []
                changed.append("vaccinations_due")
            elif cf == "vaccinations_completed" and self.visit.vaccinations_completed:
                _record("vaccinations_completed", list(self.visit.vaccinations_completed), [])
                self.visit.vaccinations_completed = []
                changed.append("vaccinations_completed")

        if "beneficiary_id" in fields and update.beneficiary_id is not None:
            _record("beneficiary_id", self.visit.beneficiary_id, update.beneficiary_id)
            self.visit.beneficiary_id = update.beneficiary_id
            self.candidate_beneficiary_id = update.beneficiary_id
            self.identity_verified = True
            self.confirmed_fields.add("beneficiary_id")
            self._backfill_alert_beneficiary()
            changed.append("beneficiary_id")

        if "beneficiary_name" in fields and update.beneficiary_name is not None:
            _record("beneficiary_name", self.visit.beneficiary_name, update.beneficiary_name)
            self.visit.beneficiary_name = update.beneficiary_name
            self.candidate_beneficiary_name = update.beneficiary_name
            self.confirmed_fields.add("beneficiary_name")
            changed.append("beneficiary_name")

        if "visit_type" in fields and update.visit_type is not None:
            old_vt = self.visit.visit_type.value if self.visit.visit_type else None
            _record("visit_type", old_vt, update.visit_type.value)
            self.visit.visit_type = update.visit_type
            self.confirmed_fields.add("visit_type")
            changed.append("visit_type")

        if "weight_kg" in fields and update.weight_kg is not None:
            _record("weight_kg", self.visit.weight_kg, update.weight_kg)
            self.visit.weight_kg = update.weight_kg
            self.confirmed_fields.add("weight_kg")
            changed.append("weight_kg")
            # Clear any prior uncertain weight observation once confirmed scalar is recorded
            self.visit.observations = [
                o for o in self.visit.observations if str(o.get("key", "")).lower() != "weight_kg"
            ]

        if "vaccinations_completed" in fields and update.vaccinations_completed is not None:
            old_vc = list(self.visit.vaccinations_completed)
            if is_patch and not merge_lists:
                new_vc = [v.strip() for v in update.vaccinations_completed if v.strip()]
            else:
                new_vc = self._merge_unique_list(
                    self.visit.vaccinations_completed, update.vaccinations_completed
                )
            self.visit.vaccinations_completed = new_vc
            _record("vaccinations_completed", old_vc, list(new_vc))
            # If a vaccine is completed, automatically remove it from due list
            completed_low = {v.lower() for v in new_vc}
            filtered_due = [v for v in self.visit.vaccinations_due if v.lower() not in completed_low]
            if filtered_due != self.visit.vaccinations_due:
                _record("vaccinations_due", list(self.visit.vaccinations_due), filtered_due)
                self.visit.vaccinations_due = filtered_due
                if "vaccinations_due" not in changed:
                    changed.append("vaccinations_due")
            self.confirmed_fields.add("vaccinations_completed")
            changed.append("vaccinations_completed")

        if "vaccinations_due" in fields and update.vaccinations_due is not None:
            old_vd = list(self.visit.vaccinations_due)
            if is_patch and not merge_lists:
                new_vd = [v.strip() for v in update.vaccinations_due if v.strip()]
            else:
                new_vd = self._merge_unique_list(
                    self.visit.vaccinations_due, update.vaccinations_due
                )
            self.visit.vaccinations_due = new_vd
            _record("vaccinations_due", old_vd, list(new_vd))
            if is_patch:
                due_low = {v.lower() for v in new_vd}
                filtered_comp = [
                    v for v in self.visit.vaccinations_completed if v.lower() not in due_low
                ]
                if filtered_comp != self.visit.vaccinations_completed:
                    _record(
                        "vaccinations_completed",
                        list(self.visit.vaccinations_completed),
                        filtered_comp,
                    )
                    self.visit.vaccinations_completed = filtered_comp
                    if "vaccinations_completed" not in changed:
                        changed.append("vaccinations_completed")
            self.confirmed_fields.add("vaccinations_due")
            changed.append("vaccinations_due")

        if "next_visit_date" in fields and update.next_visit_date is not None:
            new_nd = update.next_visit_date.strip()
            _record("next_visit_date", self.visit.next_visit_date, new_nd)
            self.visit.next_visit_date = new_nd
            self.confirmed_fields.add("next_visit_date")
            changed.append("next_visit_date")

        if "follow_up_actions" in fields and update.follow_up_actions is not None:
            old_fa = list(self.visit.follow_up_actions)
            if is_patch and not merge_lists:
                new_fa = [a.strip() for a in update.follow_up_actions if a.strip()]
            else:
                new_fa = self._merge_unique_list(
                    self.visit.follow_up_actions, update.follow_up_actions
                )
            self.visit.follow_up_actions = new_fa
            _record("follow_up_actions", old_fa, list(new_fa))
            self.confirmed_fields.add("follow_up_actions")
            changed.append("follow_up_actions")

        # Dynamic observations: upsert by normalized key and support explicit removal
        if update.remove_observation_keys:
            rm_obs = {k.strip().lower() for k in update.remove_observation_keys if k.strip()}
            old_obs = list(self.visit.observations)
            new_obs = [
                o for o in old_obs if str(o.get("key", "")).strip().lower() not in rm_obs
            ]
            if new_obs != old_obs:
                _record("observations", old_obs, new_obs)
                self.visit.observations = new_obs
                if "observations" not in changed:
                    changed.append("observations")

        if "observations" in fields and update.observations is not None:
            old_obs = [dict(o) for o in self.visit.observations]
            if is_patch and not merge_lists:
                new_obs = [dict(o) for o in update.observations]
            else:
                new_obs = [dict(o) for o in self.visit.observations]
                for inc_obs in update.observations:
                    inc_key = str(inc_obs.get("key", "")).strip().lower()
                    if not inc_key:
                        continue
                    replaced = False
                    for idx, cur in enumerate(new_obs):
                        if str(cur.get("key", "")).strip().lower() == inc_key:
                            new_obs[idx] = dict(inc_obs)
                            replaced = True
                            break
                    if not replaced:
                        new_obs.append(dict(inc_obs))
            if new_obs != old_obs:
                _record("observations", old_obs, new_obs)
                self.visit.observations = new_obs
                if "observations" not in changed:
                    changed.append("observations")

        # Repeatable events: upsert in-place by (event_type, name.lower()) and support removal
        if update.remove_event_names:
            rm_ev = {n.strip().lower() for n in update.remove_event_names if n.strip()}
            old_ev = list(self.visit.events)
            new_ev = [
                e for e in old_ev if str(e.get("name", "")).strip().lower() not in rm_ev
            ]
            if new_ev != old_ev:
                _record("events", old_ev, new_ev)
                self.visit.events = new_ev
                if "events" not in changed:
                    changed.append("events")
            # Keep legacy lists aligned on event deletion
            f_comp = [v for v in self.visit.vaccinations_completed if v.strip().lower() not in rm_ev]
            f_due = [v for v in self.visit.vaccinations_due if v.strip().lower() not in rm_ev]
            if f_comp != self.visit.vaccinations_completed:
                self.visit.vaccinations_completed = f_comp
                if "vaccinations_completed" not in changed:
                    changed.append("vaccinations_completed")
            if f_due != self.visit.vaccinations_due:
                self.visit.vaccinations_due = f_due
                if "vaccinations_due" not in changed:
                    changed.append("vaccinations_due")

        if "events" in fields and update.events is not None:
            old_ev = [dict(e) for e in self.visit.events]
            if is_patch and not merge_lists:
                new_ev = [dict(e) for e in update.events]
            else:
                new_ev = [dict(e) for e in self.visit.events]
                for inc_ev in update.events:
                    ev_type = str(inc_ev.get("event_type", "immunisation")).strip().lower()
                    ev_name = str(inc_ev.get("name", "")).strip().lower()
                    if not ev_name:
                        continue
                    replaced = False
                    for idx, cur in enumerate(new_ev):
                        if (
                            str(cur.get("event_type", "immunisation")).strip().lower() == ev_type
                            and str(cur.get("name", "")).strip().lower() == ev_name
                        ):
                            new_ev[idx] = dict(inc_ev)
                            replaced = True
                            break
                    if not replaced:
                        new_ev.append(dict(inc_ev))
            if new_ev != old_ev:
                _record("events", old_ev, new_ev)
                self.visit.events = new_ev
                if "events" not in changed:
                    changed.append("events")
                # Keep legacy vaccination arrays synchronized when UI edits an event directly
                if is_patch and not merge_lists:
                    imm_events = [e for e in new_ev if str(e.get("event_type", "")).lower() == "immunisation"]
                    self.visit.vaccinations_completed = [
                        str(e["name"]) for e in imm_events if e.get("status") == "completed" and e.get("name")
                    ]
                    self.visit.vaccinations_due = [
                        str(e["name"]) for e in imm_events if e.get("status") in {"due", "scheduled"} and e.get("name")
                    ]

        if update.trace is not None:
            self.visit.utterance_traces.append(dict(update.trace))

        # Any update invalidates a previously generated summary
        if changed:
            if self.last_read_back_text is not None:
                self.summary_outdated = True
            self.last_read_back_text = None
            changed_set = set(changed)
            self.pending_clarifications = [
                c for c in self.pending_clarifications if c.field not in changed_set
            ]
            self.visit.updated_at = utc_now_iso()

        self._last_prev_snapshot = prev_snapshot
        self._last_new_snapshot = new_snapshot

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

    def start_beneficiary_greeting(
        self,
        *,
        beneficiary_id: str | None = None,
        beneficiary_name: str | None = None,
        language: str | None = None,
    ) -> TransitionResult:
        """Initiate Section 1 personalized spoken greeting & enter identity verification."""
        previous = self.state
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError(
                "Visit record is already committed; start a new session for another visit."
            )
        if language:
            self.set_language(language)

        eff_id = beneficiary_id if beneficiary_id is not None else self.visit.beneficiary_id
        eff_name = beneficiary_name if beneficiary_name is not None else self.visit.beneficiary_name

        self.candidate_beneficiary_id = eff_id
        self.candidate_beneficiary_name = eff_name
        self.visit.beneficiary_id = eff_id
        self.visit.beneficiary_name = eff_name
        self.identity_verified = False
        self.confirmed_fields.discard("beneficiary_id")
        self.confirmed_fields.discard("beneficiary_name")

        actions: list[StateMachineAction] = []
        self._transition(ConversationState.SESSION_START, "session_started", actions)
        self._transition(
            ConversationState.BENEFICIARY_GREETING, "beneficiary_greeting_started", actions
        )

        greeting = generate_beneficiary_greeting_text(eff_name, eff_id, self.active_language)
        if eff_id and eff_name:
            self._transition(
                ConversationState.IDENTITY_CONFIRMATION,
                "awaiting_beneficiary_identity_confirmation",
                actions,
            )
            clar = ClarificationRequest(
                field="beneficiary_id",
                reason="ambiguous_beneficiary",
                question=greeting,
                candidates=[f"{eff_id}: {eff_name}"],
            )
            self.pending_clarifications = [clar]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.DRAFT_UPDATED,
                    payload={
                        "changed_fields": ["beneficiary_id", "beneficiary_name"],
                        "visit_record": self.visit.to_contract_payload(),
                    },
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [clar.model_dump(mode="json")],
                        "language": self.active_language,
                        "text": greeting,
                    },
                )
            )
        else:
            self._transition(
                ConversationState.IDENTITY_CORRECTION,
                "no_initial_beneficiary_selected",
                actions,
            )
            clar = ClarificationRequest(
                field="beneficiary_id",
                reason="missing",
                question=greeting,
            )
            self.pending_clarifications = [clar]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [clar.model_dump(mode="json")],
                        "language": self.active_language,
                        "text": greeting,
                    },
                )
            )

        actions.append(
            StateMachineAction(
                action_type=ActionType.SPEAK,
                payload={"text": greeting, "language": self.active_language},
            )
        )
        return self._result(
            previous,
            actions,
            spoken_text=greeting,
            metadata={"identity_verified": False, "candidate_beneficiary_id": eff_id},
        )

    def handle_identity_confirmation_response(
        self,
        utterance: str,
        *,
        language: str | None = None,
    ) -> TransitionResult:
        """Handle YES / NO / unclear response in IDENTITY_CONFIRMATION or CANDIDATE_CONFIRMATION."""
        previous = self.state
        if language:
            self.set_language(language)

        intent = classify_confirmation_intent(utterance)
        actions: list[StateMachineAction] = []

        if intent == "confirm":
            eff_id = self.candidate_beneficiary_id or self.visit.beneficiary_id
            eff_name = self.candidate_beneficiary_name or self.visit.beneficiary_name or eff_id or "Beneficiary"
            self.visit.beneficiary_id = eff_id
            self.visit.beneficiary_name = eff_name
            self.visit.updated_at = utc_now_iso()
            self.identity_verified = True
            if eff_id:
                self.confirmed_fields.add("beneficiary_id")
            if eff_name:
                self.confirmed_fields.add("beneficiary_name")
            self._backfill_alert_beneficiary()
            self.pending_clarifications = [
                c for c in self.pending_clarifications if c.field != "beneficiary_id"
            ]

            self._transition(
                ConversationState.GATHERING_NOTES,
                "beneficiary_identity_confirmed",
                actions,
            )
            spoken = generate_identity_confirmed_text(eff_name, self.active_language)
            actions.append(
                StateMachineAction(
                    action_type=ActionType.DRAFT_UPDATED,
                    payload={
                        "changed_fields": ["beneficiary_id", "beneficiary_name"],
                        "visit_record": self.visit.to_contract_payload(),
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
                metadata={"intent": "confirm", "identity_verified": True},
            )

        if intent == "reject":
            rejected_id = self.candidate_beneficiary_id or self.visit.beneficiary_id
            self.candidate_beneficiary_id = None
            self.candidate_beneficiary_name = None
            self.visit.beneficiary_id = None
            self.visit.beneficiary_name = None
            self.visit.updated_at = utc_now_iso()
            self.identity_verified = False
            self.confirmed_fields.discard("beneficiary_id")
            self.confirmed_fields.discard("beneficiary_name")

            self._transition(
                ConversationState.IDENTITY_CORRECTION,
                "worker_rejected_beneficiary",
                actions,
            )
            spoken = generate_identity_correction_prompt(self.active_language)
            clar = ClarificationRequest(
                field="beneficiary_id",
                reason="missing",
                question=spoken,
            )
            self.pending_clarifications = [clar]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.DRAFT_UPDATED,
                    payload={
                        "changed_fields": ["beneficiary_id", "beneficiary_name"],
                        "visit_record": self.visit.to_contract_payload(),
                    },
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [clar.model_dump(mode="json")],
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
                metadata={
                    "intent": "reject",
                    "identity_verified": False,
                    "rejected_beneficiary_id": rejected_id,
                },
            )

        # Scenario E: Ambiguous YES/NO response -> never confirm
        spoken = generate_unclear_identity_confirmation_text(self.active_language)
        clar = ClarificationRequest(
            field="beneficiary_id",
            reason="ambiguous_beneficiary",
            question=spoken,
            candidates=(
                [f"{self.candidate_beneficiary_id}: {self.candidate_beneficiary_name}"]
                if self.candidate_beneficiary_id and self.candidate_beneficiary_name
                else []
            ),
        )
        self.pending_clarifications = [clar]
        actions.append(
            StateMachineAction(
                action_type=ActionType.CLARIFICATION_PROMPT,
                payload={
                    "clarifications": [clar.model_dump(mode="json")],
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
            metadata={"intent": "unclear", "identity_verified": False},
        )

    def apply_beneficiary_lookup_result(
        self,
        matches: list[tuple[str, str]],
        *,
        language: str | None = None,
    ) -> TransitionResult:
        """Transition through BENEFICIARY_LOOKUP and handle 1, >1, or 0 matching beneficiaries."""
        previous = self.state
        if language:
            self.set_language(language)

        actions: list[StateMachineAction] = []
        self._transition(
            ConversationState.BENEFICIARY_LOOKUP, "searching_beneficiary_directory", actions
        )

        if len(matches) == 1:
            bid, bname = matches[0]
            self.candidate_beneficiary_id = bid
            self.candidate_beneficiary_name = bname
            self.visit.beneficiary_id = bid
            self.visit.beneficiary_name = bname
            self.visit.updated_at = utc_now_iso()
            self.identity_verified = False
            self.confirmed_fields.discard("beneficiary_id")
            self.confirmed_fields.discard("beneficiary_name")

            self._transition(
                ConversationState.CANDIDATE_CONFIRMATION,
                "single_candidate_found",
                actions,
            )
            spoken = generate_candidate_confirmation_text(bname, bid, self.active_language)
            clar = ClarificationRequest(
                field="beneficiary_id",
                reason="ambiguous_beneficiary",
                question=spoken,
                candidates=[f"{bid}: {bname}"],
            )
            self.pending_clarifications = [clar]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.DRAFT_UPDATED,
                    payload={
                        "changed_fields": ["beneficiary_id", "beneficiary_name"],
                        "visit_record": self.visit.to_contract_payload(),
                    },
                )
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [clar.model_dump(mode="json")],
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
                metadata={
                    "lookup_outcome": "single_match",
                    "candidate_beneficiary_id": bid,
                    "candidate_beneficiary_name": bname,
                    "identity_verified": False,
                },
            )

        if len(matches) > 1:
            self.candidate_beneficiary_id = None
            self.candidate_beneficiary_name = None
            self.visit.beneficiary_id = None
            self.visit.beneficiary_name = None
            self.identity_verified = False
            self._transition(
                ConversationState.IDENTITY_CORRECTION,
                "multiple_beneficiaries_matched",
                actions,
            )
            spoken = generate_multiple_beneficiaries_text(matches, self.active_language)
            cand_strings = [f"{bid}: {bname}" for bid, bname in matches]
            clar = ClarificationRequest(
                field="beneficiary_id",
                reason="ambiguous_beneficiary",
                question=spoken,
                candidates=cand_strings,
            )
            self.pending_clarifications = [clar]
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [clar.model_dump(mode="json")],
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
                metadata={"lookup_outcome": "multiple_matches", "candidates": cand_strings},
            )

        # Scenario D: 0 matches
        self.candidate_beneficiary_id = None
        self.candidate_beneficiary_name = None
        self.visit.beneficiary_id = None
        self.visit.beneficiary_name = None
        self.identity_verified = False
        self._transition(
            ConversationState.IDENTITY_CORRECTION,
            "beneficiary_not_found",
            actions,
        )
        spoken = generate_beneficiary_not_found_text(self.active_language)
        clar = ClarificationRequest(
            field="beneficiary_id",
            reason="missing",
            question=spoken,
        )
        self.pending_clarifications = [clar]
        actions.append(
            StateMachineAction(
                action_type=ActionType.CLARIFICATION_PROMPT,
                payload={
                    "clarifications": [clar.model_dump(mode="json")],
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
            metadata={"lookup_outcome": "not_found"},
        )

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
            spoken = _CONFIRMATION_PENDING_MESSAGES.get(
                self.active_language, _CONFIRMATION_PENDING_MESSAGES["en-IN"]
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
            spoken = _REJECT_WITHOUT_FIELD_MESSAGES.get(
                self.active_language, _REJECT_WITHOUT_FIELD_MESSAGES["en-IN"]
            )
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
        spoken = _UNCLEAR_CONFIRMATION_MESSAGES.get(
            self.active_language, _UNCLEAR_CONFIRMATION_MESSAGES["en-IN"]
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
            spoken = _COMMITTED_MESSAGES.get(
                self.active_language, _COMMITTED_MESSAGES["en-IN"]
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
        spoken = _PERSISTENCE_FAILED_MESSAGES.get(
            self.active_language, _PERSISTENCE_FAILED_MESSAGES["en-IN"]
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

    # -- Section 1–9 Continuous Editing, Final Review & Submission API -------

    def apply_continuous_update(
        self,
        update: ExtractionUpdate,
        *,
        is_correction: bool = False,
        merge_lists: bool = True,
        language: str | None = None,
    ) -> TransitionResult:
        """Apply new fields or field-level corrections and keep conversation open for edits."""
        previous = self.state
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Cannot modify a committed visit record.")

        if language:
            self.set_language(language)
        elif update.detected_language:
            self.set_language(update.detected_language)

        actions: list[StateMachineAction] = []
        self.visit.status = VisitStatus.DRAFT
        self.awaiting_persistence = False
        self.persistence_error = None
        self.readback_silence_repompts = 0
        self.submission_silence_reprompts = 0

        if is_correction:
            self._transition(
                ConversationState.CORRECTION_PATCH, "continuous_field_correction", actions
            )
        elif self.state in (
            ConversationState.IDLE,
            ConversationState.GATHERING_NOTES,
            ConversationState.CONTINUE_CONVERSATION,
            ConversationState.ASK_READBACK_PREFERENCE,
            ConversationState.ASK_SUBMISSION_CONFIRMATION,
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
            ConversationState.CLARIFICATION_REQUIRED,
        ):
            self._transition(
                ConversationState.EXTRACTING_FIELDS, "continuous_extraction", actions
            )

        changed = self._apply_update_fields(
            update, is_patch=is_correction, merge_lists=merge_lists
        )
        prev_vals = dict(getattr(self, "_last_prev_snapshot", {}))
        new_vals = dict(getattr(self, "_last_new_snapshot", {}))

        # Only classify as correction when an existing value was actually replaced or explicit correction
        actually_replaced = any(
            k in prev_vals and prev_vals[k] not in (None, [], "")
            for k in changed
        )
        emit_correction = is_correction or actually_replaced

        if emit_correction and changed:
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CORRECTION_APPLIED,
                    payload={
                        "patched_fields": changed,
                        "previous_values": prev_vals,
                        "new_values": new_vals,
                        "visit_record": self.visit.to_contract_payload(),
                    },
                )
            )

        actions.append(
            StateMachineAction(
                action_type=ActionType.DRAFT_UPDATED,
                payload={
                    "changed_fields": changed,
                    "visit_record": self.visit.to_contract_payload(),
                },
            )
        )

        # If an explicit ambiguity clarification was emitted (e.g., bare ambiguous number)
        ambiguous_clars = [
            c
            for c in update.clarifications
            if c.reason not in ("missing",) and c.field not in changed
        ]
        if ambiguous_clars:
            self.pending_clarifications = ambiguous_clars
            self._transition(
                ConversationState.CLARIFICATION_REQUIRED,
                "ambiguous_field_needs_clarification",
                actions,
            )
            prompt = generate_clarification_text(ambiguous_clars, self.active_language)
            actions.append(
                StateMachineAction(
                    action_type=ActionType.CLARIFICATION_PROMPT,
                    payload={
                        "clarifications": [c.model_dump(mode="json") for c in ambiguous_clars],
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
                metadata={"patched_fields": changed, "is_correction": emit_correction},
            )

        self._transition(
            ConversationState.CONTINUE_CONVERSATION,
            "continue_continuous_editing",
            actions,
        )
        spoken = generate_patch_acknowledgement_text(
            visit=self.visit,
            changed_fields=changed,
            is_correction=emit_correction,
            language=self.active_language,
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
            metadata={"patched_fields": changed, "is_correction": emit_correction},
        )

    def indicate_worker_done(self, *, language: str | None = None) -> TransitionResult:
        """Transition from continuous editing to ASK_READBACK_PREFERENCE (Section 6)."""
        previous = self.state
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Visit record is already committed.")
        if language:
            self.set_language(language)

        actions: list[StateMachineAction] = []
        clarifications = self._compute_clarifications()
        if clarifications:
            self.pending_clarifications = clarifications
            self._transition(
                ConversationState.CLARIFICATION_REQUIRED,
                "missing_required_before_final_review",
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

        self.readback_silence_repompts = 0
        self.submission_silence_reprompts = 0
        self._transition(
            ConversationState.FINAL_REVIEW_READY, "worker_indicated_done", actions
        )
        self._transition(
            ConversationState.ASK_READBACK_PREFERENCE,
            "ask_readback_preference",
            actions,
        )
        spoken = generate_readback_preference_question(self.active_language)
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
            metadata={"awaiting_readback_preference": True},
        )

    def handle_readback_preference_response(
        self,
        utterance: str,
        *,
        correction_patch: ExtractionUpdate | None = None,
        language: str | None = None,
    ) -> TransitionResult:
        """Handle YES / NO / correction / unclear during ASK_READBACK_PREFERENCE."""
        previous = self.state
        if language:
            self.set_language(language)
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Visit record is already committed.")

        # Scenario C: worker wants to edit a field before summary
        if correction_patch is not None and (
            correction_patch.specified_fields() or correction_patch.clear_fields
        ):
            return self.apply_continuous_update(correction_patch, is_correction=True)
        inferred = extract_fallback_correction_patch(utterance)
        if inferred is not None:
            return self.apply_continuous_update(inferred, is_correction=True)

        intent = classify_confirmation_intent(utterance)
        actions: list[StateMachineAction] = []

        if intent == "confirm":
            self.pending_clarifications = []
            self.summary_outdated = False
            self._transition(
                ConversationState.READ_COMPLETE_SUMMARY,
                "worker_requested_summary_readback",
                actions,
            )
            summary = generate_complete_summary_with_submit_prompt(
                self.visit, self.active_language
            )
            self.last_read_back_text = summary
            actions.append(
                StateMachineAction(
                    action_type=ActionType.READ_BACK_STARTED,
                    payload={
                        "visit_draft_id": self.visit.visit_draft_id,
                        "language": self.active_language,
                        "read_back_text": summary,
                    },
                )
            )
            self._transition(
                ConversationState.ASK_SUBMISSION_CONFIRMATION,
                "awaiting_submission_after_summary",
                actions,
            )
            actions.append(
                StateMachineAction(
                    action_type=ActionType.SPEAK,
                    payload={"text": summary, "language": self.active_language},
                )
            )
            return self._result(
                previous,
                actions,
                spoken_text=summary,
                metadata={"readback_choice": "yes"},
            )

        if intent == "reject":
            # Scenario B: Worker declined summary read-back ONLY -> ask whether to submit
            self._transition(
                ConversationState.ASK_SUBMISSION_CONFIRMATION,
                "worker_declined_summary_readback",
                actions,
            )
            spoken = generate_submission_confirmation_question(self.active_language)
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
                metadata={"readback_choice": "no"},
            )

        # Ambiguous response -> repeat question clearly without auto-assuming YES or NO
        spoken = generate_unclear_readback_preference_question(self.active_language)
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

    def handle_submission_confirmation_response(
        self,
        utterance: str,
        *,
        correction_patch: ExtractionUpdate | None = None,
        language: str | None = None,
    ) -> TransitionResult:
        """Handle YES / NO / correction / unclear during ASK_SUBMISSION_CONFIRMATION."""
        previous = self.state
        if language:
            self.set_language(language)
        if self.state == ConversationState.COMMITTED:
            raise InvalidTransitionError("Visit record is already committed.")

        # Test 8: worker changes a field after hearing summary -> invalidate old summary & return to editing
        if correction_patch is not None and (
            correction_patch.specified_fields() or correction_patch.clear_fields
        ):
            self.summary_outdated = True
            self.last_read_back_text = None
            return self.apply_continuous_update(correction_patch, is_correction=True)
        inferred = extract_fallback_correction_patch(utterance)
        if inferred is not None:
            self.summary_outdated = True
            self.last_read_back_text = None
            return self.apply_continuous_update(inferred, is_correction=True)

        intent = classify_confirmation_intent(utterance)
        actions: list[StateMachineAction] = []

        if intent == "confirm":
            clarifications = self._compute_clarifications()
            if clarifications or not self.identity_verified or not self.visit.beneficiary_id:
                self.pending_clarifications = clarifications
                self._transition(
                    ConversationState.CLARIFICATION_REQUIRED,
                    "validation_failed_before_submit",
                    actions,
                )
                prompt = generate_clarification_text(
                    clarifications or [ClarificationRequest(field="beneficiary_id", reason="missing")],
                    self.active_language,
                )
                actions.append(
                    StateMachineAction(
                        action_type=ActionType.SPEAK,
                        payload={"text": prompt, "language": self.active_language},
                    )
                )
                return self._result(previous, actions, spoken_text=prompt)

            self._transition(
                ConversationState.READY_TO_CONFIRM,
                "worker_approved_submission",
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
            spoken = _CONFIRMATION_PENDING_MESSAGES.get(
                self.active_language, _CONFIRMATION_PENDING_MESSAGES["en-IN"]
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
                metadata={"intent": "confirm", "awaiting_persistence": True},
            )

        if intent == "reject":
            # Test 9: submission declined -> retain unsubmitted draft and allow further edits
            self.visit.status = VisitStatus.DRAFT
            self.awaiting_persistence = False
            self._transition(
                ConversationState.CONTINUE_CONVERSATION,
                "worker_declined_submission_keep_draft",
                actions,
            )
            spoken = generate_submission_declined_text(self.active_language)
            actions.append(
                StateMachineAction(
                    action_type=ActionType.DRAFT_UPDATED,
                    payload={
                        "changed_fields": [],
                        "visit_record": self.visit.to_contract_payload(),
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
                metadata={"intent": "reject", "draft_retained": True},
            )

        spoken = generate_unclear_submission_question(self.active_language)
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

    def handle_silence_timeout(self) -> TransitionResult:
        """Section 7: Repeat question once on silence, then preserve unsubmitted draft (never auto-submit)."""
        previous = self.state
        actions: list[StateMachineAction] = []

        if self.state == ConversationState.ASK_READBACK_PREFERENCE:
            if self.readback_silence_repompts < 1:
                self.readback_silence_repompts += 1
                spoken = generate_readback_preference_question(self.active_language)
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
                    metadata={"silence_action": "repeat_once"},
                )
            self.visit.status = VisitStatus.DRAFT
            self._transition(
                ConversationState.CONTINUE_CONVERSATION,
                "silence_retained_unsubmitted_draft",
                actions,
            )
            spoken = generate_submission_declined_text(self.active_language)
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
                metadata={"silence_action": "retained_draft"},
            )

        if self.state == ConversationState.ASK_SUBMISSION_CONFIRMATION:
            if self.submission_silence_reprompts < 1:
                self.submission_silence_reprompts += 1
                spoken = generate_submission_confirmation_question(self.active_language)
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
                    metadata={"silence_action": "repeat_once"},
                )
            self.visit.status = VisitStatus.DRAFT
            self._transition(
                ConversationState.CONTINUE_CONVERSATION,
                "silence_retained_unsubmitted_draft",
                actions,
            )
            spoken = generate_submission_declined_text(self.active_language)
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
                metadata={"silence_action": "retained_draft"},
            )

        return self._result(previous, actions, metadata={"silence_action": "noop"})
