"""Deterministic multilingual & code-mixed healthcare visit field extractor.

Extracts structured ASHA home-visit fields from Indic + English code-mixed ASR
transcripts without guessing missing facts, fabricating beneficiary IDs, or
performing clinical diagnosis / danger-sign classification.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.extraction.models import (
    ExtractionResult,
    FieldClarification,
    FollowUpAction,
    VisitDraft,
    VisitType,
)
from app.services.beneficiaries import (
    SyntheticBeneficiary,
    SyntheticBeneficiaryDirectory,
)

# ---------------------------------------------------------------------------
# Digit & text normalization tables
# ---------------------------------------------------------------------------

_INDIC_DIGIT_TRANS = str.maketrans(
    "०१२३४५६७८९"  # Devanagari
    "೦೧೨೩೪೫೬೭೮೯"  # Kannada
    "௦௧௨௩௪௫௬௭௮௯",  # Tamil
    "0123456789" * 3,
)

# Boundary helpers that work reliably with Indic combining marks (matras/virama).
_INDIC_CHAR_CLASS = r"A-Za-z0-9_\u0900-\u097F\u0B80-\u0BFF\u0C80-\u0CFF"
_LB = rf"(?<![{_INDIC_CHAR_CLASS}])"
_RB = rf"(?![{_INDIC_CHAR_CLASS}])"


def _normalize_text(text: str) -> str:
    """Normalize Unicode NFC, Indic numerals to ASCII digits, and collapse whitespace."""
    normalized = unicodedata.normalize("NFC", text).translate(_INDIC_DIGIT_TRANS)
    return re.sub(r"\s+", " ", normalized).strip()


def _wb_pattern(phrase: str) -> str:
    """Build a token-bounded regex pattern safe for Latin and Indic scripts."""
    escaped = re.escape(phrase)
    escaped = escaped.replace(r"\ ", r"\s+")
    return rf"{_LB}{escaped}{_RB}"


# ---------------------------------------------------------------------------
# Number word dictionaries (English + Hindi / Hinglish / Devanagari)
# ---------------------------------------------------------------------------

_EN_UNITS: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}

_EN_TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fourty": 40,  # common ASR spelling
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

_EN_ORDINALS: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
    "sixteenth": 16,
    "seventeenth": 17,
    "eighteenth": 18,
    "nineteenth": 19,
    "twentieth": 20,
    "thirtieth": 30,
}

# Hindi / Hinglish cardinals (0..100 + multipliers)
_HI_NUMBERS: dict[str, int] = {
    "shunya": 0,
    "ek": 1,
    "do": 2,
    "teen": 3,
    "tin": 3,
    "char": 4,
    "chaar": 4,
    "panch": 5,
    "paanch": 5,
    "chhe": 6,
    "cheh": 6,
    "chhah": 6,
    "saat": 7,
    "sat": 7,
    "aath": 8,
    "ath": 8,
    "nau": 9,
    "das": 10,
    "gyarah": 11,
    "gyara": 11,
    "barah": 12,
    "bara": 12,
    "terah": 13,
    "tera": 13,
    "chaudah": 14,
    "chauda": 14,
    "pandrah": 15,
    "pandra": 15,
    "solah": 16,
    "satrah": 17,
    "atharah": 18,
    "unnis": 19,
    "bees": 20,
    "bis": 20,
    "ikkis": 21,
    "bais": 22,
    "teis": 23,
    "chaubis": 24,
    "pachchis": 25,
    "pachis": 25,
    "chhabbis": 26,
    "sattais": 27,
    "atthais": 28,
    "untis": 29,
    "tees": 30,
    "tis": 30,
    "paitis": 35,
    "paintis": 35,
    "chalis": 40,
    "chaalis": 40,
    "bayalis": 42,
    "paintalis": 45,
    "paitalis": 45,
    "adtalis": 48,
    "artalis": 48,
    "pachas": 50,
    "pachaas": 50,
    "ikyawan": 51,
    "bawan": 52,
    "baawan": 52,
    "tirpan": 53,
    "chauwan": 54,
    "pachpan": 55,
    "chhappan": 56,
    "sattawan": 57,
    "atthawan": 58,
    "unsath": 59,
    "saath": 60,
    "sath": 60,
    "iksath": 61,
    "basath": 62,
    "painsath": 65,
    "sattar": 70,
    "pachhattar": 75,
    "assi": 80,
    "nabbe": 90,
    "sau": 100,
    # Devanagari
    "शून्य": 0,
    "एक": 1,
    "दो": 2,
    "तीन": 3,
    "चार": 4,
    "पांच": 5,
    "पाँच": 5,
    "छह": 6,
    "छे": 6,
    "सात": 7,
    "आठ": 8,
    "नौ": 9,
    "दस": 10,
    "ग्यारह": 11,
    "बारह": 12,
    "तेरह": 13,
    "चौदह": 14,
    "पंद्रह": 15,
    "पन्द्रह": 15,
    "सोलह": 16,
    "सत्रह": 17,
    "अठारह": 18,
    "उन्नीस": 19,
    "बीस": 20,
    "इक्कीस": 21,
    "बाईस": 22,
    "तेईस": 23,
    "चौबीस": 24,
    "पच्चीस": 25,
    "छब्बीस": 26,
    "सत्ताईस": 27,
    "अट्ठाईस": 28,
    "अठ्ठाईस": 28,
    "उनतीस": 29,
    "तीस": 30,
    "इकतीस": 31,
    "पैंतीस": 35,
    "चालीस": 40,
    "बयालीस": 42,
    "पैंतालीस": 45,
    "अड़तालीस": 48,
    "पचास": 50,
    "इक्यावन": 51,
    "बावन": 52,
    "तिरपन": 53,
    "चौवन": 54,
    "पचपन": 55,
    "छप्पन": 56,
    "सत्तावन": 57,
    "अट्ठावन": 58,
    "उनसठ": 59,
    "साठ": 60,
    "बासठ": 62,
    "पैंसठ": 65,
    "सत्तर": 70,
    "पचहत्तर": 75,
    "अस्सी": 80,
    "नब्बे": 90,
    "सौ": 100,
}

_MULTIPLIERS: dict[str, int] = {
    "hundred": 100,
    "sau": 100,
    "सौ": 100,
    "thousand": 1000,
    "hazar": 1000,
    "hazaar": 1000,
    "हजार": 1000,
    "हज़ार": 1000,
}

_DECIMAL_WORDS: frozenset[str] = frozenset(
    {"point", "dot", "dashamlav", "दशमलव", "पॉइंट", "प्वाइंट"}
)

_FRACTION_IDIOMS: dict[str, float] = {
    "half": 0.5,
    "aadha": 0.5,
    "adha": 0.5,
    "आधा": 0.5,
    "dedh": 1.5,
    "derh": 1.5,
    "डेढ़": 1.5,
    "डेढ": 1.5,
    "dhai": 2.5,
    "dhaai": 2.5,
    "adhaai": 2.5,
    "ढाई": 2.5,
    "अढ़ाई": 2.5,
}

_PREFIX_FRACTIONS: dict[str, float] = {
    "sawa": 0.25,
    "sava": 0.25,
    "सवा": 0.25,
    "sadhe": 0.5,
    "saadhe": 0.5,
    "साढ़े": 0.5,
    "साढे": 0.5,
    "paune": -0.25,
    "पौने": -0.25,
}

_CONNECTOR_WORDS: frozenset[str] = frozenset({"and", "a", "aur", "और"})

# Tokens allowed to START a spoken numeric expression (excludes connectors like "and"/"aur"/"a").
_NUMBER_START_TOKENS: frozenset[str] = (
    frozenset(_EN_UNITS)
    | frozenset(_EN_TENS)
    | frozenset(_EN_ORDINALS)
    | frozenset(_HI_NUMBERS)
    | frozenset(_MULTIPLIERS)
    | frozenset(_FRACTION_IDIOMS)
    | frozenset(_PREFIX_FRACTIONS)
)

# All tokens allowed inside a spoken numeric expression.
_NUMBER_WORD_TOKENS: frozenset[str] = (
    _NUMBER_START_TOKENS | _DECIMAL_WORDS | _CONNECTOR_WORDS
)


def _parse_int_tokens(tokens: list[str]) -> int | None:
    """Parse a sequence of integer number words (English/Hindi/digits) into an int."""
    if not tokens:
        return None
    total = 0
    current = 0
    consumed_number = False
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in {"and", "a", "aur", "और"}:
            i += 1
            continue
        if re.fullmatch(r"\d+", tok):
            current += int(tok)
            consumed_number = True
        elif tok in _EN_UNITS:
            current += _EN_UNITS[tok]
            consumed_number = True
        elif tok in _EN_TENS:
            current += _EN_TENS[tok]
            consumed_number = True
        elif tok in _EN_ORDINALS:
            current += _EN_ORDINALS[tok]
            consumed_number = True
        elif tok in _HI_NUMBERS:
            val = _HI_NUMBERS[tok]
            if val == 100:
                current = (current or 1) * 100
            else:
                current += val
            consumed_number = True
        elif tok in _MULTIPLIERS:
            mult = _MULTIPLIERS[tok]
            if mult >= 1000:
                total += (current or 1) * mult
                current = 0
            else:
                current = (current or 1) * mult
            consumed_number = True
        else:
            return None
        i += 1
    if not consumed_number:
        return None
    return total + current


def _parse_number_phrase(phrase: str) -> float | None:
    """Parse numeric, spoken English, spoken Hindi, or fractional quantity phrases."""
    cleaned = phrase.strip().lower().replace("-", " ")
    if not cleaned:
        return None

    tokens = [t for t in cleaned.split() if t]
    while tokens and tokens[0] in _CONNECTOR_WORDS:
        tokens.pop(0)
    while tokens and tokens[-1] in _CONNECTOR_WORDS:
        tokens.pop()
    if not tokens:
        return None

    # Direct float/int
    if len(tokens) == 1 and re.fullmatch(r"\d+(?:\.\d+)?", tokens[0]):
        return float(tokens[0])

    # Single-word Hindi/English fraction idioms ("dhai", "ढाई", "dedh", "आधा")
    if len(tokens) == 1 and tokens[0] in _FRACTION_IDIOMS:
        return _FRACTION_IDIOMS[tokens[0]]

    # Standalone "sawa" (= 1.25)
    if len(tokens) == 1 and tokens[0] in {"sawa", "sava", "सवा"}:
        return 1.25

    # Prefix fractions: "साढ़े तीन" -> 3.5, "सवा तीन" -> 3.25, "पौने तीन" -> 2.75
    if tokens[0] in _PREFIX_FRACTIONS and len(tokens) >= 2:
        base = _parse_int_tokens(tokens[1:])
        if base is not None and base > 0:
            return base + _PREFIX_FRACTIONS[tokens[0]]

    # "three and a half" / "two and half" / "3 and a half"
    if len(tokens) >= 3 and tokens[-1] == "half" and tokens[-2] in {"a", "and"}:
        cut = -3 if tokens[-2] == "a" and len(tokens) >= 4 and tokens[-3] == "and" else -2
        base = _parse_int_tokens(tokens[:cut])
        if base is not None:
            return base + 0.5

    # Decimal word: "two point eight", "48 point 5", "दो दशमलव आठ"
    for idx, tok in enumerate(tokens):
        if tok in _DECIMAL_WORDS and 0 < idx < len(tokens) - 1:
            int_part = _parse_int_tokens(tokens[:idx])
            frac_tokens = tokens[idx + 1 :]
            if int_part is None:
                return None
            # Support single-digit sequence ("point eight five" -> .85) or numeric ("point 8")
            if len(frac_tokens) == 1 and re.fullmatch(r"\d+", frac_tokens[0]):
                return float(f"{int_part}.{frac_tokens[0]}")
            frac_digits: list[str] = []
            for ft in frac_tokens:
                if re.fullmatch(r"\d+", ft):
                    frac_digits.append(ft)
                elif ft in _EN_UNITS and _EN_UNITS[ft] < 10:
                    frac_digits.append(str(_EN_UNITS[ft]))
                elif ft in _HI_NUMBERS and _HI_NUMBERS[ft] < 10:
                    frac_digits.append(str(_HI_NUMBERS[ft]))
                else:
                    return None
            return float(f"{int_part}.{''.join(frac_digits)}")

    int_val = _parse_int_tokens(tokens)
    return float(int_val) if int_val is not None else None


# ---------------------------------------------------------------------------
# Weight extraction patterns
# ---------------------------------------------------------------------------

_KG_UNITS = (
    "kilograms",
    "kilogram",
    "kilos",
    "kilo",
    "kgs",
    "kg",
    "किलोग्राम",
    "किग्रा",
    "किलो",
    "केजी",
    "ಕೆಜಿ",
    "கிலோ",
)
_GRAM_UNITS = (
    "grams",
    "gram",
    "gms",
    "gm",
    "g",
    "ग्राम",
    "गराम",
    "ಗ್ರಾಂ",
    "கிராம்",
)
_WEIGHT_CUES = (
    "weight",
    "wt",
    "wajan",
    "vajan",
    "wazan",
    "vazan",
    "ववेट",  # real Gnani Prisma ASR artifact
    "वेइट",
    "वेट",
    "वज़न",
    "वजन",
    "भार",
    "ತೂಕ",
    "எடை",
)

_KG_UNIT_RE = "(?:" + "|".join(re.escape(u) for u in _KG_UNITS) + ")"
_GRAM_UNIT_RE = "(?:" + "|".join(re.escape(u) for u in _GRAM_UNITS) + ")"
_WEIGHT_CUE_RE = "(?:" + "|".join(re.escape(c) for c in _WEIGHT_CUES) + ")"

# Token pattern for a spoken or numeric quantity (1..6 tokens; cannot start with connectors)
_QTY_START_TOKEN = (
    r"(?:\d+(?:\.\d+)?|"
    + "|".join(re.escape(w) for w in sorted(_NUMBER_START_TOKENS, key=len, reverse=True))
    + r")"
)
_QTY_CONT_TOKEN = (
    r"(?:\d+(?:\.\d+)?|"
    + "|".join(re.escape(w) for w in sorted(_NUMBER_WORD_TOKENS, key=len, reverse=True))
    + r")"
)
_QTY_PHRASE = rf"(?:{_QTY_START_TOKEN}(?:[\s\-]+{_QTY_CONT_TOKEN}){{0,5}})"

# Pattern 1: Compound kg + gram ("3 kilo 200 gram", "three kilo two hundred grams")
_COMPOUND_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{_LB}{_WEIGHT_CUE_RE}{_RB}\s*(?:is|hai|है|=|:)?\s*)?"
    rf"(?P<kg_qty>{_LB}{_QTY_PHRASE}{_RB})\s*(?P<kg_unit>{_KG_UNIT_RE}{_RB})"
    rf"\s*(?:and|aur|और|,)?\s*"
    rf"(?P<g_qty>{_LB}{_QTY_PHRASE}{_RB})\s*(?P<g_unit>{_GRAM_UNIT_RE}{_RB})",
    re.IGNORECASE,
)

# Pattern 2: Numeric+attached unit or spoken phrase + kg unit
_KG_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{_LB}{_WEIGHT_CUE_RE}{_RB}\s*(?:is|hai|है|=|:)?\s*)?"
    rf"(?P<qty>{_LB}{_QTY_PHRASE})\s*(?P<unit>{_KG_UNIT_RE}{_RB})",
    re.IGNORECASE,
)

# Pattern 3: Numeric+attached unit or spoken phrase + gram unit
_GRAM_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{_LB}{_WEIGHT_CUE_RE}{_RB}\s*(?:is|hai|है|=|:)?\s*)?"
    rf"(?P<qty>{_LB}{_QTY_PHRASE})\s*(?P<unit>{_GRAM_UNIT_RE}{_RB})",
    re.IGNORECASE,
)

# Pattern 4: Explicit weight cue followed by unitless quantity ("weight is 2.8", "वजन 52")
_CUE_ONLY_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{_LB}{_WEIGHT_CUE_RE}{_RB})\s*(?:is|was|hai|है|था|=|:)?\s*"
    rf"(?P<qty>{_LB}{_QTY_PHRASE}{_RB})",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Visit type patterns
# ---------------------------------------------------------------------------

_VISIT_TYPE_PATTERNS: dict[VisitType, tuple[re.Pattern[str], ...]] = {
    "ANC": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "anc",
            "a.n.c",
            "antenatal",
            "ante-natal",
            "ante natal",
            "pregnancy checkup",
            "pregnancy visit",
            "pregnant visit",
            "pregnant checkup",
            "garbhavati",
            "garbhwati",
            "garbhavastha",
            "गर्भवती",
            "गर्भावस्था",
            "एएनसी",
            "प्रसव पूर्व",
            "गर्भ जांच",
            "ಗರ್ಭಿಣಿ",
            "கர்ப்பிணி",
        )
    ),
    "PNC": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "pnc",
            "p.n.c",
            "postnatal",
            "post-natal",
            "post natal",
            "postpartum",
            "post partum",
            "after delivery",
            "delivery ke baad",
            "prasav ke baad",
            "prasavottar",
            "जच्चा",
            "प्रसव के बाद",
            "डिलीवरी के बाद",
            "पीएनसी",
            "प्रसवोत्तर",
            "ಬಾಣಂತಿ",
            "பிரசவத்திற்கு பிறகு",
        )
    ),
    "Newborn": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "newborn",
            "new born",
            "hbnc",
            "h.b.n.c",
            "neonate",
            "neonatal",
            "navjat",
            "navjaat",
            "shishu",
            "baby checkup",
            "baby visit",
            "baby weight",
            "नवजात",
            "शिशु",
            "एचबीएनसी",
            "ನವಜಾತ",
            "பிறந்த குழந்தை",
        )
    ),
    "Immunisation": tuple(
        re.compile(_wb_pattern(p), re.IGNORECASE)
        for p in (
            "immunisation",
            "immunization",
            "tikakaran",
            "teekakaran",
            "vaccine visit",
            "vaccination visit",
            "tika visit",
            "टीकाकरण",
            "टीका विजिट",
            "ಲಸಿಕೆ",
            "தடுப்பூசி",
        )
    ),
}

_SECONDARY_NEWBORN_PATTERN = re.compile(_wb_pattern("baby"), re.IGNORECASE)
_SECONDARY_IMMUNISATION_PATTERN = re.compile(
    rf"{_LB}(?:vaccination|vaccines?){_RB}", re.IGNORECASE
)

# ---------------------------------------------------------------------------
# Vaccination patterns
# ---------------------------------------------------------------------------

_VACCINE_SPECS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Hepatitis B", ("hepatitis b", "hep b", "hep-b", "hepb", "हेपेटाइटिस बी")),
    (
        "Pentavalent",
        (
            "pentavalent",
            "penta-1",
            "penta-2",
            "penta-3",
            "penta 1",
            "penta 2",
            "penta 3",
            "penta1",
            "penta2",
            "penta3",
            "penta",
            "पेंटावैलेंट",
            "पेंटा",
        ),
    ),
    ("Rotavirus", ("rotavirus", "rota virus", "rota", "rvv", "रोटावायरस", "रोटा")),
    (
        "OPV",
        (
            "opv-0",
            "opv-1",
            "opv-2",
            "opv-3",
            "opv 0",
            "opv 1",
            "opv 2",
            "opv 3",
            "opv0",
            "opv1",
            "opv2",
            "opv3",
            "opv",
            "o.p.v",
            "polio drops",
            "polio",
            "ओपीवी",
            "पोलियो",
        ),
    ),
    ("BCG", ("bcg", "b.c.g", "बीसीजी")),
    ("PCV", ("pcv-1", "pcv-2", "pcv booster", "pcv", "p.c.v", "pneumococcal", "पीसीवी")),
    ("IPV", ("fipv", "ipv-1", "ipv-2", "ipv", "i.p.v", "आईपीवी")),
    ("DPT", ("dpt booster", "dpt-1", "dpt-2", "dpt", "d.p.t", "डीपीटी")),
    (
        "MR",
        (
            "measles rubella",
            "measles-rubella",
            "measles",
            "mr-1",
            "mr-2",
            "mr 1",
            "mr 2",
            "mr1",
            "mr2",
            "mr",
            "m.r",
            "खसरा",
            "एमआर",
        ),
    ),
    (
        "Td",
        (
            "td booster",
            "td-1",
            "td-2",
            "td 1",
            "td 2",
            "td1",
            "td2",
            "td",
            "t.d",
            "टीडी",
        ),
    ),
    (
        "TT",
        (
            "tt booster",
            "tt-1",
            "tt-2",
            "tt 1",
            "tt 2",
            "tt1",
            "tt2",
            "tt",
            "t.t",
            "tetanus",
            "टीटी",
            "टी.टी",
            "टिटनेस",
        ),
    ),
)

_COMPILED_VACCINES: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = tuple(
    (name, tuple(re.compile(_wb_pattern(p), re.IGNORECASE) for p in aliases))
    for name, aliases in _VACCINE_SPECS
)

_VACCINE_DUE_CUES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(_wb_pattern(p), re.IGNORECASE)
    for p in (
        "not yet given",
        "not given",
        "not done",
        "not completed",
        "not received",
        "not taken",
        "not administered",
        "to be given",
        "still due",
        "pending",
        "overdue",
        "due",
        "remaining",
        "missed",
        "upcoming",
        "scheduled",
        "baaki",
        "baki",
        "bakaya",
        "nahi laga",
        "nahin laga",
        "nahi lagi",
        "nahin lagi",
        "nahi diya",
        "nahin diya",
        "nahi hua",
        "nahin hua",
        "nahi hui",
        "nahin hui",
        "abhi nahi",
        "dena hai",
        "lagna hai",
        "lagwana hai",
        "बाकी",
        "बकाया",
        "नहीं लगा",
        "नहीं लगी",
        "नहीं दिया",
        "नहीं हुआ",
        "नहीं हुई",
        "अभी नहीं",
        "देना है",
        "लगना है",
        "लगवाना है",
        "ಬಾಕಿ",
        "ಕೊಟ್ಟಿಲ್ಲ",
        "ಹಾಕಬೇಕು",
        "ಕೊಡಬೇಕು",
        "பாக்கி",
        "போடவில்லை",
        "போடணும்",
        "கொடுக்கணும்",
        "போட வேண்டும்",
        "நிலுவை",
    )
)

_VACCINE_COMPLETED_CUES: tuple[re.Pattern[str], ...] = tuple(
    re.compile(_wb_pattern(p), re.IGNORECASE)
    for p in (
        "given",
        "done",
        "completed",
        "administered",
        "received",
        "taken",
        "finished",
        "vaccinated",
        "lag gaya",
        "lag gayi",
        "lag gai",
        "laga diya",
        "lag chuka",
        "lag chuki",
        "de diya",
        "de di",
        "ho gaya",
        "ho gayi",
        "ho gai",
        "mil gaya",
        "mil gayi",
        "போட்டாச்சு",
        "போட்டுவிட்டேன்",
        "கொடுத்தாச்சு",
        "போட்டேன்",
        "ಹಾಕಿದೆ",
        "ಕೊಟ್ಟಿದೆ",
        "ಲಸಿಕೆ ಹಾಕಲಾಗಿದೆ",
        "लग गया",
        "लग गई",
        "लगा दिया",
        "दे दिया",
        "हो गया",
        "हो गई",
        "मिल गया",
        "ಕೊಟ್ಟಿದೆ",
        "ಹಾಕಿದೆ",
        "போட்டாச்சு",
        "கொடுத்தாச்சு",
    )
)

# ---------------------------------------------------------------------------
# Date parsing tables & patterns
# ---------------------------------------------------------------------------

_MONTH_NAMES: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "जनवरी": 1,
    "feb": 2,
    "february": 2,
    "फरवरी": 2,
    "mar": 3,
    "march": 3,
    "मार्च": 3,
    "apr": 4,
    "april": 4,
    "अप्रैल": 4,
    "may": 5,
    "मई": 5,
    "jun": 6,
    "june": 6,
    "जून": 6,
    "jul": 7,
    "july": 7,
    "जुलाई": 7,
    "aug": 8,
    "august": 8,
    "अगस्त": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "सितंबर": 9,
    "सितम्बर": 9,
    "oct": 10,
    "october": 10,
    "अक्टूबर": 10,
    "अक्तूबर": 10,
    "nov": 11,
    "november": 11,
    "नवंबर": 11,
    "नवम्बर": 11,
    "dec": 12,
    "december": 12,
    "दिसंबर": 12,
    "दिसम्बर": 12,
}

_WEEKDAY_FULL_NAMES: dict[str, int] = {
    "monday": 0,
    "somwar": 0,
    "somvar": 0,
    "सोमवार": 0,
    "tuesday": 1,
    "mangalwar": 1,
    "mangalvar": 1,
    "मंगलवार": 1,
    "wednesday": 2,
    "budhwar": 2,
    "budhvar": 2,
    "बुधवार": 2,
    "thursday": 3,
    "guruwar": 3,
    "guruvar": 3,
    "brihaspatiwar": 3,
    "गुरुवार": 3,
    "बृहस्पतिवार": 3,
    "friday": 4,
    "shukrawar": 4,
    "shukravar": 4,
    "शुक्रवार": 4,
    "saturday": 5,
    "shaniwar": 5,
    "shanivar": 5,
    "शनिवार": 5,
    "sunday": 6,
    "rabiwar": 6,
    "raviwar": 6,
    "ravivar": 6,
    "रविवार": 6,
}

_WEEKDAY_ABBR_NAMES: dict[str, int] = {
    "mon": 0,
    "tue": 1,
    "tues": 1,
    "wed": 2,
    "thu": 3,
    "thurs": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}

_WEEKDAY_NAMES: dict[str, int] = {**_WEEKDAY_FULL_NAMES, **_WEEKDAY_ABBR_NAMES}

_MONTH_RE = "(?:" + "|".join(re.escape(m) for m in sorted(_MONTH_NAMES, key=len, reverse=True)) + ")"
_WEEKDAY_FULL_RE = "(?:" + "|".join(re.escape(w) for w in sorted(_WEEKDAY_FULL_NAMES, key=len, reverse=True)) + ")"
_WEEKDAY_ABBR_RE = "(?:" + "|".join(re.escape(w) for w in sorted(_WEEKDAY_ABBR_NAMES, key=len, reverse=True)) + ")"

_DAY_WORD_TOKENS = (
    frozenset(_EN_UNITS)
    | frozenset(_EN_TENS)
    | frozenset(_EN_ORDINALS)
    | frozenset(k for k, v in _HI_NUMBERS.items() if 1 <= v <= 31)
)
_DAY_WORD_RE = "(?:" + "|".join(re.escape(w) for w in sorted(_DAY_WORD_TOKENS, key=len, reverse=True)) + ")"
_DAY_EXPR_RE = rf"(?:\d{{1,2}}(?:st|nd|rd|th)?|{_DAY_WORD_RE}(?:[\s\-]+{_DAY_WORD_RE})?)"

_ISO_DATE_RE = re.compile(rf"{_LB}(?P<y>\d{{4}})-(?P<m>\d{{1,2}})-(?P<d>\d{{1,2}}){_RB}")
_DMY_DATE_RE = re.compile(
    rf"{_LB}(?P<d>\d{{1,2}})[/\-\.](?P<m>\d{{1,2}})[/\-\.](?P<y>\d{{2,4}}){_RB}"
)
_DAY_MONTH_RE = re.compile(
    rf"{_LB}(?P<day>{_DAY_EXPR_RE})(?:\s+of)?\s+(?P<month>{_MONTH_RE})(?:,?\s+(?P<year>\d{{4}}))?{_RB}",
    re.IGNORECASE,
)
_MONTH_DAY_RE = re.compile(
    rf"{_LB}(?P<month>{_MONTH_RE})\s+(?P<day>{_DAY_EXPR_RE})(?:,?\s+(?P<year>\d{{4}}))?{_RB}",
    re.IGNORECASE,
)

_COUNT_TOKEN_RE = (
    r"(?:\d+|"
    + "|".join(
        re.escape(w)
        for w in sorted(
            frozenset(_EN_UNITS)
            | frozenset(_EN_TENS)
            | frozenset(_HI_NUMBERS)
            | frozenset({"a", "an"}),
            key=len,
            reverse=True,
        )
    )
    + r")"
)

_COUNT_EXPR_RE = rf"(?:{_COUNT_TOKEN_RE}(?:[\s\-]+{_COUNT_TOKEN_RE})?)"

_AFTER_DAYS_RE = re.compile(
    rf"(?:{_LB}(?:after|in)\s+(?P<n1>{_COUNT_EXPR_RE})\s+(?:days?|din){_RB}|"
    rf"{_LB}(?P<n2>{_COUNT_EXPR_RE})\s+(?:days?\s+(?:later|from\s+now)|din\s+(?:baad|bad|mein|me)|दिन\s+(?:बाद|में)){_RB})",
    re.IGNORECASE,
)
_AFTER_WEEKS_RE = re.compile(
    rf"(?:{_LB}(?:after|in)\s+(?P<n1>{_COUNT_EXPR_RE})\s+(?:weeks?|hafte|hafta|saptah){_RB}|"
    rf"{_LB}(?P<n2>{_COUNT_EXPR_RE})\s+(?:weeks?\s+(?:later|from\s+now)|hafte\s+(?:baad|bad)|saptah\s+(?:baad|bad)|हफ्ते\s+बाद|सप्ताह\s+बाद){_RB})",
    re.IGNORECASE,
)
_NEXT_WEEK_RE = re.compile(
    rf"{_LB}(?:next\s+week|agle\s+hafte|agla\s+hafta|agle\s+saptah|अगले\s+हफ्ते|अगले\s+सप्ताह){_RB}",
    re.IGNORECASE,
)
_WEEKDAY_NEXT_RE = re.compile(
    rf"(?:{_LB}(?:(?:next|coming|on|agle|agla|अगले)\s+)?(?P<wd1>{_WEEKDAY_FULL_RE})(?:\s+(?:ko|को))?{_RB}|"
    rf"{_LB}(?:next|coming|on|agle|agla)\s+(?P<wd2>{_WEEKDAY_ABBR_RE}){_RB})",
    re.IGNORECASE,
)
_TOMORROW_RE = re.compile(rf"{_LB}(?:tomorrow|kal|कल){_RB}", re.IGNORECASE)
_DAY_AFTER_TOMORROW_RE = re.compile(
    rf"{_LB}(?:day\s+after\s+tomorrow|parso|parson|परसों|परसो){_RB}", re.IGNORECASE
)
_PAST_KAL_GUARD_RE = re.compile(
    rf"{_LB}(?:kal|parso|parson|कल|परसों|परसो)\s+(?:se|tha|thi|the|hua|hui|raat|subah\s+se|sham\s+se|aayi|aaya|gaya|gayi|से|था|थी|थे|हुआ|हुई|रात){_RB}",
    re.IGNORECASE,
)
_AMBIGUOUS_DATE_RE = re.compile(
    rf"{_LB}(?:"
    r"some\s*day\s+next\s+month|"
    r"some\s*time\s+next\s+month|"
    r"some\s*day\s+next\s+week|"
    r"some\s*time\s+next\s+week|"
    r"some\s*time\s+later|"
    r"next\s+month|"
    r"agle\s+mahine(?:\s+kisi\s+din)?|"
    r"अगले\s+महीने(?:\s+किसी\s+दिन)?|"
    r"kisi\s+din|"
    r"किसी\s+दिन"
    rf"){_RB}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Follow-up action cues
# ---------------------------------------------------------------------------

_IFA_NON_ADHERENCE_RE = re.compile(
    rf"(?:"
    rf"{_LB}(?:ifa|iron|calcium|आयरन|आईएफए|कैल्शियम)[^,.;।]{{0,45}}"
    rf"(?:nahi\s+le|nahin\s+le|nahi\s+kha|nahin\s+kha|not\s+taking|not\s+regular|irregular|missed|skipped|chhoot|chhut|नहीं\s+ले|नहीं\s+खा|छूट\s+गई){_RB}|"
    rf"{_LB}(?:not\s+taking|missed|skipped|irregular(?:\s+with)?)\s+(?:the\s+)?"
    rf"(?:ifa|iron|calcium)(?:\s+(?:tablets?|pills?|goli))?{_RB}"
    rf")",
    re.IGNORECASE,
)

_WEIGHT_MONITOR_RE = re.compile(
    rf"{_LB}(?:recheck\s+weight|monitor\s+weight|weight\s+monitoring|weight\s+check\s+karna|vajan\s+dobara|wajan\s+dobara|वजन\s+दोबारा){_RB}",
    re.IGNORECASE,
)

_FOLLOWUP_VISIT_CUE_RE = re.compile(
    rf"{_LB}(?:next\s+visit|follow[\s\-]?up(?:\s+visit)?|agla\s+visit|agli\s+visit|अगला\s+विजिट|अगली\s+विजिट|dobara\s+aana|दोबारा\s+आना){_RB}",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Voice correction intent cues
# ---------------------------------------------------------------------------

_CORRECTION_COMMA_RE = re.compile(
    rf"{_LB}(?:no|nahi|nahin|नहीं|नही)\s*[,.:!।\-]",
    re.IGNORECASE,
)
_CORRECTION_START_RE = re.compile(
    r"^\s*(?:no|nope|nahi|nahin|sorry|wait|actually|नहीं|नही|गलत|माफ\s+कीजिए)\s+"
    r"(?!(?:fever|bleeding|headache|swelling|danger|problem|issue|symptom|symptoms|"
    r"bukhar|dard|sujan|dikkat|takleef|complication|complications)\b)",
    re.IGNORECASE,
)
_CORRECTION_INLINE_RE = re.compile(
    rf"{_LB}(?:galat|गलत|wrong|incorrect|actually|correction|correct\s+that|"
    rf"change\s+(?:it|the|weight|visit|date|beneficiary|vaccine)|"
    rf"update\s+(?:it|the|weight|visit|date|beneficiary|vaccine)|"
    rf"i\s+meant|make\s+it|instead|badal\s+do|badlo|sahi\s+karo|theek\s+karo|बदलो|बदल\s+दो|दरअसल){_RB}",
    re.IGNORECASE,
)

# Beneficiary ID regex
_BEN_ID_RE = re.compile(rf"{_LB}B\s*E\s*N[\s\-_]?(\d{{3,6}}){_RB}", re.IGNORECASE)

# Category <-> VisitType compatibility for disambiguation
_VISIT_TYPE_CATEGORIES: dict[VisitType, frozenset[str]] = {
    "ANC": frozenset({"pregnant_woman"}),
    "PNC": frozenset({"postnatal_mother"}),
    "Newborn": frozenset({"newborn"}),
    "Immunisation": frozenset({"infant", "newborn", "pregnant_woman"}),
}


class VisitFieldExtractor:
    """Deterministic extractor & validator for structured ASHA home-visit drafts."""

    def __init__(
        self,
        beneficiary_directory: SyntheticBeneficiaryDirectory | None = None,
        timezone_name: str = "Asia/Kolkata",
    ) -> None:
        self._directory = beneficiary_directory or SyntheticBeneficiaryDirectory()
        self._timezone_name = timezone_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract(
        self,
        text: str,
        *,
        reference_date: date | None = None,
        active_language: str = "hi-IN",
        existing_draft: VisitDraft | None = None,
    ) -> ExtractionResult:
        """Extract only fields grounded in `text`; never guess missing facts."""
        _ = active_language  # Retained for interface parity and future locale hints
        normalized = _normalize_text(text)
        if not normalized:
            return ExtractionResult()

        ref_date = reference_date or datetime.now(ZoneInfo(self._timezone_name)).date()

        patch: dict[str, Any] = {}
        clarifications: list[FieldClarification] = []
        provenance: dict[str, str] = {}

        # 1. Correction intent detection
        detected_correction = self._detect_correction(normalized)

        # 2. Visit type (extracted early so it can help disambiguate beneficiary & weight bounds)
        visit_type, vt_source, vt_clar = self._extract_visit_type(normalized)
        if visit_type is not None:
            patch["visit_type"] = visit_type
            if vt_source:
                provenance["visit_type"] = vt_source
        if vt_clar is not None:
            clarifications.append(vt_clar)

        effective_visit_type: VisitType | None = visit_type or (
            existing_draft.visit_type if existing_draft else None
        )

        # 3. Beneficiary resolution against SyntheticBeneficiaryDirectory
        ben, ben_source, ben_clar = self._extract_beneficiary(
            normalized, effective_visit_type=effective_visit_type
        )
        if ben is not None:
            patch["beneficiary_id"] = ben.beneficiary_id
            patch["beneficiary_name"] = ben.full_name
            if ben_source:
                provenance["beneficiary_id"] = ben_source
                provenance["beneficiary_name"] = ben_source
        if ben_clar is not None:
            clarifications.append(ben_clar)

        effective_ben: SyntheticBeneficiary | None = ben
        if effective_ben is None and existing_draft and existing_draft.beneficiary_id:
            effective_ben = self._directory.get_by_id(existing_draft.beneficiary_id)

        # 4. Weight normalization & physiological bounds validation
        weight_kg, weight_source, weight_clar = self._extract_weight(
            normalized,
            effective_visit_type=effective_visit_type,
            effective_beneficiary=effective_ben,
        )
        if weight_kg is not None:
            patch["weight_kg"] = weight_kg
            if weight_source:
                patch["weight_source_text"] = weight_source
                provenance["weight_kg"] = weight_source
        if weight_clar is not None:
            clarifications.append(weight_clar)

        # 5. Vaccinations (completed vs due)
        v_completed, v_due, v_prov, v_clars = self._extract_vaccinations(normalized)
        if v_completed:
            patch["vaccinations_completed"] = v_completed
            if "vaccinations_completed" in v_prov:
                provenance["vaccinations_completed"] = v_prov["vaccinations_completed"]
        if v_due:
            patch["vaccinations_due"] = v_due
            if "vaccinations_due" in v_prov:
                provenance["vaccinations_due"] = v_prov["vaccinations_due"]
        clarifications.extend(v_clars)

        # 6. Next visit date (ISO YYYY-MM-DD)
        next_date, date_source, date_clar = self._extract_next_visit_date(
            normalized, reference_date=ref_date
        )
        if next_date is not None:
            patch["next_visit_date"] = next_date
            if date_source:
                patch["next_visit_date_source_text"] = date_source
                provenance["next_visit_date"] = date_source
        if date_clar is not None:
            clarifications.append(date_clar)

        # 7. Grounded follow-up actions
        actions = self._derive_follow_up_actions(
            normalized,
            vaccinations_due=v_due,
            next_visit_date=next_date,
            date_source=date_source,
        )
        if actions:
            patch["follow_up_actions"] = actions

        # Identify corrected fields when correction intent is detected
        corrected_fields: list[str] = []
        if detected_correction:
            for key in (
                "beneficiary_id",
                "visit_type",
                "weight_kg",
                "vaccinations_completed",
                "vaccinations_due",
                "next_visit_date",
            ):
                if key in patch:
                    corrected_fields.append(key)
            # Only list follow_up_actions as a corrected field when an explicit
            # standalone action (e.g. ifa_adherence / weight_monitoring) was mentioned,
            # not merely a derived routine_visit/vaccination action from date/vaccine fields.
            if any(
                a.action_type in {"ifa_adherence", "weight_monitoring", "other"}
                for a in actions
            ):
                corrected_fields.append("follow_up_actions")

        return ExtractionResult(
            patch=patch,
            clarifications=clarifications,
            detected_correction=detected_correction,
            corrected_fields=corrected_fields,
            provenance=provenance,
        )

    def apply_to_draft(
        self,
        draft: VisitDraft,
        result: ExtractionResult,
        *,
        correction_mode: bool = False,
    ) -> VisitDraft:
        """Apply an `ExtractionResult` patch onto `draft`, returning a new `VisitDraft`.

        Safety guarantees:
        - Preserves all unmentioned fields during corrections.
        - NEVER clears `danger_sign_flagged` or removes existing `danger_signs`.
        - NEVER silently overwrites confirmed fields with null or uncertain values.
        - Clears `status="confirmed"` back to `"draft"` if a confirmed field is modified.
        """
        updated = draft.model_copy(deep=True)
        is_correction = correction_mode or result.detected_correction
        confirmed_set = set(updated.confirmed_fields)
        changed_confirmed = False

        # Protect safety-critical danger-sign fields unconditionally
        preserved_danger_flag = updated.danger_sign_flagged
        preserved_danger_signs = list(updated.danger_signs)

        patch = result.patch

        # Scalar fields
        scalar_pairs: tuple[tuple[str, str | None], ...] = (
            ("beneficiary_id", "beneficiary_name"),
            ("visit_type", None),
            ("weight_kg", "weight_source_text"),
            ("next_visit_date", "next_visit_date_source_text"),
        )
        for field_name, companion_field in scalar_pairs:
            if field_name not in patch:
                continue
            new_val = patch[field_name]
            if new_val is None:
                # Never overwrite an existing or confirmed field with null
                continue
            current_val = getattr(updated, field_name)
            if field_name in confirmed_set and not is_correction:
                # Never silently overwrite a confirmed field outside correction mode
                continue
            setattr(updated, field_name, new_val)
            if companion_field and companion_field in patch and patch[companion_field] is not None:
                setattr(updated, companion_field, patch[companion_field])
            if field_name in confirmed_set and new_val != current_val:
                confirmed_set.discard(field_name)
                changed_confirmed = True

        # Vaccinations completed
        if "vaccinations_completed" in patch and patch["vaccinations_completed"]:
            new_completed: list[str] = list(patch["vaccinations_completed"])
            if "vaccinations_completed" not in confirmed_set or is_correction:
                merged_completed = _dedupe_preserve_order(
                    updated.vaccinations_completed + new_completed
                )
                if (
                    "vaccinations_completed" in confirmed_set
                    and merged_completed != updated.vaccinations_completed
                ):
                    confirmed_set.discard("vaccinations_completed")
                    changed_confirmed = True
                updated.vaccinations_completed = merged_completed
                # If a vaccine is now completed, remove it from vaccinations_due
                completed_lower = {v.lower() for v in new_completed}
                updated.vaccinations_due = [
                    v for v in updated.vaccinations_due if v.lower() not in completed_lower
                ]

        # Vaccinations due
        if "vaccinations_due" in patch and patch["vaccinations_due"]:
            new_due: list[str] = list(patch["vaccinations_due"])
            if "vaccinations_due" not in confirmed_set or is_correction:
                merged_due = _dedupe_preserve_order(updated.vaccinations_due + new_due)
                if "vaccinations_due" in confirmed_set and merged_due != updated.vaccinations_due:
                    confirmed_set.discard("vaccinations_due")
                    changed_confirmed = True
                updated.vaccinations_due = merged_due
                if is_correction:
                    due_lower = {v.lower() for v in new_due}
                    updated.vaccinations_completed = [
                        v
                        for v in updated.vaccinations_completed
                        if v.lower() not in due_lower
                    ]

        # Follow-up actions: merge without dropping existing grounded/danger actions
        if "follow_up_actions" in patch and patch["follow_up_actions"]:
            incoming_actions = [
                a if isinstance(a, FollowUpAction) else FollowUpAction.model_validate(a)
                for a in patch["follow_up_actions"]
            ]
            existing_actions = list(updated.follow_up_actions)
            for inc in incoming_actions:
                # If correcting next_visit_date, replace prior routine_visit action date cleanly
                if is_correction and inc.action_type == "routine_visit" and inc.due_date:
                    existing_actions = [
                        a for a in existing_actions if a.action_type != "routine_visit"
                    ]
                if not any(
                    a.action_type == inc.action_type
                    and a.description == inc.description
                    and a.due_date == inc.due_date
                    for a in existing_actions
                ):
                    existing_actions.append(inc)
            updated.follow_up_actions = existing_actions

        # Update clarifications: clear resolved fields, upsert newly emitted clarifications
        resolved_fields = {k for k, v in patch.items() if v is not None and v != []}
        clar_by_field: dict[str, FieldClarification] = {
            c.field_name: c
            for c in updated.clarifications_needed
            if c.field_name not in resolved_fields
        }
        for new_clar in result.clarifications:
            if new_clar.field_name not in resolved_fields:
                clar_by_field[new_clar.field_name] = new_clar
        updated.clarifications_needed = list(clar_by_field.values())

        # Reflect confirmation / draft status update
        updated.confirmed_fields = [f for f in updated.confirmed_fields if f in confirmed_set]
        if changed_confirmed and updated.status == "confirmed":
            updated.status = "draft"

        # Restore safety-critical danger-sign invariants unconditionally
        updated.danger_sign_flagged = preserved_danger_flag or updated.danger_sign_flagged
        updated.danger_signs = _dedupe_preserve_order(
            preserved_danger_signs + list(updated.danger_signs)
        )

        return updated

    # ------------------------------------------------------------------
    # Private extractors
    # ------------------------------------------------------------------

    def _detect_correction(self, text: str) -> bool:
        if _CORRECTION_COMMA_RE.search(text):
            return True
        if _CORRECTION_START_RE.search(text):
            return True
        return bool(_CORRECTION_INLINE_RE.search(text))

    def _extract_visit_type(
        self, text: str
    ) -> tuple[VisitType | None, str | None, FieldClarification | None]:
        matched_types: dict[VisitType, str] = {}
        negated_types: set[VisitType] = set()

        for vtype, patterns in _VISIT_TYPE_PATTERNS.items():
            for pat in patterns:
                m = pat.search(text)
                if m:
                    # Check immediate negation before/after match (e.g. "not ANC", "ANC nahi")
                    before = text[max(0, m.start() - 18) : m.start()].lower()
                    after = text[m.end() : min(len(text), m.end() + 18)].lower()
                    if re.search(r"\b(?:not|no|nahi|nahin|नहीं)\s*$", before) or re.match(
                        r"^\s*(?:nahi|nahin|नहीं)\b", after
                    ):
                        negated_types.add(vtype)
                        continue
                    matched_types[vtype] = m.group(0)
                    break

        # Secondary cues only if no primary visit type matched
        if not matched_types:
            m_baby = _SECONDARY_NEWBORN_PATTERN.search(text)
            if m_baby:
                matched_types["Newborn"] = m_baby.group(0)
            else:
                m_imm = _SECONDARY_IMMUNISATION_PATTERN.search(text)
                if m_imm:
                    matched_types["Immunisation"] = m_imm.group(0)

        if not matched_types:
            return None, None, None

        if len(matched_types) == 1:
            vtype, src = next(iter(matched_types.items()))
            return vtype, src, None

        # If Immunisation + another primary type co-occur, check whether Immunisation was
        # explicitly framed as the visit type ("immunisation visit") vs incidental mention.
        if "Immunisation" in matched_types and len(matched_types) == 2:
            imm_src = matched_types["Immunisation"].lower()
            other_type = next(k for k in matched_types if k != "Immunisation")
            if "visit" in imm_src or "tikakaran" in imm_src or "टीकाकरण" in imm_src:
                return "Immunisation", matched_types["Immunisation"], None
            return other_type, matched_types[other_type], None

        # Genuine conflict between multiple visit types (e.g. "ANC and PNC")
        candidates = list(matched_types.keys())
        return (
            None,
            None,
            FieldClarification(
                field_name="visit_type",
                reason=f"Multiple visit types mentioned in utterance: {', '.join(candidates)}.",
                prompt_hint="Please confirm whether this visit is "
                + " or ".join(candidates)
                + ".",
                candidates=candidates,
            ),
        )

    def _extract_beneficiary(
        self,
        text: str,
        *,
        effective_visit_type: VisitType | None = None,
    ) -> tuple[SyntheticBeneficiary | None, str | None, FieldClarification | None]:
        # 1. Explicit beneficiary ID lookup (highest precision)
        id_match = _BEN_ID_RE.search(text)
        if id_match:
            canonical_id = f"BEN-{id_match.group(1)}"
            found = self._directory.get_by_id(canonical_id)
            if found is not None:
                return found, id_match.group(0), None
            return (
                None,
                None,
                FieldClarification(
                    field_name="beneficiary_id",
                    reason=f"Beneficiary ID {canonical_id} was not found in the synthetic directory.",
                    prompt_hint=f"I could not find {canonical_id} in the beneficiary list. Please repeat the beneficiary's name or ID.",
                    candidates=[],
                ),
            )

        all_bens = self._directory.list_all()
        text_lower = text.lower()

        # 2. Exact full-name matches (prefer longest match, e.g., "Baby of Kavitha Rao" > "Kavitha Rao")
        full_matches: list[tuple[int, SyntheticBeneficiary, str]] = []
        for ben in all_bens:
            pat = re.compile(_wb_pattern(ben.full_name), re.IGNORECASE)
            m = pat.search(text)
            if m:
                full_matches.append((len(ben.full_name), ben, m.group(0)))
        if full_matches:
            max_len = max(item[0] for item in full_matches)
            top = [(b, s) for length, b, s in full_matches if length == max_len]
            if len(top) == 1:
                return top[0][0], top[0][1], None
            return self._resolve_or_clarify_candidates(
                [b for b, _ in top],
                source_text=top[0][1],
                text_lower=text_lower,
                effective_visit_type=effective_visit_type,
            )

        # 3. Multi-word alias matches (e.g., "lakshmi narayanan", "kavitha baby", "kavitha newborn")
        multi_matches: list[tuple[int, SyntheticBeneficiary, str]] = []
        for ben in all_bens:
            for alias in ben.aliases:
                if " " not in alias.strip():
                    continue
                m = re.search(_wb_pattern(alias), text, re.IGNORECASE)
                if m:
                    multi_matches.append((len(alias), ben, m.group(0)))
                    break
        if multi_matches:
            max_len = max(item[0] for item in multi_matches)
            top_bens: list[SyntheticBeneficiary] = []
            top_src = ""
            seen_ids: set[str] = set()
            for length, b, s in multi_matches:
                if length == max_len and b.beneficiary_id not in seen_ids:
                    seen_ids.add(b.beneficiary_id)
                    top_bens.append(b)
                    top_src = top_src or s
            if len(top_bens) == 1:
                return top_bens[0], top_src, None
            return self._resolve_or_clarify_candidates(
                top_bens,
                source_text=top_src,
                text_lower=text_lower,
                effective_visit_type=effective_visit_type,
            )

        # 4. Single-word alias & first-name matches across ALL beneficiaries
        candidates: list[SyntheticBeneficiary] = []
        seen_ids = set()
        matched_term = ""

        # Collect single-word triggers per beneficiary
        for ben in all_bens:
            tokens_to_check: list[str] = []
            for alias in ben.aliases:
                alias_s = alias.strip()
                if alias_s and " " not in alias_s:
                    tokens_to_check.append(alias_s)
            name_parts = ben.full_name.split()
            # Include first name token for regular person names (skip "Baby of ...")
            if name_parts and name_parts[0].lower() != "baby":
                first_tok = name_parts[0]
                if first_tok.lower() not in {t.lower() for t in tokens_to_check}:
                    tokens_to_check.append(first_tok)

            for tok in tokens_to_check:
                m = re.search(_wb_pattern(tok), text, re.IGNORECASE)
                if m:
                    if ben.beneficiary_id not in seen_ids:
                        seen_ids.add(ben.beneficiary_id)
                        candidates.append(ben)
                        matched_term = matched_term or m.group(0)
                    break

        # Special handling for newborn/baby of a matched mother (e.g., "Kavitha ka newborn visit" -> BEN-1044)
        if candidates and (
            effective_visit_type == "Newborn"
            or re.search(
                rf"{_LB}(?:baby|newborn|navjat|navjaat|shishu|bachcha|bacha|नवजात|शिशु){_RB}",
                text,
                re.IGNORECASE,
            )
        ):
            baby_matches: list[SyntheticBeneficiary] = []
            for ben in all_bens:
                if ben.category == "newborn" and ben.full_name.lower().startswith("baby of "):
                    mother_name = ben.full_name[8:].strip().lower()
                    for cand in candidates:
                        if cand.full_name.lower() == mother_name or (
                            cand.full_name.split()[0].lower() in mother_name
                        ):
                            baby_matches.append(ben)
                            break
            if len(baby_matches) == 1:
                return baby_matches[0], matched_term, None

        if not candidates:
            return None, None, None

        if len(candidates) == 1:
            return candidates[0], matched_term, None

        return self._resolve_or_clarify_candidates(
            candidates,
            source_text=matched_term,
            text_lower=text_lower,
            effective_visit_type=effective_visit_type,
        )

    def _resolve_or_clarify_candidates(
        self,
        candidates: list[SyntheticBeneficiary],
        *,
        source_text: str,
        text_lower: str,
        effective_visit_type: VisitType | None,
    ) -> tuple[SyntheticBeneficiary | None, str | None, FieldClarification | None]:
        remaining = list(candidates)

        # Disambiguate by village / ward mention
        village_hits: list[SyntheticBeneficiary] = []
        for ben in remaining:
            village_tokens = [
                tok
                for tok in re.findall(r"[a-z0-9]+", ben.village.lower())
                if tok not in {"demo", "ward"} and len(tok) >= 3
            ]
            if any(re.search(_wb_pattern(vt), text_lower) for vt in village_tokens):
                village_hits.append(ben)
        if len(village_hits) == 1:
            return village_hits[0], source_text, None
        if village_hits:
            remaining = village_hits

        # Disambiguate by surname / second name token
        surname_hits: list[SyntheticBeneficiary] = []
        for ben in remaining:
            parts = ben.full_name.lower().split()
            if len(parts) >= 2 and any(
                re.search(_wb_pattern(p), text_lower) for p in parts[1:] if len(p) >= 2
            ):
                surname_hits.append(ben)
        if len(surname_hits) == 1:
            return surname_hits[0], source_text, None
        if surname_hits:
            remaining = surname_hits

        # Disambiguate by visit type <-> beneficiary category
        if effective_visit_type is not None:
            allowed_cats = _VISIT_TYPE_CATEGORIES.get(effective_visit_type, frozenset())
            cat_hits = [b for b in remaining if b.category in allowed_cats]
            if len(cat_hits) == 1:
                return cat_hits[0], source_text, None
            if cat_hits:
                remaining = cat_hits

        # Still ambiguous -> emit FieldClarification and NEVER fabricate an ID
        candidate_labels = [
            f"{b.beneficiary_id}: {b.full_name} ({b.village})" for b in remaining
        ]
        short_options = " or ".join(f"{b.full_name} ({b.beneficiary_id})" for b in remaining)
        return (
            None,
            None,
            FieldClarification(
                field_name="beneficiary_id",
                reason=f"Multiple beneficiaries match '{source_text}'.",
                prompt_hint=f"Multiple records match {source_text}. Did you mean {short_options}?",
                candidates=candidate_labels,
            ),
        )

    def _extract_weight(
        self,
        text: str,
        *,
        effective_visit_type: VisitType | None,
        effective_beneficiary: SyntheticBeneficiary | None,
    ) -> tuple[float | None, str | None, FieldClarification | None]:
        raw_kg: float | None = None
        source_text: str | None = None

        # 1. Compound kg + gram ("3 kilo 200 gram")
        m_comp = _COMPOUND_WEIGHT_PATTERN.search(text)
        if m_comp:
            kg_part = _parse_number_phrase(m_comp.group("kg_qty"))
            g_part = _parse_number_phrase(m_comp.group("g_qty"))
            if kg_part is not None and g_part is not None:
                raw_kg = kg_part + (g_part / 1000.0)
                source_text = m_comp.group(0).strip()

        # 2. Kilograms ("fifty two kilo", "2.8 kg", "ढाई किलो", "साढ़े तीन किलो", "ववेट fifty two kilo")
        if raw_kg is None:
            m_kg = _KG_WEIGHT_PATTERN.search(text)
            if m_kg:
                val = _parse_number_phrase(m_kg.group("qty"))
                if val is not None:
                    raw_kg = val
                    source_text = m_kg.group(0).strip()

        # 3. Grams ("2800 gram", "2800g", "2500 ग्राम")
        if raw_kg is None:
            m_g = _GRAM_WEIGHT_PATTERN.search(text)
            if m_g:
                val = _parse_number_phrase(m_g.group("qty"))
                if val is not None:
                    raw_kg = val / 1000.0
                    source_text = m_g.group(0).strip()

        # 4. Explicit weight cue without unit ("weight is 52", "वजन 2.8")
        if raw_kg is None:
            m_cue = _CUE_ONLY_WEIGHT_PATTERN.search(text)
            if m_cue:
                val = _parse_number_phrase(m_cue.group("qty"))
                if val is not None:
                    raw_kg = val
                    source_text = m_cue.group(0).strip()

        if raw_kg is None:
            return None, None, None

        weight_kg = round(raw_kg, 3)

        # Physiological bounds validation
        min_kg, max_kg, context_label = self._weight_bounds(
            effective_visit_type=effective_visit_type,
            effective_beneficiary=effective_beneficiary,
            text=text,
        )
        if weight_kg < min_kg or weight_kg > max_kg:
            return (
                None,
                None,
                FieldClarification(
                    field_name="weight_kg",
                    reason=(
                        f"Extracted weight {weight_kg} kg from '{source_text}' is outside "
                        f"plausible {context_label} bounds ({min_kg}–{max_kg} kg)."
                    ),
                    prompt_hint=(
                        f"I heard {source_text} ({weight_kg} kg), which seems unusual for a "
                        f"{context_label} record. Please repeat the weight in kilograms or grams."
                    ),
                    candidates=[],
                ),
            )

        return weight_kg, source_text, None

    def _weight_bounds(
        self,
        *,
        effective_visit_type: VisitType | None,
        effective_beneficiary: SyntheticBeneficiary | None,
        text: str,
    ) -> tuple[float, float, str]:
        if effective_visit_type == "Newborn" or (
            effective_beneficiary is not None
            and effective_beneficiary.category in {"newborn", "infant"}
        ):
            return 0.4, 15.0, "newborn/infant"

        if effective_visit_type in {"ANC", "PNC"} or (
            effective_beneficiary is not None
            and effective_beneficiary.category in {"pregnant_woman", "postnatal_mother"}
        ):
            return 25.0, 150.0, "adult maternal"

        if re.search(
            rf"{_LB}(?:newborn|navjat|shishu|baby|नवजात|शिशु){_RB}", text, re.IGNORECASE
        ):
            return 0.4, 15.0, "newborn/infant"

        return 0.4, 150.0, "human"

    def _extract_vaccinations(
        self, text: str
    ) -> tuple[list[str], list[str], dict[str, str], list[FieldClarification]]:
        completed: list[str] = []
        due: list[str] = []
        completed_sources: list[str] = []
        due_sources: list[str] = []
        clarifications: list[FieldClarification] = []

        # Split on major clause separators first
        raw_clauses = re.split(
            r"[,;.\n।]+|\b(?:but|lekin|par|magar|whereas|while)\b|(?:लेकिन|मगर|परंतु)",
            text,
            flags=re.IGNORECASE,
        )

        # Further split on "and" / "aur" / "और" ONLY when both sides carry their own status cue
        clauses: list[str] = []
        for rc in raw_clauses:
            rc = rc.strip()
            if not rc:
                continue
            conj_parts = re.split(r"\b(?:and|aur)\b|और", rc, flags=re.IGNORECASE)
            if len(conj_parts) > 1 and all(
                self._clause_has_vaccine_cue(part) for part in conj_parts
            ):
                clauses.extend(p.strip() for p in conj_parts if p.strip())
            else:
                clauses.append(rc)

        for clause in clauses:
            found_vaccines = self._find_vaccines_in_clause(clause)
            if not found_vaccines:
                continue

            cues = self._find_vaccine_cues_in_clause(clause)
            if not cues:
                # Never invent vaccination status if not stated
                for vname, _span in found_vaccines:
                    clarifications.append(
                        FieldClarification(
                            field_name="vaccinations_due",
                            reason=f"Vaccination '{vname}' was mentioned without completed or pending status.",
                            prompt_hint=f"Has {vname} already been given, or is it still pending?",
                            candidates=[f"{vname} completed", f"{vname} due"],
                        )
                    )
                continue

            for vname, (v_start, v_end) in found_vaccines:
                status = self._assign_nearest_cue(v_start, v_end, cues)
                if status == "completed":
                    if vname not in completed:
                        completed.append(vname)
                    completed_sources.append(clause)
                elif status == "due":
                    if vname not in due:
                        due.append(vname)
                    due_sources.append(clause)

        provenance: dict[str, str] = {}
        if completed_sources:
            provenance["vaccinations_completed"] = "; ".join(
                _dedupe_preserve_order(completed_sources)
            )
        if due_sources:
            provenance["vaccinations_due"] = "; ".join(_dedupe_preserve_order(due_sources))

        return completed, due, provenance, clarifications

    def _clause_has_vaccine_cue(self, clause: str) -> bool:
        return bool(self._find_vaccine_cues_in_clause(clause))

    def _find_vaccines_in_clause(self, clause: str) -> list[tuple[str, tuple[int, int]]]:
        matches: list[tuple[str, tuple[int, int]]] = []
        occupied_spans: list[tuple[int, int]] = []

        for canonical, patterns in _COMPILED_VACCINES:
            for pat in patterns:
                for m in pat.finditer(clause):
                    span = (m.start(), m.end())
                    # Skip honorific "Mr." followed by a person's name
                    if canonical == "MR" and re.match(
                        r"mr\.\s+[a-z]", clause[m.start() : m.end() + 10], re.IGNORECASE
                    ):
                        continue
                    if any(not (span[1] <= s or span[0] >= e) for s, e in occupied_spans):
                        continue
                    occupied_spans.append(span)
                    matches.append((canonical, span))
                    break
        matches.sort(key=lambda item: item[1][0])
        return matches

    def _find_vaccine_cues_in_clause(
        self, clause: str
    ) -> list[tuple[str, tuple[int, int]]]:
        cues: list[tuple[str, tuple[int, int]]] = []
        occupied: list[tuple[int, int]] = []

        # Match DUE cues first so negated completions ("not given", "nahi laga") are masked
        for pat in _VACCINE_DUE_CUES:
            for m in pat.finditer(clause):
                span = (m.start(), m.end())
                if any(not (span[1] <= s or span[0] >= e) for s, e in occupied):
                    continue
                occupied.append(span)
                cues.append(("due", span))

        for pat in _VACCINE_COMPLETED_CUES:
            for m in pat.finditer(clause):
                span = (m.start(), m.end())
                if any(not (span[1] <= s or span[0] >= e) for s, e in occupied):
                    continue
                occupied.append(span)
                cues.append(("completed", span))

        cues.sort(key=lambda item: item[1][0])
        return cues

    def _assign_nearest_cue(
        self,
        v_start: int,
        v_end: int,
        cues: list[tuple[str, tuple[int, int]]],
    ) -> str:
        # Prefer the closest cue AFTER the vaccine mention (typical EN/HI word order),
        # falling back to the closest cue BEFORE it (e.g., "pending Pentavalent").
        after = [(c_start - v_end, status) for status, (c_start, _c_end) in cues if c_start >= v_end]
        if after:
            after.sort(key=lambda item: item[0])
            return after[0][1]
        before = [(v_start - c_end, status) for status, (_c_start, c_end) in cues if c_end <= v_start]
        if before:
            before.sort(key=lambda item: item[0])
            return before[0][1]
        return cues[0][0]

    def _extract_next_visit_date(
        self,
        text: str,
        *,
        reference_date: date,
    ) -> tuple[str | None, str | None, FieldClarification | None]:
        # 1. Explicit ISO YYYY-MM-DD
        m_iso = _ISO_DATE_RE.search(text)
        if m_iso:
            y, m, d = int(m_iso.group("y")), int(m_iso.group("m")), int(m_iso.group("d"))
            try:
                parsed = date(y, m, d)
                return parsed.isoformat(), m_iso.group(0), None
            except ValueError:
                return None, None, self._invalid_date_clarification(m_iso.group(0))

        # 2. Explicit DD/MM/YYYY or DD-MM-YYYY
        m_dmy = _DMY_DATE_RE.search(text)
        if m_dmy:
            d, m, y = int(m_dmy.group("d")), int(m_dmy.group("m")), int(m_dmy.group("y"))
            if y < 100:
                y += 2000
            try:
                parsed = date(y, m, d)
                return parsed.isoformat(), m_dmy.group(0), None
            except ValueError:
                return None, None, self._invalid_date_clarification(m_dmy.group(0))

        # 3. Day + Month or Month + Day ("25 November", "twenty eighth November", "28 Nov", "31 February")
        for pat in (_DAY_MONTH_RE, _MONTH_DAY_RE):
            m_dm = pat.search(text)
            if m_dm:
                day_val = self._parse_day_token(m_dm.group("day"))
                month_val = _MONTH_NAMES.get(m_dm.group("month").lower())
                year_str = m_dm.group("year")
                if day_val is not None and month_val is not None:
                    year_val = int(year_str) if year_str else reference_date.year
                    try:
                        candidate = date(year_val, month_val, day_val)
                    except ValueError:
                        return None, None, self._invalid_date_clarification(m_dm.group(0))
                    # If no year was given and date is in the past, roll to next year
                    if not year_str and candidate < reference_date:
                        try:
                            candidate = date(year_val + 1, month_val, day_val)
                        except ValueError:
                            return None, None, self._invalid_date_clarification(m_dm.group(0))
                    return candidate.isoformat(), m_dm.group(0), None

        # 4. Relative day offsets ("after 7 days", "7 din baad", "सात दिन बाद")
        m_days = _AFTER_DAYS_RE.search(text)
        if m_days:
            raw_n = m_days.group("n1") or m_days.group("n2")
            days = self._parse_count_token(raw_n)
            if days is not None and 0 < days <= 365:
                return (reference_date + timedelta(days=days)).isoformat(), m_days.group(0), None

        # 5. Relative week offsets ("after 2 weeks", "2 hafte baad")
        m_weeks = _AFTER_WEEKS_RE.search(text)
        if m_weeks:
            raw_n = m_weeks.group("n1") or m_weeks.group("n2")
            weeks = self._parse_count_token(raw_n)
            if weeks is not None and 0 < weeks <= 52:
                return (
                    (reference_date + timedelta(days=7 * weeks)).isoformat(),
                    m_weeks.group(0),
                    None,
                )

        # 6. Ambiguous date phrases ("some day next month", "next month", "agle mahine")
        # Check BEFORE next_week so "some day next week" is caught as ambiguous!
        m_ambig = _AMBIGUOUS_DATE_RE.search(text)
        if m_ambig:
            return (
                None,
                None,
                FieldClarification(
                    field_name="next_visit_date",
                    reason=f"Next visit date '{m_ambig.group(0)}' is too ambiguous to convert to a calendar date.",
                    prompt_hint="Please specify an exact date or number of days for the next visit.",
                    candidates=[],
                ),
            )

        # 7. "next week" / "agle hafte"
        m_nw = _NEXT_WEEK_RE.search(text)
        if m_nw:
            return (reference_date + timedelta(days=7)).isoformat(), m_nw.group(0), None

        # 8. "day after tomorrow" / "parso"
        m_parso = _DAY_AFTER_TOMORROW_RE.search(text)
        if m_parso and not _PAST_KAL_GUARD_RE.search(text):
            return (reference_date + timedelta(days=2)).isoformat(), m_parso.group(0), None

        # 9. "tomorrow" / "kal" (guarded against past-tense Hindi "kal se" / "kal tha")
        m_kal = _TOMORROW_RE.search(text)
        if m_kal and not _PAST_KAL_GUARD_RE.search(text):
            return (reference_date + timedelta(days=1)).isoformat(), m_kal.group(0), None

        # 10. Weekday ("next Monday", "agle somwar")
        m_wd = _WEEKDAY_NEXT_RE.search(text)
        if m_wd:
            raw_wd = m_wd.group("wd1") or m_wd.group("wd2")
            wd_idx = _WEEKDAY_NAMES.get(raw_wd.lower()) if raw_wd else None
            if wd_idx is not None:
                delta = (wd_idx - reference_date.weekday()) % 7
                if delta == 0:
                    delta = 7
                return (reference_date + timedelta(days=delta)).isoformat(), m_wd.group(0), None

        return None, None, None

    def _parse_day_token(self, raw_day: str) -> int | None:
        cleaned = raw_day.strip().lower()
        m_num = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", cleaned)
        if m_num:
            return int(m_num.group(1))
        val = _parse_int_tokens(cleaned.replace("-", " ").split())
        if val is not None and 1 <= val <= 31:
            return val
        return None

    def _parse_count_token(self, raw_count: str | None) -> int | None:
        if not raw_count:
            return None
        cleaned = raw_count.strip().lower()
        if cleaned in {"a", "an"}:
            return 1
        if cleaned.isdigit():
            return int(cleaned)
        return _parse_int_tokens(cleaned.replace("-", " ").split())

    def _invalid_date_clarification(self, raw_text: str) -> FieldClarification:
        return FieldClarification(
            field_name="next_visit_date",
            reason=f"'{raw_text}' is not a valid calendar date.",
            prompt_hint=f"The date '{raw_text}' is not valid. Please confirm the correct next visit date.",
            candidates=[],
        )

    def _derive_follow_up_actions(
        self,
        text: str,
        *,
        vaccinations_due: list[str],
        next_visit_date: str | None,
        date_source: str | None,
    ) -> list[FollowUpAction]:
        actions: list[FollowUpAction] = []

        # 1. Pending/due vaccinations
        if vaccinations_due:
            vaccines_str = ", ".join(vaccinations_due)
            actions.append(
                FollowUpAction(
                    action_type="vaccination",
                    description=f"Schedule and administer due vaccination(s): {vaccines_str}",
                    due_date=next_visit_date,
                    priority="high",
                    source_phrase=vaccines_str,
                )
            )

        # 2. IFA / calcium non-adherence
        m_ifa = _IFA_NON_ADHERENCE_RE.search(text)
        if m_ifa:
            actions.append(
                FollowUpAction(
                    action_type="ifa_adherence",
                    description="Follow up and counsel beneficiary on regular IFA/calcium adherence",
                    due_date=next_visit_date,
                    priority="high",
                    source_phrase=m_ifa.group(0).strip(),
                )
            )

        # 3. Explicit weight monitoring
        m_wm = _WEIGHT_MONITOR_RE.search(text)
        if m_wm:
            actions.append(
                FollowUpAction(
                    action_type="weight_monitoring",
                    description="Recheck and monitor beneficiary weight at follow-up",
                    due_date=next_visit_date,
                    priority="normal",
                    source_phrase=m_wm.group(0).strip(),
                )
            )

        # 4. Routine follow-up visit when explicitly requested or scheduled
        m_fv = _FOLLOWUP_VISIT_CUE_RE.search(text)
        if next_visit_date is not None or m_fv is not None:
            desc = (
                f"Conduct scheduled follow-up home visit on {next_visit_date}"
                if next_visit_date
                else "Conduct follow-up home visit"
            )
            actions.append(
                FollowUpAction(
                    action_type="routine_visit",
                    description=desc,
                    due_date=next_visit_date,
                    priority="normal",
                    source_phrase=date_source or (m_fv.group(0).strip() if m_fv else None),
                )
            )

        return actions


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
