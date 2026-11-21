"""Deterministic multilingual danger-sign detector (Layer 1 safety engine).

Implements:
- Clause-level context filtering (negation, historical/resolved, other-person subject)
- Verified clinical threshold checks grounded strictly in ``docs/DANGER_SIGN_GUIDELINES.md``
- Exact, alias, normalized, and guarded fuzzy matching across English, Hindi/Hinglish,
  Kannada, and Tamil
- Conservative uncertainty reporting (``uncertain_matches`` with ``requires_clarification=True``)
- Urgent PHC referral message generation (never diagnosing, prescribing, or fabricating PHC details)
- Layer-2 LLM advisory merge that strictly prevents suppressing or downgrading Layer-1 matches
"""

from __future__ import annotations

import difflib
import re
from typing import Any

from .catalog import CATALOG_BY_ID, DANGER_SIGN_CATALOG
from .models import DangerMatch, DangerSignEntry, DetectionResult
from .normalizer import normalize_for_exact, normalize_text, split_clauses


# =============================================================================
# Urgent Referral Messages (NO diagnosis, NO prescriptions, NO fabricated PHC)
# =============================================================================

_REFERRAL_MESSAGES: dict[str, str] = {
    "hi-IN": (
        "चेतावनी: गंभीर खतरे का संकेत मिला है। कृपया लाभार्थी को बिना देर किए "
        "तुरंत नजदीकी प्राथमिक स्वास्थ्य केंद्र (पीएचसी) या अस्पताल ले जाएं।"
    ),
    "en-IN": (
        "Urgent danger sign detected. Please refer and take the beneficiary to the "
        "nearest Primary Health Centre (PHC) or hospital immediately for medical evaluation. "
        "Do not delay."
    ),
    "kn-IN": (
        "ತುರ್ತು ಎಚ್ಚರಿಕೆ: ಗಂಭೀರ ಅಪಾಯದ ಲಕ್ಷಣ ಕಂಡುಬಂದಿದೆ. ದಯವಿಟ್ಟು ತಡಮಾಡದೆ "
        "ಫಲಾನುಭವಿಯನ್ನು ತಕ್ಷಣ ಹತ್ತಿರದ ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ (PHC) ಅಥವಾ ಆಸ್ಪತ್ರೆಗೆ ಕರೆದೊಯ್ಯಿರಿ."
    ),
    "ta-IN": (
        "அவசர எச்சரிக்கை: ஆபத்தான அறிகுறி கண்டறியப்பட்டுள்ளது. தாமதிக்காமல் "
        "பயனாளியை உடனடியாக அருகிலுள்ள ஆரம்ப சுகாதார நிலையம் (PHC) அல்லது மருத்துவமனைக்கு "
        "அழைத்துச் செல்லவும்."
    ),
    "te-IN": (
        "అత్యవసర హెచ్చరిక: తీవ్రమైన ప్రమాద లక్షణం గుర్తించబడింది. దయచేసి ఆలస్యం చేయకుండా "
        "లబ్ధిదారుని వెంటనే సమీప ప్రాథమిక ఆరోగ్య కేంద్రం (PHC) లేదా ఆసుపత్రికి తీసుకెళ్లండి."
    ),
    "ml-IN": (
        "അടിയന്തര മുന്നറിയിപ്പ്: ഗുരുതരമായ അപായ ലക്ഷണം കണ്ടെത്തിയിരിക്കുന്നു. ഒട്ടും വൈകാതെ "
        "ഗുണഭോക്താവിനെ ഉടൻ തന്നെ അടുത്തുള്ള പ്രാഥമിക ആരോഗ്യ കേന്ദ്രത്തിലേക്കോ (PHC) ആശുപത്രിയിലേക്കോ കൊണ്ടുപോകുക."
    ),
    "mr-IN": (
        "तातडीचा इशारा: गंभीर धोक्याचे लक्षण आढळले आहे. कृपया उशीर न करता "
        "लाभार्थ्याला त्वरित जवळच्या प्राथमिक आरोग्य केंद्रात (PHC) किंवा रुग्णालयात घेऊन जा."
    ),
    "bn-IN": (
        "জরুরি সতর্কতা: গুরুতর বিপদের লক্ষণ শনাক্ত হয়েছে। দয়া করে দেরি না করে "
        "উপভোক্তাকে অবিলম্বে নিকটবর্তী প্রাথমিক স্বাস্থ্যকেন্দ্র (PHC) বা হাসপাতালে নিয়ে যান।"
    ),
    "gu-IN": (
        "તાત્કાલિક ચેતવણી: ગંભીર જોખમનું લક્ષણ જણાયું છે. કૃપા કરીને વિલંબ કર્યા વિના "
        "લાભાર્થીને તરત જ નજીકના પ્રાથમિક આરોગ્ય કેન્દ્ર (PHC) અથવા હોસ્પિટલમાં લઈ જાઓ."
    ),
    "pa-IN": (
        "ਐਮਰਜੈਂਸੀ ਅਲਰਟ: ਗੰਭੀਰ ਖ਼ਤਰੇ ਦਾ ਲੱਛਣ ਮਿਲਿਆ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਬਿਨਾਂ ਦੇਰੀ ਕੀਤੇ "
        "ਲਾਭਪਾਤਰੀ ਨੂੰ ਤੁਰੰਤ ਨਜ਼ਦੀਕੀ ਪ੍ਰਾਇਮਰੀ ਹੈਲਥ ਸੈਂਟਰ (PHC) ਜਾਂ ਹਸਪਤਾਲ ਲੈ ਜਾਓ।"
    ),
    "hinglish": (
        "Urgent chetavni: Gambhir khatre ka sanket mila hai. Kripya bina der kiye "
        "labharthi ko turant nazdeeki Primary Health Centre (PHC) ya hospital le jaayein."
    ),
}

