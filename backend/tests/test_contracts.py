"""Contract validation tests for Agent 1 shared v1 JSON Schemas, OpenAPI 3.1, and mock events.

Validates:
- Valid JSON syntax and Draft 2020-12 / OpenAPI 3.1.0 metadata across all shared-contracts/*
- Zero secret leakage or raw provider-specific payload exposure
- All synthetic examples in visit.schema.json and danger-alert.schema.json (plus negative cases)
- Disjoint oneOf discrimination across all 8 client->server and 23 server->client events
- Every line of shared-contracts/mock-events.jsonl against voice-events.schema.json,
  and embedded visit/draft/alert payloads against visit.schema.json and danger-alert.schema.json
- OpenAPI 3.1.0 paths, error codes, and live FastAPI Milestone 1 REST endpoint parity
"""

from __future__ import annotations

import base64
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_DIR = REPO_ROOT / "shared-contracts"

VISIT_SCHEMA_PATH = CONTRACTS_DIR / "visit.schema.json"
DANGER_ALERT_SCHEMA_PATH = CONTRACTS_DIR / "danger-alert.schema.json"
VOICE_EVENTS_SCHEMA_PATH = CONTRACTS_DIR / "voice-events.schema.json"
OPENAPI_PATH = CONTRACTS_DIR / "openapi.json"
MOCK_EVENTS_PATH = CONTRACTS_DIR / "mock-events.jsonl"

EXPECTED_CLIENT_EVENT_TYPES = {
    "audio_chunk",
    "barge_in",
    "text_input",
    "set_language",
    "confirm_visit",
    "persistence_ack",
    "ping",
    "end_session",
}

EXPECTED_SERVER_EVENT_TYPES = {
    "session_ready",
    "session_state",
    "speech_start",
    "speech_end",
    "partial_transcript",
    "final_transcript",
    "assistant_response",
    "tts_start",
    "tts_audio_chunk",
    "tts_complete",
    "barge_in",
    "tts_cancelled",
    "visit_draft_updated",
    "clarification_required",
    "read_back_started",
    "correction_applied",
    "visit_confirmed",
    "persistence_requested",
    "visit_committed",
    "persistence_rejected",
    "danger_alert",
    "error",
    "pong",
}

EXPECTED_ERROR_CODES = {
    "MISSING_CREDENTIALS",
    "INVALID_JSON",
    "STT_STREAM_ERROR",
    "TTS_STREAM_ERROR",
    "TURN_PROCESSING_ERROR",
    "BENEFICIARY_NOT_FOUND",
    "PERSISTENCE_FAILED",
}


# ---------------------------------------------------------------------------
# Minimal, strict Draft 2020-12 JSON Schema validator (zero extra dependencies)
# ---------------------------------------------------------------------------


def _resolve_ref(ref: str, root_schema: dict[str, Any]) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise AssertionError(f"Unsupported external $ref in self-contained test: {ref}")
    node: Any = root_schema
    for part in ref[2:].split("/"):
        node = node[part]
    assert isinstance(node, dict), f"$ref {ref} did not resolve to an object schema"
    return node


def _check_type(value: Any, expected: str) -> bool:
    if expected == "null":
        return value is None
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "string":
        return isinstance(value, str)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    raise AssertionError(f"Unsupported JSON Schema type: {expected}")


def _check_format(value: str, fmt: str) -> bool:
    if fmt == "date":
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            return False
        try:
            date.fromisoformat(value)
            return True
        except ValueError:
            return False
    if fmt == "date-time":
        if "T" not in value:
            return False
        normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            dt = datetime.fromisoformat(normalized)
            return dt.tzinfo is not None
        except ValueError:
            return False
    return True


