"""Central Phase 2 Healthcare Integration Pipeline (1A + 1B + 1C -> v1 Contracts).

Wires:
- Layer 1 Deterministic Danger-Sign Engine (1A) on EVERY partial & final transcript
- Healthcare Visit Field Extractor & Validator (1C) on final transcripts
- Conversation State Machine, Read-Back, Correction & Confirmation Gate (1B)
- Contract-validated `v1` JSON serialization for `visit.schema.json`,
  `danger-alert.schema.json`, and `voice-events.schema.json`
"""

from __future__ import annotations

import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.conversation.models import (
    ActionType,
    ClarificationRequest,
    ConversationState,
    DangerAlertInput,
    DangerAlertRecord,
    ExtractionUpdate,
    TransitionResult,
    VisitRecordState,
    VisitStatus,
    detect_language_from_text,
    normalize_language,
)
from app.conversation.state_machine import (
    ConversationStateMachine,
    InvalidTransitionError,
    classify_confirmation_intent,
)
from app.core.config import get_settings
from app.core.logging import log_event
from app.danger_signs.detector import detect_danger_signs, get_referral_message
from app.danger_signs.models import DangerMatch, DetectionResult
from app.extraction.extractor import VisitFieldExtractor
from app.extraction.models import FollowUpAction, VisitDraft
from app.services.beneficiaries import SyntheticBeneficiaryDirectory
from app.voice.interfaces import TranscriptEvent
from app.voice.orchestration.session import VoiceSessionOrchestrator

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")

_MATCH_TYPE_TO_CONTRACT: dict[str, str] = {
    "exact": "exact_phrase",
    "alias": "code_mixed_pattern",
    "normalized": "normalized_variant",
    "threshold": "numeric_threshold",
    "fuzzy": "fuzzy_assisted",
}