_LANGUAGE_ALIASES: dict[str, str] = {
    "hi": "hi-IN",
    "hi-in": "hi-IN",
    "hindi": "hi-IN",
    "en": "en-IN",
    "en-in": "en-IN",
    "en-us": "en-IN",
    "en-gb": "en-IN",
    "english": "en-IN",
    "kn": "kn-IN",
    "kn-in": "kn-IN",
    "kannada": "kn-IN",
    "ta": "ta-IN",
    "ta-in": "ta-IN",
    "tamil": "ta-IN",
    "te": "te-IN",
    "te-in": "te-IN",
    "telugu": "te-IN",
    "ml": "ml-IN",
    "ml-in": "ml-IN",
    "malayalam": "ml-IN",
    "mr": "mr-IN",
    "mr-in": "mr-IN",
    "marathi": "mr-IN",
    "bn": "bn-IN",
    "bn-in": "bn-IN",
    "bengali": "bn-IN",
    "bangla": "bn-IN",
    "gu": "gu-IN",
    "gu-in": "gu-IN",
    "gujarati": "gu-IN",
    "pa": "pa-IN",
    "pa-in": "pa-IN",
    "punjabi": "pa-IN",
    "hi-latn": "hinglish",
    "hinglish": "hinglish",
}


def get_referral_message(language: str) -> str:
    """Return an urgent PHC referral message in the active language.

    Strictly avoids diagnosing, prescribing medicine, recommending home remedies,
    or inventing PHC names, locations, or phone numbers.
    """
    key = (language or "").strip().lower()
    canonical_lang = _LANGUAGE_ALIASES.get(key, "en-IN")
    return _REFERRAL_MESSAGES[canonical_lang]


# =============================================================================
# Context / Subject / Disambiguation Helpers
# =============================================================================

_NEWBORN_CUE_RE = re.compile(
    r"(?:\b(?:newborn|baby|infant|neonate|neonatal|child|baccha|shishu|navjat|"
    r"magu|kuzhandhai|papa|umbilical|naal|nabhi|cord\s*stump|birth\s*weight|vlbw|hbnc)\b|"
    r"बच्चा|बच्चे|नवजात|शिशु|नाभि|ಮಗು|ನವಜಾತ|குழந்தை|பிறந்த)",
    flags=re.IGNORECASE,
)

_PNC_CUE_RE = re.compile(
    r"(?:\b(?:postpartum|postnatal|pnc|after\s+delivery|pph|lochia|episiotomy|"
    r"perineal|delivery\s+ke\s+baad|prasav\s+ke\s+baad|herige\s+nantara|prasavathirkku\s+pin|"
    r"pads?\s*(?:a\s*day|per\s*day|daily|in\s*\d+\s*min)|thick\s*cloth)\b|"
    r"प्रसव\s+के\s+बाद|लोचिया|टांकों|ಹೆರಿಗೆಯ\s+ನಂತರ|பிரசவத்திற்கு\s+பின்)",
    flags=re.IGNORECASE,
)

_INTRA_CUE_RE = re.compile(
    r"(?:\b(?:intranatal|during\s+labour|during\s+delivery|in\s+labour|labour\s+pain|"
    r"placenta|meconium|prolapse|prasav\s+peeda)\b|"
    r"प्रसव\s+के\s+दौरान|प्रसव\s+पीड़ा|आंवल)",
    flags=re.IGNORECASE,
)

_MOTHER_CUE_RE = re.compile(
    r"(?:\b(?:mother|pregnant|pregnancy|antenatal|anc|woman|patient|mahila|garbhavati|"
    r"maa|mata|taayi|amma|thaai|vaginal|fetal|foetal|postpartum|pnc)\b|"
    r"माँ|माता|महिला|गर्भवती|योनि|ತಾಯಿ|கர்ப்ப|தாய்)",
    flags=re.IGNORECASE,
)

# Negation markers (pre-positioned and post-positioned)
_PRE_NEGATION_RE = re.compile(
    r"(?:\b(?:no|not|none|never|without|absent|denied|denies|negative\s+for|"
    r"ruled\s+out|free\s+of|has\s+no|have\s+no|had\s+no|doesn't\s+have|does\s+not\s+have|"
    r"didn't\s+have|did\s+not\s+have|is\s+not\s+having|isn't\s+having|koi\s+\w+\s+nahi)\b)",
    flags=re.IGNORECASE,
)

_POST_NEGATION_RE = re.compile(
    r"(?:\b(?:nahi|nahin|absent|denied|illai|illa|illave\s+illa|ruled\s+out|negative)\b|"
    r"नहीं|ಇಲ್ಲ|இல்லை)",
    flags=re.IGNORECASE,
)

_CIRCUMFIX_KOI_NAHI_RE = re.compile(
    r"(?:\bkoi\b.{0,45}\bnahi\b|कोई.{0,45}नहीं)",
    flags=re.IGNORECASE,
)

# Historical / resolved markers
_HISTORICAL_RE = re.compile(
    r"(?:\b(?:last\s+(?:month|week|year|pregnancy)|"
    r"(?:\d+|two|three|four|few|several|a)\s+(?:weeks?|months?|years?)\s+ago|"
    r"previously|in\s+(?:her\s+)?previous\s+pregnancy|previous\s+pregnancy|"
    r"earlier\s+resolved|already\s+resolved|resolved\s+now|has\s+resolved|"
    r"used\s+to\s+have|old\s+history|history\s+of|"
    r"pichle\s+(?:mahine|hafte|saal)|pichli\s+pregnancy|"
    r"pehle\s+(?:tha|thi|hua\s+tha|hui\s+thi)|ab\s+(?:theek|normal|nahi)\s+hai|"
    r"theek\s+ho\s+(?:gaya|gayi)|"
    r"kaleda\s+tingalu|modale\s+ittu|eega\s+sariyagide|"
    r"kadantha\s+maadham|munbu\s+irundhadhu|ippo\s+sariyagi)\b|"
    r"पिछले\s+(?:महीने|हफ्ते|साल)|पहले\s+(?:था|थी)|अब\s+ठीक\s+है|ठीक\s+हो\s+ग(?:या|ई))",
    flags=re.IGNORECASE,
)

# Other-person subject markers
_OTHER_PERSON_RE = re.compile(
    r"(?:\b(?:neighbour|neighbours|neighbor|neighbors|padosi|padosan|"
    r"sister|sisters|behen|bahan|bhabhi|nanad|devrani|jethani|"
    r"friend|friends|dost|saheli|someone\s+else|somebody\s+else|another\s+woman|"
    r"kisi\s+aur|dusre|dusri\s+mahila|aunt|chachi|mausi|bua|mother-in-law|saas|"
    r"husband|pati|brother|bhai|elder\s+child|bada\s+beta|badi\s+beti|"
    r"pakkada\s+maneyavaru|pakkathu\s+veettu)\b|"
    r"पड़ोसी|बहन|दोस्त|सास|किसी\s+और|दूसरी\s+महिला)",
    flags=re.IGNORECASE,
)

