"""Unicode, Indic numeral, ASR spelling, and clause normalization utilities.

Pure Python stdlib implementation tailored for noisy Indic + English code-mixed
ASR transcripts (Hindi/Hinglish, English, Kannada, Tamil).
"""

from __future__ import annotations

import re
import unicodedata


# Indic script digit translation tables -> ASCII 0-9
_INDIC_DIGIT_MAP: dict[int, str] = {
    # Devanagari ०-९
    **{0x0966 + i: str(i) for i in range(10)},
    # Kannada ೦-೯
    **{0x0CE6 + i: str(i) for i in range(10)},
    # Tamil ௦-௯
    **{0x0BE6 + i: str(i) for i in range(10)},
}

# Common ASR / Hinglish / Indic-English spelling normalizations (token-level)
_TOKEN_CANONICAL_MAP: dict[str, str] = {
    # Bleeding / blood
    "koon": "khoon",
    "khun": "khoon",
    "khon": "khoon",
    "khooon": "khoon",
    "bliding": "bleeding",
    "bleading": "bleeding",
    "bleedng": "bleeding",
    "raktasrav": "raktasrava",
    "raktasraav": "raktasrava",
    "raththam": "raktam",
    "ratham": "raktam",
    # Fever
    "bukar": "bukhar",
    "bhukar": "bukhar",
    "bukhaar": "bukhar",
    "bhukhar": "bukhar",
    "bukhr": "bukhar",
    "fevar": "fever",
    "fevr": "fever",
    "kaichal": "kaychal",
    "kaaichal": "kaychal",
    "jwar": "jvara",
    "jwara": "jvara",
    # Convulsions / fits
    "phits": "fits",
    "fitts": "fits",
    "fitz": "fits",
    "jhatka": "jhatke",
    "jhatkay": "jhatke",
    "jatke": "jhatke",
    "jhatake": "jhatke",
    "daure": "daura",
    "dora": "daura",
    "dauraa": "daura",
    "convulsion": "convulsions",
    "convulsons": "convulsions",
    "convultions": "convulsions",
    "convulshun": "convulsions",
    "convulshuns": "convulsions",
    "seizure": "seizures",
    "seizur": "seizures",
    "seisure": "seizures",
    "valippu": "valippu",
    # Breathing / breathlessness
    "sans": "saans",
    "saansh": "saans",
    "saanss": "saans",
    "shwas": "saans",
    "swaas": "saans",
    "breathles": "breathless",
    "brethless": "breathless",
    "breathlesness": "breathlessness",
    "indrawng": "indrawing",
    # Swelling / oedema
    "soojan": "sujan",
    "sujhan": "sujan",
    "sojan": "sujan",
    "sujun": "sujan",
    "sweling": "swelling",
    "swelng": "swelling",
    "oedema": "swelling",
    "edema": "swelling",
    # Umbilical / cord
    "nal": "naal",
    "naabhi": "nabhi",
    "umbilcal": "umbilical",
    "umbilicus": "umbilical",
    # Feeding / milk
    "dudh": "doodh",
    "dood": "doodh",
    "doodhh": "doodh",
    "dhudh": "doodh",
    "breastfed": "breastfeed",
    "brestfeed": "breastfeed",
    "brestfeeding": "breastfeeding",
    # Headache / vision / dizziness
    "headach": "headache",
    "headake": "headache",
    "hedache": "headache",
    "blured": "blurred",
    "blurry": "blurred",
    "blury": "blurred",
    "dhundla": "dhundhla",
    "dhundhala": "dhundhla",
    "dhundhali": "dhundhla",
    "chakar": "chakkar",
    "chakr": "chakkar",
    # Newborn / baby
    "bache": "baccha",
    "bacha": "baccha",
    "bachcha": "baccha",
    "bachhe": "baccha",
    "bachche": "baccha",
    "bacche": "baccha",
    "newborn": "newborn",
    "newbon": "newborn",
    # Abdomen / pain / vomiting
    "pait": "pet",
    "peit": "pet",
    "darad": "dard",
    "durd": "dard",
    "vomitting": "vomiting",
    "vomting": "vomiting",
    "ultee": "ulti",
    "ultiyan": "ulti",
    "ultiyaan": "ulti",
    "ultiya": "ulti",
    # Unconscious / lethargy / hypothermia / jaundice
    "behoshi": "behosh",
    "bihosh": "behosh",
    "behoshi": "behosh",
    "unconcious": "unconscious",
    "unconsious": "unconscious",
    "unconscius": "unconscious",
    "susti": "sust",
    "shust": "sust",
    "thandi": "thanda",
    "thnda": "thanda",
    "thandaa": "thanda",
    "pila": "peela",
    "peeli": "peela",
    "pili": "peela",
    "pilia": "peeliya",
    "peelia": "peeliya",
    "piliya": "peeliya",
    "jaundis": "jaundice",
    "jondis": "jaundice",
    "jaundise": "jaundice",
    # Infection / pus / foul smell
    "puss": "pus",
    "mavaad": "mawad",
    "mawaad": "mawad",
    "badboo": "badbu",
    "badbudaar": "badbu",
    "badbudar": "badbu",
    # Negation & context words
    "nahin": "nahi",
    "nahee": "nahi",
    "naheen": "nahi",
    "nhi": "nahi",
    "nai": "nahi",
    "thik": "theek",
    "teek": "theek",
    "pichhle": "pichle",
    "pichla": "pichle",
    "pichhla": "pichle",
    "padoshi": "padosi",
    "parosi": "padosi",
    "neighbor": "neighbour",
    "neighbors": "neighbours",
    "bahan": "behen",
    # Units / measurements
    "kilo": "kg",
    "kilos": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    "kgs": "kg",
    "grams": "g",
    "gram": "g",
    "gms": "g",
    "gm": "g",
    "fahrenheit": "f",
    "farenheit": "f",
    "celsius": "c",
    "centigrade": "c",
    "haemoglobin": "hemoglobin",
    "labor": "labour",
}

