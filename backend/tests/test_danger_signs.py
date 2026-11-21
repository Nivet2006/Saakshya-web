"""Comprehensive deterministic unit tests for the Layer-1 danger-sign engine.

Verifies official guideline grounding, multilingual/code-mix/ASR normalization,
clinical thresholds, clause-level context suppression (negation, historical,
other-person), multi-clause mixed sentences, uncertainty handling, partial
transcripts, safe referral messages, and the Layer-2 non-suppression invariant.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.danger_signs import (  # noqa: E402
    CATALOG_BY_ID,
    DANGER_SIGN_CATALOG,
    DangerMatch,
    DetectionResult,
    detect_danger_signs,
    get_referral_message,
    llm_advisory_merge,
    normalize_text,
    normalize_unicode_and_digits,
    split_clauses,
)


# =============================================================================
# 1. Catalog Grounding & Schema Integrity
# =============================================================================

_OFFICIAL_DOC_CODES = (
    "MOD6",
    "MOD7",
    "HBNC-2014",
    "MCP-CARD",
    "MCP-GB",
    "INT-ASHA-2026",
    "DAKSHATA",
    "HBYC",
)


def test_catalog_every_entry_has_official_citation() -> None:
    assert len(DANGER_SIGN_CATALOG) >= 35
    categories = {e.category for e in DANGER_SIGN_CATALOG}
    assert categories == {"ANC", "Intranatal", "PNC", "Newborn"}

    for entry in DANGER_SIGN_CATALOG:
        assert entry.source_doc.strip(), f"{entry.canonical_id} missing source_doc"
        assert entry.source_section.strip(), f"{entry.canonical_id} missing source_section"
        assert any(code in entry.source_doc for code in _OFFICIAL_DOC_CODES), (
            f"{entry.canonical_id} source_doc not grounded in verified codes: {entry.source_doc}"
        )
        assert "p." in entry.source_section or "pp." in entry.source_section, (
            f"{entry.canonical_id} source_section missing page citation: {entry.source_section}"
        )


def test_required_canonical_ids_present() -> None:
    required_ids = {
        "ANC_VAGINAL_BLEEDING",
        "ANC_CONVULSIONS",
        "ANC_SEVERE_HEADACHE_BLURRED_VISION",
        "ANC_SWELLING_FACE_HANDS",
        "ANC_HIGH_BP",
        "ANC_REDUCED_FETAL_MOVEMENT",
        "ANC_SEVERE_ABDOMINAL_PAIN",
        "ANC_HIGH_FEVER",
        "ANC_BREATHLESSNESS",
        "ANC_PROM",
        "PNC_EXCESSIVE_BLEEDING",
        "PNC_PUERPERAL_SEPSIS",
        "NB_UNABLE_TO_FEED",
        "NB_FAST_BREATHING",
        "NB_SEVERE_CHEST_INDRAWING",
        "NB_LETHARGY_UNCONSCIOUS",
        "NB_FEVER",
        "NB_HYPOTHERMIA",
        "NB_UMBILICAL_INFECTION",
        "NB_SEVERE_JAUNDICE",
        "NB_SEVERE_SKIN_PUSTULES",
        "NB_BLEEDING",
        "NB_VERY_LOW_BIRTH_WEIGHT",
        "NB_BIRTH_ASPHYXIA",
        "NB_WEAK_OR_NO_CRY",
    }
    missing = required_ids - set(CATALOG_BY_ID.keys())
    assert not missing, f"Missing required canonical IDs: {missing}"


# =============================================================================
# 2. Normalizer Tests (Unicode, Indic Digits, Number Words, ASR Typos, Clauses)
# =============================================================================

def test_indic_numeral_normalization() -> None:
    assert normalize_unicode_and_digits("बीपी १५०/१००") == "बीपी 150/100"
    assert normalize_unicode_and_digits("ತೂಕ ೧.೬ kg") == "ತೂಕ 1.6 kg"
    assert normalize_unicode_and_digits("காய்ச்சல் ௧௦௨ F") == "காய்ச்சல் 102 F"


def test_asr_spelling_and_number_word_normalization() -> None:
    norm = normalize_text("koon bukar phits jhatke sans soojan nal dudh")
    assert "khoon" in norm
    assert "bukhar" in norm
    assert "fits" in norm
    assert "jhatke" in norm
    assert "saans" in norm
    assert "sujan" in norm
    assert "naal" in norm
    assert "doodh" in norm

    assert "150/95" in normalize_text("BP is one hundred fifty over ninety five")
    assert "65 breaths" in normalize_text("sixty five breaths per minute")
    assert "1.6 kg" in normalize_text("birth weight one point six kilo")
    assert "6 pads" in normalize_text("changing six pads a day")


def test_clause_splitting_preserves_decimals_and_splits_contrasts() -> None:
    clauses = split_clauses("No bleeding, but newborn is unable to feed. Weight is 2.8 kg.")
    assert len(clauses) == 3
    assert "No bleeding" in clauses[0]
    assert "newborn is unable to feed" in clauses[1]
    assert "2.8 kg" in clauses[2]

    list_clauses = split_clauses("Swelling of face, hands, and feet")
    assert len(list_clauses) == 1


# =============================================================================
# 3. Canonical Danger Signs & Quantitative Thresholds Across All 4 Phases
# =============================================================================

@pytest.mark.parametrize(
    ("text", "context", "expected_id"),
    [
        # ANC
        ("Mother has vaginal bleeding since morning", {"visit_type": "ANC"}, "ANC_VAGINAL_BLEEDING"),
        ("Pregnant woman had fits and convulsions", {"visit_type": "ANC"}, "ANC_CONVULSIONS"),
        ("Severe headache and blurred vision", {"visit_type": "ANC"}, "ANC_SEVERE_HEADACHE_BLURRED_VISION"),
        ("Swelling of face and hands observed", {"visit_type": "ANC"}, "ANC_SWELLING_FACE_HANDS"),
        ("Blood pressure is 140/90 mmHg", {"visit_type": "ANC"}, "ANC_HIGH_BP"),
        ("BP is 150 by 100", {"visit_type": "ANC"}, "ANC_HIGH_BP"),
        ("BP is १५०/९५", {"visit_type": "ANC"}, "ANC_HIGH_BP"),
        ("Reduced fetal movement since yesterday", {"visit_type": "ANC"}, "ANC_REDUCED_FETAL_MOVEMENT"),
        ("Severe abdominal pain continuously", {"visit_type": "ANC"}, "ANC_SEVERE_ABDOMINAL_PAIN"),
        ("High fever 101.5 F during pregnancy", {"visit_type": "ANC"}, "ANC_HIGH_FEVER"),
        ("Hb is 6.2 g/dl and severe anaemia", {"visit_type": "ANC"}, "ANC_SEVERE_ANAEMIA"),
        ("Mother has difficulty breathing and breathlessness", {"visit_type": "ANC"}, "ANC_BREATHLESSNESS"),
        ("Water bag burst without labour pains", {"visit_type": "ANC"}, "ANC_PROM"),
        ("Preterm labour pains at 32 weeks", {"visit_type": "ANC"}, "ANC_PRETERM_LABOUR"),
        # Intranatal
        ("Fresh bleeding during labour", {"visit_type": "Intranatal"}, "INTRA_EXCESSIVE_BLEEDING"),
        ("Labour pain for 14 hours without delivery", {"visit_type": "Intranatal"}, "INTRA_PROLONGED_LABOUR"),
        ("Amniotic fluid is green and meconium stained", {"visit_type": "Intranatal"}, "INTRA_MECONIUM_LIQUOR"),
        ("Cord prolapse seen during labour", {"visit_type": "Intranatal"}, "INTRA_MALPRESENTATION_PROLAPSE"),
        ("Placenta not delivered after birth", {"visit_type": "Intranatal"}, "INTRA_RETAINED_PLACENTA"),
        # PNC
        ("Mother changing 6 pads a day after delivery", {"visit_type": "PNC"}, "PNC_EXCESSIVE_BLEEDING"),
        ("Soaking more than 5 pads per day", {"visit_type": "PNC"}, "PNC_EXCESSIVE_BLEEDING"),
        ("Postpartum soaking 3 pads in 20 minutes", {"visit_type": "PNC"}, "PNC_EXCESSIVE_BLEEDING"),
        ("Foul-smelling lochia and fever 101 F", {"visit_type": "PNC"}, "PNC_PUERPERAL_SEPSIS"),
        ("Postpartum temperature is 102.8 F", {"visit_type": "PNC"}, "PNC_HIGH_FEVER"),
        ("Mother speaking abnormally after delivery", {"visit_type": "PNC"}, "PNC_CONVULSIONS_ABNORMAL_SPEECH"),
        ("Pus from stitches on perineal cut", {"visit_type": "PNC"}, "PNC_PERINEAL_WOUND_INFECTION"),
        # Newborn / HBNC
        ("Baby did not cry at birth and is gasping", {"visit_type": "Newborn"}, "NB_BIRTH_ASPHYXIA"),
        ("Newborn unable to feed or suck", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("Baby breathing rate is 64 breaths per minute", {"visit_type": "Newborn"}, "NB_FAST_BREATHING"),
        ("Respiratory rate 60 per min", {"visit_type": "Newborn"}, "NB_FAST_BREATHING"),
        ("Severe chest indrawing seen", {"visit_type": "Newborn"}, "NB_SEVERE_CHEST_INDRAWING"),
        ("Newborn is lethargic and all limbs limp", {"visit_type": "Newborn"}, "NB_LETHARGY_UNCONSCIOUS"),
        ("Baby cry is weak", {"visit_type": "Newborn"}, "NB_WEAK_OR_NO_CRY"),
        ("Baby having fits and convulsions", {"visit_type": "Newborn"}, "NB_CONVULSIONS"),
        ("Newborn temperature is 99.6 F", {"visit_type": "Newborn"}, "NB_FEVER"),
        ("Baby temperature is 37.8 C", {"visit_type": "Newborn"}, "NB_FEVER"),
        ("Newborn temperature is 95.2 F", {"visit_type": "Newborn"}, "NB_HYPOTHERMIA"),
        ("Baby temperature 35.0 C and cold to touch", {"visit_type": "Newborn"}, "NB_HYPOTHERMIA"),
        ("Pus on umbilicus and umbilical redness", {"visit_type": "Newborn"}, "NB_UMBILICAL_INFECTION"),
        ("Yellow palms and soles on newborn", {"visit_type": "Newborn"}, "NB_SEVERE_JAUNDICE"),
        ("Jaundice on day 1 within 24 hours", {"visit_type": "Newborn"}, "NB_SEVERE_JAUNDICE"),
        ("Baby has 12 pustules on body", {"visit_type": "Newborn"}, "NB_SEVERE_SKIN_PUSTULES"),
        ("One large boil on newborn skin", {"visit_type": "Newborn"}, "NB_SEVERE_SKIN_PUSTULES"),
        ("Blood in stools of newborn", {"visit_type": "Newborn"}, "NB_BLEEDING"),
        ("Umbilical cord bleeding in baby", {"visit_type": "Newborn"}, "NB_BLEEDING"),
        ("Baby birth weight is 1.6 kg", {"visit_type": "Newborn"}, "NB_VERY_LOW_BIRTH_WEIGHT"),
        ("Newborn weight is 1500 g", {"visit_type": "Newborn"}, "NB_VERY_LOW_BIRTH_WEIGHT"),
        ("Baby turning blue with central cyanosis", {"visit_type": "Newborn"}, "NB_CYANOSIS_DIARRHOEA_NO_URINE"),
    ],
)
def test_canonical_danger_sign_detection(text: str, context: dict, expected_id: str) -> None:
    res = detect_danger_signs(text, language="en-IN", context=context)
    assert res.danger_sign_flagged is True, f"Expected flag for: {text!r}"
    assert res.escalation_required is True
    assert res.referral_message is not None
    matched_ids = {m.canonical_id for m in res.matches}
    assert expected_id in matched_ids, f"Expected {expected_id} in {matched_ids} for: {text!r}"


# =============================================================================
# 4. Multilingual (Hindi, Hinglish, Kannada, Tamil) & ASR Noise / Fuzzy Matching
# =============================================================================

@pytest.mark.parametrize(
    ("text", "lang", "context", "expected_id"),
    [
        # Hindi Devanagari
        ("महिला को योनि से खून आ रहा है", "hi-IN", {"visit_type": "ANC"}, "ANC_VAGINAL_BLEEDING"),
        ("बच्चा दूध नहीं पी रहा है", "hi-IN", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("बच्चे की पसलियां चल रही हैं", "hi-IN", {"visit_type": "Newborn"}, "NB_SEVERE_CHEST_INDRAWING"),
        ("नाभि में मवाद है", "hi-IN", {"visit_type": "Newborn"}, "NB_UMBILICAL_INFECTION"),
        ("बच्चे की हथेली और तलवे पीले हैं", "hi-IN", {"visit_type": "Newborn"}, "NB_SEVERE_JAUNDICE"),
        ("बच्चा ठंडा पड़ गया है", "hi-IN", {"visit_type": "Newborn"}, "NB_HYPOTHERMIA"),
        # Hinglish + ASR typos
        ("Mother ko koon beh raha hai", "hi-IN", {"visit_type": "ANC"}, "ANC_VAGINAL_BLEEDING"),
        ("Patient ko phits aur jhatke aa rahe hain", "hi-IN", {"visit_type": "ANC"}, "ANC_CONVULSIONS"),
        ("Chehre par soojan hai aur dhundla dikhai de raha", "hi-IN", {"visit_type": "ANC"}, "ANC_SWELLING_FACE_HANDS"),
        ("Baccha dudh nahi pee raha hai", "hi-IN", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("Bacche ki nal mein puss aur laal hai", "hi-IN", {"visit_type": "Newborn"}, "NB_UMBILICAL_INFECTION"),
        ("Bacche ki sans bahut tez chal rahi hai", "hi-IN", {"visit_type": "Newborn"}, "NB_FAST_BREATHING"),
        ("Mother ko bahut tez bukar hai", "hi-IN", {"visit_type": "ANC"}, "ANC_HIGH_FEVER"),
        # Kannada (script & transliteration)
        ("ತಾಯಿಗೆ ಯೋನಿ ರಕ್ತಸ್ರಾವ ಆಗುತ್ತಿದೆ", "kn-IN", {"visit_type": "ANC"}, "ANC_VAGINAL_BLEEDING"),
        ("ಮಗು ಹಾಲು ಕುಡಿಯುತ್ತಿಲ್ಲ", "kn-IN", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("ಹೊಕ್ಕುಳಲ್ಲಿ ಕೀವು ಇದೆ", "kn-IN", {"visit_type": "Newborn"}, "NB_UMBILICAL_INFECTION"),
        ("ಮಗು ತಣ್ಣಗಿದೆ", "kn-IN", {"visit_type": "Newborn"}, "NB_HYPOTHERMIA"),
        ("Magu haalu kudiyuttilla", "kn-IN", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("Angai angaalu haladi", "kn-IN", {"visit_type": "Newborn"}, "NB_SEVERE_JAUNDICE"),
        # Tamil (script & transliteration)
        ("பிறப்புறுப்பு ரத்தப்போக்கு உள்ளது", "ta-IN", {"visit_type": "ANC"}, "ANC_VAGINAL_BLEEDING"),
        ("குழந்தை பால் குடிக்கவில்லை", "ta-IN", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("மார்பு உள்ளிழுத்தல் உள்ளது", "ta-IN", {"visit_type": "Newborn"}, "NB_SEVERE_CHEST_INDRAWING"),
        ("தொப்புளில் சீழ் உள்ளது", "ta-IN", {"visit_type": "Newborn"}, "NB_UMBILICAL_INFECTION"),
        ("Kuzhandhai paal kudikkavillai", "ta-IN", {"visit_type": "Newborn"}, "NB_UNABLE_TO_FEED"),
        ("Ullangai ullangaal manjal", "ta-IN", {"visit_type": "Newborn"}, "NB_SEVERE_JAUNDICE"),
        # Fuzzy ASR noise
        ("Mother is having convulshuns right now", "en-IN", {"visit_type": "ANC"}, "ANC_CONVULSIONS"),
        ("Newborn has severe chest indrawng", "en-IN", {"visit_type": "Newborn"}, "NB_SEVERE_CHEST_INDRAWING"),
        ("Baby has umbilcal infction", "en-IN", {"visit_type": "Newborn"}, "NB_UMBILICAL_INFECTION"),
    ],
)
def test_multilingual_codemix_and_asr_noise(text: str, lang: str, context: dict, expected_id: str) -> None:
    res = detect_danger_signs(text, language=lang, context=context)
    assert res.danger_sign_flagged is True, f"Expected flag for: {text!r}"
    assert res.active_language == lang
    assert res.referral_message == get_referral_message(lang)
    assert expected_id in {m.canonical_id for m in res.matches}


# =============================================================================
# 5. Context Suppression: Negation, Historical/Resolved, Other-Person Subject
# =============================================================================

@pytest.mark.parametrize(
    ("text", "expected_reason"),
    [
        ("No vaginal bleeding", "negation"),
        ("Bleeding is absent", "negation"),
        ("Patient denies fits or convulsions", "negation"),
        ("Bleeding nahi hai", "negation"),
        ("Koi bukhar nahi hai", "negation"),
        ("कोई रक्तस्राव नहीं है", "negation"),
        ("Raktasrava illa", "negation"),
        ("Raththam varudhu illai", "negation"),
        ("வலிப்பு இல்லை", "negation"),
        ("Last month she had swelling of face", "historical"),
        ("Pichle mahine vaginal bleeding hui thi", "historical"),
        ("Two weeks ago she had high fever, earlier resolved", "historical"),
        ("Pehle tez bukhar tha ab theek hai", "historical"),
        ("In previous pregnancy she had convulsions", "historical"),
        ("Neighbour had fits yesterday", "other_person"),
        ("Padosi ko bahut bleeding hui", "other_person"),
        ("Her sister had high BP 150/100", "other_person"),
        ("Behen ko severe headache tha", "other_person"),
        ("Friend had postpartum bleeding", "other_person"),
        ("Someone else in the village had convulsions", "other_person"),
    ],
)
def test_context_suppression_does_not_flag(text: str, expected_reason: str) -> None:
    res = detect_danger_signs(text, language="hi-IN")
    assert res.danger_sign_flagged is False, f"Unexpected flag for suppressed context: {text!r} -> {res.matches}"
    assert res.escalation_required is False
    assert res.referral_message is None
    reasons = {s["reason"] for s in res.suppressed_context_matches}
    assert expected_reason in reasons, f"Expected reason {expected_reason!r} in {res.suppressed_context_matches}"


# =============================================================================
# 6. Multi-Clause Mixed Sentences (CRITICAL Safety Behavior)
# =============================================================================

def test_multiclause_no_bleeding_but_newborn_unable_to_feed() -> None:
    res = detect_danger_signs("No bleeding, but newborn is unable to feed", language="en-IN")
    assert res.danger_sign_flagged is True
    assert res.escalation_required is True
    assert "NB_UNABLE_TO_FEED" in {m.canonical_id for m in res.matches}
    assert "ANC_VAGINAL_BLEEDING" not in {m.canonical_id for m in res.matches}
    assert any(
        s["canonical_id"] == "ANC_VAGINAL_BLEEDING" and s["reason"] == "negation"
        for s in res.suppressed_context_matches
    )


def test_multiclause_hinglish_negation_plus_positive() -> None:
    res = detect_danger_signs("Bleeding nahi hai lekin bacche ko tez saans chal rahi hai", language="hi-IN")
    assert res.danger_sign_flagged is True
    assert "NB_FAST_BREATHING" in {m.canonical_id for m in res.matches}
    assert "ANC_VAGINAL_BLEEDING" not in {m.canonical_id for m in res.matches}
    assert any(s["reason"] == "negation" for s in res.suppressed_context_matches)


def test_multiclause_historical_plus_current_positive() -> None:
    res = detect_danger_signs(
        "Last month she had swelling of face, now severe headache and blurred vision",
        language="en-IN",
    )
    assert res.danger_sign_flagged is True
    matched_ids = {m.canonical_id for m in res.matches}
    assert "ANC_SEVERE_HEADACHE_BLURRED_VISION" in matched_ids
    assert "ANC_SWELLING_FACE_HANDS" not in matched_ids
    assert any(
        s["canonical_id"] == "ANC_SWELLING_FACE_HANDS" and s["reason"] == "historical"
        for s in res.suppressed_context_matches
    )


def test_multiclause_other_person_plus_active_beneficiary_positive() -> None:
    res = detect_danger_signs("Neighbour had fits, but mother has high BP 150/100", language="en-IN")
    assert res.danger_sign_flagged is True
    matched_ids = {m.canonical_id for m in res.matches}
    assert "ANC_HIGH_BP" in matched_ids
    assert "ANC_CONVULSIONS" not in matched_ids
    assert any(
        s["canonical_id"] == "ANC_CONVULSIONS" and s["reason"] == "other_person"
        for s in res.suppressed_context_matches
    )


def test_multiclause_kannada_negation_plus_newborn_feeding() -> None:
    res = detect_danger_signs("Raktasrava illa, aadre magu haalu kudiyuttilla", language="kn-IN")
    assert res.danger_sign_flagged is True
    assert "NB_UNABLE_TO_FEED" in {m.canonical_id for m in res.matches}
    assert "ANC_VAGINAL_BLEEDING" not in {m.canonical_id for m in res.matches}


def test_multiclause_multiple_negations_plus_hypothermia() -> None:
    res = detect_danger_signs("No fever, no fits; baby is cold to touch", language="en-IN")
    assert res.danger_sign_flagged is True
    matched_ids = {m.canonical_id for m in res.matches}
    assert "NB_HYPOTHERMIA" in matched_ids
    assert "ANC_CONVULSIONS" not in matched_ids
    assert "ANC_HIGH_FEVER" not in matched_ids


# =============================================================================
# 7. Conservative Uncertainty Handling vs Catastrophic Signs
# =============================================================================

@pytest.mark.parametrize(
    "text",
    [
        "thoda headache hai",
        "mild fever maybe",
        "lagta hai kuch swelling hai",
        "slight abdominal pain",
        "baby temperature is 96.4 F",
    ],
)
def test_ambiguous_or_mild_expressions_go_to_uncertain_matches(text: str) -> None:
    ctx = {"visit_type": "Newborn"} if "baby" in text else {"visit_type": "ANC"}
    res = detect_danger_signs(text, language="hi-IN", context=ctx)
    assert res.danger_sign_flagged is False
    assert len(res.uncertain_matches) >= 1
    assert all(m.requires_clarification is True for m in res.uncertain_matches)


def test_mild_vaginal_bleeding_in_pregnancy_still_flagged_immediately() -> None:
    # MOD6 p. 30: ANY amount of vaginal bleeding in pregnancy requires immediate referral
    res = detect_danger_signs("thoda vaginal bleeding ho raha hai", language="hi-IN", context={"visit_type": "ANC"})
    assert res.danger_sign_flagged is True
    assert "ANC_VAGINAL_BLEEDING" in {m.canonical_id for m in res.matches}


# =============================================================================
# 8. Routine Normal Visits (No False Positives)
# =============================================================================

@pytest.mark.parametrize(
    ("text", "context"),
    [
        ("Sunita Devi ANC visit, BP 118/76, weight 54 kg, Hb 11.2, next visit next Tuesday.", {"visit_type": "ANC"}),
        ("No, weight is 2.8 kilo, baby is feeding well, temperature 98.4 F, respiratory rate 44 per min.", {"visit_type": "Newborn"}),
        ("Newborn weight is 2.2 kg, feeding well and warm to touch.", {"visit_type": "Newborn"}),
        ("Mother changing 3 pads a day after delivery, feeling well.", {"visit_type": "PNC"}),
        ("Immunisation visit done, BCG and OPV given, no complaints.", {"visit_type": "Immunisation"}),
        ("Labour started 4 hours ago, mother is stable.", {"visit_type": "Intranatal"}),
        ("", None),
    ],
)
def test_normal_routine_records_do_not_false_positive(text: str, context: dict | None) -> None:
    res = detect_danger_signs(text, language="en-IN", context=context)
    assert res.danger_sign_flagged is False, f"False positive on routine record: {text!r} -> {res.matches}"
    assert res.escalation_required is False
    assert res.matches == []


# =============================================================================
# 9. Partial Transcript Handling
# =============================================================================

def test_partial_transcript_flags_immediately_and_sets_is_partial() -> None:
    res = detect_danger_signs(
        "mother has heavy vaginal bleeding",
        language="hi-IN",
        context={"is_partial": True, "visit_type": "ANC"},
    )
    assert res.is_partial is True
    assert res.danger_sign_flagged is True
    assert res.escalation_required is True
    assert res.referral_message == get_referral_message("hi-IN")
    assert "ANC_VAGINAL_BLEEDING" in {m.canonical_id for m in res.matches}


# =============================================================================
# 10. Referral Messages Safety Checks
# =============================================================================

@pytest.mark.parametrize("lang", ["hi-IN", "en-IN", "kn-IN", "ta-IN", "hinglish", "unknown-XX"])
def test_referral_messages_safe_and_non_empty(lang: str) -> None:
    msg = get_referral_message(lang)
    assert isinstance(msg, str) and len(msg) > 20
    lower = msg.lower()
    # Must NEVER prescribe medicine, recommend home remedies, or invent phone numbers
    forbidden_terms = (
        "paracetamol",
        "amoxicillin",
        "antibiotic",
        "medicine",
        "tablet",
        "syrup",
        "home remedy",
        "108",
        "102",
        "diagnos",
    )
    for term in forbidden_terms:
        assert term not in lower, f"Forbidden term {term!r} found in referral message for {lang}"
    # Must not contain invented phone numbers
    assert not re.search(r"\d{3,}", msg), f"Unexpected numeric string/phone number in referral message: {msg}"


# =============================================================================
# 11. Layer-2 Advisory Merge Non-Suppression Invariant
# =============================================================================

def test_llm_advisory_merge_never_suppresses_layer1_positive() -> None:
    layer1 = detect_danger_signs("Mother has vaginal bleeding and BP 150/95", language="hi-IN")
    assert layer1.danger_sign_flagged is True
    orig_ids = {m.canonical_id for m in layer1.matches}
    assert {"ANC_VAGINAL_BLEEDING", "ANC_HIGH_BP"}.issubset(orig_ids)

    # Even if LLM says empty flags and no clarification needed, Layer 1 MUST remain intact
    merged = llm_advisory_merge(layer1, llm_flags=[], llm_clarification_needed=False)
    assert merged.danger_sign_flagged is True
    assert merged.escalation_required is True
    assert merged.referral_message == layer1.referral_message
    assert {m.canonical_id for m in merged.matches} == orig_ids

    # Passing None also preserves everything
    merged_none = llm_advisory_merge(layer1, llm_flags=None, llm_clarification_needed=False)
    assert merged_none.danger_sign_flagged is True
    assert {m.canonical_id for m in merged_none.matches} == orig_ids


def test_llm_advisory_merge_adds_verified_uncertain_and_ignores_hallucinated_ids() -> None:
    layer1 = detect_danger_signs("Mother says she is feeling very uneasy today", language="en-IN")
    assert layer1.danger_sign_flagged is False
    assert layer1.matches == []

    merged = llm_advisory_merge(
        layer1,
        llm_flags=["ANC_HIGH_BP", "INVENTED_NONEXISTENT_SIGN"],
        llm_clarification_needed=True,
    )
    # LLM cannot act as sole deterministic confirmer; verified catalog flag goes to uncertain_matches
    assert merged.danger_sign_flagged is False
    assert merged.matches == []
    uncertain_ids = {m.canonical_id for m in merged.uncertain_matches}
    assert "ANC_HIGH_BP" in uncertain_ids
    assert "INVENTED_NONEXISTENT_SIGN" not in uncertain_ids
    assert all(m.requires_clarification is True for m in merged.uncertain_matches)
    # Verify Pydantic serialization round-trip
    dumped = merged.model_dump()
    assert DetectionResult.model_validate(dumped) == merged
    for m in merged.uncertain_matches:
        assert isinstance(m, DangerMatch)