# Hedging / mild / ambiguous modifiers
_HEDGE_RE = re.compile(
    r"(?:\b(?:maybe|might\s+be|possibly|not\s+sure|unsure|mild|slight|slightly|"
    r"a\s+little|little\s+bit|a\s+bit|looks\s+like|seems\s+like|probably|perhaps|"
    r"thoda|thodi|thoda\s+sa|thodi\s+si|halka|halki|shayad|lagta\s+hai|lag\s+raha\s+hai|"
    r"pata\s+nahi|kuch|swalpa|irabahudu|konjam|irukkalam)\b|"
    r"थोड़ा|थोड़ी|हल्का|हल्की|शायद|लगता\s+है|ಸ್ವಲ್ಪ|ಇರಬಹುದು|கொஞ்சம்|இருக்கலாம்)",
    flags=re.IGNORECASE,
)


def _infer_clause_phase_and_subject(
    clause_norm: str,
    prior_category: str | None,
    prior_subject: str | None,
    context: dict[str, Any] | None,
) -> tuple[str | None, str | None]:
    """Infer effective (category, subject) from clause cues, caller context, and prior clauses.

    Subject continuity flows forward from earlier clauses and caller context,
    never backward from a later contrastive clause (e.g., 'No bleeding, but newborn...').
    """
    ctx_visit = (context or {}).get("visit_type")
    ctx_subject = (context or {}).get("subject")

    # 1. Clause-level explicit cues take highest priority
    has_nb = bool(_NEWBORN_CUE_RE.search(clause_norm))
    has_pnc = bool(_PNC_CUE_RE.search(clause_norm))
    has_intra = bool(_INTRA_CUE_RE.search(clause_norm))
    has_mother = bool(_MOTHER_CUE_RE.search(clause_norm))

    if has_nb and not has_mother:
        return ("Newborn", "newborn")
    if has_pnc:
        return ("PNC", "mother")
    if has_intra:
        return ("Intranatal", "mother")
    if has_mother and not has_nb:
        if ctx_visit in ("ANC", "PNC", "Intranatal"):
            return (ctx_visit, "mother")
        return ("ANC", "mother")

    # 2. Caller-provided context
    if ctx_subject in ("newborn", "infant") or ctx_visit == "Newborn":
        return ("Newborn", "newborn")
    if ctx_visit in ("ANC", "PNC", "Intranatal"):
        return (ctx_visit, "mother")

    # 3. Forward continuity from earlier clauses in the same utterance
    if prior_category is not None or prior_subject is not None:
        return (prior_category, prior_subject)

    return (None, None)


def _contains_phrase(text: str, phrase: str) -> re.Match[str] | None:
    """Match a phrase in normalized text respecting word boundaries for ASCII/Latin text."""
    if not phrase:
        return None
    escaped = re.escape(phrase)
    # Use word boundaries on ASCII alphanumeric edges; Indic scripts don't play well with \b around combining marks
    starts_ascii = phrase[0].isascii() and phrase[0].isalnum()
    ends_ascii = phrase[-1].isascii() and phrase[-1].isalnum()
    prefix = r"(?<![a-z0-9])" if starts_ascii else ""
    suffix = r"(?![a-z0-9])" if ends_ascii else ""
    return re.search(f"{prefix}{escaped}{suffix}", text)


def _check_suppression_context(
    clause_norm: str,
    match_start: int,
    match_end: int,
    matched_phrase: str,
    entry: DangerSignEntry,
) -> str | None:
    """Determine if a match in a clause should be suppressed due to historical, other-person, or negation context.

    Returns suppression reason ('historical', 'other_person', 'negation') or None.
    """
    # 1. Historical / resolved context in this clause
    if _HISTORICAL_RE.search(clause_norm):
        return "historical"

    # 2. Other-person subject in this clause (unless active beneficiary is also explicitly named)
    if _OTHER_PERSON_RE.search(clause_norm):
        # Suppress if the clause is talking about the other person rather than mother/newborn
        has_active_beneficiary = bool(
            re.search(
                r"\b(?:this\s+mother|patient|beneficiary|pregnant\s+woman|newborn|her\s+baby)\b",
                clause_norm,
            )
        )
        if not has_active_beneficiary:
            return "other_person"

    # 3. Negation check — carefully respecting intrinsic-negative danger signs!
    norm_matched = normalize_text(matched_phrase)
    is_intrinsic_neg = any(
        normalize_text(p) == norm_matched or normalize_text(p) in norm_matched
        for p in entry.intrinsic_negative_phrases
    )

    if is_intrinsic_neg:
        # Only suppress an intrinsic-negative sign if explicitly double-negated outside the matched span
        before = clause_norm[:match_start].strip()
        if re.search(r"\b(?:not\s+true|false|no\s+longer|resolved)\s*$", before):
            return "negation"
        return None

    # Check circumfix Hindi "koi ... nahi" across the clause
    if _CIRCUMFIX_KOI_NAHI_RE.search(clause_norm):
        return "negation"

    # Inspect text immediately before and after the matched phrase within this clause
    before = clause_norm[:match_start]
    after = clause_norm[match_end:]

    # Scope pre-negation: look back up to 40 chars without crossing a strong new-subject transition
    before_window = before[-45:]
    # If "and" is followed by a new subject/verb before our match (e.g. "no bleeding and baby has high fever"),
    # do not let "no" leak across the "and <subject> has" boundary.
    and_split = re.split(r"\b(?:and|aur|और)\s+(?:baby|newborn|mother|she|he|baccha|maa|patient)\b", before_window)
    scoped_before = and_split[-1] if and_split else before_window
    if _PRE_NEGATION_RE.search(scoped_before):
        return "negation"

    # Scope post-negation: look ahead up to 35 chars without crossing "and/aur" + another symptom
    after_window = after[:35]
    after_split = re.split(r"\b(?:and|aur|और|with)\b", after_window)
    scoped_after = after_split[0] if after_split else after_window
    if _POST_NEGATION_RE.search(scoped_after):
        return "negation"

    return None


