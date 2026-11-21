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
    age_years: int = 25
    household_head: str | None = None
    phone_number: str | None = None
    edd_date: str | None = None
    high_risk_status: bool = False
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
    """Extract a canonical `BEN-XXXX` ID from spoken digits, Indic words, or ASR artifacts."""
    from app.extraction.numbers import resolve_beneficiary_id_mention

    selected_id, _src, _is_corr, _conflicts = resolve_beneficiary_id_mention(text)
    return selected_id


_RUNTIME_CUSTOM_BENEFICIARIES: list[SyntheticBeneficiary] = []


class SyntheticBeneficiaryDirectory:
    """Lookup interface resolving spoken names/IDs ONLY against synthetic fixtures."""

    def __init__(self, items: tuple[SyntheticBeneficiary, ...] = SYNTHETIC_BENEFICIARIES) -> None:
        self._base_items = items
        self._sync_index()

    def _sync_index(self) -> None:
        merged = list(self._base_items)
        seen = {b.beneficiary_id.upper() for b in merged}
        for custom in _RUNTIME_CUSTOM_BENEFICIARIES:
            if custom.beneficiary_id.upper() not in seen:
                merged.append(custom)
                seen.add(custom.beneficiary_id.upper())
        self._items = tuple(merged)
        self._by_id = {b.beneficiary_id.upper(): b for b in self._items}

    def list_all(self) -> list[SyntheticBeneficiary]:
        self._sync_index()
        return list(self._items)

    def get_by_id(self, beneficiary_id: str) -> SyntheticBeneficiary | None:
        self._sync_index()
        return self._by_id.get(beneficiary_id.strip().upper())

    def add_beneficiary(
        self,
        *,
        full_name: str,
        category: str = "pregnant_woman",
        village: str = "Rampur Demo Ward 1",
        preferred_language: str = "hi-IN",
        age_years: int = 25,
        household_head: str | None = None,
        phone_number: str | None = None,
        edd_date: str | None = None,
        high_risk_status: bool = False,
        beneficiary_id: str | None = None,
    ) -> SyntheticBeneficiary:
        """Register a new synthetic/demo beneficiary in the runtime directory."""
        self._sync_index()
        clean_name = " ".join(full_name.strip().split())
        if not clean_name:
            raise ValueError("full_name is required")

        if beneficiary_id and beneficiary_id.strip():
            bid = beneficiary_id.strip().upper()
        else:
            max_num = 1056
            for b in self._items:
                m = re.match(r"BEN-(\d+)$", b.beneficiary_id.upper())
                if m:
                    max_num = max(max_num, int(m.group(1)))
            bid = f"BEN-{max_num + 1}"

        name_lower = clean_name.lower()
        parts = [p for p in re.split(r"\s+", name_lower) if len(p) >= 2]
        aliases = tuple(dict.fromkeys([name_lower, *parts]))

        cat_map = {
            "PREGNANT_WOMAN": "pregnant_woman",
            "LACTATING_MOTHER": "postnatal_mother",
            "INFANT": "infant",
            "CHILD": "infant",
        }
        norm_cat = cat_map.get(category.strip().upper(), category.strip().lower() or "pregnant_woman")

        ben = SyntheticBeneficiary(
            beneficiary_id=bid,
            full_name=clean_name,
            aliases=aliases,
            category=norm_cat,
            village=village.strip() or "Rampur Demo Ward 1",
            preferred_language=preferred_language.strip() or "hi-IN",
            age_years=max(0, int(age_years)),
            household_head=household_head.strip() if household_head else None,
            phone_number=phone_number.strip() if phone_number else None,
            edd_date=edd_date.strip() if edd_date else None,
            high_risk_status=bool(high_risk_status),
            synthetic=True,
        )
        _RUNTIME_CUSTOM_BENEFICIARIES.append(ben)
        self._sync_index()
        return ben

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
