"""Healthcare abbreviation normalization & regional medical terminology helpers.

Expands spoken/spaced/ASR-split Indian public-health abbreviations (ANC, PNC,
HBNC, BP, Hb, SpO2, MUAC, KMC, EBF, ORS, IFA, RBS, EDD, LMP, LBW, VLBW, PHC,
CHC, FRU, etc.) and maps regional terminology across 10 Indic languages.
"""

from __future__ import annotations

import re

# Spaced or punctuated ASR variants -> canonical medical abbreviations
_ABBREVIATION_NORMALIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<!\w)a\.?\s*n\.?\s*c\.?(?!\w)", re.IGNORECASE), "ANC"),
    (re.compile(r"(?<!\w)p\.?\s*n\.?\s*c\.?(?!\w)", re.IGNORECASE), "PNC"),
    (re.compile(r"(?<!\w)h\.?\s*b\.?\s*n\.?\s*c\.?(?!\w)", re.IGNORECASE), "HBNC"),
    (re.compile(r"(?<!\w)b\.?\s*p\.?(?!\w)", re.IGNORECASE), "BP"),
    (re.compile(r"(?<!\w)h\.?\s*b\.?(?!\w)", re.IGNORECASE), "Hb"),
    (re.compile(r"(?<!\w)(?:sp\s*o\s*2|s\s*p\s*o\s*2|spo2|o2\s*sat(?:uration)?)(?!\w)", re.IGNORECASE), "SpO2"),
    (re.compile(r"(?<!\w)m\.?\s*u\.?\s*a\.?\s*c\.?(?!\w)", re.IGNORECASE), "MUAC"),
    (re.compile(r"(?<!\w)k\.?\s*m\.?\s*c\.?(?!\w)", re.IGNORECASE), "KMC"),
    (re.compile(r"(?<!\w)e\.?\s*b\.?\s*f\.?(?!\w)", re.IGNORECASE), "EBF"),
    (re.compile(r"(?<!\w)o\.?\s*r\.?\s*s\.?(?!\w)", re.IGNORECASE), "ORS"),
    (re.compile(r"(?<!\w)i\.?\s*f\.?\s*a\.?(?!\w)", re.IGNORECASE), "IFA"),
    (re.compile(r"(?<!\w)(?:r\.?\s*b\.?\s*s\.?|g\.?\s*r\.?\s*b\.?\s*s\.?|f\.?\s*b\.?\s*s\.?)(?!\w)", re.IGNORECASE), "RBS"),
    (re.compile(r"(?<!\w)p\.?\s*r\.?(?=\s+\d)", re.IGNORECASE), "PR"),
    (re.compile(r"(?<!\w)r\.?\s*r\.?(?=\s+\d)", re.IGNORECASE), "RR"),
    (re.compile(r"(?<!\w)e\.?\s*d\.?\s*d\.?(?!\w)", re.IGNORECASE), "EDD"),
    (re.compile(r"(?<!\w)l\.?\s*m\.?\s*p\.?(?!\w)", re.IGNORECASE), "LMP"),
    (re.compile(r"(?<!\w)v\.?\s*l\.?\s*b\.?\s*w\.?(?!\w)", re.IGNORECASE), "VLBW"),
    (re.compile(r"(?<!\w)l\.?\s*b\.?\s*w\.?(?!\w)", re.IGNORECASE), "LBW"),
    (re.compile(r"(?<!\w)p\.?\s*h\.?\s*c\.?(?!\w)", re.IGNORECASE), "PHC"),
    (re.compile(r"(?<!\w)c\.?\s*h\.?\s*c\.?(?!\w)", re.IGNORECASE), "CHC"),
    (re.compile(r"(?<!\w)f\.?\s*r\.?\s*u\.?(?!\w)", re.IGNORECASE), "FRU"),
    (re.compile(r"(?<!\w)h\.?\s*w\.?\s*c\.?(?!\w)", re.IGNORECASE), "HWC"),
    (re.compile(r"(?<!\w)a\.?\s*n\.?\s*m\.?(?!\w)", re.IGNORECASE), "ANM"),
    # Indic script transliterations of common abbreviations
    (re.compile(r"बी\.?\s*पी\.?"), "BP"),
    (re.compile(r"एच\.?\s*बी\.?"), "Hb"),
    (re.compile(r"ओ\.?\s*आर\.?\s*एस\.?"), "ORS"),
    (re.compile(r"आई\.?\s*एफ\.?\s*ए\.?"), "IFA"),
    (re.compile(r"के\.?\s*एम\.?\s*सी\.?"), "KMC"),
    (re.compile(r"पी\.?\s*एच\.?\s*सी\.?"), "PHC"),
    (re.compile(r"सी\.?\s*एच\.?\s*सी\.?"), "CHC"),
)


def normalize_healthcare_abbreviations(text: str) -> str:
    """Normalize spaced, punctuated, or Indic-script healthcare abbreviations."""
    if not text:
        return text
    out = text
    for pat, repl in _ABBREVIATION_NORMALIZATIONS:
        out = pat.sub(repl, out)
    return out