def _select_disambiguated_entry(
    entry: DangerSignEntry,
    inferred_category: str | None,
    inferred_subject: str | None,
) -> DangerSignEntry:
    """Resolve cross-phase symptoms (bleeding, convulsions, fever, jaundice, etc.) to the right canonical ID."""
    group = entry.disambiguation_group
    if not group:
        return entry

    if group == "bleeding":
        if inferred_subject == "newborn" or inferred_category == "Newborn":
            return CATALOG_BY_ID["NB_BLEEDING"]
        if inferred_category == "PNC":
            return CATALOG_BY_ID["PNC_EXCESSIVE_BLEEDING"]
        if inferred_category == "Intranatal":
            return CATALOG_BY_ID["INTRA_EXCESSIVE_BLEEDING"]
        return entry

    if group == "convulsions":
        if inferred_subject == "newborn" or inferred_category == "Newborn":
            return CATALOG_BY_ID["NB_CONVULSIONS"]
        if inferred_category == "PNC":
            return CATALOG_BY_ID["PNC_CONVULSIONS_ABNORMAL_SPEECH"]
        return entry

    if group == "fever":
        if inferred_subject == "newborn" or inferred_category == "Newborn":
            return CATALOG_BY_ID["NB_FEVER"]
        if inferred_category == "PNC":
            return CATALOG_BY_ID["PNC_HIGH_FEVER"]
        return entry

    if group == "foul_discharge":
        if inferred_category == "PNC":
            return CATALOG_BY_ID["PNC_PUERPERAL_SEPSIS"]
        return entry

    if group == "breathing":
        if entry.canonical_id == "ANC_BREATHLESSNESS" and (
            inferred_subject == "newborn" or inferred_category == "Newborn"
        ):
            return CATALOG_BY_ID["NB_FAST_BREATHING"]
        return entry

    if group == "urine":
        if inferred_subject == "newborn" or inferred_category == "Newborn":
            return CATALOG_BY_ID["NB_CYANOSIS_DIARRHOEA_NO_URINE"]
        if inferred_category == "PNC":
            return CATALOG_BY_ID["PNC_URINARY_RETENTION_DVT"]
        return entry

    if group == "jaundice":
        if inferred_subject == "newborn" or inferred_category == "Newborn":
            return CATALOG_BY_ID["NB_SEVERE_JAUNDICE"]
        return entry

    return entry


def _make_match(
    entry: DangerSignEntry,
    matched_phrase: str,
    evidence_text: str,
    confidence: float,
    match_type: str,
    requires_clarification: bool = False,
) -> DangerMatch:
    return DangerMatch(
        canonical_id=entry.canonical_id,
        canonical_name=entry.canonical_name,
        subject=entry.subject,
        category=entry.category,
        matched_phrase=matched_phrase,
        evidence_text=evidence_text.strip()[:160],
        confidence=round(min(max(confidence, 0.0), 1.0), 3),
        match_type=match_type,  # type: ignore[arg-type]
        source_doc=entry.source_doc,
        source_section=entry.source_section,
        requires_clarification=requires_clarification,
    )


# =============================================================================
# Quantitative Clinical Threshold Detectors (Grounded in DANGER_SIGN_GUIDELINES.md)
# =============================================================================

_BP_SLASH_RE = re.compile(
    r"(?:(?:bp|pressure)\D{0,15})?(\d{2,3})\s*/\s*(\d{2,3})(?:\s*(?:mm\s*hg|bp))?",
    flags=re.IGNORECASE,
)
_BP_SYSTOLIC_RE = re.compile(r"\bsystolic\D{0,10}(\d{2,3})\b", flags=re.IGNORECASE)
_BP_DIASTOLIC_RE = re.compile(r"\bdiastolic\D{0,10}(\d{2,3})\b", flags=re.IGNORECASE)

_RR_RE = re.compile(
    r"(?:(?:respiratory\s*rate|breathing\s*rate|breath\s*rate|rr|breaths|saans)\D{0,22}(\d{2,3})"
    r"(?:\s*(?:/\s*min|per\s*min(?:ute)?|bpm|breaths?\s*(?:per|/)\s*min(?:ute)?))?|"
    r"(\d{2,3})\s*(?:breaths?\s*(?:per|/)\s*min(?:ute)?|/\s*min\s*(?:breathing|rr|saans)))",
    flags=re.IGNORECASE,
)

_TEMP_EXPLICIT_UNIT_RE = re.compile(
    r"(\d{2,3}(?:\.\d+)?)\s*(?:°\s*)?([fc])\b",
    flags=re.IGNORECASE,
)
_TEMP_CUE_NUMBER_RE = re.compile(
    r"(?:temp(?:erature)?|fever|bukhar|taap|jvara|kaychal|thermometer)\D{0,18}(\d{2,3}(?:\.\d+)?)\b",
    flags=re.IGNORECASE,
)

_PADS_DAY_RE = re.compile(
    r"(?:(more\s+than|over|>|zyada|jyada)\s*)?(\d+)\s*(?:se\s*(?:zyada|jyada)\s*)?"
    r"(?:pads?|sanitary\s*pads?|napkins?)\s*(?:a\s*day|per\s*day|daily|in\s*a\s*day|roz|ek\s*din\s*mein|din\s*mein)",
    flags=re.IGNORECASE,
)
_PADS_SHORT_RE = re.compile(
    r"(\d+)\s*(?:pads?|sanitary\s*pads?)\s*(?:soaked\s*)?(?:in|within)\s*(\d+)\s*(?:min|mins|minutes?)",
    flags=re.IGNORECASE,
)
_THICK_CLOTH_RE = re.compile(
    r"(?:(more\s+than|over|>)\s*1|([2-9]|\d{2}))\s*thick\s*cloths?\s*(?:a\s*day|per\s*day|daily)?",
    flags=re.IGNORECASE,
)
_BLOOD_ML_RE = re.compile(
    r"(?:bleeding|blood\s*loss|khoon)\D{0,20}(\d{3,4})\s*ml\b|(\d{3,4})\s*ml\s*(?:blood|bleeding)",
    flags=re.IGNORECASE,
)

