"""Per-worker correction memory for adaptive ASR normalization and keyterm biasing.

Learns frequently used corrections (e.g. ASR misrecognitions of medical terms,
abbreviations, regional words, or beneficiary names) per ASHA `worker_id` and
applies them deterministically to subsequent utterances for that worker.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


DEFAULT_MEMORY_PATH = Path(__file__).resolve().parents[2] / "data" / "worker_corrections.json"


@dataclass
class PhraseCorrectionEntry:
    wrong_phrase: str
    corrected_phrase: str
    field_name: str | None = None
    count: int = 1
    last_used_at: str = field(default_factory=_utc_now_iso)


class WorkerCorrectionMemory:
    """Thread-safe, JSON-persisted per-worker correction store."""

    def __init__(self, storage_path: Path | str | None = None) -> None:
        self._path = Path(storage_path) if storage_path else DEFAULT_MEMORY_PATH
        self._lock = threading.Lock()
        # worker_id -> {"phrases": {wrong_lower: PhraseCorrectionEntry}, "field_counts": {field: int}}
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for wid, entry in raw.items():
                    if not isinstance(entry, dict):
                        continue
                    phrases: dict[str, PhraseCorrectionEntry] = {}
                    for k, p in (entry.get("phrases") or {}).items():
                        if isinstance(p, dict) and p.get("wrong_phrase") and p.get("corrected_phrase"):
                            phrases[k] = PhraseCorrectionEntry(
                                wrong_phrase=str(p["wrong_phrase"]),
                                corrected_phrase=str(p["corrected_phrase"]),
                                field_name=p.get("field_name"),
                                count=int(p.get("count", 1)),
                                last_used_at=str(p.get("last_used_at") or _utc_now_iso()),
                            )
                    field_counts = {
                        str(fk): int(fv)
                        for fk, fv in (entry.get("field_counts") or {}).items()
                    }
                    self._data[str(wid)] = {
                        "phrases": phrases,
                        "field_counts": field_counts,
                    }
        except Exception:
            # Corrupted or unreadable store starts clean rather than crashing voice pipeline
            self._data = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            serializable: dict[str, Any] = {}
            for wid, entry in self._data.items():
                serializable[wid] = {
                    "phrases": {
                        k: asdict(v) for k, v in entry["phrases"].items()
                    },
                    "field_counts": dict(entry["field_counts"]),
                }
            self._path.write_text(
                json.dumps(serializable, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _ensure_worker(self, worker_id: str) -> dict[str, Any]:
        wid = (worker_id or "ASHA-DEMO-01").strip() or "ASHA-DEMO-01"
        if wid not in self._data:
            self._data[wid] = {"phrases": {}, "field_counts": {}}
        return self._data[wid]

    def record_correction(
        self,
        worker_id: str,
        *,
        wrong_phrase: str | None = None,
        corrected_phrase: str | None = None,
        field_name: str | None = None,
    ) -> PhraseCorrectionEntry | None:
        """Record a worker's spoken/field correction so future utterances adapt."""
        with self._lock:
            w = self._ensure_worker(worker_id)
            if field_name:
                fc = w["field_counts"]
                fc[field_name] = int(fc.get(field_name, 0)) + 1

            entry: PhraseCorrectionEntry | None = None
            if wrong_phrase and corrected_phrase:
                wrong_clean = re.sub(r"\s+", " ", wrong_phrase.strip())
                right_clean = re.sub(r"\s+", " ", corrected_phrase.strip())
                if (
                    wrong_clean
                    and right_clean
                    and wrong_clean.lower() != right_clean.lower()
                    and len(wrong_clean) >= 2
                    and len(wrong_clean) <= 80
                    and len(right_clean) <= 80
                ):
                    key = wrong_clean.lower()
                    existing = w["phrases"].get(key)
                    if existing is not None and existing.corrected_phrase.lower() == right_clean.lower():
                        existing.count += 1
                        existing.last_used_at = _utc_now_iso()
                        if field_name and not existing.field_name:
                            existing.field_name = field_name
                        entry = existing
                    else:
                        entry = PhraseCorrectionEntry(
                            wrong_phrase=wrong_clean,
                            corrected_phrase=right_clean,
                            field_name=field_name,
                            count=1,
                        )
                        w["phrases"][key] = entry
            self._save()
            return entry

    def apply_learned_corrections(
        self,
        worker_id: str,
        text: str,
        *,
        min_count: int = 1,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Apply learned phrase replacements for `worker_id` to `text`."""
        if not text or not text.strip():
            return text, []
        with self._lock:
            w = self._data.get((worker_id or "").strip())
            if not w or not w["phrases"]:
                return text, []
            entries = [
                e for e in w["phrases"].values() if e.count >= min_count
            ]

        # Apply longest phrases first to avoid partial overlap
        entries.sort(key=lambda e: len(e.wrong_phrase), reverse=True)
        updated = text
        applied: list[dict[str, Any]] = []
        for entry in entries:
            escaped = re.escape(entry.wrong_phrase).replace(r"\ ", r"\s+")
            pat = re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)
            if pat.search(updated):
                updated = pat.sub(entry.corrected_phrase, updated)
                applied.append(
                    {
                        "wrong_phrase": entry.wrong_phrase,
                        "corrected_phrase": entry.corrected_phrase,
                        "field_name": entry.field_name,
                        "count": entry.count,
                    }
                )
        return updated, applied

    def get_worker_bias_keywords(self, worker_id: str, *, limit: int = 15) -> list[str]:
        """Return the worker's most frequently corrected target terms for STT biasing."""
        with self._lock:
            w = self._data.get((worker_id or "").strip())
            if not w or not w["phrases"]:
                return []
            entries = sorted(
                w["phrases"].values(),
                key=lambda e: (e.count, len(e.corrected_phrase)),
                reverse=True,
            )
            out: list[str] = []
            for e in entries:
                term = e.corrected_phrase.strip()
                if term and term not in out:
                    out.append(term)
                if len(out) >= limit:
                    break
            return out

    def get_worker_summary(self, worker_id: str) -> dict[str, Any]:
        """Return a serializable summary of learned corrections for `worker_id`."""
        with self._lock:
            w = self._data.get((worker_id or "").strip())
            if not w:
                return {
                    "worker_id": worker_id,
                    "phrase_corrections": [],
                    "field_correction_counts": {},
                }
            phrases = sorted(
                [asdict(v) for v in w["phrases"].values()],
                key=lambda d: d["count"],
                reverse=True,
            )
            return {
                "worker_id": worker_id,
                "phrase_corrections": phrases,
                "field_correction_counts": dict(w["field_counts"]),
            }


_global_worker_memory: WorkerCorrectionMemory | None = None


def get_worker_memory() -> WorkerCorrectionMemory:
    """Return the process-wide singleton WorkerCorrectionMemory."""
    global _global_worker_memory
    if _global_worker_memory is None:
        _global_worker_memory = WorkerCorrectionMemory()
    return _global_worker_memory