_PHRASE_CANONICAL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bb\.\s*p\.?\b"), "bp"),
    (re.compile(r"\bblood\s+pressure\b"), "bp"),
    (re.compile(r"\b(?:deg|degree|degrees)\s*([fc])\b"), r"\1"),
    (re.compile(r"°\s*([fc])\b"), r" \1"),
    (re.compile(r"\bin[-\s]drawing\b"), "indrawing"),
    (re.compile(r"\bpost[-\s]partum\b"), "postpartum"),
    (re.compile(r"\bpre[-\s]term\b"), "preterm"),
    (re.compile(r"\bbreast[-\s]feed(?:ing)?\b"), "breastfeeding"),
    (re.compile(r"\bnew[-\s]born\b"), "newborn"),
    (re.compile(r"\bweight\s*kg\b"), "weight kg"),
)

# English number words (simple cardinal & compound numbers for clinical values)
_UNITS: dict[str, int] = {
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

_TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

# Only convert standalone English number words when adjacent to clinical/numeric cues
# so prose like "no one" or "one of the" is not mangled unnecessarily.
_CLINICAL_NUMBER_FOLLOWERS = (
    r"pads?|cloth|cloths|breaths?|bpm|per|minutes?|mins?|hours?|hrs?|"
    r"days?|weeks?|months?|kg|kilo|kilos|g|grams?|pustules?|boils?|"
    r"f\b|c\b|fahrenheit|celsius|degree|degrees|mmhg|over|by|point|hundred"
)

_COMPOUND_NUM_RE = re.compile(
    r"\b(" + "|".join(_TENS.keys()) + r")[\s-]+(" + "|".join(k for k, v in _UNITS.items() if 1 <= v <= 9) + r")\b"
)
_HUNDRED_NUM_RE = re.compile(
    r"\b(one|two)\s+hundred(?:\s+and)?(?:\s+("
    + "|".join(list(_TENS.keys()) + list(_UNITS.keys()))
    + r")(?:\s+("
    + "|".join(k for k, v in _UNITS.items() if 1 <= v <= 9)
    + r"))?)?\b"
)
_DECIMAL_WORDS_RE = re.compile(
    r"\b(\d+|" + "|".join(list(_TENS.keys()) + list(_UNITS.keys())) + r")\s+point\s+("
    + "|".join(k for k, v in _UNITS.items() if 0 <= v <= 9)
    + r"|\d)\b"
)
_SINGLE_NUM_BEFORE_CLINICAL_RE = re.compile(
    r"\b(" + "|".join(list(_TENS.keys()) + list(_UNITS.keys())) + r")\b(?=\s+(?:" + _CLINICAL_NUMBER_FOLLOWERS + r"))"
)

# Clause boundary splitting
_STRONG_CLAUSE_SEP_RE = re.compile(
    r"(?:(?<!\d)\.(?!\d)|[;!?।\n]+|\b(?:but|however|although|though|yet|whereas|lekin|parantu|magar|kintu|aadre|aadare|aanaal)\b|लेकिन|परंतु|मगर|किंतु|ಆದರೆ|ஆனால்)",
    flags=re.IGNORECASE,
)

# Cues that indicate a comma separates two independent clauses rather than list items
_COMMA_LEFT_CONTEXT_CUE_RE = re.compile(
    r"(?:\b(?:no|not|none|never|absent|denied|denies|nahi|nahin|illa|illai|resolved|"
    r"ago|last\s+(?:month|week|year|pregnancy)|previously|pehle|pichle|"
    r"neighbour|neighbor|padosi|sister|behen|friend|dost|someone\s+else)\b|"
    r"नहीं|पिछले|पहले|पड़ोसी|बहन|ಇಲ್ಲ|இல்லை)",
    flags=re.IGNORECASE,
)

_COMMA_RIGHT_NEW_CLAUSE_RE = re.compile(
    r"^\s*(?:no|not|none|nahi|nahin|now|currently|today|ab|abhi|aaj|"
    r"baby|newborn|infant|mother|she|he|patient|baccha|shishu|maa|magu|kuzhandhai|"
    r"neighbour|neighbor|padosi|sister|behen|weight|bp|temp|temperature|fever|bukhar|"
    r"नहीं|अब|अभी|बच्चा|माँ|आज)\b",
    flags=re.IGNORECASE,
)

_BODY_PART_CONTINUATION_RE = re.compile(
    r"^\s*(?:and\s+|or\s+)?(?:hands?|feet|legs?|face|eyes?|mouth|nose|anus|soles?|palms?|"
    r"haath|pair|chehra|aankh)\b",
    flags=re.IGNORECASE,
)


def normalize_unicode_and_digits(text: str) -> str:
    """Apply NFKC normalization and map Indic digits (Devanagari/Kannada/Tamil) to ASCII."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    return normalized.translate(_INDIC_DIGIT_MAP)


def _word_to_int(word: str) -> int | None:
    if word.isdigit():
        return int(word)
    if word in _UNITS:
        return _UNITS[word]
    if word in _TENS:
        return _TENS[word]
    return None


def normalize_number_words(text: str) -> str:
    """Convert English number words in clinical contexts into ASCII digits."""
    if not text:
        return ""

    def _replace_hundred(match: re.Match[str]) -> str:
        base = 100 if match.group(1) == "one" else 200
        mid = match.group(2)
        low = match.group(3)
        total = base
        if mid:
            val = _word_to_int(mid)
            if val is not None:
                total += val
        if low:
            val = _word_to_int(low)
            if val is not None:
                total += val
        return str(total)

    def _replace_compound(match: re.Match[str]) -> str:
        return str(_TENS[match.group(1)] + _UNITS[match.group(2)])

    def _replace_decimal(match: re.Match[str]) -> str:
        left = _word_to_int(match.group(1))
        right = _word_to_int(match.group(2))
        if left is None or right is None:
            return match.group(0)
        return f"{left}.{right}"

    def _replace_single(match: re.Match[str]) -> str:
        val = _word_to_int(match.group(1))
        return str(val) if val is not None else match.group(0)

    out = _HUNDRED_NUM_RE.sub(_replace_hundred, text)
    out = _COMPOUND_NUM_RE.sub(_replace_compound, out)
    out = _DECIMAL_WORDS_RE.sub(_replace_decimal, out)
    out = _SINGLE_NUM_BEFORE_CLINICAL_RE.sub(_replace_single, out)
    # Normalize "140 over 90" / "140 by 90" to "140/90"
    out = re.sub(r"\b(\d{2,3})\s+(?:over|by)\s+(\d{2,3})\b", r"\1/\2", out)
    return out


def normalize_for_exact(text: str) -> str:
    """Light normalization preserving original words: NFKC, Indic digits, lowercasing, space collapse."""
    s = normalize_unicode_and_digits(text).lower()
    s = normalize_number_words(s)
    s = re.sub(r"[\u200c\u200d]", "", s)  # strip zero-width joiners/non-joiners
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_text(text: str) -> str:
    """Full ASR/transliteration normalization for robust deterministic matching."""
    s = normalize_for_exact(text)
    if not s:
        return ""

    for pattern, repl in _PHRASE_CANONICAL_PATTERNS:
        s = pattern.sub(repl, s)

    # Normalize punctuation to spaces while keeping decimals, slashes, <, >, +, and Indic scripts
    s = re.sub(r"[,;:!?\"'()\[\]{}|।]+", " ", s)
    s = re.sub(r"(?<!\d)\.(?!\d)", " ", s)

    # Token-level ASR spelling canonicalization (only Latin tokens via dict lookup)
    tokens = s.split()
    mapped: list[str] = []
    for tok in tokens:
        mapped.append(_TOKEN_CANONICAL_MAP.get(tok, tok))
    return " ".join(mapped)


def tokenize(text: str) -> list[str]:
    """Extract normalized whitespace-delimited tokens."""
    norm = normalize_text(text)
    return norm.split() if norm else []


def split_clauses(text: str) -> list[str]:
    """Split a multi-clause utterance into independent clauses without breaking decimal numbers or body-part lists."""
    if not text or not text.strip():
        return []

    cleaned = normalize_unicode_and_digits(text).strip()
    # First split on strong sentence/contrastive boundaries
    coarse_parts = [p.strip() for p in _STRONG_CLAUSE_SEP_RE.split(cleaned) if p and p.strip()]

    clauses: list[str] = []
    for part in coarse_parts:
        if "," not in part:
            clauses.append(part)
            continue

        # Decide whether each comma separates clauses or list items
        subparts = [sp.strip() for sp in part.split(",") if sp.strip()]
        if len(subparts) <= 1:
            clauses.extend(subparts)
            continue

        current = subparts[0]
        for nxt in subparts[1:]:
            should_split = False
            if _BODY_PART_CONTINUATION_RE.match(nxt) and not _COMMA_LEFT_CONTEXT_CUE_RE.search(current):
                should_split = False
            elif _COMMA_LEFT_CONTEXT_CUE_RE.search(current) or _COMMA_RIGHT_NEW_CLAUSE_RE.match(nxt):
                should_split = True
            elif len(nxt.split()) >= 3 and len(current.split()) >= 2:
                should_split = True

            if should_split:
                clauses.append(current.strip())
                current = nxt
            else:
                current = f"{current}, {nxt}"
        if current.strip():
            clauses.append(current.strip())

    return clauses