_WEIGHT_RE = re.compile(
    r"(?:birth\s*weight|weight|vajan|wajan|wt|tuka|edai)?\D{0,15}(\d+(?:\.\d+)?)\s*(kg|g)\b",
    flags=re.IGNORECASE,
)
_WEIGHT_GAIN_RE = re.compile(
    r"\b(?:gain|gained|gaining|badha|badh|increase|increased)\b",
    flags=re.IGNORECASE,
)

_HB_RE = re.compile(
    r"\b(?:hb|hemoglobin)\D{0,12}(\d+(?:\.\d+)?)\b",
    flags=re.IGNORECASE,
)

_LABOUR_HOURS_RE = re.compile(
    r"(?:labour|delivery\s*pain|prasav\s*peeda|dard)\D{0,25}(?:(more\s+than|over|>)\s*)?(\d+)\s*(?:hours?|hrs?|ghante|ghanton)",
    flags=re.IGNORECASE,
)

_PUSTULE_COUNT_RE = re.compile(
    r"(?:(more\s+than|over|>)\s*)?(\d+)\s*(?:se\s*(?:zyada|jyada)\s*)?(?:pustules?|boils?|phode|fode|phunsi)",
    flags=re.IGNORECASE,
)


def _detect_thresholds_in_clause(
    clause_raw: str,
    clause_norm: str,
    inferred_category: str | None,
    inferred_subject: str | None,
    confirmed: list[DangerMatch],
    uncertain: list[DangerMatch],
    suppressed: list[dict[str, str]],
) -> None:
    """Evaluate verified numerical clinical thresholds within a single clause."""

    def _emit_or_suppress(
        entry: DangerSignEntry,
        m_start: int,
        m_end: int,
        matched_phrase: str,
        is_uncertain: bool = False,
        confidence: float = 0.96,
    ) -> None:
        reason = _check_suppression_context(clause_norm, m_start, m_end, matched_phrase, entry)
        if reason:
            suppressed.append(
                {
                    "canonical_id": entry.canonical_id,
                    "matched_phrase": matched_phrase,
                    "reason": reason,
                    "clause": clause_raw.strip()[:160],
                }
            )
            return
        match = _make_match(
            entry=entry,
            matched_phrase=matched_phrase,
            evidence_text=clause_raw,
            confidence=confidence,
            match_type="threshold",
            requires_clarification=is_uncertain,
        )
        if is_uncertain:
            uncertain.append(match)
        else:
            confirmed.append(match)

    # 1. Blood Pressure >= 140/90 (INT-ASHA-2026 p. 181; DAKSHATA CHECK-1 p. 14)
    bp_matched = False
    for m in _BP_SLASH_RE.finditer(clause_norm):
        sys_val = int(m.group(1))
        dia_val = int(m.group(2))
        if 70 <= sys_val <= 260 and 40 <= dia_val <= 160 and sys_val > dia_val:
            if sys_val >= 140 or dia_val >= 90:
                _emit_or_suppress(CATALOG_BY_ID["ANC_HIGH_BP"], m.start(), m.end(), f"BP {sys_val}/{dia_val}")
                bp_matched = True
    if not bp_matched:
        sys_m = _BP_SYSTOLIC_RE.search(clause_norm)
        dia_m = _BP_DIASTOLIC_RE.search(clause_norm)
        if sys_m and 140 <= int(sys_m.group(1)) <= 260:
            _emit_or_suppress(CATALOG_BY_ID["ANC_HIGH_BP"], sys_m.start(), sys_m.end(), sys_m.group(0))
        elif dia_m and 90 <= int(dia_m.group(1)) <= 160:
            _emit_or_suppress(CATALOG_BY_ID["ANC_HIGH_BP"], dia_m.start(), dia_m.end(), dia_m.group(0))

    # 2. Newborn Fast Breathing >= 60 breaths/min (HBNC-2014 pp. 22, 28; HBYC p. 53)
    #    or Slow Breathing < 30 breaths/min (DAKSHATA CHECK-3/4 pp. 16-17)
    is_newborn_ctx = inferred_subject == "newborn" or inferred_category == "Newborn"
    for m in _RR_RE.finditer(clause_norm):
        val_str = m.group(1) or m.group(2)
        if not val_str:
            continue
        rr = int(val_str)
        if 60 <= rr <= 160:
            if is_newborn_ctx or inferred_subject is None:
                _emit_or_suppress(
                    CATALOG_BY_ID["NB_FAST_BREATHING"],
                    m.start(),
                    m.end(),
                    f"respiratory rate {rr}/min",
                )
        elif is_newborn_ctx and 5 <= rr < 30:
            _emit_or_suppress(
                CATALOG_BY_ID["NB_FAST_BREATHING"],
                m.start(),
                m.end(),
                f"slow breathing {rr}/min",
            )

    # 3. Temperature thresholds (Newborn fever > 99°F / hypothermia < 95.9°F; ANC > 100°F; PNC > 102°F)
    temp_hits: list[tuple[int, int, float, str, str]] = []
    seen_spans: set[tuple[int, int]] = set()
    for m in _TEMP_EXPLICIT_UNIT_RE.finditer(clause_norm):
        val = float(m.group(1))
        unit = m.group(2).lower()
        temp_f = val if unit == "f" else (val * 9.0 / 5.0) + 32.0
        if 85.0 <= temp_f <= 110.0:
            seen_spans.add((m.start(), m.end()))
            temp_hits.append((m.start(), m.end(), temp_f, f"{val}°{unit.upper()}", m.group(0)))

    for m in _TEMP_CUE_NUMBER_RE.finditer(clause_norm):
        if any(s <= m.start(1) <= e for s, e in seen_spans):
            continue
        val = float(m.group(1))
        if 90.0 <= val <= 110.0:
            temp_hits.append((m.start(), m.end(), val, f"{val}°F", m.group(0)))
        elif 30.0 <= val <= 43.0:
            temp_f = (val * 9.0 / 5.0) + 32.0
            temp_hits.append((m.start(), m.end(), temp_f, f"{val}°C", m.group(0)))

    for start, end, temp_f, label, _raw in temp_hits:
        if is_newborn_ctx:
            if temp_f > 99.0:
                _emit_or_suppress(CATALOG_BY_ID["NB_FEVER"], start, end, f"temperature {label}")
            elif temp_f < 95.9:
                _emit_or_suppress(CATALOG_BY_ID["NB_HYPOTHERMIA"], start, end, f"temperature {label}")
            elif temp_f < 97.0:
                # Mild cold stress (< 97°F / 36.1°C per MOD6 p. 59 & HBNC-2014 p. 21) -> clarify / reassess
                _emit_or_suppress(
                    CATALOG_BY_ID["NB_HYPOTHERMIA"],
                    start,
                    end,
                    f"mild cold stress {label}",
                    is_uncertain=True,
                    confidence=0.75,
                )
        elif inferred_category == "PNC":
            has_foul = bool(re.search(r"\b(?:foul|smelly|badbu|lochia|durgandh)\b", clause_norm))
            has_engorged = bool(re.search(r"\b(?:engorged|breast\s+swollen|stan)\b", clause_norm))
            if temp_f > 100.0 and has_foul:
                _emit_or_suppress(CATALOG_BY_ID["PNC_PUERPERAL_SEPSIS"], start, end, f"foul lochia + fever {label}")
            elif temp_f > 102.0 or (temp_f > 100.0 and has_engorged):
                _emit_or_suppress(CATALOG_BY_ID["PNC_HIGH_FEVER"], start, end, f"postpartum fever {label}")
            elif temp_f > 100.0:
                _emit_or_suppress(
                    CATALOG_BY_ID["PNC_HIGH_FEVER"],
                    start,
                    end,
                    f"postpartum fever {label}",
                    is_uncertain=True,
                    confidence=0.72,
                )
        else:
            # ANC / default maternal fever: > 100°F (MOD6 p. 32; DAKSHATA >= 38°C / 100.5°F)
            if temp_f > 100.0:
                _emit_or_suppress(CATALOG_BY_ID["ANC_HIGH_FEVER"], start, end, f"fever {label}")

    # 4. Postpartum bleeding pad/cloth/ml thresholds (HBNC-2014 p. 19; INT-ASHA-2026 p. 48; DAKSHATA p. 16)
    for m in _PADS_DAY_RE.finditer(clause_norm):
        qual = m.group(1)
        count = int(m.group(2))
        if count > 5 or (count == 5 and qual):
            _emit_or_suppress(CATALOG_BY_ID["PNC_EXCESSIVE_BLEEDING"], m.start(), m.end(), m.group(0))
    for m in _PADS_SHORT_RE.finditer(clause_norm):
        pads = int(m.group(1))
        mins = int(m.group(2))
        if (pads >= 2 and mins <= 30) or (pads >= 1 and mins < 5):
            _emit_or_suppress(CATALOG_BY_ID["PNC_EXCESSIVE_BLEEDING"], m.start(), m.end(), m.group(0))
    for m in _THICK_CLOTH_RE.finditer(clause_norm):
        _emit_or_suppress(CATALOG_BY_ID["PNC_EXCESSIVE_BLEEDING"], m.start(), m.end(), m.group(0))
    for m in _BLOOD_ML_RE.finditer(clause_norm):
        ml_val = int(m.group(1) or m.group(2))
        if ml_val >= 500:
            _emit_or_suppress(CATALOG_BY_ID["PNC_EXCESSIVE_BLEEDING"], m.start(), m.end(), f"blood loss {ml_val} ml")

    # 5. Very Low Birth Weight < 1.8 kg / 1800 g (MOD6 pp. 48-49; HBNC-2014 p. 20; SUMAN-2020 p. 37)
    if is_newborn_ctx and not _WEIGHT_GAIN_RE.search(clause_norm):
        for m in _WEIGHT_RE.finditer(clause_norm):
            val = float(m.group(1))
            unit = m.group(2).lower()
            weight_kg = val if unit == "kg" else val / 1000.0
            if 0.3 <= weight_kg < 1.8:
                _emit_or_suppress(
                    CATALOG_BY_ID["NB_VERY_LOW_BIRTH_WEIGHT"],
                    m.start(),
                    m.end(),
                    f"birth weight {weight_kg:.2f} kg",
                )

    # 6. Severe Anaemia Hb < 7.0 g/dl (MOD6 p. 28; INT-ASHA-2026 p. 179)
    for m in _HB_RE.finditer(clause_norm):
        hb_val = float(m.group(1))
        if 1.0 <= hb_val < 7.0:
            _emit_or_suppress(CATALOG_BY_ID["ANC_SEVERE_ANAEMIA"], m.start(), m.end(), f"Hb {hb_val} g/dl")

    # 7. Prolonged Labour > 12 hours (MCP-CARD p. 4; MCP-GB p. 15; MOD6 p. 33)
    for m in _LABOUR_HOURS_RE.finditer(clause_norm):
        qual = m.group(1)
        hours = int(m.group(2))
        if (hours > 12 or (hours == 12 and qual)) and hours <= 120:
            _emit_or_suppress(CATALOG_BY_ID["INTRA_PROLONGED_LABOUR"], m.start(), m.end(), m.group(0))

    # 8. Severe Skin Pustules > 10 pustules (INT-ASHA-2026 p. 46)
    if is_newborn_ctx or inferred_subject is None:
        for m in _PUSTULE_COUNT_RE.finditer(clause_norm):
            qual = m.group(1)
            count = int(m.group(2))
            if count > 10 or (count == 10 and qual):
                _emit_or_suppress(CATALOG_BY_ID["NB_SEVERE_SKIN_PUSTULES"], m.start(), m.end(), m.group(0))