_STATE_TO_WS_SESSION_STATE: dict[ConversationState, str] = {
    ConversationState.IDLE: "idle",
    ConversationState.GATHERING_NOTES: "listening",
    ConversationState.EXTRACTING_FIELDS: "processing",
    ConversationState.CLARIFICATION_REQUIRED: "speaking",
    ConversationState.READ_BACK_CONFIRMATION: "speaking",
    ConversationState.CORRECTION_PATCH: "processing",
    ConversationState.READY_TO_CONFIRM: "listening",
    ConversationState.COMMITTED: "idle",
    ConversationState.DANGER_ESCALATION: "danger_escalation",
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _map_follow_up_action_type(action_type: str, visit_type: str | None) -> str:
    if action_type == "vaccination":
        return "vaccination_followup"
    if action_type == "ifa_adherence":
        return "nutrition_counsel"
    if action_type == "danger_referral":
        return "phc_referral"
    if action_type == "weight_monitoring":
        return "hbnc_visit" if visit_type == "Newborn" else "home_visit"
    if action_type == "routine_visit":
        if visit_type == "ANC":
            return "anc_checkup"
        if visit_type == "PNC":
            return "pnc_checkup"
        if visit_type == "Newborn":
            return "hbnc_visit"
        return "home_visit"
    return "other"


def format_danger_alert_contract(
    *,
    alert_id: str,
    session_id: str,
    visit_id: str,
    beneficiary_id: str | None,
    match: DangerMatch,
    language: str,
    referral_message: str,
    detected_at: str | None = None,
    status: str = "active",
    acknowledged_by: str | None = None,
    acknowledged_at: str | None = None,
) -> dict[str, Any]:
    """Serialize a 1A DangerMatch into a strict `danger-alert.schema.json` v1 dict."""
    evidence = (match.evidence_text or match.matched_phrase or match.canonical_name).strip()[:200]
    return {
        "schema_version": "v1",
        "alert_id": alert_id,
        "session_id": session_id,
        "visit_id": visit_id,
        "beneficiary_id": beneficiary_id,
        "canonical_danger_sign_id": match.canonical_id,
        "canonical_name": match.canonical_name,
        "subject": match.subject,
        "category": match.category,
        "supporting_evidence": evidence,
        "match_type": _MATCH_TYPE_TO_CONTRACT.get(match.match_type, "code_mixed_pattern"),
        "source_guideline_ref": f"{match.source_doc} ({match.source_section})",
        "detected_at": detected_at or utc_now_iso(),
        "status": status,
        "acknowledged_by": acknowledged_by,
        "acknowledged_at": acknowledged_at,
        "escalation_language": normalize_language(language),
        "referral_message": referral_message,
        "danger_sign_flagged": True,
        "priority": "urgent",
    }


def format_visit_contract(
    *,
    visit_state: VisitRecordState,
    session_id: str,
    worker_id: str,
    language: str,
    weight_source_text: str | None = None,
    next_visit_date_source_text: str | None = None,
    structured_follow_ups: list[dict[str, Any]] | None = None,
    confirmed_at: str | None = None,
    committed_at: str | None = None,
) -> dict[str, Any]:
    """Serialize VisitRecordState into a strict `visit.schema.json` v1 dict."""
    vtype_str = visit_state.visit_type.value if visit_state.visit_type else None
    follow_ups = list(structured_follow_ups or [])
    if not follow_ups and visit_state.follow_up_actions:
        follow_ups = [
            {
                "action_type": "other",
                "description": desc,
                "due_date": visit_state.next_visit_date,
                "priority": "normal",
                "source_phrase": None,
            }
            for desc in visit_state.follow_up_actions
        ]

    # Ensure urgent PHC referral follow-up exists if danger_sign_flagged is True
    if visit_state.danger_sign_flagged and not any(
        f.get("action_type") == "phc_referral" for f in follow_ups
    ):
        today_ist = datetime.now(IST).date().isoformat()
        follow_ups.insert(
            0,
            {
                "action_type": "phc_referral",
                "description": "Immediate referral to nearest PHC for detected danger sign",
                "due_date": today_ist,
                "priority": "urgent",
                "source_phrase": (visit_state.danger_signs[0] if visit_state.danger_signs else None),
            },
        )

    return {
        "schema_version": "v1",
        "visit_id": visit_state.visit_draft_id,
        "session_id": session_id,
        "worker_id": worker_id,
        "beneficiary_id": visit_state.beneficiary_id,
        "beneficiary_name": visit_state.beneficiary_name,
        "visit_type": vtype_str,
        "weight_kg": visit_state.weight_kg,
        "weight_source_text": weight_source_text,
        "vaccinations_completed": list(visit_state.vaccinations_completed),
        "vaccinations_due": list(visit_state.vaccinations_due),
        "next_visit_date": visit_state.next_visit_date,
        "next_visit_date_source_text": next_visit_date_source_text,
        "danger_signs": list(visit_state.danger_signs),
        "danger_sign_flagged": bool(visit_state.danger_sign_flagged),
        "follow_up_actions": follow_ups,
        "status": visit_state.status.value,
        "confirmed_at": confirmed_at,
        "committed_at": committed_at,
        "persistence_record_id": visit_state.record_id,
        "language": normalize_language(language),
        "timezone": "Asia/Kolkata",
        "synthetic": True,
    }


class HealthcareSessionPipeline:
    """Per-session coordinator integrating 1A (Danger Signs), 1B (State Machine), and 1C (Extraction)."""

    def __init__(
        self,
        *,
        session_id: str,
        worker_id: str = "ASHA-DEMO-01",
        language: str = "hi-IN",
        beneficiary_id: str | None = None,
        directory: SyntheticBeneficiaryDirectory | None = None,
        reference_date: date | None = None,
    ) -> None:
        self.session_id = session_id
        self.worker_id = worker_id
        self.language = normalize_language(language)
        self._directory = directory or SyntheticBeneficiaryDirectory()
        self._extractor = VisitFieldExtractor(beneficiary_directory=self._directory)
        self._reference_date = reference_date

        ben_name: str | None = None
        if beneficiary_id:
            ben = self._directory.get_by_id(beneficiary_id)
            if ben is not None:
                beneficiary_id = ben.beneficiary_id
                ben_name = ben.full_name

        self.sm = ConversationStateMachine(
            session_id=session_id,
            language=self.language,
            beneficiary_id=beneficiary_id,
            beneficiary_name=ben_name,
        )
        self.sm.start_gathering()

        self._weight_source_text: str | None = None
        self._next_visit_date_source_text: str | None = None
        self._structured_follow_ups: list[dict[str, Any]] = []
        self._confirmed_at: str | None = None
        self._committed_at: str | None = None
        self._contract_alerts: dict[str, dict[str, Any]] = {}
        self._orchestrator: VoiceSessionOrchestrator | None = None

    def attach_orchestrator(self, orchestrator: VoiceSessionOrchestrator) -> None:
        self._orchestrator = orchestrator

    def current_visit_contract(self) -> dict[str, Any]:
        return format_visit_contract(
            visit_state=self.sm.visit,
            session_id=self.session_id,
            worker_id=self.worker_id,
            language=self.sm.active_language,
            weight_source_text=self._weight_source_text,
            next_visit_date_source_text=self._next_visit_date_source_text,
            structured_follow_ups=self._structured_follow_ups,
            confirmed_at=self._confirmed_at,
            committed_at=self._committed_at,
        )

    def current_alerts_contract(self) -> list[dict[str, Any]]:
        # Keep beneficiary_id synced on alerts if resolved later in the visit
        ben_id = self.sm.visit.beneficiary_id
        out: list[dict[str, Any]] = []
        for alert in self._contract_alerts.values():
            if ben_id and alert["beneficiary_id"] is None:
                alert["beneficiary_id"] = ben_id
            out.append(dict(alert))
        return out

    def _build_draft_snapshot_for_extractor(self) -> VisitDraft:
        v = self.sm.visit
        return VisitDraft(
            visit_id=v.visit_draft_id,
            beneficiary_id=v.beneficiary_id,
            beneficiary_name=v.beneficiary_name,
            visit_type=v.visit_type.value if v.visit_type else None,
            weight_kg=v.weight_kg,
            weight_source_text=self._weight_source_text,
            vaccinations_completed=list(v.vaccinations_completed),
            vaccinations_due=list(v.vaccinations_due),
            next_visit_date=v.next_visit_date,
            next_visit_date_source_text=self._next_visit_date_source_text,
            danger_signs=list(v.danger_signs),
            danger_sign_flagged=v.danger_sign_flagged,
            status=v.status.value,
            confirmed_fields=sorted(self.sm.confirmed_fields),
        )

    def _run_danger_check(self, text: str, *, language: str, is_partial: bool) -> DetectionResult:
        vtype = self.sm.visit.visit_type.value if self.sm.visit.visit_type else None
        subject: str | None = None
        if vtype == "Newborn":
            subject = "newborn"
        elif vtype in ("ANC", "PNC"):
            subject = "mother"
        return detect_danger_signs(
            text,
            language=language,
            context={"is_partial": is_partial, "visit_type": vtype, "subject": subject},
        )

    async def on_partial_transcript(
        self, event: TranscriptEvent, orchestrator: VoiceSessionOrchestrator
    ) -> bool:
        """Layer 1 Danger-Sign Engine + live non-mutating field autofeed on EVERY partial transcript."""
        settings = get_settings()
        raw_lang = event.language_code or orchestrator.active_language or self.language
        lang = detect_language_from_text(event.text, fallback=raw_lang)
        self.sm.set_language(lang)
        self.language = lang
        orchestrator.active_language = lang

        if settings.danger_sign_partial_matching:
            result = self._run_danger_check(event.text, language=lang, is_partial=True)
            if result.danger_sign_flagged and result.matches:
                await self._trigger_danger_escalation(result, orchestrator, is_partial=True)
                return True

        # Live autofeed: extract structured fields from partial speech without mutating state machine
        partial_text = (event.text or "").strip()
        if len(partial_text) >= 4 and partial_text != getattr(self, "_last_partial_preview_text", None):
            self._last_partial_preview_text = partial_text
            existing_draft = self._build_draft_snapshot_for_extractor()
            preview = self._extractor.extract(
                partial_text,
                reference_date=self._reference_date,
                active_language=lang,
                existing_draft=existing_draft,
            )
            if preview.patch:
                preview_contract = self.current_visit_contract()
                updated_fields: list[str] = []
                for key in (
                    "beneficiary_id",
                    "beneficiary_name",
                    "visit_type",
                    "weight_kg",
                    "vaccinations_completed",
                    "vaccinations_due",
                    "next_visit_date",
                ):
                    if key in preview.patch and preview.patch[key] not in (None, []):
                        preview_contract[key] = preview.patch[key]
                        updated_fields.append(key)
                if "follow_up_actions" in preview.patch and preview.patch["follow_up_actions"]:
                    preview_contract["follow_up_actions"] = [
                        {
                            "action_type": _map_follow_up_action_type(a.action_type, preview_contract.get("visit_type")),
                            "description": a.description,
                            "due_date": a.due_date,
                            "priority": a.priority,
                            "source_phrase": a.source_phrase,
                        }
                        for a in preview.patch["follow_up_actions"]
                    ]
                    updated_fields.append("follow_up_actions")
                if updated_fields:
                    await orchestrator.emit_event(
                        "visit_draft_updated",
                        visit_id=self.sm.visit.visit_draft_id,
                        draft=preview_contract,
                        updated_fields=updated_fields,
                        missing_required_fields=self._missing_required_fields(),
                    )
        return False

    async def on_final_transcript(
        self, event: TranscriptEvent, orchestrator: VoiceSessionOrchestrator
    ) -> bool:
        """Process a final transcript through 1A (Danger) -> 1C (Extraction) -> 1B (State Machine)."""
        raw_lang = event.language_code or orchestrator.active_language or self.language
        lang = detect_language_from_text(event.text, fallback=raw_lang)
        self.sm.set_language(lang)
        self.language = lang
        orchestrator.active_language = lang

        # 1. Layer 1 Deterministic Danger-Sign Check (ALWAYS runs first; NEVER suppressed)
        danger_res = self._run_danger_check(event.text, language=lang, is_partial=False)
        danger_fired = False
        if danger_res.danger_sign_flagged and danger_res.matches:
            danger_fired = await self._trigger_danger_escalation(
                danger_res, orchestrator, is_partial=False
            )

        # If we were in DANGER_ESCALATION and worker continues speaking visit notes, resume workflow
        if self.sm.state == ConversationState.DANGER_ESCALATION and not danger_fired:
            self.sm.resume_after_danger()

        # 2. Extract structured healthcare visit fields (1C)
        existing_draft = self._build_draft_snapshot_for_extractor()
        extraction = self._extractor.extract(
            event.text,
            reference_date=self._reference_date,
            active_language=lang,
            existing_draft=existing_draft,
        )

        # Preserve source provenance phrases and structured follow-ups for v1 contract
        if "weight_source_text" in extraction.patch:
            self._weight_source_text = extraction.patch["weight_source_text"]
        if "next_visit_date_source_text" in extraction.patch:
            self._next_visit_date_source_text = extraction.patch["next_visit_date_source_text"]

        extracted_followups: list[FollowUpAction] = extraction.patch.get("follow_up_actions", [])
        if extracted_followups:
            vtype_hint = extraction.patch.get("visit_type") or (
                self.sm.visit.visit_type.value if self.sm.visit.visit_type else None
            )
            existing_descs = {f["description"] for f in self._structured_follow_ups}
            for act in extracted_followups:
                if act.description not in existing_descs:
                    self._structured_follow_ups.append(
                        {
                            "action_type": _map_follow_up_action_type(act.action_type, vtype_hint),
                            "description": act.description,
                            "due_date": act.due_date,
                            "priority": act.priority,
                            "source_phrase": act.source_phrase,
                        }
                    )
                    existing_descs.add(act.description)

        # Build 1B ExtractionUpdate DTO
        sm_clarifications = [
            ClarificationRequest(
                field=c.field_name,
                reason=c.reason,
                question=c.prompt_hint,
                candidates=list(c.candidates),
            )
            for c in extraction.clarifications
        ]
        # Surface any conservative uncertain danger-sign matches as clarifications
        for um in danger_res.uncertain_matches:
            sm_clarifications.append(
                ClarificationRequest(
                    field="danger_signs",
                    reason="uncertain_danger_sign",
                    question=(
                        f"You mentioned '{um.matched_phrase}'. "
                        f"Is this severe or ongoing right now? Please clarify so I can check for danger signs."
                    ),
                )
            )

        update_kwargs: dict[str, Any] = {}
        explicit_fields: set[str] = set()
        for key in (
            "beneficiary_id",
            "beneficiary_name",
            "visit_type",
            "weight_kg",
            "vaccinations_completed",
            "vaccinations_due",
            "next_visit_date",
        ):
            if key in extraction.patch:
                update_kwargs[key] = extraction.patch[key]
                explicit_fields.add(key)

        if extracted_followups:
            update_kwargs["follow_up_actions"] = [a.description for a in extracted_followups]
            explicit_fields.add("follow_up_actions")

        update = ExtractionUpdate(
            **update_kwargs,
            clarifications=sm_clarifications,
            explicit_fields=explicit_fields if explicit_fields else None,
            detected_language=lang,
        )

        # 3. Route into Conversation State Machine (1B)
        if danger_fired:
            # Record any extracted fields silently into the draft without interrupting urgent referral speech
            if explicit_fields:
                for field_name in explicit_fields:
                    val = getattr(update, field_name)
                    if val is not None:
                        setattr(self.sm.visit, field_name, val)
                await orchestrator.emit_event(
                    "visit_draft_updated",
                    visit_id=self.sm.visit.visit_draft_id,
                    draft=self.current_visit_contract(),
                    updated_fields=sorted(explicit_fields),
                    missing_required_fields=self._missing_required_fields(),
                )
            return True

        if self.sm.state in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
        ):
            patch_arg = update if explicit_fields else None
            # Handle explicit confirmation or correction
            transition = self.sm.handle_confirmation_response(
                event.text,
                correction_patch=patch_arg,
            )
            await self._dispatch_transition(transition, orchestrator)
            return True

        # If worker gave an explicit correction while gathering/clarifying
        if extraction.detected_correction and explicit_fields:
            transition = self.sm.apply_correction_patch(update)
            await self._dispatch_transition(transition, orchestrator)
            return True

        # If nothing clinical/structured was extracted at all (e.g. greeting or general chitchat)
        if not explicit_fields and not sm_clarifications:
            # Let Milestone 1 LLM handle conversational greeting naturally unless awaiting confirmation
            return False

        transition = self.sm.apply_extraction(update)
        await self._dispatch_transition(transition, orchestrator)
        return True

    async def handle_explicit_confirm_command(
        self, confirmed: bool, orchestrator: VoiceSessionOrchestrator
    ) -> None:
        """Handle client `confirm_visit` WS command."""
        utterance = "yes confirm" if confirmed else "no"
        if self.sm.state not in (
            ConversationState.READ_BACK_CONFIRMATION,
            ConversationState.READY_TO_CONFIRM,
        ):
            if confirmed:
                await orchestrator.emit_event(
                    "error",
                    code="INVALID_STATE_TRANSITION",
                    message="Visit record must complete read-back before confirmation.",
                    retryable=False,
                )
                return
        transition = self.sm.handle_confirmation_response(utterance)
        await self._dispatch_transition(transition, orchestrator)

    async def handle_persistence_ack(
        self,
        *,
        accepted: bool,
        persistence_record_id: str | None = None,
        committed_at: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        emit_ws: bool = True,
    ) -> dict[str, Any]:
        """Process Agent 3 persistence acknowledgement (HTTP or WS)."""
        if self.sm.visit.status != VisitStatus.CONFIRMED and accepted:
            raise InvalidTransitionError(
                f"Cannot commit visit '{self.sm.visit.visit_draft_id}' while status is "
                f"'{self.sm.visit.status.value}'. Explicit worker confirmation is required first."
            )

        transition = self.sm.handle_persistence_result(
            accepted=accepted,
            record_id=persistence_record_id,
            error=error_message,
        )
        if accepted:
            self._committed_at = committed_at or utc_now_iso()

        if emit_ws and self._orchestrator is not None:
            await self._dispatch_transition(
                transition,
                self._orchestrator,
                error_code=error_code,
            )

        return {
            "schema_version": "v1",
            "session_id": self.session_id,
            "visit_id": self.sm.visit.visit_draft_id,
            "status": self.sm.visit.status.value,
            "persistence_record_id": self.sm.visit.record_id,
            "committed_at": self._committed_at,
        }

    async def _trigger_danger_escalation(
        self,
        detection: DetectionResult,
        orchestrator: VoiceSessionOrchestrator,
        *,
        is_partial: bool,
    ) -> bool:
        """Interrupt active speech immediately, emit v1 `danger_alert`, speak urgent PHC referral."""
        lang = normalize_language(detection.active_language or self.language)
        referral_msg = detection.referral_message or get_referral_message(lang)
        emitted_new_urgent = False

        for match in detection.matches:
            already_seen = match.canonical_id in self._contract_alerts
            alert_id = (
                self._contract_alerts[match.canonical_id]["alert_id"]
                if already_seen
                else f"alrt_{uuid.uuid4().hex[:12]}"
            )
            contract_alert = format_danger_alert_contract(
                alert_id=alert_id,
                session_id=self.session_id,
                visit_id=self.sm.visit.visit_draft_id,
                beneficiary_id=self.sm.visit.beneficiary_id,
                match=match,
                language=lang,
                referral_message=referral_msg,
                detected_at=(
                    self._contract_alerts[match.canonical_id]["detected_at"]
                    if already_seen
                    else utc_now_iso()
                ),
            )
            self._contract_alerts[match.canonical_id] = contract_alert

            sm_input = DangerAlertInput(
                alert_id=alert_id,
                canonical_id=match.canonical_id,
                category=match.category,
                display_name=match.canonical_name,
                matched_phrase=match.evidence_text or match.matched_phrase,
                guideline_reference=f"{match.source_doc} ({match.source_section})",
                confidence=match.confidence,
                is_partial=is_partial,
                escalation_message=referral_msg,
                language=lang,
            )
            self.sm.handle_danger_detection(sm_input)

            if not already_seen:
                emitted_new_urgent = True
                log_event(
                    logger,
                    "danger_sign_escalated",
                    session=self.session_id,
                    canonical_id=match.canonical_id,
                    is_partial=is_partial,
                )
                await orchestrator.emit_event(
                    "danger_alert",
                    priority="urgent",
                    danger_sign_flagged=True,
                    interrupts_speech=True,
                    alert=contract_alert,
                )

        if emitted_new_urgent:
            await orchestrator.emit_event(
                "visit_draft_updated",
                visit_id=self.sm.visit.visit_draft_id,
                draft=self.current_visit_contract(),
                updated_fields=["danger_signs", "danger_sign_flagged", "follow_up_actions"],
                missing_required_fields=self._missing_required_fields(),
            )
            await orchestrator.speak_urgent(referral_msg, language=lang)
        return emitted_new_urgent

    def _missing_required_fields(self) -> list[str]:
        missing: list[str] = []
        if self.sm.visit.beneficiary_id is None:
            missing.append("beneficiary_id")
        if self.sm.visit.visit_type is None:
            missing.append("visit_type")
        if not self.sm.visit.has_clinical_observation():
            missing.append("clinical_observation")
        return missing

    def _normalize_clarification_reason(self, field: str, reason: str) -> str:
        r = (reason or "").lower()
        if r in ("ambiguous_beneficiary", "missing_required", "ambiguous_value", "uncertain_danger_sign", "conflict"):
            return r
        if field == "beneficiary_id" and "ambig" in r:
            return "ambiguous_beneficiary"
        if "missing" in r:
            return "missing_required"
        if "conflict" in r:
            return "conflict"
        if "danger" in r:
            return "uncertain_danger_sign"
        return "ambiguous_value"

    async def _dispatch_transition(
        self,
        transition: TransitionResult,
        orchestrator: VoiceSessionOrchestrator,
        *,
        error_code: str | None = None,
    ) -> None:
        """Emit strict v1 contract WebSocket events & trigger TTS for a 1B TransitionResult."""
        visit_id = self.sm.visit.visit_draft_id
        lang = normalize_language(transition.spoken_language)
        next_turn_id = max(1, orchestrator.active_turn_id + 1)

        for action in transition.actions:
            atype = action.action_type
            payload = action.payload

            if atype == ActionType.DRAFT_UPDATED:
                await orchestrator.emit_event(
                    "visit_draft_updated",
                    visit_id=visit_id,
                    draft=self.current_visit_contract(),
                    updated_fields=list(payload.get("updated_fields", [])),
                    missing_required_fields=self._missing_required_fields(),
                )

            elif atype == ActionType.CLARIFICATION_PROMPT:
                raw_clars = payload.get("clarifications", [])
                first = raw_clars[0] if raw_clars else {"field": "visit_notes", "reason": "missing_required"}
                field_name = str(first.get("field", "visit_notes"))
                candidates = [
                    {"id": str(c), "label": str(c), "detail": None}
                    for c in (first.get("candidates") or [])
                ]
                ev_kwargs: dict[str, Any] = {
                    "visit_id": visit_id,
                    "field": field_name,
                    "reason": self._normalize_clarification_reason(field_name, str(first.get("reason", ""))),
                    "prompt_text": transition.spoken_text or first.get("question") or f"Please clarify {field_name}.",
                    "language": lang,
                }
                if candidates:
                    ev_kwargs["candidates"] = candidates
                await orchestrator.emit_event("clarification_required", **ev_kwargs)

            elif atype == ActionType.CORRECTION_APPLIED:
                corrected = list(payload.get("patched_fields") or payload.get("corrected_fields") or [])
                if not corrected:
                    corrected = ["visit_record"]
                draft_dict = self.current_visit_contract()
                preserved = [
                    k
                    for k in ("beneficiary_id", "visit_type", "weight_kg", "vaccinations_due", "next_visit_date", "danger_sign_flagged")
                    if k not in corrected and draft_dict.get(k) not in (None, [], False)
                ]
                await orchestrator.emit_event(
                    "correction_applied",
                    visit_id=visit_id,
                    corrected_fields=corrected,
                    previous_values=dict(payload.get("previous_values", {})),
                    new_values={k: draft_dict.get(k) for k in corrected if k in draft_dict},
                    preserved_fields=preserved,
                    requires_re_read_back=True,
                    draft=draft_dict,
                )

            elif atype == ActionType.READ_BACK_STARTED:
                summary = payload.get("read_back_text") or transition.spoken_text or "Visit summary."
                await orchestrator.emit_event(
                    "read_back_started",
                    visit_id=visit_id,
                    turn_id=next_turn_id,
                    summary_text=summary,
                    language=lang,
                    draft=self.current_visit_contract(),
                )

            elif atype == ActionType.WORKER_CONFIRMED:
                self._confirmed_at = utc_now_iso()
                await orchestrator.emit_event(
                    "visit_confirmed",
                    visit_id=visit_id,
                    confirmed_at=self._confirmed_at,
                    visit=self.current_visit_contract(),
                )

            elif atype == ActionType.PERSISTENCE_REQUESTED:
                corr_id = f"corr_{uuid.uuid4().hex[:10]}"
                await orchestrator.emit_event(
                    "persistence_requested",
                    correlation_id=corr_id,
                    visit_id=visit_id,
                    visit=self.current_visit_contract(),
                    danger_alerts=self.current_alerts_contract(),
                )

            elif atype == ActionType.VISIT_COMMITTED:
                await orchestrator.emit_event(
                    "visit_committed",
                    visit_id=visit_id,
                    visit=self.current_visit_contract(),
                    persistence_record_id=self.sm.visit.record_id or "persisted",
                    committed_at=self._committed_at or utc_now_iso(),
                )

            elif atype == ActionType.PERSISTENCE_REJECTED:
                await orchestrator.emit_event(
                    "persistence_rejected",
                    visit_id=visit_id,
                    code=error_code or "PERSISTENCE_FAILED",
                    reason=payload.get("error") or "Persistence layer rejected visit write.",
                    retryable=True,
                )

        if transition.spoken_text:
            if transition.is_urgent or transition.interrupt_speech:
                await orchestrator.speak_urgent(
                    transition.spoken_text, language=transition.spoken_language
                )
            else:
                await orchestrator.speak_direct(
                    transition.spoken_text, language=transition.spoken_language
                )
            if transition.current_state == ConversationState.READ_BACK_CONFIRMATION:
                self.sm.on_read_back_completed()


