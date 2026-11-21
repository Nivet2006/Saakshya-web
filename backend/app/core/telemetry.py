"""PHI-safe Time-to-First-Audio (TTFA) latency & task-completion telemetry tracker.

Tracks per-turn timestamps required by Section 5:
- `speech_started_at`
- `speech_ended_at`
- `transcript_finalized_at`
- `llm_first_token_at`
- `tts_first_chunk_at`
- `audio_first_played_at`

Computes:
- TTFA median (P50), P95, average (`audio_first_played_at - speech_ended_at`)
- Initial greeting latency
- STT finalization time
- LLM time to first token
- TTS first-chunk latency
- Section 6 9-step task completion & field accuracy metrics
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def _epoch_to_iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _percentile(sorted_vals: list[float], pct: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return round(sorted_vals[0], 2)
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return round(sorted_vals[low], 2)
    weight = rank - low
    return round(sorted_vals[low] * (1.0 - weight) + sorted_vals[high] * weight, 2)


def _summary_stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "p50_ms": None, "p95_ms": None, "avg_ms": None, "min_ms": None, "max_ms": None}
    s = sorted(values)
    return {
        "count": len(s),
        "p50_ms": _percentile(s, 50.0),
        "p95_ms": _percentile(s, 95.0),
        "avg_ms": round(sum(s) / len(s), 2),
        "min_ms": round(s[0], 2),
        "max_ms": round(s[-1], 2),
    }


@dataclass
class TurnLatencyRecord:
    """PHI-free per-turn latency record."""

    session_id: str
    turn_id: int
    is_greeting: bool = False
    turn_created_at: float = field(default_factory=time.time)
    speech_started_at: float | None = None
    speech_ended_at: float | None = None
    transcript_finalized_at: float | None = None
    llm_first_token_at: float | None = None
    tts_first_chunk_at: float | None = None
    audio_first_played_at: float | None = None
    stt_reported_latency_ms: float | None = None

    @property
    def ttfa_ms(self) -> float | None:
        """Time to First Audio = audio_first_played_at - speech_ended_at (ms)."""
        if self.is_greeting:
            return None
        played = self.audio_first_played_at or self.tts_first_chunk_at
        ended = self.speech_ended_at or self.transcript_finalized_at
        if played is None or ended is None:
            return None
        return round(max(0.0, (played - ended) * 1000.0), 2)

    @property
    def greeting_latency_ms(self) -> float | None:
        if not self.is_greeting:
            return None
        played = self.audio_first_played_at or self.tts_first_chunk_at
        base = self.turn_created_at
        if played is None:
            return None
        return round(max(0.0, (played - base) * 1000.0), 2)

    @property
    def stt_finalization_ms(self) -> float | None:
        if self.transcript_finalized_at is not None and self.speech_ended_at is not None:
            return round(max(0.0, (self.transcript_finalized_at - self.speech_ended_at) * 1000.0), 2)
        if self.stt_reported_latency_ms is not None:
            return round(float(self.stt_reported_latency_ms), 2)
        return None

    @property
    def llm_first_token_ms(self) -> float | None:
        if self.llm_first_token_at is None:
            return None
        base = self.transcript_finalized_at or self.turn_created_at
        return round(max(0.0, (self.llm_first_token_at - base) * 1000.0), 2)

    @property
    def tts_first_chunk_ms(self) -> float | None:
        if self.tts_first_chunk_at is None:
            return None
        base = self.llm_first_token_at or self.transcript_finalized_at or self.turn_created_at
        return round(max(0.0, (self.tts_first_chunk_at - base) * 1000.0), 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "is_greeting": self.is_greeting,
            "speech_started_at": _epoch_to_iso(self.speech_started_at),
            "speech_ended_at": _epoch_to_iso(self.speech_ended_at),
            "transcript_finalized_at": _epoch_to_iso(self.transcript_finalized_at),
            "llm_first_token_at": _epoch_to_iso(self.llm_first_token_at),
            "tts_first_chunk_at": _epoch_to_iso(self.tts_first_chunk_at),
            "audio_first_played_at": _epoch_to_iso(self.audio_first_played_at),
            "ttfa_ms": self.ttfa_ms,
            "greeting_latency_ms": self.greeting_latency_ms,
            "stt_finalization_ms": self.stt_finalization_ms,
            "llm_first_token_ms": self.llm_first_token_ms,
            "tts_first_chunk_ms": self.tts_first_chunk_ms,
        }


@dataclass
class TaskSuccessSteps:
    """Section 6 primary acceptance 9-step task sequence."""

    session_started: bool = False
    beneficiary_identified: bool = False
    identity_voice_confirmed: bool = False
    visit_notes_captured: bool = False
    required_fields_extracted: bool = False
    clarifications_resolved: bool = True
    read_back_completed: bool = False
    worker_confirmed: bool = False
    visit_persisted: bool = False

    @property
    def task_completed(self) -> bool:
        return (
            self.session_started
            and self.beneficiary_identified
            and self.identity_voice_confirmed
            and self.visit_notes_captured
            and self.required_fields_extracted
            and self.clarifications_resolved
            and self.read_back_completed
            and self.worker_confirmed
            and self.visit_persisted
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            "session_started": self.session_started,
            "beneficiary_identified": self.beneficiary_identified,
            "identity_voice_confirmed": self.identity_voice_confirmed,
            "visit_notes_captured": self.visit_notes_captured,
            "required_fields_extracted": self.required_fields_extracted,
            "clarifications_resolved": self.clarifications_resolved,
            "read_back_completed": self.read_back_completed,
            "worker_confirmed": self.worker_confirmed,
            "visit_persisted": self.visit_persisted,
            "task_completed": self.task_completed,
        }


class SessionTelemetryTracker:
    """Tracks PHI-free latency timestamps and task completion milestones for one session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.turns: dict[int, TurnLatencyRecord] = {}
        self.steps = TaskSuccessSteps(session_started=True)
        self._pending_speech_start: float | None = None
        self._pending_speech_end: float | None = None
        self._last_finalized_at: float | None = None
        self._last_stt_latency_ms: float | None = None
        self.barge_in_count: int = 0
        self.correction_count: int = 0

    def mark_speech_start(self, ts: float | None = None) -> None:
        now = ts or time.time()
        if self._pending_speech_start is None:
            self._pending_speech_start = now

    def mark_speech_end(self, ts: float | None = None) -> None:
        self._pending_speech_end = ts or time.time()

    def mark_transcript_finalized(
        self,
        *,
        ts: float | None = None,
        stt_latency_ms: float | None = None,
    ) -> None:
        now = ts or time.time()
        self._last_finalized_at = now
        self._last_stt_latency_ms = stt_latency_ms
        if self._pending_speech_end is None:
            if stt_latency_ms is not None and stt_latency_ms >= 0:
                self._pending_speech_end = now - (stt_latency_ms / 1000.0)
            else:
                self._pending_speech_end = now
        if self._pending_speech_start is None:
            self._pending_speech_start = self._pending_speech_end

    def start_turn(self, turn_id: int, *, is_greeting: bool = False) -> TurnLatencyRecord:
        now = time.time()
        rec = TurnLatencyRecord(
            session_id=self.session_id,
            turn_id=turn_id,
            is_greeting=is_greeting,
            turn_created_at=now,
            speech_started_at=None if is_greeting else self._pending_speech_start,
            speech_ended_at=None if is_greeting else self._pending_speech_end,
            transcript_finalized_at=None if is_greeting else self._last_finalized_at,
            stt_reported_latency_ms=None if is_greeting else self._last_stt_latency_ms,
        )
        self.turns[turn_id] = rec
        if not is_greeting:
            self._pending_speech_start = None
            self._pending_speech_end = None
            self._last_finalized_at = None
            self._last_stt_latency_ms = None
        return rec

    def mark_llm_first_token(self, turn_id: int, ts: float | None = None) -> None:
        rec = self.turns.get(turn_id)
        if rec is not None and rec.llm_first_token_at is None:
            rec.llm_first_token_at = ts or time.time()

    def mark_tts_first_chunk(self, turn_id: int, ts: float | None = None) -> None:
        now = ts or time.time()
        rec = self.turns.get(turn_id)
        if rec is not None and rec.tts_first_chunk_at is None:
            rec.tts_first_chunk_at = now
            if rec.audio_first_played_at is None:
                rec.audio_first_played_at = now

    def mark_audio_first_played(
        self,
        turn_id: int,
        *,
        ts: float | None = None,
        client_ttfa_ms: float | None = None,
    ) -> None:
        rec = self.turns.get(turn_id)
        if rec is None:
            return
        if client_ttfa_ms is not None and client_ttfa_ms >= 0 and rec.speech_ended_at is not None:
            rec.audio_first_played_at = rec.speech_ended_at + (client_ttfa_ms / 1000.0)
        else:
            rec.audio_first_played_at = ts or time.time()

    def summary(self) -> dict[str, Any]:
        ttfa_vals = [r.ttfa_ms for r in self.turns.values() if r.ttfa_ms is not None]
        greeting_vals = [
            r.greeting_latency_ms for r in self.turns.values() if r.greeting_latency_ms is not None
        ]
        stt_vals = [
            r.stt_finalization_ms for r in self.turns.values() if r.stt_finalization_ms is not None
        ]
        llm_vals = [
            r.llm_first_token_ms for r in self.turns.values() if r.llm_first_token_ms is not None
        ]
        tts_vals = [
            r.tts_first_chunk_ms for r in self.turns.values() if r.tts_first_chunk_ms is not None
        ]

        ttfa_stats = _summary_stats(ttfa_vals)
        return {
            "schema_version": "v1",
            "session_id": self.session_id,
            "ttfa_p50_ms": ttfa_stats["p50_ms"],
            "ttfa_p95_ms": ttfa_stats["p95_ms"],
            "ttfa_avg_ms": ttfa_stats["avg_ms"],
            "initial_greeting_latency_ms": greeting_vals[0] if greeting_vals else None,
            "stt_finalization_stats": _summary_stats(stt_vals),
            "llm_first_token_stats": _summary_stats(llm_vals),
            "tts_first_chunk_stats": _summary_stats(tts_vals),
            "ttfa_stats": ttfa_stats,
            "barge_in_count": self.barge_in_count,
            "correction_count": self.correction_count,
            "task_success": self.steps.to_dict(),
            "turns": [r.to_dict() for r in sorted(self.turns.values(), key=lambda x: x.turn_id)],
        }