# =============================================================================
# Fuzzy Matching (Guarded against false positives)
# =============================================================================

_FUZZY_STOPWORDS = frozenset(
    {
        "mother",
        "baby",
        "newborn",
        "woman",
        "patient",
        "normal",
        "weight",
        "visit",
        "check",
        "today",
        "feeding",
        "breathing",
        "feeling",
        "taking",
        "having",
        "coming",
        "going",
        "doing",
        "better",
        "good",
        "fine",
        "well",
        "healthy",
        "medicine",
        "tablet",
        "vaccine",
        "vaccines",
        "immunisation",
        "immunization",
    }
)


def _fuzzy_match_entry(clause_norm: str, entry: DangerSignEntry) -> tuple[str, int, int, float] | None:
    """Guarded token-window fuzzy matching using stdlib difflib for ASR spelling noise."""
    if not entry.fuzzy_targets:
        return None

    tokens = clause_norm.split()
    if not tokens:
        return None

    # Precompute token spans in clause_norm
    spans: list[tuple[int, int]] = []
    cursor = 0
    for tok in tokens:
        idx = clause_norm.find(tok, cursor)
        spans.append((idx, idx + len(tok)))
        cursor = idx + len(tok)

    best: tuple[str, int, int, float] | None = None
    for target in entry.fuzzy_targets:
        t_norm = normalize_text(target)
        t_tokens = t_norm.split()
        n = len(t_tokens)
        if n == 0 or len(tokens) < n:
            continue
        if n == 1 and len(t_norm) < 7:
            # Skip short single-word fuzzy matching to prevent false positives
            continue

        threshold = 0.86 if n == 1 else 0.83
        for i in range(len(tokens) - n + 1):
            window_tokens = tokens[i : i + n]
            if n == 1 and window_tokens[0] in _FUZZY_STOPWORDS:
                continue
            window_str = " ".join(window_tokens)
            # Quick length-ratio filter
            if abs(len(window_str) - len(t_norm)) > max(3, int(len(t_norm) * 0.28)):
                continue
            ratio = difflib.SequenceMatcher(None, window_str, t_norm).ratio()
            if ratio >= threshold:
                if best is None or ratio > best[3]:
                    best = (window_str, spans[i][0], spans[i + n - 1][1], ratio)
    return best