class SessionRegistry:
    """In-memory active session registry linking REST control plane & live WS pipelines."""

    def __init__(self) -> None:
        self._meta: dict[str, dict[str, Any]] = {}
        self._pipelines: dict[str, HealthcareSessionPipeline] = {}

    def create_session(
        self,
        *,
        session_id: str,
        language: str,
        beneficiary_id: str | None,
        worker_id: str,
        created_at: str,
    ) -> HealthcareSessionPipeline:
        self._meta[session_id] = {
            "session_id": session_id,
            "language": language,
            "beneficiary_id": beneficiary_id,
            "worker_id": worker_id,
            "created_at": created_at,
        }
        pipeline = HealthcareSessionPipeline(
            session_id=session_id,
            worker_id=worker_id,
            language=language if language != "indic-auto" else get_settings().default_language,
            beneficiary_id=beneficiary_id,
        )
        self._pipelines[session_id] = pipeline
        return pipeline

    def get_metadata(self, session_id: str) -> dict[str, Any] | None:
        return self._meta.get(session_id)

    def get_or_create_pipeline(
        self,
        session_id: str,
        *,
        language: str = "hi-IN",
        beneficiary_id: str | None = None,
        worker_id: str = "ASHA-DEMO-01",
    ) -> HealthcareSessionPipeline:
        if session_id in self._pipelines:
            return self._pipelines[session_id]
        meta = self._meta.get(session_id, {})
        return self.create_session(
            session_id=session_id,
            language=meta.get("language", language),
            beneficiary_id=meta.get("beneficiary_id", beneficiary_id),
            worker_id=meta.get("worker_id", worker_id),
            created_at=meta.get("created_at", utc_now_iso()),
        )

    def get_pipeline(self, session_id: str) -> HealthcareSessionPipeline | None:
        return self._pipelines.get(session_id)


session_registry = SessionRegistry()