class TelemetryRegistry:
    """In-memory registry aggregating PHI-free latency & task metrics across sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionTelemetryTracker] = {}

    def get_or_create(self, session_id: str) -> SessionTelemetryTracker:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionTelemetryTracker(session_id)
        return self._sessions[session_id]

    def get(self, session_id: str) -> SessionTelemetryTracker | None:
        return self._sessions.get(session_id)

    def aggregate_summary(self) -> dict[str, Any]:
        all_ttfa: list[float] = []
        all_greeting: list[float] = []
        all_stt: list[float] = []
        all_llm: list[float] = []
        all_tts: list[float] = []
        completed_count = 0
        total_sessions = len(self._sessions)

        for tracker in self._sessions.values():
            if tracker.steps.task_completed:
                completed_count += 1
            for r in tracker.turns.values():
                if r.ttfa_ms is not None:
                    all_ttfa.append(r.ttfa_ms)
                if r.greeting_latency_ms is not None:
                    all_greeting.append(r.greeting_latency_ms)
                if r.stt_finalization_ms is not None:
                    all_stt.append(r.stt_finalization_ms)
                if r.llm_first_token_ms is not None:
                    all_llm.append(r.llm_first_token_ms)
                if r.tts_first_chunk_ms is not None:
                    all_tts.append(r.tts_first_chunk_ms)

        ttfa_stats = _summary_stats(all_ttfa)
        greeting_stats = _summary_stats(all_greeting)
        return {
            "schema_version": "v1",
            "total_sessions": total_sessions,
            "completed_tasks": completed_count,
            "task_completion_rate": (
                round(completed_count / total_sessions, 4) if total_sessions > 0 else 0.0
            ),
            "ttfa_p50_ms": ttfa_stats["p50_ms"],
            "ttfa_p95_ms": ttfa_stats["p95_ms"],
            "ttfa_avg_ms": ttfa_stats["avg_ms"],
            "initial_greeting_p50_ms": greeting_stats["p50_ms"],
            "initial_greeting_avg_ms": greeting_stats["avg_ms"],
            "ttfa_stats": ttfa_stats,
            "greeting_stats": greeting_stats,
            "stt_finalization_stats": _summary_stats(all_stt),
            "llm_first_token_stats": _summary_stats(all_llm),
            "tts_first_chunk_stats": _summary_stats(all_tts),
        }


telemetry_registry = TelemetryRegistry()