# =============================================================================
# Public Detection Entrypoint
# =============================================================================

def detect_danger_signs(
    text: str,
    language: str = "hi-IN",
    context: dict[str, Any] | None = None,
) -> DetectionResult:
    """Detect verified maternal and newborn danger signs deterministically.

    Parameters
    ----------
    text:
        Raw ASR transcript (partial or final) in English, Hindi/Hinglish, Kannada, or Tamil.
    language:
        Active conversation language code (e.g., ``"hi-IN"``, ``"en-IN"``, ``"kn-IN"``, ``"ta-IN"``).
    context:
        Optional dict with keys ``is_partial`` (bool), ``visit_type`` (str | None),
        and ``subject`` (str | None).
    """
    is_partial = bool((context or {}).get("is_partial", False))
    active_lang = language or "hi-IN"

    if not text or not text.strip():
        return DetectionResult(
            danger_sign_flagged=False,
            escalation_required=False,
            matches=[],
            uncertain_matches=[],
            suppressed_context_matches=[],
            active_language=active_lang,
            referral_message=None,
            is_partial=is_partial,
        )

    clauses = split_clauses(text)

    confirmed_raw: list[DangerMatch] = []
    uncertain_raw: list[DangerMatch] = []
    suppressed: list[dict[str, str]] = []

    prior_category: str | None = None
    prior_subject: str | None = None

    for clause in clauses:
        clause_exact = normalize_for_exact(clause)
        clause_norm = normalize_text(clause)
        if not clause_norm:
            continue

        inferred_category, inferred_subject = _infer_clause_phase_and_subject(
            clause_norm=clause_norm,
            prior_category=prior_category,
            prior_subject=prior_subject,
            context=context,
        )
        if inferred_category is not None:
            prior_category = inferred_category
        if inferred_subject is not None:
            prior_subject = inferred_subject
        has_hedge = bool(_HEDGE_RE.search(clause_norm))

        # Step 1: Quantitative clinical thresholds
        _detect_thresholds_in_clause(
            clause_raw=clause,
            clause_norm=clause_norm,
            inferred_category=inferred_category,
            inferred_subject=inferred_subject,
            confirmed=confirmed_raw,
            uncertain=uncertain_raw,
            suppressed=suppressed,
        )

        # Step 2: Phrase-level exact / alias / normalized / fuzzy / uncertain matching
        for entry in DANGER_SIGN_CATALOG:
            hit_phrase: str | None = None
            hit_type: str | None = None
            hit_conf: float = 0.0
            hit_span: tuple[int, int] | None = None
            is_uncertain_hit = False

            # 2a. Exact match on lightly normalized text
            for phrase in entry.exact_phrases:
                p_exact = normalize_for_exact(phrase)
                m = _contains_phrase(clause_exact, p_exact)
                if m:
                    # Map span into clause_norm for context check
                    p_norm = normalize_text(phrase)
                    m_norm = _contains_phrase(clause_norm, p_norm)
                    hit_phrase = phrase
                    hit_type = "exact"
                    hit_conf = 0.96
                    hit_span = m_norm.span() if m_norm else (0, len(clause_norm))
                    break

            # 2b. Multilingual alias match on lightly normalized text
            if hit_phrase is None:
                for alias in entry.aliases:
                    a_exact = normalize_for_exact(alias)
                    m = _contains_phrase(clause_exact, a_exact)
                    if m:
                        a_norm = normalize_text(alias)
                        m_norm = _contains_phrase(clause_norm, a_norm)
                        hit_phrase = alias
                        hit_type = "alias"
                        hit_conf = 0.91
                        hit_span = m_norm.span() if m_norm else (0, len(clause_norm))
                        break

            # 2c. Normalized ASR-spelling match on full normalized text
            if hit_phrase is None:
                for candidate in (*entry.exact_phrases, *entry.aliases):
                    c_norm = normalize_text(candidate)
                    m_norm = _contains_phrase(clause_norm, c_norm)
                    if m_norm:
                        hit_phrase = candidate
                        hit_type = "normalized"
                        hit_conf = 0.87
                        hit_span = m_norm.span()
                        break

            # 2d. Guarded fuzzy match (skipped on short partial transcripts to avoid cut-off noise)
            if hit_phrase is None and (not is_partial or len(clause_norm.split()) >= 3):
                fuzzy_res = _fuzzy_match_entry(clause_norm, entry)
                if fuzzy_res is not None:
                    f_phrase, f_start, f_end, f_ratio = fuzzy_res
                    hit_phrase = f_phrase
                    hit_type = "fuzzy"
                    hit_conf = min(0.85, round(f_ratio * 0.92, 3))
                    hit_span = (f_start, f_end)

            # 2e. Conservative uncertain / ambiguous cues
            if hit_phrase is None and entry.uncertain_phrases:
                for u_phrase in entry.uncertain_phrases:
                    u_norm = normalize_text(u_phrase)
                    m_norm = _contains_phrase(clause_norm, u_norm)
                    if m_norm:
                        # Special clinical rule: in newborn context, ANY reported fever is confirmed NB_FEVER!
                        if entry.canonical_id == "ANC_HIGH_FEVER" and (
                            inferred_subject == "newborn" or inferred_category == "Newborn"
                        ):
                            hit_phrase = u_phrase
                            hit_type = "alias"
                            hit_conf = 0.90
                            hit_span = m_norm.span()
                            is_uncertain_hit = False
                        else:
                            hit_phrase = u_phrase
                            hit_type = "alias"
                            hit_conf = 0.58
                            hit_span = m_norm.span()
                            is_uncertain_hit = True
                        break

            if hit_phrase is None or hit_type is None or hit_span is None:
                continue

            # Disambiguate cross-phase canonical ID
            resolved_entry = _select_disambiguated_entry(entry, inferred_category, inferred_subject)

            # Check context suppression (historical, other-person, negation)
            reason = _check_suppression_context(
                clause_norm=clause_norm,
                match_start=hit_span[0],
                match_end=hit_span[1],
                matched_phrase=hit_phrase,
                entry=entry,
            )
            if reason:
                suppressed.append(
                    {
                        "canonical_id": resolved_entry.canonical_id,
                        "matched_phrase": hit_phrase,
                        "reason": reason,
                        "clause": clause.strip()[:160],
                    }
                )
                continue

            # Apply conservative hedge downgrade ONLY for non-catastrophic graded signs
            if not is_uncertain_hit and has_hedge and resolved_entry.allow_hedge_downgrade:
                is_uncertain_hit = True
                hit_conf = min(hit_conf, 0.62)

            match = _make_match(
                entry=resolved_entry,
                matched_phrase=hit_phrase,
                evidence_text=clause,
                confidence=hit_conf,
                match_type=hit_type,
                requires_clarification=is_uncertain_hit,
            )
            if is_uncertain_hit:
                uncertain_raw.append(match)
            else:
                confirmed_raw.append(match)

    # Deduplicate confirmed matches by canonical_id (keeping highest confidence)
    best_confirmed: dict[str, DangerMatch] = {}
    for m in confirmed_raw:
        existing = best_confirmed.get(m.canonical_id)
        if existing is None or m.confidence > existing.confidence:
            best_confirmed[m.canonical_id] = m

    # Deduplicate uncertain matches, excluding any canonical_id already confirmed
    best_uncertain: dict[str, DangerMatch] = {}
    for m in uncertain_raw:
        if m.canonical_id in best_confirmed:
            continue
        existing = best_uncertain.get(m.canonical_id)
        if existing is None or m.confidence > existing.confidence:
            best_uncertain[m.canonical_id] = m

    # Deduplicate suppressed records
    dedup_suppressed: list[dict[str, str]] = []
    seen_suppressed: set[tuple[str, str, str]] = set()
    for s in suppressed:
        key = (s["canonical_id"], s["reason"], s["clause"])
        if key not in seen_suppressed:
            seen_suppressed.add(key)
            dedup_suppressed.append(s)

    matches = list(best_confirmed.values())
    uncertain_matches = list(best_uncertain.values())
    flagged = len(matches) > 0

    return DetectionResult(
        danger_sign_flagged=flagged,
        escalation_required=flagged,
        matches=matches,
        uncertain_matches=uncertain_matches,
        suppressed_context_matches=dedup_suppressed,
        active_language=active_lang,
        referral_message=get_referral_message(active_lang) if flagged else None,
        is_partial=is_partial,
    )


