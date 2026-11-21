"""100% synthetic demonstration beneficiary directory.

GUARDRAIL: Never store real beneficiary names, phone numbers, addresses, or health
records. All entries below are entirely fictional demo personas for hackathon use.
"""

from __future__ import annotations

from dataclasses import dataclass


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
        aliases=("lakshmi", "laxmi", "लक्ष्मी", "ಲಕ್ಷ್ಮಿ", "லட்சுமி"),
        category="pregnant_woman",
        village="Rampur Demo Ward 1",
        preferred_language="hi-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1043",
        full_name="Kavitha Rao",
        aliases=("kavitha", "kavita", "कविता", "ಕವಿತಾ"),
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
        aliases=("sunita", "suneeta", "सुनीता"),
        category="pregnant_woman",
        village="Rampur Demo Ward 1",
        preferred_language="hi-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1046",
        full_name="Meena Selvam",
        aliases=("meena", "मीना", "மீனா"),
        category="infant",
        village="Kaveri Demo Ward 3",
        preferred_language="ta-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1047",
        full_name="Anita Devi",
        aliases=("anita", "aneeta", "अनीता"),
        category="pregnant_woman",
        village="Rampur Demo Ward 2",
        preferred_language="hi-IN",
    ),
    SyntheticBeneficiary(
        beneficiary_id="BEN-1048",
        full_name="Lakshmi Narayanan",
        aliases=("lakshmi narayanan", "lakshmi n"),
        category="postnatal_mother",
        village="Kaveri Demo Ward 3",
        preferred_language="ta-IN",
    ),
)


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

        exact_matches: list[SyntheticBeneficiary] = []
        partial_matches: list[SyntheticBeneficiary] = []
        for ben in self._items:
            full_lower = ben.full_name.lower()
            if q == full_lower or q in ben.aliases:
                exact_matches.append(ben)
            elif q in full_lower or any(q in a or a in q for a in ben.aliases):
                partial_matches.append(ben)
        return exact_matches or partial_matches

