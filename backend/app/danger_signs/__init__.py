"""Deterministic danger-sign detection package (Layer 1 safety engine)."""

from .catalog import CATALOG_BY_ID, DANGER_SIGN_CATALOG, get_catalog_entry
from .detector import detect_danger_signs, get_referral_message, llm_advisory_merge
from .models import DangerMatch, DangerSignEntry, DetectionResult
from .normalizer import normalize_for_exact, normalize_text, normalize_unicode_and_digits, split_clauses

__all__ = [
    "CATALOG_BY_ID",
    "DANGER_SIGN_CATALOG",
    "DangerMatch",
    "DangerSignEntry",
    "DetectionResult",
    "detect_danger_signs",
    "get_catalog_entry",
    "get_referral_message",
    "llm_advisory_merge",
    "normalize_for_exact",
    "normalize_text",
    "normalize_unicode_and_digits",
    "split_clauses",
]