# =============================================================================
# Layer-2 Advisory Merge (Safety Invariant: LLM can NEVER suppress Layer 1)
# =============================================================================

def llm_advisory_merge(
    layer1: DetectionResult,
    llm_flags: list[str] | None = None,
    llm_clarification_needed: bool = False,
) -> DetectionResult:
    """Merge advisory Layer-2 LLM signals with deterministic Layer-1 output.

    Safety Invariant
    ----------------
    Layer 2 LLM can NEVER downgrade, remove, or cancel any Layer-1 positive match,
    ``danger_sign_flagged``, ``escalation_required``, or ``referral_message``.
    Catalog-verified LLM flags not already confirmed by Layer 1 are surfaced as
    ``uncertain_matches`` (``requires_clarification=True``) so the assistant asks
    a conservative clarifying question without letting the LLM act as sole detector.
    """
    merged_matches = [m.model_copy(deep=True) for m in layer1.matches]
    merged_uncertain = [m.model_copy(deep=True) for m in layer1.uncertain_matches]
    merged_suppressed = [dict(s) for s in layer1.suppressed_context_matches]

    confirmed_ids = {m.canonical_id for m in merged_matches}
    uncertain_ids = {m.canonical_id for m in merged_uncertain}

    if llm_flags:
        for flag in llm_flags:
            if not isinstance(flag, str):
                continue
            entry = CATALOG_BY_ID.get(flag.strip().upper())
            if entry is None:
                # Ignore unverified/hallucinated IDs not grounded in DANGER_SIGN_GUIDELINES.md
                continue
            if entry.canonical_id in confirmed_ids or entry.canonical_id in uncertain_ids:
                continue
            merged_uncertain.append(
                DangerMatch(
                    canonical_id=entry.canonical_id,
                    canonical_name=entry.canonical_name,
                    subject=entry.subject,
                    category=entry.category,
                    matched_phrase="llm_advisory",
                    evidence_text="Advisory Layer-2 signal requiring worker clarification",
                    confidence=0.65,
                    match_type="alias",
                    source_doc=entry.source_doc,
                    source_section=entry.source_section,
                    requires_clarification=True,
                )
            )
            uncertain_ids.add(entry.canonical_id)

    if llm_clarification_needed:
        for um in merged_uncertain:
            um.requires_clarification = True

    # Layer-1 positive flags are strictly immutable (can NEVER flip True -> False)
    flagged = layer1.danger_sign_flagged or len(merged_matches) > 0
    escalation = layer1.escalation_required or flagged
    referral = layer1.referral_message
    if flagged and not referral:
        referral = get_referral_message(layer1.active_language)

    return DetectionResult(
        danger_sign_flagged=flagged,
        escalation_required=escalation,
        matches=merged_matches,
        uncertain_matches=merged_uncertain,
        suppressed_context_matches=merged_suppressed,
        active_language=layer1.active_language,
        referral_message=referral,
        is_partial=layer1.is_partial,
    )