def validate_instance(
    instance: Any,
    schema: dict[str, Any],
    root_schema: dict[str, Any] | None = None,
    path: str = "$",
) -> list[str]:
    """Validate `instance` against Draft 2020-12 `schema`, returning a list of errors."""
    root = root_schema if root_schema is not None else schema
    if "$ref" in schema:
        resolved = _resolve_ref(schema["$ref"], root)
        return validate_instance(instance, resolved, root, path)

    errors: list[str] = []

    if "oneOf" in schema:
        matches = 0
        branch_errors: list[list[str]] = []
        for idx, sub in enumerate(schema["oneOf"]):
            errs = validate_instance(instance, sub, root, path)
            if not errs:
                matches += 1
            else:
                branch_errors.append([f"[branch {idx}] {e}" for e in errs[:2]])
        if matches != 1:
            errors.append(
                f"{path}: expected exactly 1 matching oneOf branch, got {matches}"
            )
        return errors

    if "anyOf" in schema:
        if not any(not validate_instance(instance, sub, root, path) for sub in schema["anyOf"]):
            errors.append(f"{path}: value did not match anyOf")
        return errors

    if "allOf" in schema:
        for sub in schema["allOf"]:
            errors.extend(validate_instance(instance, sub, root, path))

    if "const" in schema:
        expected_const = schema["const"]
        if instance != expected_const or type(instance) is not type(expected_const):
            errors.append(f"{path}: expected const {expected_const!r}, got {instance!r}")

    if "enum" in schema:
        if not any(
            instance == opt and type(instance) is type(opt) for opt in schema["enum"]
        ):
            errors.append(f"{path}: {instance!r} not in enum {schema['enum']!r}")

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_check_type(instance, t) for t in types):
            errors.append(
                f"{path}: expected type {types}, got {type(instance).__name__} ({instance!r})"
            )
            return errors

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: string longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: string {instance!r} does not match pattern {schema['pattern']!r}")
        if "format" in schema and not _check_format(instance, schema["format"]):
            errors.append(f"{path}: string {instance!r} invalid for format {schema['format']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: array length {len(instance)} < minItems {schema['minItems']}")
        if "items" in schema:
            for idx, item in enumerate(instance):
                errors.extend(
                    validate_instance(item, schema["items"], root, f"{path}[{idx}]")
                )

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        for req_key in schema.get("required", []):
            if req_key not in instance:
                errors.append(f"{path}: missing required property {req_key!r}")
        if schema.get("additionalProperties") is False:
            unknown = set(instance.keys()) - set(props.keys())
            if unknown:
                errors.append(f"{path}: unexpected additional properties {sorted(unknown)}")
        for key, val in instance.items():
            if key in props:
                errors.extend(validate_instance(val, props[key], root, f"{path}.{key}"))

    return errors


