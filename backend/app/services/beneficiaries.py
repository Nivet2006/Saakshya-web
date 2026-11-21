"""100% synthetic demonstration beneficiary directory.

GUARDRAIL: Never store real beneficiary names, phone numbers, addresses, or health
records. All entries below are entirely fictional demo personas for hackathon use.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_INDIC_DIGIT_TRANS = str.maketrans(
    "०१२३४५६७८९"  # Devanagari
    "೦೧೨೩೪೫೬೭೮೯"  # Kannada
    "௦௧௨௩௪௫௬௭௮௯",  # Tamil
    "0123456789" * 3,
)

_SPOKEN_DIGIT_WORDS: dict[str, str] = {
    "zero": "0",
    "oh": "0",
    "shunya": "0",
    "शून्य": "0",
    "one": "1",
    "ek": "1",
    "एक": "1",
    "two": "2",
    "do": "2",
    "दो": "2",
    "three": "3",
    "teen": "3",
    "tin": "3",
    "तीन": "3",
    "four": "4",
    "char": "4",
    "chaar": "4",
    "चार": "4",
    "five": "5",
    "panch": "5",
    "paanch": "5",
    "पांच": "5",
    "पाँच": "5",
    "six": "6",
    "chhe": "6",
    "cheh": "6",
    "छह": "6",
    "seven": "7",
    "saat": "7",
    "sat": "7",
    "सात": "7",
    "eight": "8",
    "aath": "8",
    "ath": "8",
    "आठ": "8",
    "nine": "9",
    "nau": "9",
    "नौ": "9",
    "ten": "10",
    "das": "10",
    "दस": "10",
    "forty": "4",
    "fifty": "5",
}

_IDENTITY_STOPWORDS = frozenset(
    {
        "no",
        "nope",
        "nahi",
        "nahin",
        "not",
        "actually",
        "sorry",
        "wait",
        "different",
        "wrong",
        "other",
        "beneficiary",
        "name",
        "id",
        "is",
        "it",
        "its",
        "the",
        "correct",
        "visiting",
        "visit",
        "today",
        "for",
        "of",
        "hai",
        "hoon",
        "hun",
        "मेरा",
        "मतलब",
        "नहीं",
        "सही",
        "लाभार्थी",
        "नाम",
        "आईडी",
        "है",
    }
)


@dataclass(frozen=True, slots=True)
class SyntheticBeneficiary:
    beneficiary_id: str
    full_name: str
    aliases: tuple[str, ...]
    category: str  # "pregnant_woman" | "postnatal_mother" | "newborn" | "infant"
    village: str
    preferred_language: str
    synthetic: bool = True


SYNTHETIC_BENEFICIARIES: tuple[SyntheticBeneficiary, ...] = (
    SyntheticBeneficiary(
        beneficiary_id="BEN-1042",
        full_name="Lakshmi Devi",
        aliases=("lakshmi", "laxmi", "लक्ष्मी", "ಲಕ್ಷ್ಮಿ", "லட்சுமி", "लक्ष्मी देवी"),
        category="pregnant_woman",
        village="Rampur Demo Ward 1",
        preferred_language="hi-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1043",
        full_name="Kavitha Rao",
        aliases=("kavitha", "kavita", "कविता", "ಕವಿತಾ", "कविता राव"),
        category="postnatal_mother",
        village="Shantinagar Demo Ward 2",
        preferred_language="kn-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1044",
        full_name="Baby of Kavitha Rao",
        aliases=("kavitha baby", "kavita baby", "kavitha newborn", "baby kavitha"),
        category="newborn",
        village="Shantinagar Demo Ward 2",
        preferred_language="kn-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1045",
        full_name="Sunita Kumari",
        aliases=("sunita", "suneeta", "सुनीता", "सुनीता कुमारी"),
        category="pregnant_woman",
        village="Rampur Demo Ward 1",
        preferred_language="hi-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1046",
        full_name="Meena Selvam",
        aliases=("meena", "मीना", "மீனா", "மீனா செல்வம்"),
        category="infant",
        village="Kaveri Demo Ward 3",
        preferred_language="ta-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1047",
        full_name="Anita Devi",
        aliases=("anita", "aneeta", "अनीता", "अनीता देवी"),
        category="pregnant_woman",
        village="Rampur Demo Ward 2",
        preferred_language="hi-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1048",
        full_name="Lakshmi Narayanan",
        aliases=("lakshmi narayanan", "lakshmi n", "लक्ष्मी नारायणन", "லட்சுமி நாராயணன்"),
        category="postnatal_mother",
        village="Kaveri Demo Ward 3",
        preferred_language="ta-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1056",
        full_name="Anitha Sharma",
        aliases=(
            "anitha sharma",
            "anita sharma",
            "anitha",
            "अनिता शर्मा",
            "अनीता शर्मा",
            "ಅನಿತಾ ಶರ್ಮಾ",
            "அனிதா சர்மா",
        ),
        category="pregnant_woman",
        village="Rampur Demo Ward 1",
        preferred_language="hi-IN",
    ),
)


def extract_spoken_beneficiary_id(text: str) -> str | None:
    """Extract a canonical `BEN-XXXX` ID from spoken digits or number words."""
    norm = unicodedata.normalize("NFC", text).translate(_INDIC_DIGIT_TRANS)
    # 1. Direct BEN-1042 or B E N 1 0 4 2
    m_direct = re.search(
        r"\bB\s*E\s*N[\s\-_]*(\d)\s*(\d)\s*(\d)\s*(\d)\b",
        norm,
        re.IGNORECASE,
    )
    if m_direct:
        return f"BEN-{''.join(m_direct.groups())}"

    m_ben = re.search(r"\bB\s*E\s*N[\s\-_]*(\d{3,6})\b", norm, re.IGNORECASE)
    if m_ben:
        return f"BEN-{m_ben.group(1)}"

    # 2. Spoken digit words after BEN / ID / beneficiary (e.g. "BEN one zero five six", "ID 1042")
    tokens = re.findall(r"[A-Za-z0-9\u0900-\u097F]+", norm.lower())
    for idx, tok in enumerate(tokens):
        if tok in {"ben", "id", "आईडी"}:
            digits: list[str] = []
            for sub in tokens[idx + 1 : idx + 7]:
                if sub.isdigit():
                    digits.append(sub)
                elif sub in _SPOKEN_DIGIT_WORDS:
                    digits.append(_SPOKEN_DIGIT_WORDS[sub])
                elif digits:
                    break
            joined = "".join(digits)
            if len(joined) == 4 and joined.isdigit():
                return f"BEN-{joined}"

    # 3. Standalone 4-digit ID (1040..1099) when utterance is short
    m_four = re.search(r"\b(10\d{2})\b", norm)
    if m_four and len(tokens) <= 6:
        return f"BEN-{m_four.group(1)}"

    return None


class SyntheticBeneficiaryDirectory:
    """Lookup interface resolving spoken names/IDs ONLY against synthetic fixtures."""

    def __init__(self, items: tuple[SyntheticBeneficiary, ...] = SYNTHETIC_BENEFICIARIES) -> None:
        self._items = items
        self._by_id = {b.beneficiary_id.upper(): b for b in items}

    def list_all(self) -> list[SyntheticBeneficiary]:
        return list(self._items)

    def get_by_id(self, beneficiary_id: str) -> SyntheticBeneficiary | None:
        return self._by_id.get(beneficiary_id.strip().upper())

    def search_by_name(self, query: str) -> list[SyntheticBeneficiary]:
        """Return all matching synthetic beneficiaries (caller asks if >1 match)."""
        q = query.strip().lower()
        if not q:
            return []
        exact_id = self.get_by_id(q)
        if exact_id is not None:
            return [exact_id]

        spoken_id = extract_spoken_beneficiary_id(q)
        if spoken_id is not None:
            by_spoken = self.get_by_id(spoken_id)
            return [by_spoken] if by_spoken is not None else []

        exact_matches: list[SyntheticBeneficiary] = []
        partial_matches: list[SyntheticBeneficiary] = []
        for ben in self._items:
            full_lower = ben.full_name.lower()
            if q == full_lower or q in ben.aliases:
                exact_matches.append(ben)
            elif q in full_lower or any(q in a or a in q for a in ben.aliases):
                partial_matches.append(ben)
        return exact_matches or partial_matches

    def resolve_spoken_identity(
        self,
        utterance: str,
        *,
        exclude_beneficiary_id: str | None = None,
    ) -> tuple[list[SyntheticBeneficiary], str | None]:
        """Resolve a spoken identity utterance (e.g. 'Actually, it is Anitha Sharma' or 'BEN-1056').

        Returns `(matching_beneficiaries, extracted_id_if_any)`.
        Never guesses when multiple beneficiaries match a shared first name (e.g. 'Lakshmi').
        """
        raw = utterance.strip()
        if not raw:
            return [], None

        # 1. Check explicit spoken Beneficiary ID first
        spoken_id = extract_spoken_beneficiary_id(raw)
        if spoken_id is not None:
            found = self.get_by_id(spoken_id)
            if found is not None:
                if exclude_beneficiary_id and found.beneficiary_id == exclude_beneficiary_id:
                    return [], spoken_id
                return [found], spoken_id
            return [], spoken_id

        norm = unicodedata.normalize("NFC", raw).lower()
        # 2. Check exact full-name or multi-word alias match in utterance
        full_hits: list[tuple[int, SyntheticBeneficiary]] = []
        for ben in self._items:
            if exclude_beneficiary_id and ben.beneficiary_id == exclude_beneficiary_id:
                continue
            candidates_phrases = [ben.full_name.lower(), *(a.lower() for a in ben.aliases if " " in a)]
            for phrase in candidates_phrases:
                if re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", norm):
                    full_hits.append((len(phrase), ben))
                    break
        if full_hits:
            max_len = max(length for length, _ in full_hits)
            unique: list[SyntheticBeneficiary] = []
            seen: set[str] = set()
            for length, ben in full_hits:
                if length == max_len and ben.beneficiary_id not in seen:
                    seen.add(ben.beneficiary_id)
                    unique.append(ben)
            return unique, None

        # 3. Single-word name / alias match (strip conversational filler words)
        tokens = [
            t
            for t in re.findall(r"[A-Za-z0-9\u0900-\u097F\u0B80-\u0BFF\u0C80-\u0CFF]+", norm)
            if t not in _IDENTITY_STOPWORDS and len(t) >= 2
        ]
        if not tokens:
            return [], None

        matched_bens: list[SyntheticBeneficiary] = []
        seen_ids: set[str] = set()
        for ben in self._items:
            if exclude_beneficiary_id and ben.beneficiary_id == exclude_beneficiary_id:
                continue
            ben_tokens = {
                *(p.lower() for p in ben.full_name.split() if p.lower() not in {"baby", "of"}),
                *(a.lower() for a in ben.aliases if " " not in a),
            }
            if any(tok in ben_tokens for tok in tokens):
                if ben.beneficiary_id not in seen_ids:
                    seen_ids.add(ben.beneficiary_id)
                    matched_bens.append(ben)

        return matched_bens, None
