"""Specialized multilingual & exact-Decimal numeric and unit extraction parsers.

Supports:
- English numbers (cardinals, ordinals, decimals, fractions)
- Hindi / Hinglish / Devanagari numbers (0..100, hundreds, thousands, fractions)
- Kannada script & Romanized Kanglish numbers (0..100, hundreds, thousands, fractions)
- Tamil script & Romanized Tanglish numbers (0..100, hundreds, thousands, fractions)
- Marathi & Telugu numerals / core number words
- Mixed-language numeric expressions (e.g. "two kilo पाँच सौ gram", "teen point 5")
- Grams and kilograms with exact Decimal arithmetic (preserving source phrase & normalized value)
- Spoken Beneficiary IDs (including Prisma ASR artifacts like "BE. N 1044", Kannada/Tamil/Hindi digits)
- Repeated numerical corrections & conflict detection within an utterance
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# Indic digit & text normalization
# ---------------------------------------------------------------------------

INDIC_DIGIT_TRANS = str.maketrans(
    "०१२३४५६७८९"  # Devanagari (Hindi / Marathi)
    "೦೧೨೩೪೫೬೭೮೯"  # Kannada
    "௦௧௨௩௪௫௬௭௮௯"  # Tamil
    "౦౧౨౩౪౫౬౭౮౯",  # Telugu
    "0123456789" * 4,
)

# Exclude Devanagari danda punctuation (U+0964, U+0965) so "28 November।" matches word boundaries cleanly.
INDIC_CHAR_CLASS = r"A-Za-z0-9_\u0900-\u0963\u0966-\u097F\u0B80-\u0BFF\u0C00-\u0C7F\u0C80-\u0CFF"
LB = rf"(?<![{INDIC_CHAR_CLASS}])"
RB = rf"(?![{INDIC_CHAR_CLASS}])"


def normalize_numeric_text(text: str) -> str:
    """Normalize Unicode NFC, Indic numerals to ASCII, thousands commas, and spaced decimals."""
    normalized = unicodedata.normalize("NFC", text).translate(INDIC_DIGIT_TRANS)
    # Remove thousands commas inside integers like "2,800" -> "2800"
    normalized = re.sub(r"(?<=\d),(?=\d{3}\b)", "", normalized)
    # Collapse ASR spaced decimals like "2 . 8" -> "2.8"
    normalized = re.sub(r"(?<=\d)\s*\.\s*(?=\d)", ".", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


# ---------------------------------------------------------------------------
# Number dictionaries across English, Hindi/Hinglish, Kannada, Tamil, Marathi
# ---------------------------------------------------------------------------

EN_UNITS: dict[str, int] = {
    "zero": 0,
    "oh": 0,
    "naught": 0,
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

EN_TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fourty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

EN_ORDINALS: dict[str, int] = {
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

# Comprehensive 0..100+ vocabulary across Hindi (Roman + Devanagari),
# Kannada (script + Roman), Tamil (script + Roman), Marathi, and Telugu.
INDIC_NUMBERS: dict[str, int] = {
    # --- Hindi / Hinglish (Romanized) ---
    "shunya": 0,
    "sifar": 0,
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
    "sola": 16,
    "satrah": 17,
    "satra": 17,
    "atharah": 18,
    "athara": 18,
    "unnis": 19,
    "unnees": 19,
    "bees": 20,
    "bis": 20,
    "ikkis": 21,
    "ikkees": 21,
    "bais": 22,
    "baees": 22,
    "teis": 23,
    "teees": 23,
    "chaubis": 24,
    "chaubees": 24,
    "pachchis": 25,
    "pachis": 25,
    "pachchees": 25,
    "chhabbis": 26,
    "chhabees": 26,
    "sattais": 27,
    "sattaees": 27,
    "atthais": 28,
    "atthaees": 28,
    "untis": 29,
    "untees": 29,
    "tees": 30,
    "tis": 30,
    "iktis": 31,
    "ikatis": 31,
    "battis": 32,
    "taintis": 33,
    "chautis": 34,
    "chauntis": 34,
    "paitis": 35,
    "paintis": 35,
    "chhattis": 36,
    "saintis": 37,
    "adtis": 38,
    "artis": 38,
    "untalis": 39,
    "chalis": 40,
    "chaalis": 40,
    "iktalis": 41,
    "bayalis": 42,
    "taintalis": 43,
    "chauwalis": 44,
    "chawalis": 44,
    "paintalis": 45,
    "paitalis": 45,
    "chhiyalis": 46,
    "saintalis": 47,
    "adtalis": 48,
    "artalis": 48,
    "unchas": 49,
    "pachas": 50,
    "pachaas": 50,
    "ikyawan": 51,
    "ikyavan": 51,
    "bawan": 52,
    "baawan": 52,
    "tirpan": 53,
    "chauwan": 54,
    "chauan": 54,
    "pachpan": 55,
    "chhappan": 56,
    "sattawan": 57,
    "satavan": 57,
    "atthawan": 58,
    "athavan": 58,
    "unsath": 59,
    "saath": 60,
    "sath": 60,
    "iksath": 61,
    "basath": 62,
    "tirsath": 63,
    "chausath": 64,
    "painsath": 65,
    "paisath": 65,
    "chhiyasath": 66,
    "sadsath": 67,
    "sarsath": 67,
    "adsath": 68,
    "arsath": 68,
    "unhattar": 69,
    "sattar": 70,
    "ikhattar": 71,
    "bahattar": 72,
    "tihattar": 73,
    "chauhattar": 74,
    "pachhattar": 75,
    "chhihattar": 76,
    "sathattar": 77,
    "athhattar": 78,
    "unyasi": 79,
    "assi": 80,
    "ikyasi": 81,
    "bayasi": 82,
    "tirasi": 83,
    "chaurasi": 84,
    "pachasi": 85,
    "chhiyasi": 86,
    "satasi": 87,
    "athasi": 88,
    "nawasi": 89,
    "nabbe": 90,
    "ikyanwe": 91,
    "banwe": 92,
    "tiranwe": 93,
    "chauranwe": 94,
    "pachanwe": 95,
    "chhiyanwe": 96,
    "satanwe": 97,
    "athanwe": 98,
    "ninyanwe": 99,
    "sau": 100,
    # --- Devanagari (Hindi + Marathi) ---
    "शून्य": 0,
    "सिफर": 0,
    "एक": 1,
    "दो": 2,
    "दोन": 2,
    "तीन": 3,
    "चार": 4,
    "पांच": 5,
    "पाँच": 5,
    "पाच": 5,
    "छह": 6,
    "छे": 6,
    "सहा": 6,
    "सात": 7,
    "आठ": 8,
    "नौ": 9,
    "नऊ": 9,
    "दस": 10,
    "दहा": 10,
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
    "वीस": 20,
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
    "बत्तीस": 32,
    "तैंतीस": 33,
    "चौंतीस": 34,
    "पैंतीस": 35,
    "छत्तीस": 36,
    "सैंतीस": 37,
    "अड़तीस": 38,
    "उनतालीस": 39,
    "चालीस": 40,
    "इकतालीस": 41,
    "बयालीस": 42,
    "तैंतालीस": 43,
    "चवालीस": 44,
    "पैंतालीस": 45,
    "छियालीस": 46,
    "सैंतालीस": 47,
    "अड़तालीस": 48,
    "उनचास": 49,
    "पचास": 50,
    "पन्नास": 50,
    "इक्यावन": 51,
    "बावन": 52,
    "बावन्न": 52,
    "तिरपन": 53,
    "चौवन": 54,
    "पचपन": 55,
    "छप्पन": 56,
    "सत्तावन": 57,
    "अट्ठावन": 58,
    "उनसठ": 59,
    "साठ": 60,
    "इकसठ": 61,
    "बासठ": 62,
    "तिरसठ": 63,
    "चौंसठ": 64,
    "पैंसठ": 65,
    "छियासठ": 66,
    "सड़सठ": 67,
    "अड़सठ": 68,
    "उनहत्तर": 69,
    "सत्तर": 70,
    "इकहत्तर": 71,
    "बहत्तर": 72,
    "तिहत्तर": 73,
    "चौहत्तर": 74,
    "पचहत्तर": 75,
    "छिहत्तर": 76,
    "सतहत्तर": 77,
    "अठहत्तर": 78,
    "उन्यासी": 79,
    "अस्सी": 80,
    "इक्यासी": 81,
    "बयासी": 82,
    "तिरासी": 83,
    "चौरासी": 84,
    "पचासी": 85,
    "छियासी": 86,
    "सत्तासी": 87,
    "अठासी": 88,
    "नवासी": 89,
    "नब्बे": 90,
    "इक्यानवे": 91,
    "बानवे": 92,
    "तिरानवे": 93,
    "चौरानवे": 94,
    "पचानवे": 95,
    "छियानवे": 96,
    "सत्तानवे": 97,
    "अट्ठानवे": 98,
    "निन्यानवे": 99,
    "सौ": 100,
    # --- Kannada script ---
    "ಸೊನ್ನೆ": 0,
    "ಒಂದು": 1,
    "ಎರಡು": 2,
    "ಮೂರು": 3,
    "ನಾಲ್ಕು": 4,
    "ಐದು": 5,
    "ಆರು": 6,
    "ಏಳು": 7,
    "ಎಂಟು": 8,
    "ಒಂಬತ್ತು": 9,
    "ಹತ್ತು": 10,
    "ಹನ್ನೊಂದು": 11,
    "ಹನ್ನೆರಡು": 12,
    "ಹದಿಮೂರು": 13,
    "ಹದಿನಾಲ್ಕು": 14,
    "ಹದಿನೈದು": 15,
    "ಹದಿನಾರು": 16,
    "ಹದಿನೇಳು": 17,
    "ಹದಿನೆಂಟು": 18,
    "ಹತ್ತೊಂಬತ್ತು": 19,
    "ಇಪ್ಪತ್ತು": 20,
    "ಇಪ್ಪತ್ತೊಂದು": 21,
    "ಇಪ್ಪತ್ತೆರಡು": 22,
    "ಇಪ್ಪತ್ತಮೂರು": 23,
    "ಇಪ್ಪತ್ತನಾಲ್ಕು": 24,
    "ಇಪ್ಪತ್ತೈದು": 25,
    "ಇಪ್ಪತ್ತಾರು": 26,
    "ಇಪ್ಪತ್ತೇಳು": 27,
    "ಇಪ್ಪತ್ತೆಂಟು": 28,
    "ಇಪ್ಪತ್ತೊಂಬತ್ತು": 29,
    "ಮೂವತ್ತು": 30,
    "ಮೂವತ್ತೊಂದು": 31,
    "ಮೂವತ್ತೆರಡು": 32,
    "ಮೂವತ್ತೈದು": 35,
    "ನಲವತ್ತು": 40,
    "ನಲವತ್ತೈದು": 45,
    "ನಲವತ್ತೆಂಟು": 48,
    "ಐವತ್ತು": 50,
    "ಐವತ್ತೊಂದು": 51,
    "ಐವತ್ತೆರಡು": 52,
    "ಐವತ್ತಮೂರು": 53,
    "ಐವತ್ತನಾಲ್ಕು": 54,
    "ಐವತ್ತೈದು": 55,
    "ಐವತ್ತಾರು": 56,
    "ಐವತ್ತೇಳು": 57,
    "ಐವತ್ತೆಂಟು": 58,
    "ಅರವತ್ತು": 60,
    "ಅರವತ್ತೆರಡು": 62,
    "ಅರವತ್ತೈದು": 65,
    "ಎಪ್ಪತ್ತು": 70,
    "ಎಪ್ಪತ್ತೈದು": 75,
    "ಎಂಬತ್ತು": 80,
    "ತೊಂಬತ್ತು": 90,
    "ನೂರು": 100,
    "ಇನ್ನೂರು": 200,
    "ಮುನ್ನೂರು": 300,
    "ನಾನ್ನೂರು": 400,
    "ಐನೂರು": 500,
    "ಆರುನೂರು": 600,
    "ಏಳುನೂರು": 700,
    "ಎಂಟುನೂರು": 800,
    "ಒಂಬತ್ತುನೂರು": 900,
    # --- Romanized Kannada (Kanglish) ---
    "sonne": 0,
    "ondu": 1,
    "eradu": 2,
    "mooru": 3,
    "muru": 3,
    "naalku": 4,
    "nalku": 4,
    "aidu": 5,
    "aaru": 6,
    "elu": 7,
    "yelu": 7,
    "entu": 8,
    "yentu": 8,
    "ombattu": 9,
    "hattu": 10,
    "hannondu": 11,
    "hanneradu": 12,
    "hadimooru": 13,
    "hadinaalku": 14,
    "hadinaidu": 15,
    "hadinaaru": 16,
    "hadinelu": 17,
    "hadinentu": 18,
    "hattombattu": 19,
    "ippattu": 20,
    "ippattaidu": 25,
    "ippattentu": 28,
    "moovattu": 30,
    "muvattu": 30,
    "nalavattu": 40,
    "aivattu": 50,
    "aivatteradu": 52,
    "aivattamooru": 53,
    "aivattaidu": 55,
    "aravattu": 60,
    "eppattu": 70,
    "embattu": 80,
    "tombattu": 90,
    "nooru": 100,
    "innooru": 200,
    "munnooru": 300,
    "naannooru": 400,
    "ainooru": 500,
    "aarunooru": 600,
    "elunooru": 700,
    "entunooru": 800,
    # --- Tamil script ---
    "பூஜ்ஜியம்": 0,
    "ஒன்று": 1,
    "ஒண்ணு": 1,
    "இரண்டு": 2,
    "ரெண்டு": 2,
    "மூன்று": 3,
    "மூணு": 3,
    "நான்கு": 4,
    "நாலு": 4,
    "ஐந்து": 5,
    "அஞ்சு": 5,
    "ஆறு": 6,
    "ஏழு": 7,
    "எட்டு": 8,
    "ஒன்பது": 9,
    "பத்து": 10,
    "பதினொன்று": 11,
    "பன்னிரண்டு": 12,
    "பதிமூன்று": 13,
    "பதினான்கு": 14,
    "பதினைந்து": 15,
    "பதினாறு": 16,
    "பதினேழு": 17,
    "பதினெட்டு": 18,
    "பத்தொன்பது": 19,
    "இருபது": 20,
    "இருபத்து": 20,
    "இருபத்தொன்று": 21,
    "இருபத்திரண்டு": 22,
    "இருபத்தைந்து": 25,
    "இருபத்தெட்டு": 28,
    "முப்பது": 30,
    "முப்பத்து": 30,
    "நாற்பது": 40,
    "நாற்பத்து": 40,
    "ஐம்பது": 50,
    "ஐம்பத்து": 50,
    "ஐம்பத்திரண்டு": 52,
    "ஐம்பத்துமூன்று": 53,
    "ஐம்பத்தைந்து": 55,
    "அறுபது": 60,
    "அறுபத்து": 60,
    "எழுபது": 70,
    "எழுபத்து": 70,
    "எண்பது": 80,
    "எண்பத்து": 80,
    "தொண்ணூறு": 90,
    "தொண்ணூற்று": 90,
    "நூறு": 100,
    "இருநூறு": 200,
    "முந்நூறு": 300,
    "நானூறு": 400,
    "ஐநூறு": 500,
    "அறுநூறு": 600,
    "எழுநூறு": 700,
    "எண்ணூறு": 800,
    "தொள்ளாயிரம்": 900,
    # --- Romanized Tamil (Tanglish) ---
    "poojyam": 0,
    "ondru": 1,
    "onnu": 1,
    "irandu": 2,
    "rendu": 2,
    "moondru": 3,
    "moonu": 3,
    "naangu": 4,
    "naalu": 4,
    "aindhu": 5,
    "anju": 5,
    "ezhu": 7,
    "ettu": 8,
    "onbathu": 9,
    "patthu": 10,
    "pathu": 10,
    "irupathu": 20,
    "iruvathu": 20,
    "muppathu": 30,
    "naarpadhu": 40,
    "naapathu": 40,
    "aimbathu": 50,
    "ambathu": 50,
    "arupadhu": 60,
    "ezhupadhu": 70,
    "enbadhu": 80,
    "thonnooru": 90,
    # --- Telugu script (core) ---
    "సున్నా": 0,
    "ఒకటి": 1,
    "రెండు": 2,
    "మూడు": 3,
    "నాలుగు": 4,
    "ఐదు": 5,
    "ఆరు": 6,
    "ఏడు": 7,
    "ఎనిమిది": 8,
    "తొమ్మిది": 9,
    "పది": 10,
    "ఇరవై": 20,
    "ముప్పై": 30,
    "నలభై": 40,
    "యాభై": 50,
    "వంద": 100,
}


def _join_dravidian_stem(base_no_vowel: str, consonant_join: str, unit_word: str, matra_map: dict[str, str]) -> str:
    """Apply Unicode vowel-sign sandhi when combining Kannada/Tamil tens stems with unit words."""
    if not unit_word:
        return base_no_vowel
    first = unit_word[0]
    if first in matra_map:
        return f"{base_no_vowel}{matra_map[first]}{unit_word[1:]}"
    return f"{consonant_join}{unit_word}"


def _populate_indic_compounds() -> None:
    """Systematically generate 21..99 compound words for Kannada and Tamil with script sandhi."""
    kn_vowel_matras = {
        "ಅ": "",
        "ಆ": "ಾ",
        "ಇ": "ಿ",
        "ಈ": "ೀ",
        "ಉ": "ು",
        "ಊ": "ೂ",
        "ಎ": "ೆ",
        "ಏ": "ೇ",
        "ಐ": "ೈ",
        "ಒ": "ೊ",
        "ಓ": "ೋ",
    }
    kn_tens = {
        20: "ಇಪ್ಪತ್ತ",
        30: "ಮೂವತ್ತ",
        40: "ನಲವತ್ತ",
        50: "ಐವತ್ತ",
        60: "ಅರವತ್ತ",
        70: "ಎಪ್ಪತ್ತ",
        80: "ಎಂಬತ್ತ",
        90: "ತೊಂಬತ್ತ",
    }
    kn_units = {
        1: "ಒಂದು",
        2: "ಎರಡು",
        3: "ಮೂರು",
        4: "ನಾಲ್ಕು",
        5: "ಐದು",
        6: "ಆರು",
        7: "ಏಳು",
        8: "ಎಂಟು",
        9: "ಒಂಬತ್ತು",
    }
    for t_val, t_stem in kn_tens.items():
        for u_val, u_word in kn_units.items():
            joined = _join_dravidian_stem(t_stem, t_stem, u_word, kn_vowel_matras)
            INDIC_NUMBERS.setdefault(joined, t_val + u_val)
            INDIC_NUMBERS.setdefault(f"{t_stem}ು {u_word}", t_val + u_val)

    ta_vowel_matras = {
        "அ": "",
        "ஆ": "ா",
        "இ": "ி",
        "ஈ": "ீ",
        "உ": "ு",
        "ஊ": "ூ",
        "எ": "ெ",
        "ஏ": "ே",
        "ஐ": "ை",
        "ஒ": "ொ",
        "ஓ": "ோ",
    }
    ta_tens_stems = {
        20: ("இருபத்த", "இருபத்து ", "இருபத்தி "),
        30: ("முப்பத்த", "முப்பத்து ", "முப்பத்தி "),
        40: ("நாற்பத்த", "நாற்பத்து ", "நாற்பத்தி "),
        50: ("ஐம்பத்த", "ஐம்பத்து ", "ஐம்பத்தி "),
        60: ("அறுபத்த", "அறுபத்து ", "அறுபத்தி "),
        70: ("எழுபத்த", "எழுபத்து ", "எழுபத்தி "),
        80: ("எண்பத்த", "எண்பத்து ", "எண்பத்தி "),
        90: ("தொண்ணூற்ற", "தொண்ணூற்று ", "தொண்ணூற்றி "),
    }
    ta_units = {
        1: ("ஒன்று", "ஒண்ணு"),
        2: ("இரண்டு", "ரெண்டு"),
        3: ("மூன்று", "மூணு"),
        4: ("நான்கு", "நாலு"),
        5: ("ஐந்து", "அஞ்சு"),
        6: ("ஆறு",),
        7: ("ஏழு",),
        8: ("எட்டு",),
        9: ("ஒன்பது",),
    }
    for t_val, (elided, sep1, sep2) in ta_tens_stems.items():
        INDIC_NUMBERS.setdefault(sep2.strip(), t_val)
        for u_val, u_forms in ta_units.items():
            for u_word in u_forms:
                sandhi = _join_dravidian_stem(elided, f"{elided}ு", u_word, ta_vowel_matras)
                INDIC_NUMBERS.setdefault(sandhi, t_val + u_val)
                INDIC_NUMBERS.setdefault(f"{sep1}{u_word}", t_val + u_val)
                INDIC_NUMBERS.setdefault(f"{sep2}{u_word}", t_val + u_val)


_populate_indic_compounds()

MULTIPLIERS: dict[str, int] = {
    "hundred": 100,
    "sau": 100,
    "सौ": 100,
    "ನೂರು": 100,
    "nooru": 100,
    "நூறு": 100,
    "ವಂದ": 100,
    "వంద": 100,
    "thousand": 1000,
    "hazar": 1000,
    "hazaar": 1000,
    "हजार": 1000,
    "हज़ार": 1000,
    "ಸಾವಿರ": 1000,
    "saavira": 1000,
    "ஆயிரம்": 1000,
    "aayiram": 1000,
    "వెయ్యి": 1000,
}

DECIMAL_WORDS: frozenset[str] = frozenset(
    {
        "point",
        "dot",
        "dashamlav",
        "दशमलव",
        "पॉइंट",
        "प्वाइंट",
        "ಪಾಯಿಂಟ್",
        "ದಶಮಾಂಶ",
        "ಬಿಂದು",
        "புள்ளி",
        "பாயிண்ட்",
        "pulli",
        "పాయింట్",
    }
)

FRACTION_IDIOMS: dict[str, Decimal] = {
    "half": Decimal("0.5"),
    "aadha": Decimal("0.5"),
    "adha": Decimal("0.5"),
    "आधा": Decimal("0.5"),
    "अर्धा": Decimal("0.5"),
    "ಅರ್ಧ": Decimal("0.5"),
    "ardha": Decimal("0.5"),
    "அரை": Decimal("0.5"),
    "arai": Decimal("0.5"),
    "quarter": Decimal("0.25"),
    "kaalu": Decimal("0.25"),
    "ಕಾಲು": Decimal("0.25"),
    "pauna": Decimal("0.75"),
    "पौना": Decimal("0.75"),
    "ಮುಕ್ಕಾಲು": Decimal("0.75"),
    "mukkaalu": Decimal("0.75"),
    "dedh": Decimal("1.5"),
    "derh": Decimal("1.5"),
    "डेढ़": Decimal("1.5"),
    "डेढ": Decimal("1.5"),
    "दीड": Decimal("1.5"),
    "ಒಂದೂವರೆ": Decimal("1.5"),
    "onduvare": Decimal("1.5"),
    "ஒன்றரை": Decimal("1.5"),
    "ondrarai": Decimal("1.5"),
    "dhai": Decimal("2.5"),
    "dhaai": Decimal("2.5"),
    "adhaai": Decimal("2.5"),
    "ढाई": Decimal("2.5"),
    "अढ़ाई": Decimal("2.5"),
    "अडीच": Decimal("2.5"),
    "ಎರಡೂವರೆ": Decimal("2.5"),
    "eraduvare": Decimal("2.5"),
    "இரண்டரை": Decimal("2.5"),
    "irandarai": Decimal("2.5"),
    "ಮೂರೂವರೆ": Decimal("3.5"),
    "mooruvare": Decimal("3.5"),
    "மூன்றரை": Decimal("3.5"),
    "ನಾಲ್ಕೂವರೆ": Decimal("4.5"),
    "ಐದೂವರೆ": Decimal("5.5"),
}

PREFIX_FRACTIONS: dict[str, Decimal] = {
    "sawa": Decimal("0.25"),
    "sava": Decimal("0.25"),
    "सवा": Decimal("0.25"),
    "sadhe": Decimal("0.5"),
    "saadhe": Decimal("0.5"),
    "साढ़े": Decimal("0.5"),
    "साढे": Decimal("0.5"),
    "साडे": Decimal("0.5"),
    "paune": Decimal("-0.25"),
    "पौने": Decimal("-0.25"),
    "पावणे": Decimal("-0.25"),
}

CONNECTOR_WORDS: frozenset[str] = frozenset({"and", "a", "aur", "और", "ಮತ್ತು", "மற்றும்"})

NUMBER_START_TOKENS: frozenset[str] = (
    frozenset(EN_UNITS)
    | frozenset(EN_TENS)
    | frozenset(EN_ORDINALS)
    | frozenset(INDIC_NUMBERS)
    | frozenset(MULTIPLIERS)
    | frozenset(FRACTION_IDIOMS)
    | frozenset(PREFIX_FRACTIONS)
    | DECIMAL_WORDS
)

NUMBER_WORD_TOKENS: frozenset[str] = NUMBER_START_TOKENS | CONNECTOR_WORDS

# ---------------------------------------------------------------------------
# Exact Decimal integer & number phrase parsing
# ---------------------------------------------------------------------------


def parse_int_tokens(tokens: list[str]) -> int | None:
    """Parse a sequence of integer number words (EN/HI/KN/TA/MR/TE/digits) into an int."""
    if not tokens:
        return None
    total = 0
    current = 0
    consumed_number = False
    for tok in tokens:
        if tok in CONNECTOR_WORDS:
            continue
        if re.fullmatch(r"\d+", tok):
            current += int(tok)
            consumed_number = True
        elif tok in EN_UNITS:
            current += EN_UNITS[tok]
            consumed_number = True
        elif tok in EN_TENS:
            current += EN_TENS[tok]
            consumed_number = True
        elif tok in EN_ORDINALS:
            current += EN_ORDINALS[tok]
            consumed_number = True
        elif tok in INDIC_NUMBERS:
            val = INDIC_NUMBERS[tok]
            if val == 100:
                current = (current or 1) * 100
            else:
                current += val
            consumed_number = True
        elif tok in MULTIPLIERS:
            mult = MULTIPLIERS[tok]
            if mult >= 1000:
                total += (current or 1) * mult
                current = 0
            else:
                current = (current or 1) * mult
            consumed_number = True
        else:
            return None
    if not consumed_number:
        return None
    return total + current


def _parse_frac_tokens(frac_tokens: list[str]) -> str | None:
    """Parse fractional tokens after 'point'/'dashamlav'/'pulli' into exact digit string."""
    if not frac_tokens:
        return None
    if len(frac_tokens) == 1 and re.fullmatch(r"\d+", frac_tokens[0]):
        return frac_tokens[0]

    # Try two-digit compound number like "point eighty five" or "point twenty five" -> "85", "25"
    # ONLY when the first token is tens (>=20) or teens (10..19) and there are no leading zeros
    first_val: int | None = None
    if frac_tokens[0] in EN_TENS:
        first_val = EN_TENS[frac_tokens[0]]
    elif frac_tokens[0] in EN_UNITS and EN_UNITS[frac_tokens[0]] >= 10:
        first_val = EN_UNITS[frac_tokens[0]]
    elif frac_tokens[0] in INDIC_NUMBERS and INDIC_NUMBERS[frac_tokens[0]] >= 10:
        first_val = INDIC_NUMBERS[frac_tokens[0]]

    if first_val is not None:
        compound = parse_int_tokens(frac_tokens)
        if compound is not None and 10 <= compound < 100:
            return str(compound)

    # Otherwise digit-by-digit ("point zero eight" -> "08", "point eight five" -> "85")
    frac_digits: list[str] = []
    for ft in frac_tokens:
        if re.fullmatch(r"\d+", ft):
            frac_digits.append(ft)
        elif ft in EN_UNITS and EN_UNITS[ft] < 10:
            frac_digits.append(str(EN_UNITS[ft]))
        elif ft in INDIC_NUMBERS and INDIC_NUMBERS[ft] < 10:
            frac_digits.append(str(INDIC_NUMBERS[ft]))
        else:
            return None
    return "".join(frac_digits) if frac_digits else None


def parse_decimal_phrase(phrase: str) -> Decimal | None:
    """Parse numeric, spoken English, spoken Indic, mixed-language, or fractional phrases as exact Decimal."""
    cleaned = normalize_numeric_text(phrase).lower().replace("-", " ")
    if not cleaned:
        return None

    tokens = [t for t in cleaned.split() if t]
    while tokens and tokens[0] in CONNECTOR_WORDS:
        tokens.pop(0)
    while tokens and tokens[-1] in CONNECTOR_WORDS:
        tokens.pop()
    if not tokens:
        return None

    # Direct decimal / int
    if len(tokens) == 1 and re.fullmatch(r"\d+(?:\.\d+)?", tokens[0]):
        try:
            return Decimal(tokens[0])
        except InvalidOperation:
            return None

    # Single-word fraction idioms ("dhai", "ढाई", "dedh", "आधा", "ಒಂದೂವರೆ", "arai")
    if len(tokens) == 1 and tokens[0] in FRACTION_IDIOMS:
        return FRACTION_IDIOMS[tokens[0]]

    # Standalone "sawa" (= 1.25)
    if len(tokens) == 1 and tokens[0] in {"sawa", "sava", "सवा"}:
        return Decimal("1.25")

    # Prefix fractions: "साढ़े तीन" -> 3.5, "सवा तीन" -> 3.25, "पौने तीन" -> 2.75
    if tokens[0] in PREFIX_FRACTIONS and len(tokens) >= 2:
        base = parse_int_tokens(tokens[1:])
        if base is not None and base > 0:
            return Decimal(base) + PREFIX_FRACTIONS[tokens[0]]

    # Kannada suffix fraction: "ಎರಡು ಕಾಲು" -> 2.25, "ಎರಡು ಅರ್ಧ" -> 2.5
    if len(tokens) >= 2 and tokens[-1] in {"ಕಾಲು", "kaalu", "ಅರ್ಧ", "ardha", "ಮುಕ್ಕಾಲು", "mukkaalu"}:
        base = parse_int_tokens(tokens[:-1])
        if base is not None:
            return Decimal(base) + FRACTION_IDIOMS[tokens[-1]]

    # "<int> and a half" / "<int> aur aadha" / "<int> ಮತ್ತು ಅರ್ಧ" / "<int> மற்றும் அரை"
    _HALF_WORDS = {"half", "aadha", "adha", "आधा", "ಅರ್ಧ", "ardha", "அரை", "arai"}
    if len(tokens) >= 3 and tokens[-1] in _HALF_WORDS and tokens[-2] in ({"a"} | CONNECTOR_WORDS):
        cut = -3 if tokens[-2] == "a" and len(tokens) >= 4 and tokens[-3] in CONNECTOR_WORDS else -2
        base = parse_int_tokens(tokens[:cut])
        if base is not None:
            return Decimal(base) + Decimal("0.5")

    # Decimal word: "two point eight", "48 point 5", "दो दशमलव आठ", "point five"
    for idx, tok in enumerate(tokens):
        if tok in DECIMAL_WORDS and idx < len(tokens) - 1:
            int_part = 0 if idx == 0 else parse_int_tokens(tokens[:idx])
            if int_part is None:
                return None
            frac_str = _parse_frac_tokens(tokens[idx + 1 :])
            if frac_str is None:
                return None
            try:
                return Decimal(f"{int_part}.{frac_str}")
            except InvalidOperation:
                return None

    int_val = parse_int_tokens(tokens)
    return Decimal(int_val) if int_val is not None else None


def decimal_to_float(val: Decimal, places: int = 3) -> float:
    """Quantize a Decimal cleanly and return float for schema compatibility."""
    q = Decimal("10") ** -places
    return float(val.quantize(q, rounding=ROUND_HALF_UP))


def format_decimal_clean(val: Decimal) -> str:
    """Format Decimal without trailing insignificant zeros (e.g. Decimal('2.800') -> '2.8')."""
    s = format(val.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


# ---------------------------------------------------------------------------
# Weight extraction patterns & repeated correction / conflict resolution
# ---------------------------------------------------------------------------

KG_UNITS = (
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
    "ಕಿಲೋಗ್ರಾಂ",
    "ಕಿಲೋ",
    "ಕೆಜಿ",
    "கிலோகிராம்",
    "கிலோ",
)
GRAM_UNITS = (
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
WEIGHT_CUES = (
    "weight",
    "wt",
    "wight",
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
    "வெயிட்",
    "edai",
    "బరువు",
    "వెయిట్",
    "baruvu",
    "ഭാരം",
    "തൂക്കം",
    "thookam",
    "ওজন",
    "ojon",
    "વજન",
    "ਭਾਰ",
)

KG_UNIT_RE = "(?:" + "|".join(re.escape(u) for u in KG_UNITS) + ")"
# Exclude concentration/ratio lab units like "g/dL", "g/L", "gm%" from matching gram weights.
GRAM_UNIT_RE = (
    "(?:"
    + "|".join(re.escape(u) for u in GRAM_UNITS)
    + r")(?!\s*/\s*(?:d?l|ml)\b|\s*%)"
)
WEIGHT_CUE_RE = "(?:" + "|".join(re.escape(c) for c in WEIGHT_CUES) + ")"
CUE_CONN_RE = (
    r"(?:should\s+be|will\s+be|needs\s+to\s+be|is\s+now|recorded\s+as|"
    r"changed\s+to|updated\s+to|change\s+to|update\s+to|make\s+(?:it|that)|"
    r"is\s+around|is\s+about|around|about|nearly|almost|"
    r"to|as|is|was|are|hai|है|था|का|की|लगभग|"
    r"வந்து|உள்ளது|ஆக|என்பது|சுமார்|"
    r"వచ్చేసి|ఉంది|అంటే|సుమారు|"
    r"ಆಗಿದೆ|ಇದೆ|ಸುಮಾರು|"
    r"ആണ്|ആയി|ഏകദേശം|"
    r"=|:)?"
)

QTY_START_TOKEN = (
    r"(?:\d+(?:\.\d+)?|"
    + "|".join(re.escape(w) for w in sorted(NUMBER_START_TOKENS, key=len, reverse=True))
    + r")"
)
QTY_CONT_TOKEN = (
    r"(?:\d+(?:\.\d+)?|"
    + "|".join(re.escape(w) for w in sorted(NUMBER_WORD_TOKENS, key=len, reverse=True))
    + r")"
)
QTY_PHRASE = rf"(?:{QTY_START_TOKEN}(?:[\s\-]+{QTY_CONT_TOKEN}){{0,5}})"

COMPOUND_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{LB}{WEIGHT_CUE_RE}{RB}\s*{CUE_CONN_RE}\s*)?"
    rf"(?P<kg_qty>{LB}{QTY_PHRASE}{RB})\s*(?P<kg_unit>{KG_UNIT_RE}{RB})"
    rf"\s*(?:and|aur|और|ಮತ್ತು|மற்றும்|,)?\s*"
    rf"(?P<g_qty>{LB}{QTY_PHRASE}{RB})\s*(?P<g_unit>{GRAM_UNIT_RE}{RB})",
    re.IGNORECASE,
)

KG_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{LB}{WEIGHT_CUE_RE}{RB}\s*{CUE_CONN_RE}\s*)?"
    rf"(?P<qty>{LB}{QTY_PHRASE})\s*(?P<unit>{KG_UNIT_RE}{RB})",
    re.IGNORECASE,
)

GRAM_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{LB}{WEIGHT_CUE_RE}{RB}\s*{CUE_CONN_RE}\s*)?"
    rf"(?P<qty>{LB}{QTY_PHRASE})\s*(?P<unit>{GRAM_UNIT_RE}{RB})",
    re.IGNORECASE,
)

CUE_ONLY_WEIGHT_PATTERN = re.compile(
    rf"(?P<cue>{LB}{WEIGHT_CUE_RE}{RB})\s*{CUE_CONN_RE}\s*"
    rf"(?P<qty>{LB}{QTY_PHRASE}{RB})",
    re.IGNORECASE,
)

CORRECTION_BRIDGE_RE = re.compile(
    r"(?:no|nope|nahi|nahin|sorry|wait|actually|correction|instead|i\s+meant|change\s+to|update\s+to|make\s+(?:it|that)|"
    r"नहीं|नही|गलत|माफ\s+कीजिए|बदलो|सही|दरअसल|ಇಲ್ಲ|ತಪ್ಪು|ಬದಲಿಗೆ|இல்லை|தவறு)",
    re.IGNORECASE,
)

CONFLICT_BRIDGE_RE = re.compile(r"\b(?:or|ya)\b|या|ಅಥವಾ|அல்லது", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class WeightCandidate:
    """Parsed weight expression with exact Decimal precision and provenance span."""

    value_kg: Decimal
    raw_value: Decimal
    unit_kind: str  # "kg" | "g" | "compound_kg_g" | "unitless"
    source_text: str
    start: int
    end: int
    has_explicit_unit: bool


def find_weight_candidates(text: str) -> list[WeightCandidate]:
    """Find all weight candidates in `text` using exact Decimal arithmetic without overlap."""
    text = normalize_numeric_text(text)
    candidates: list[WeightCandidate] = []
    occupied: list[tuple[int, int]] = []

    def _overlaps(s: int, e: int) -> bool:
        return any(not (e <= os or s >= oe) for os, oe in occupied)

    # 1. Compound kg + gram
    for m in COMPOUND_WEIGHT_PATTERN.finditer(text):
        kg_part = parse_decimal_phrase(m.group("kg_qty"))
        g_part = parse_decimal_phrase(m.group("g_qty"))
        if kg_part is not None and g_part is not None:
            val_kg = kg_part + (g_part / Decimal("1000"))
            candidates.append(
                WeightCandidate(
                    value_kg=val_kg,
                    raw_value=val_kg,
                    unit_kind="compound_kg_g",
                    source_text=m.group(0).strip(),
                    start=m.start(),
                    end=m.end(),
                    has_explicit_unit=True,
                )
            )
            occupied.append((m.start(), m.end()))

    # 2. Kilograms
    for m in KG_WEIGHT_PATTERN.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        val = parse_decimal_phrase(m.group("qty"))
        if val is not None:
            candidates.append(
                WeightCandidate(
                    value_kg=val,
                    raw_value=val,
                    unit_kind="kg",
                    source_text=m.group(0).strip(),
                    start=m.start(),
                    end=m.end(),
                    has_explicit_unit=True,
                )
            )
            occupied.append((m.start(), m.end()))

    # 3. Grams
    for m in GRAM_WEIGHT_PATTERN.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        val = parse_decimal_phrase(m.group("qty"))
        if val is not None:
            candidates.append(
                WeightCandidate(
                    value_kg=val / Decimal("1000"),
                    raw_value=val,
                    unit_kind="g",
                    source_text=m.group(0).strip(),
                    start=m.start(),
                    end=m.end(),
                    has_explicit_unit=True,
                )
            )
            occupied.append((m.start(), m.end()))

    # 4. Unitless explicit weight cue ("weight is 52", "वजन 48.5", "weight 2800")
    for m in CUE_ONLY_WEIGHT_PATTERN.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        val = parse_decimal_phrase(m.group("qty"))
        if val is not None:
            candidates.append(
                WeightCandidate(
                    value_kg=val,
                    raw_value=val,
                    unit_kind="unitless",
                    source_text=m.group(0).strip(),
                    start=m.start(),
                    end=m.end(),
                    has_explicit_unit=False,
                )
            )
            occupied.append((m.start(), m.end()))

    candidates.sort(key=lambda c: c.start)
    return candidates


def resolve_repeated_candidates(
    text: str,
    candidates: list[WeightCandidate],
) -> tuple[WeightCandidate | None, bool, list[WeightCandidate]]:
    """Resolve multiple weight mentions within one utterance.

    Returns `(selected, detected_inline_correction, conflicting_candidates)`.
    - If a later candidate follows a correction bridge ("no", "sorry", "actually", "nahi")
      without an "or" conflict bridge, select the final corrected candidate and set
      `detected_inline_correction=True`.
    - If distinct candidates appear without a correction bridge (e.g. "2.6 or 2.8 kg",
      "2.6 kg 2.8 kg"), return `(None, False, distinct_candidates)` so the caller asks
      for confirmation rather than guessing.
    """
    if not candidates:
        return None, False, []
    if len(candidates) == 1:
        return candidates[0], False, []

    # Deduplicate identical values (e.g. worker repeated "2.8 kg, 2.8 kg")
    distinct: list[WeightCandidate] = []
    seen_vals: set[Decimal] = set()
    for c in candidates:
        q = c.value_kg.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        if q not in seen_vals:
            seen_vals.add(q)
            distinct.append(c)

    if len(distinct) == 1:
        return distinct[-1], False, []

    # Check transitions between adjacent candidates
    has_correction = False
    has_conflict = False
    for prev_c, next_c in zip(candidates, candidates[1:]):
        if prev_c.value_kg.quantize(Decimal("0.001")) == next_c.value_kg.quantize(Decimal("0.001")):
            continue
        between = text[prev_c.end : next_c.start]
        if CONFLICT_BRIDGE_RE.search(between):
            has_conflict = True
        elif CORRECTION_BRIDGE_RE.search(between):
            has_correction = True
        else:
            # Ambiguous consecutive distinct numbers with no correction cue
            has_conflict = True

    if has_correction and not has_conflict:
        return candidates[-1], True, []

    return None, False, distinct


# ---------------------------------------------------------------------------
# Spoken Beneficiary ID parser (multilingual + ASR-artifact resilient)
# ---------------------------------------------------------------------------

_SPOKEN_ID_DIGIT_WORDS: dict[str, str] = {
    # English
    "zero": "0",
    "oh": "0",
    "one": "1",
    "two": "2",
    "three": "3",
    "four": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8",
    "nine": "9",
    "ten": "10",
    # Hindi / Hinglish
    "shunya": "0",
    "ek": "1",
    "do": "2",
    "teen": "3",
    "tin": "3",
    "char": "4",
    "chaar": "4",
    "panch": "5",
    "paanch": "5",
    "chhe": "6",
    "cheh": "6",
    "saat": "7",
    "sat": "7",
    "aath": "8",
    "ath": "8",
    "nau": "9",
    "das": "10",
    "शून्य": "0",
    "एक": "1",
    "दो": "2",
    "तीन": "3",
    "चार": "4",
    "पांच": "5",
    "पाँच": "5",
    "छह": "6",
    "छे": "6",
    "सात": "7",
    "आठ": "8",
    "नौ": "9",
    "दस": "10",
    # Kannada
    "ಸೊನ್ನೆ": "0",
    "ಒಂದು": "1",
    "ಎರಡು": "2",
    "ಮೂರು": "3",
    "ನಾಲ್ಕು": "4",
    "ಐದು": "5",
    "ಆರು": "6",
    "ಏಳು": "7",
    "ಎಂಟು": "8",
    "ಒಂಬತ್ತು": "9",
    "ಹತ್ತು": "10",
    "sonne": "0",
    "ondu": "1",
    "eradu": "2",
    "mooru": "3",
    "naalku": "4",
    "aidu": "5",
    "aaru": "6",
    "elu": "7",
    "entu": "8",
    "ombattu": "9",
    "hattu": "10",
    # Tamil
    "பூஜ்ஜியம்": "0",
    "ஒன்று": "1",
    "ஒண்ணு": "1",
    "இரண்டு": "2",
    "ரெண்டு": "2",
    "மூன்று": "3",
    "நான்கு": "4",
    "ஐந்து": "5",
    "ஆறு": "6",
    "ஏழு": "7",
    "எட்டு": "8",
    "ஒன்பது": "9",
    "பத்து": "10",
    "ondru": "1",
    "onnu": "1",
    "irandu": "2",
    "rendu": "2",
    "moondru": "3",
    "naangu": "4",
    "aindhu": "5",
    "ezhu": "7",
    "ettu": "8",
    "onbathu": "9",
    "patthu": "10",
    # Two-digit ID tail words ("ten forty four" -> 10 + 44)
    "forty": "4",
    "fifty": "5",
}

_TWO_DIGIT_WORDS: dict[str, str] = {
    **{k: str(v) for k, v in INDIC_NUMBERS.items() if 10 <= v <= 99},
    "ten": "10",
    "eleven": "11",
    "twelve": "12",
    "thirteen": "13",
    "fourteen": "14",
    "fifteen": "15",
    "sixteen": "16",
    "seventeen": "17",
    "eighteen": "18",
    "nineteen": "19",
    "twenty": "20",
    "thirty": "30",
    "forty": "40",
    "fifty": "50",
    "sixty": "60",
    "seventy": "70",
    "eighty": "80",
    "ninety": "90",
}


def find_beneficiary_id_candidates(text: str) -> list[tuple[str, str, int, int]]:
    """Find all `(canonical_ben_id, source_text, start, end)` mentions in `text`.

    Handles:
    - `BEN-1042`, `BEN 1042`, `B E N 1 0 4 2`
    - Prisma ASR artifacts: `BE. N 1044`, `B.E.N. 1044`, `बीईएन 1042`, `बी ई एन 1042`
    - Spoken digits: `BEN one zero five six`, `ID ek shunya char do`, `BEN ten forty four`
    """
    norm = normalize_numeric_text(text)
    results: list[tuple[str, str, int, int]] = []
    occupied: list[tuple[int, int]] = []

    def _add(bid: str, src: str, s: int, e: int) -> None:
        if any(not (e <= os or s >= oe) for os, oe in occupied):
            return
        occupied.append((s, e))
        results.append((bid, src, s, e))

    # 1. Explicit BEN/BE.N/बीईएन + 4 separated or grouped digits
    for m in re.finditer(
        r"\b(?:B[\s.\-_]*E[\s.\-_]*N|बी[\s.\-_]*ई[\s.\-_]*एन)[\s.\-_]*(?P<d>\d(?:\s*\d){2,5})\b",
        norm,
        re.IGNORECASE,
    ):
        digits = re.sub(r"\s+", "", m.group("d"))
        _add(f"BEN-{digits}", m.group(0).strip(), m.start(), m.end())

    # 2. Spoken digit words after BEN / BE.N / ID / आईडी / ಐಡಿ / ஐடி
    token_matches = list(
        re.finditer(rf"[{INDIC_CHAR_CLASS}]+", norm.lower())
    )
    i = 0
    while i < len(token_matches):
        tok = token_matches[i].group(0)
        # Check "be" followed by "n" (e.g., "BE. N one zero four four")
        trigger_end_idx = i
        matched_trigger = tok in {"ben", "id", "आईडी", "बीईएन", "ಐಡಿ", "ஐடி"}
        if not matched_trigger and tok == "be" and i + 1 < len(token_matches) and token_matches[i + 1].group(0) == "n":
            matched_trigger = True
            trigger_end_idx = i + 1

        if matched_trigger:
            start_pos = token_matches[i].start()
            digits_buf: list[str] = []
            end_pos = token_matches[trigger_end_idx].end()
            j = trigger_end_idx + 1
            while j < min(len(token_matches), trigger_end_idx + 8):
                sub = token_matches[j].group(0)
                if sub.isdigit():
                    digits_buf.append(sub)
                    end_pos = token_matches[j].end()
                elif sub in _TWO_DIGIT_WORDS and len("".join(digits_buf)) <= 2:
                    # Handle "ten forty four" (10 + 40 + 4 = 1044) vs "forty two" -> "42"
                    if sub in EN_TENS and j + 1 < len(token_matches) and token_matches[j + 1].group(0) in EN_UNITS and EN_UNITS[token_matches[j + 1].group(0)] < 10:
                        val = EN_TENS[sub] + EN_UNITS[token_matches[j + 1].group(0)]
                        digits_buf.append(str(val))
                        end_pos = token_matches[j + 1].end()
                        j += 1
                    else:
                        digits_buf.append(_TWO_DIGIT_WORDS[sub])
                        end_pos = token_matches[j].end()
                elif sub in _SPOKEN_ID_DIGIT_WORDS:
                    digits_buf.append(_SPOKEN_ID_DIGIT_WORDS[sub])
                    end_pos = token_matches[j].end()
                elif digits_buf:
                    break
                else:
                    break
                if len("".join(digits_buf)) >= 4:
                    break
                j += 1
            joined = "".join(digits_buf)
            if len(joined) == 4 and joined.isdigit():
                _add(f"BEN-{joined}", norm[start_pos:end_pos].strip(), start_pos, end_pos)
                i = j
                continue
        i += 1

    # 3. Standalone short-utterance 4-digit ID (1040..1099)
    if not results and len(token_matches) <= 6:
        m_four = re.search(r"\b(10\d{2})\b", norm)
        if m_four:
            _add(f"BEN-{m_four.group(1)}", m_four.group(0), m_four.start(), m_four.end())

    results.sort(key=lambda r: r[2])
    return results


def resolve_beneficiary_id_mention(text: str) -> tuple[str | None, str | None, bool, list[str]]:
    """Resolve beneficiary ID mentions, handling repeated corrections & conflicts.

    Returns `(selected_id, source_text, detected_correction, conflicting_ids)`.
    """
    norm = normalize_numeric_text(text)
    cands = find_beneficiary_id_candidates(norm)
    if not cands:
        return None, None, False, []
    if len(cands) == 1:
        bid, src, _, _ = cands[0]
        return bid, src, False, []

    distinct_ids: list[str] = []
    for bid, _, _, _ in cands:
        if bid not in distinct_ids:
            distinct_ids.append(bid)
    if len(distinct_ids) == 1:
        bid, src, _, _ = cands[-1]
        return bid, src, False, []

    has_corr = False
    has_conf = False
    for prev_c, next_c in zip(cands, cands[1:]):
        if prev_c[0] == next_c[0]:
            continue
        between = norm[prev_c[3] : next_c[2]]
        if CONFLICT_BRIDGE_RE.search(between):
            has_conf = True
        elif CORRECTION_BRIDGE_RE.search(between):
            has_corr = True
        else:
            has_conf = True

    if has_corr and not has_conf:
        bid, src, _, _ = cands[-1]
        return bid, src, True, []
    return None, None, False, distinct_ids