def assert_valid(instance: Any, schema: dict[str, Any], root: dict[str, Any] | None = None) -> None:
    errors = validate_instance(instance, schema, root)
    assert not errors, "Schema validation failed:\n  - " + "\n  - ".join(errors)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def visit_schema() -> dict[str, Any]:
    return json.loads(VISIT_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def danger_alert_schema() -> dict[str, Any]:
    return json.loads(DANGER_ALERT_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def voice_events_schema() -> dict[str, Any]:
    return json.loads(VOICE_EVENTS_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def openapi_spec() -> dict[str, Any]:
    return json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_contract_files_exist_and_have_no_secrets_or_provider_leakage() -> None:
    forbidden_substrings = [
        "X-API-Key-ID",
        "x-api-key-id",
        "api.vachana.ai",
        "GNANI_API_KEY=",
        "GEMINI_API_KEY=",
        "GROQ_API_KEY=",
        "SUPABASE_SERVICE_ROLE_KEY=",
    ]
    for path in (
        VISIT_SCHEMA_PATH,
        DANGER_ALERT_SCHEMA_PATH,
        VOICE_EVENTS_SCHEMA_PATH,
        OPENAPI_PATH,
        MOCK_EVENTS_PATH,
    ):
        assert path.exists(), f"Missing contract file: {path}"
        raw = path.read_text(encoding="utf-8")
        for forbidden in forbidden_substrings:
            assert forbidden not in raw, f"Forbidden provider/secret token {forbidden!r} found in {path.name}"


def test_schema_draft_and_version_headers(
    visit_schema: dict[str, Any],
    danger_alert_schema: dict[str, Any],
    voice_events_schema: dict[str, Any],
    openapi_spec: dict[str, Any],
) -> None:
    for schema in (visit_schema, danger_alert_schema, voice_events_schema):
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert "/v1/" in schema["$id"]

    assert openapi_spec["openapi"] == "3.1.0"
    assert openapi_spec["x-contract-version"] == "v1"


def test_visit_schema_examples_and_negative_cases(visit_schema: dict[str, Any]) -> None:
    examples = visit_schema.get("examples", [])
    assert len(examples) >= 2, "Expected routine ANC and danger-flagged Newborn examples"

    visit_types_seen = set()
    danger_flags_seen = set()
    for ex in examples:
        assert_valid(ex, visit_schema)
        assert ex["synthetic"] is True
        visit_types_seen.add(ex["visit_type"])
        danger_flags_seen.add(ex["danger_sign_flagged"])

    assert "ANC" in visit_types_seen
    assert "Newborn" in visit_types_seen
    assert danger_flags_seen == {False, True}

    # Negative: bad beneficiary ID pattern
    bad_ben = dict(examples[0], beneficiary_id="INVALID-123")
    assert validate_instance(bad_ben, visit_schema)

    # Negative: invalid visit_type enum
    bad_type = dict(examples[0], visit_type="Surgery")
    assert validate_instance(bad_type, visit_schema)

    # Negative: wrong timezone
    bad_tz = dict(examples[0], timezone="UTC")
    assert validate_instance(bad_tz, visit_schema)

    # Negative: unexpected additional field
    bad_extra = dict(examples[0], provider_raw_blob={})
    assert validate_instance(bad_extra, visit_schema)


def test_danger_alert_schema_examples_and_negative_cases(
    danger_alert_schema: dict[str, Any],
) -> None:
    examples = danger_alert_schema.get("examples", [])
    assert len(examples) >= 2
    for ex in examples:
        assert_valid(ex, danger_alert_schema)
        assert ex["danger_sign_flagged"] is True
        assert ex["priority"] == "urgent"

    # Negative: danger_sign_flagged must be const true
    bad_flag = dict(examples[0], danger_sign_flagged=False)
    assert validate_instance(bad_flag, danger_alert_schema)

    # Negative: priority must be const urgent
    bad_priority = dict(examples[0], priority="normal")
    assert validate_instance(bad_priority, danger_alert_schema)

    # Negative: missing source_guideline_ref
    missing_ref = dict(examples[0])
    del missing_ref["source_guideline_ref"]
    assert validate_instance(missing_ref, danger_alert_schema)


def test_voice_events_schema_covers_all_client_and_server_events(
    voice_events_schema: dict[str, Any],
) -> None:
    # Verify binary audio framing metadata
    framing = voice_events_schema["x-binary-audio-framing"]
    assert framing["encoding"] == "pcm_s16le"
    assert framing["sample_rate"] == 16000
    assert framing["channels"] == 1
    assert framing["frame_samples"] == 512
    assert framing["frame_bytes"] == 1024
    assert framing["frame_ms"] == 32

    defs = voice_events_schema["$defs"]
    client_types = set()
    for ref_obj in defs["ClientEvent"]["oneOf"]:
        sub = _resolve_ref(ref_obj["$ref"], voice_events_schema)
        client_types.add(sub["properties"]["type"]["const"])

    server_types = set()
    for ref_obj in defs["ServerEvent"]["oneOf"]:
        sub = _resolve_ref(ref_obj["$ref"], voice_events_schema)
        server_types.add(sub["properties"]["type"]["const"])

    assert client_types == EXPECTED_CLIENT_EVENT_TYPES
    assert server_types == EXPECTED_SERVER_EVENT_TYPES

    # Verify client barge_in and server barge_in are strictly disjoint under root oneOf
    client_barge_in = {"schema_version": "v1", "type": "barge_in", "reason": "user_tap"}
    server_barge_in = {
        "schema_version": "v1",
        "type": "barge_in",
        "session_id": "sess_demo_1",
        "timestamp": "2026-11-21T09:15:09Z",
        "cancelled_turn_id": 1,
        "new_turn_id": 2,
        "trigger": "vad",
    }
    assert_valid(client_barge_in, voice_events_schema)
    assert_valid(server_barge_in, voice_events_schema)

    # Verify all remaining client->server event samples pass root oneOf
    sample_client_events = [
        {"schema_version": "v1", "type": "audio_chunk", "audio_base64": "AAAA", "seq": 1},
        {"schema_version": "v1", "type": "text_input", "text": "Weight 2.8 kilo hai"},
        {"schema_version": "v1", "type": "set_language", "language": "kn-IN"},
        {
            "schema_version": "v1",
            "type": "confirm_visit",
            "visit_id": "vis_demo_1",
            "confirmed": True,
            "confirmation_method": "voice",
        },
        {
            "schema_version": "v1",
            "type": "persistence_ack",
            "visit_id": "vis_demo_1",
            "correlation_id": "corr_1",
            "accepted": True,
            "persistence_record_id": "supa_1",
            "committed_at": "2026-11-21T09:15:18Z",
        },
        {"schema_version": "v1", "type": "ping", "client_timestamp": "2026-11-21T09:15:00Z"},
        {"schema_version": "v1", "type": "end_session", "reason": "completed"},
    ]
    for ev in sample_client_events:
        assert_valid(ev, voice_events_schema)

    # Verify error and pong and persistence_rejected server events
    sample_server_events = [
        {
            "schema_version": "v1",
            "type": "error",
            "session_id": "sess_demo_1",
            "code": "MISSING_CREDENTIALS",
            "message": "Missing required environment variables: GNANI_API_KEY",
            "retryable": False,
        },
        {
            "schema_version": "v1",
            "type": "pong",
            "session_id": "sess_demo_1",
            "timestamp": "2026-11-21T09:15:00Z",
        },
        {
            "schema_version": "v1",
            "type": "persistence_rejected",
            "session_id": "sess_demo_1",
            "timestamp": "2026-11-21T09:15:19Z",
            "visit_id": "vis_demo_1",
            "correlation_id": "corr_1",
            "code": "PERSISTENCE_FAILED",
            "reason": "Transient database timeout",
            "retryable": True,
        },
    ]
    for ev in sample_server_events:
        assert_valid(ev, voice_events_schema)


def test_mock_events_jsonl_validates_end_to_end(
    voice_events_schema: dict[str, Any],
    visit_schema: dict[str, Any],
    danger_alert_schema: dict[str, Any],
) -> None:
    lines = [
        line.strip()
        for line in MOCK_EVENTS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(lines) >= 25

    seen_types: list[str] = []
    for line_no, raw_line in enumerate(lines, start=1):
        event = json.loads(raw_line)
        errors = validate_instance(event, voice_events_schema)
        assert not errors, f"Line {line_no} ({event.get('type')}) failed validation: {errors}"
        ev_type = event["type"]
        seen_types.append(ev_type)

        # Validate embedded VisitRecord payloads directly against standalone visit.schema.json
        if "draft" in event:
            assert_valid(event["draft"], visit_schema)
        if "visit" in event:
            assert_valid(event["visit"], visit_schema)

        # Validate embedded DangerAlert payloads directly against standalone danger-alert.schema.json
        if "alert" in event:
            assert_valid(event["alert"], danger_alert_schema)
        if "danger_alerts" in event:
            for alert in event["danger_alerts"]:
                assert_valid(alert, danger_alert_schema)

        # Validate base64 PCM_S16LE alignment on TTS chunks
        if ev_type == "tts_audio_chunk":
            pcm = base64.b64decode(event["audio_base64"])
            assert len(pcm) > 0 and len(pcm) % 2 == 0

    required_lifecycle = {
        "session_ready",
        "partial_transcript",
        "final_transcript",
        "clarification_required",
        "visit_draft_updated",
        "read_back_started",
        "assistant_response",
        "tts_start",
        "tts_audio_chunk",
        "tts_complete",
        "barge_in",
        "tts_cancelled",
        "correction_applied",
        "danger_alert",
        "visit_confirmed",
        "persistence_requested",
        "persistence_ack",
        "visit_committed",
    }
    missing = required_lifecycle - set(seen_types)
    assert not missing, f"mock-events.jsonl missing lifecycle events: {sorted(missing)}"

    # Safety/lifecycle ordering invariants
    assert seen_types.index("danger_alert") < seen_types.index("visit_confirmed")
    assert seen_types.index("read_back_started") < seen_types.index("visit_confirmed")
    assert seen_types.index("visit_confirmed") < seen_types.index("visit_committed")


def test_openapi_spec_structure_paths_and_examples(openapi_spec: dict[str, Any]) -> None:
    expected_paths = {
        "/health": {"get"},
        "/api/v1/sessions": {"post"},
        "/api/v1/beneficiaries": {"get"},
        "/api/v1/sessions/{session_id}/visit": {"get"},
        "/api/v1/sessions/{session_id}/persistence-ack": {"post"},
        "/api/v1/danger-signs/check": {"post"},
    }
    paths = openapi_spec["paths"]
    for path, methods in expected_paths.items():
        assert path in paths, f"OpenAPI missing path {path}"
        for method in methods:
            assert method in paths[path], f"OpenAPI missing {method.upper()} {path}"

    error_codes = set(openapi_spec["components"]["schemas"]["ErrorCode"]["enum"])
    assert EXPECTED_ERROR_CODES.issubset(error_codes)

    # Validate every inline OpenAPI request/response example against its referenced component schema
    for path, methods in paths.items():
        for method, op in methods.items():
            req_content = op.get("requestBody", {}).get("content", {}).get("application/json", {})
            if "example" in req_content and "schema" in req_content:
                assert_valid(req_content["example"], req_content["schema"], openapi_spec)
            for status_code, resp in op.get("responses", {}).items():
                resp_content = resp.get("content", {}).get("application/json", {})
                if "example" in resp_content and "schema" in resp_content:
                    assert_valid(resp_content["example"], resp_content["schema"], openapi_spec)


def test_live_milestone1_rest_endpoints_match_openapi_contract(
    openapi_spec: dict[str, Any],
) -> None:
    """Verify existing FastAPI REST endpoints strictly conform to shared-contracts/openapi.json."""
    client = TestClient(create_app())
    schemas = openapi_spec["components"]["schemas"]

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert_valid(health_resp.json(), schemas["HealthResponse"], openapi_spec)

    ben_resp = client.get("/api/v1/beneficiaries")
    assert ben_resp.status_code == 200
    assert_valid(ben_resp.json(), schemas["BeneficiaryListResponse"], openapi_spec)

    sess_resp = client.post(
        "/api/v1/sessions",
        json={"language": "hi-IN", "beneficiary_id": "BEN-1042", "worker_id": "ASHA-DEMO-01"},
    )
    assert sess_resp.status_code == 200
    assert_valid(sess_resp.json(), schemas["CreateSessionResponse"], openapi_spec)
