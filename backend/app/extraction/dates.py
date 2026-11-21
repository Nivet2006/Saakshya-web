"""Specialized multilingual date parser for ASHA home-visit scheduling.

Supports:
- ISO-8601 (`2026-11-28`), `DD/MM/YYYY`, `DD-MM-YYYY`, `DD.MM.YYYY`
- Spoken day + month and month + day in English, Hindi/Devanagari, Kannada, and Tamil
- Ordinal days (`1st`..`31st`, `first`..`thirty first`, Hindi/Kannada/Tamil day numbers)
- Relative offsets (`tomorrow`/`kal`/`ನಾಳೆ`/`நாளை`, `day after tomorrow`/`parso`,
  `next week`, `after N days/weeks`, weekday names in EN/HI/KN/TA)
- Repeated date corrections & conflicting date detection within an utterance
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta

from app.extraction.numbers import (
    CONFLICT_BRIDGE_RE,
    CORRECTION_BRIDGE_RE,
    EN_ORDINALS,
    EN_TENS,
    EN_UNITS,
    INDIC_NUMBERS,
    LB,
    RB,
    parse_int_tokens,
)

MONTH_NAMES: dict[str, int] = {
    # English
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
    # Hindi / Devanagari
    "जनवरी": 1,
    "फरवरी": 2,
    "मार्च": 3,
    "अप्रैल": 4,
    "मई": 5,
    "जून": 6,
    "जुलाई": 7,
    "अगस्त": 8,
    "सितंबर": 9,
    "सितम्बर": 9,
    "अक्टूबर": 10,
    "अक्तूबर": 10,
    "नवंबर": 11,
    "नवम्बर": 11,
    "दिसंबर": 12,
    "दिसम्बर": 12,
    # Kannada
    "ಜನವರಿ": 1,
    "ಫೆಬ್ರವರಿ": 2,
    "ಮಾರ್ಚ್": 3,
    "ಏಪ್ರಿಲ್": 4,
    "ಮೇ": 5,
    "ಜೂನ್": 6,
    "ಜುಲೈ": 7,
    "ಆಗಸ್ಟ್": 8,
    "ಸೆಪ್ಟೆಂಬರ್": 9,
    "ಅಕ್ಟೋಬರ್": 10,
    "ನವೆಂಬರ್": 11,
    "ಡಿಸೆಂಬರ್": 12,
    # Tamil
    "ஜனவரி": 1,
    "பிப்ரவரி": 2,
    "மார்ச்": 3,
    "ஏப்ரல்": 4,
    "மே": 5,
    "ஜூன்": 6,
    "ஜூலை": 7,
    "ஆகஸ்ட்": 8,
    "செப்டம்பர்": 9,
    "அக்டோபர்": 10,
    "நவம்பர்": 11,
    "டிசம்பர்": 12,
}

WEEKDAY_FULL_NAMES: dict[str, int] = {
    "monday": 0,
    "somwar": 0,
    "somvar": 0,
    "सोमवार": 0,
    "ಸೋಮವಾರ": 0,
    "திங்கட்கிழமை": 0,
    "திங்கள்": 0,
    "tuesday": 1,
    "mangalwar": 1,
    "mangalvar": 1,
    "मंगलवार": 1,
    "ಮಂಗಳವಾರ": 1,
    "செவ்வாய்க்கிழமை": 1,
    "wednesday": 2,
    "budhwar": 2,
    "budhvar": 2,
    "बुधवार": 2,
    "ಬುಧವಾರ": 2,
    "புதன்கிழமை": 2,
    "thursday": 3,
    "guruwar": 3,
    "guruvar": 3,
    "brihaspatiwar": 3,
    "गुरुवार": 3,
    "बृहस्पतिवार": 3,
    "ಗುರುವಾರ": 3,
    "வியாழக்கிழமை": 3,
    "friday": 4,
    "shukrawar": 4,
    "shukravar": 4,
    "शुक्रवार": 4,
    "ಶುಕ್ರವಾರ": 4,
    "வெள்ளிக்கிழமை": 4,
    "saturday": 5,
    "shaniwar": 5,
    "shanivar": 5,
    "शनिवार": 5,
    "ಶನಿವಾರ": 5,
    "சனிக்கிழமை": 5,
    "sunday": 6,
    "rabiwar": 6,
    "raviwar": 6,
    "ravivar": 6,
    "रविवार": 6,
    "ಭಾನುವಾರ": 6,
    "ஞாயிற்றுக்கிழமை": 6,
}

WEEKDAY_ABBR_NAMES: dict[str, int] = {
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

WEEKDAY_NAMES: dict[str, int] = {**WEEKDAY_FULL_NAMES, **WEEKDAY_ABBR_NAMES}

_MONTH_RE = "(?:" + "|".join(re.escape(m) for m in sorted(MONTH_NAMES, key=len, reverse=True)) + ")"
_WEEKDAY_FULL_RE = "(?:" + "|".join(re.escape(w) for w in sorted(WEEKDAY_FULL_NAMES, key=len, reverse=True)) + ")"
_WEEKDAY_ABBR_RE = "(?:" + "|".join(re.escape(w) for w in sorted(WEEKDAY_ABBR_NAMES, key=len, reverse=True)) + ")"

_DAY_WORD_TOKENS = (
    frozenset(EN_UNITS)
    | frozenset(EN_TENS)
    | frozenset(EN_ORDINALS)
    | frozenset(k for k, v in INDIC_NUMBERS.items() if 1 <= v <= 31)
)
_DAY_WORD_RE = "(?:" + "|".join(re.escape(w) for w in sorted(_DAY_WORD_TOKENS, key=len, reverse=True)) + ")"
_DAY_EXPR_RE = rf"(?:\d{{1,2}}(?:st|nd|rd|th)?|{_DAY_WORD_RE}(?:[\s\-]+{_DAY_WORD_RE})?)"

_ISO_DATE_RE = re.compile(rf"{LB}(?P<y>\d{{4}})-(?P<m>\d{{1,2}})-(?P<d>\d{{1,2}}){RB}")
_DMY_DATE_RE = re.compile(
    rf"{LB}(?P<d>\d{{1,2}})[/\-\.](?P<m>\d{{1,2}})[/\-\.](?P<y>\d{{2,4}}){RB}"
)
_DAY_MONTH_RE = re.compile(
    rf"{LB}(?P<day>{_DAY_EXPR_RE})(?:\s+of)?\s+(?P<month>{_MONTH_RE})(?:,?\s+(?P<year>\d{{4}}))?{RB}",
    re.IGNORECASE,
)
_MONTH_DAY_RE = re.compile(
    rf"{LB}(?P<month>{_MONTH_RE})\s+(?P<day>{_DAY_EXPR_RE})(?:,?\s+(?P<year>\d{{4}}))?{RB}",
    re.IGNORECASE,
)

_COUNT_TOKEN_RE = (
    r"(?:\d+|"
    + "|".join(
        re.escape(w)
        for w in sorted(
            frozenset(EN_UNITS)
            | frozenset(EN_TENS)
            | frozenset(INDIC_NUMBERS)
            | frozenset({"a", "an"}),
            key=len,
            reverse=True,
        )
    )
    + r")"
)
_COUNT_EXPR_RE = rf"(?:{_COUNT_TOKEN_RE}(?:[\s\-]+{_COUNT_TOKEN_RE})?)"

_AFTER_DAYS_RE = re.compile(
    rf"(?:{LB}(?:after|in)\s+(?P<n1>{_COUNT_EXPR_RE})\s+(?:days?|din){RB}|"
    rf"{LB}(?P<n2>{_COUNT_EXPR_RE})\s+(?:(?:days?|din)\s+(?:later|from\s+now|baad|bad|mein|me)|दिन\s+(?:बाद|में)|ದಿನದ\s+ನಂತರ|ದಿನಗಳ\s+ನಂತರ|நாட்கள்\s+கழித்து){RB})",
    re.IGNORECASE,
)
_AFTER_WEEKS_RE = re.compile(
    rf"(?:{LB}(?:after|in)\s+(?P<n1>{_COUNT_EXPR_RE})\s+(?:weeks?|hafte|hafta|saptah){RB}|"
    rf"{LB}(?P<n2>{_COUNT_EXPR_RE})\s+(?:weeks?\s+(?:later|from\s+now)|hafte\s+(?:baad|bad)|saptah\s+(?:baad|bad)|हफ्ते\s+बाद|सप्ताह\s+बाद|ವಾರಗಳ\s+ನಂತರ|வாரங்கள்\s+கழித்து){RB})",
    re.IGNORECASE,
)
_NEXT_WEEK_RE = re.compile(
    rf"{LB}(?:next\s+week|agle\s+hafte|agla\s+hafta|agle\s+saptah|अगले\s+हफ्ते|अगले\s+सप्ताह|ಮುಂದಿನ\s+ವಾರ|அடுத்த\s+வாரம்){RB}",
    re.IGNORECASE,
)
_WEEKDAY_NEXT_RE = re.compile(
    rf"(?:{LB}(?:(?:next|coming|on|agle|agla|अगले|ಮುಂದಿನ|அடுத்த)\s+)?(?P<wd1>{_WEEKDAY_FULL_RE})(?:\s+(?:ko|को))?{RB}|"
    rf"{LB}(?:next|coming|on|agle|agla)\s+(?P<wd2>{_WEEKDAY_ABBR_RE}){RB})",
    re.IGNORECASE,
)
_TOMORROW_RE = re.compile(rf"{LB}(?:tomorrow|kal|कल|ನಾಳೆ|நாளை){RB}", re.IGNORECASE)
_DAY_AFTER_TOMORROW_RE = re.compile(
    rf"{LB}(?:day\s+after\s+tomorrow|parso|parson|परसों|परसो|ನಾಡಿದ್ದು|நாளை\s+மறுநாள்){RB}",
    re.IGNORECASE,
)
_PAST_KAL_GUARD_RE = re.compile(
    rf"{LB}(?:kal|parso|parson|कल|परसों|परसो)\s+(?:se|tha|thi|the|hua|hui|raat|subah\s+se|sham\s+se|aayi|aaya|gaya|gayi|से|था|थी|थे|हुआ|हुई|रात){RB}",
    re.IGNORECASE,
)
AMBIGUOUS_DATE_RE = re.compile(
    rf"{LB}(?:"
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
    rf"){RB}",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class DateCandidate:
    iso_date: str | None
    source_text: str
    start: int
    end: int
    invalid_calendar_date: bool = False
    ambiguous_dmy_mdy: bool = False


def _parse_day_token(raw_day: str) -> int | None:
    cleaned = raw_day.strip().lower()
    m_num = re.fullmatch(r"(\d{1,2})(?:st|nd|rd|th)?", cleaned)
    if m_num:
        return int(m_num.group(1))
    val = parse_int_tokens(cleaned.replace("-", " ").split())
    if val is not None and 1 <= val <= 31:
        return val
    return None


def _parse_count_token(raw_count: str | None) -> int | None:
    if not raw_count:
        return None
    cleaned = raw_count.strip().lower()
    if cleaned in {"a", "an"}:
        return 1
    if cleaned.isdigit():
        return int(cleaned)
    return parse_int_tokens(cleaned.replace("-", " ").split())


def find_date_candidates(text: str, *, reference_date: date) -> list[DateCandidate]:
    """Find all date expressions in `text` without overlap, preserving order & provenance."""
    candidates: list[DateCandidate] = []
    occupied: list[tuple[int, int]] = []

    def _overlaps(s: int, e: int) -> bool:
        return any(not (e <= os or s >= oe) for os, oe in occupied)

    def _add(cand: DateCandidate) -> None:
        occupied.append((cand.start, cand.end))
        candidates.append(cand)

    # 1. Explicit ISO YYYY-MM-DD
    for m in _ISO_DATE_RE.finditer(text):
        y, mo, d = int(m.group("y")), int(m.group("m")), int(m.group("d"))
        try:
            _add(
                DateCandidate(
                    date(y, mo, d).isoformat(),
                    m.group(0),
                    m.start(),
                    m.end(),
                    ambiguous_dmy_mdy=(1 <= d <= 12 and 1 <= mo <= 12 and d != mo),
                )
            )
        except ValueError:
            _add(DateCandidate(None, m.group(0), m.start(), m.end(), invalid_calendar_date=True))

    # 2. Explicit DD/MM/YYYY or DD-MM-YYYY
    for m in _DMY_DATE_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        d, mo, y = int(m.group("d")), int(m.group("m")), int(m.group("y"))
        if y < 100:
            y += 2000
        try:
            _add(
                DateCandidate(
                    date(y, mo, d).isoformat(),
                    m.group(0),
                    m.start(),
                    m.end(),
                    ambiguous_dmy_mdy=(1 <= d <= 12 and 1 <= mo <= 12 and d != mo),
                )
            )
        except ValueError:
            _add(DateCandidate(None, m.group(0), m.start(), m.end(), invalid_calendar_date=True))

    # 3. Day + Month or Month + Day
    for pat in (_DAY_MONTH_RE, _MONTH_DAY_RE):
        for m in pat.finditer(text):
            if _overlaps(m.start(), m.end()):
                continue
            day_val = _parse_day_token(m.group("day"))
            month_val = MONTH_NAMES.get(m.group("month").lower())
            year_str = m.group("year")
            if day_val is not None and month_val is not None:
                year_val = int(year_str) if year_str else reference_date.year
                try:
                    cand = date(year_val, month_val, day_val)
                except ValueError:
                    _add(DateCandidate(None, m.group(0), m.start(), m.end(), invalid_calendar_date=True))
                    continue
                if not year_str and cand < reference_date:
                    try:
                        cand = date(year_val + 1, month_val, day_val)
                    except ValueError:
                        _add(DateCandidate(None, m.group(0), m.start(), m.end(), invalid_calendar_date=True))
                        continue
                _add(DateCandidate(cand.isoformat(), m.group(0), m.start(), m.end()))

    # 4. Relative day offsets
    for m in _AFTER_DAYS_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        raw_n = m.group("n1") or m.group("n2")
        days = _parse_count_token(raw_n)
        if days is not None and 0 < days <= 365:
            _add(DateCandidate((reference_date + timedelta(days=days)).isoformat(), m.group(0), m.start(), m.end()))

    # 5. Relative week offsets
    for m in _AFTER_WEEKS_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        raw_n = m.group("n1") or m.group("n2")
        weeks = _parse_count_token(raw_n)
        if weeks is not None and 0 < weeks <= 52:
            _add(DateCandidate((reference_date + timedelta(days=7 * weeks)).isoformat(), m.group(0), m.start(), m.end()))

    # 6. Ambiguous phrase guard (skip relative matches inside ambiguous phrases)
    m_amb = AMBIGUOUS_DATE_RE.search(text)
    if m_amb and not candidates:
        return []

    # 7. Next week
    for m in _NEXT_WEEK_RE.finditer(text):
        if not _overlaps(m.start(), m.end()):
            _add(DateCandidate((reference_date + timedelta(days=7)).isoformat(), m.group(0), m.start(), m.end()))

    # 8. Day after tomorrow / parso
    if not _PAST_KAL_GUARD_RE.search(text):
        for m in _DAY_AFTER_TOMORROW_RE.finditer(text):
            if not _overlaps(m.start(), m.end()):
                _add(DateCandidate((reference_date + timedelta(days=2)).isoformat(), m.group(0), m.start(), m.end()))
        for m in _TOMORROW_RE.finditer(text):
            if not _overlaps(m.start(), m.end()):
                _add(DateCandidate((reference_date + timedelta(days=1)).isoformat(), m.group(0), m.start(), m.end()))

    # 9. Weekday
    for m in _WEEKDAY_NEXT_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        raw_wd = m.group("wd1") or m.group("wd2")
        wd_idx = WEEKDAY_NAMES.get(raw_wd.lower()) if raw_wd else None
        if wd_idx is not None:
            delta = (wd_idx - reference_date.weekday()) % 7
            if delta == 0:
                delta = 7
            _add(DateCandidate((reference_date + timedelta(days=delta)).isoformat(), m.group(0), m.start(), m.end()))

    candidates.sort(key=lambda c: c.start)
    return candidates


def resolve_date_candidates(
    text: str,
    candidates: list[DateCandidate],
) -> tuple[DateCandidate | None, bool, list[DateCandidate]]:
    """Resolve multiple date mentions (handling repeated corrections vs conflicts)."""
    if not candidates:
        return None, False, []
    if len(candidates) == 1:
        return candidates[0], False, []

    valid_cands = [c for c in candidates if c.iso_date is not None]
    if not valid_cands:
        return candidates[-1], False, []

    distinct_dates = []
    seen = set()
    for c in valid_cands:
        if c.iso_date not in seen:
            seen.add(c.iso_date)
            distinct_dates.append(c)

    if len(distinct_dates) == 1:
        return distinct_dates[-1], False, []

    # If an earlier candidate was invalid (e.g. "31 Feb, sorry 28 Feb") or corrected via bridge:
    has_corr = False
    has_conf = False
    for prev_c, next_c in zip(candidates, candidates[1:]):
        if prev_c.iso_date == next_c.iso_date and prev_c.iso_date is not None:
            continue
        between = text[prev_c.end : next_c.start]
        if CONFLICT_BRIDGE_RE.search(between):
            has_conf = True
        elif CORRECTION_BRIDGE_RE.search(between):
            has_corr = True
        else:
            # e.g. "next visit 25 November after 7 days" or ambiguous two dates without correction cue
            # Allow "after 7 days" + "25 Nov" only if they resolve to different dates -> conflict!
            has_conf = True

    if has_corr and not has_conf:
        return candidates[-1], True, []
    return None, False, distinct_dates

