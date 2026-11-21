"""Environment-backed configuration loader reading from repository root `.env`."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve repository root `.env` regardless of current working directory
REPO_ROOT = Path(__file__).resolve().parents[3]
ROOT_ENV_FILE = REPO_ROOT / ".env"

DEFAULT_GNANI_STT_WS_URL = "wss://api.vachana.ai/stt/v3/stream"
DEFAULT_GNANI_TTS_WS_URL = "wss://api.vachana.ai/api/v1/tts"

# Focused ASHA clinical & measurement keyterms for Gnani Prisma v3.0 biasing (<= 200 items).
# Beneficiary names & IDs are injected dynamically ONLY for the active session context
# so prompts are never overloaded with irrelevant vocabulary.
ASHA_CORE_KEYWORDS: tuple[str, ...] = (
    "ASHA",
    "ANC",
    "ANC checkup",
    "PNC",
    "PNC visit",
    "HBNC",
    "Newborn",
    "Immunisation",
    "PHC",
    "Primary Health Centre",
    "TT injection",
    "Td injection",
    "IFA",
    "IFA goli",
    "calcium goli",
    "BCG",
    "OPV",
    "Pentavalent",
    "Measles",
    "MR vaccine",
    "Rotavirus",
    "PCV",
    "IPV",
    "kilo",
    "kilogram",
    "kilograms",
    "gram",
    "grams",
    "bleeding",
    "convulsions",
    "fits",
    "daura",
    "jhatke",
    "bukhar",
    "tez bukhar",
    "chest indrawing",
    "fast breathing",
    "lethargy",
    "umbilical pus",
    "naal",
    "blurred vision",
    "severe headache",
    "weight",
    "vajan",
    "wajan",
    "next visit",
)

# Backward-compatible alias
ASHA_DOMAIN_KEYWORDS: tuple[str, ...] = ASHA_CORE_KEYWORDS

DEFAULT_ASHA_STT_TOPIC = (
    "ASHA community health worker home visit notes including maternal or newborn weight "
    "in kilograms or grams, vaccinations, danger signs, and follow-up visit dates."
)


def build_contextual_stt_options(
    *,
    beneficiary_name: str | None = None,
    beneficiary_id: str | None = None,
    extra_speaker_names: list[str] | None = None,
    previous_text: str | None = None,
) -> dict[str, Any]:
    """Build focused, non-overloaded Prisma v3.0 context options for a session."""
    keywords = list(ASHA_CORE_KEYWORDS)
    speaker_names: list[str] = []

    def _add_name(name: str | None) -> None:
        if not name:
            return
        cleaned = name.strip()
        if cleaned and cleaned not in speaker_names and len(speaker_names) < 4:
            speaker_names.append(cleaned)
        if cleaned and cleaned not in keywords and len(keywords) < 200:
            keywords.append(cleaned)

    _add_name(beneficiary_name)
    if beneficiary_name and beneficiary_name.lower().startswith("baby of "):
        _add_name(beneficiary_name[8:].strip())
    if extra_speaker_names:
        for nm in extra_speaker_names:
            _add_name(nm)

    if beneficiary_id and beneficiary_id.strip():
        bid = beneficiary_id.strip()
        if bid not in keywords and len(keywords) < 200:
            keywords.append(bid)

    return {
        "keywords": keywords[:200],
        "speaker_names": speaker_names[:4],
        "previous_text": (previous_text or "").strip()[-600:],
        "topic": DEFAULT_ASHA_STT_TOPIC,
    }


class Settings(BaseSettings):
    """Application settings loaded from root `.env` and environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(ROOT_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Gnani Speech Services
    gnani_api_key: SecretStr = Field(default=SecretStr(""), alias="GNANI_API_KEY")
    gnani_stt_model: str = Field(default="prisma-v3.0", alias="GNANI_STT_MODEL")
    gnani_tts_model: str = Field(default="timbre-v3.0", alias="GNANI_TTS_MODEL")
    gnani_stt_ws_url: str = Field(default="", alias="GNANI_STT_WS_URL")
    gnani_tts_ws_url: str = Field(default="", alias="GNANI_TTS_WS_URL")
    gnani_tts_voice: str = Field(default="Shivani", alias="GNANI_TTS_VOICE")
    gnani_stt_format: str = Field(default="transcribe", alias="GNANI_STT_FORMAT")
    gnani_stt_enable_partials: bool = Field(default=True, alias="GNANI_STT_ENABLE_PARTIALS")
    gnani_stt_secondary_enabled: bool = Field(
        default=True, alias="GNANI_STT_SECONDARY_ENABLED"
    )
    gnani_stt_secondary_format: str = Field(
        default="codemix", alias="GNANI_STT_SECONDARY_FORMAT"
    )
    mandatory_numeric_confirmation: bool = Field(
        default=False, alias="MANDATORY_NUMERIC_CONFIRMATION"
    )

    # LLM Configuration
    llm_provider: str = Field(default="gemini", alias="LLM_PROVIDER")
    llm_model: str = Field(default="", alias="LLM_MODEL")
    gemini_api_key: SecretStr = Field(default=SecretStr(""), alias="GEMINI_API_KEY")
    llm_fallback_provider: str = Field(default="groq", alias="LLM_FALLBACK_PROVIDER")
    llm_fallback_model: str = Field(default="llama-3.1-8b-instant", alias="LLM_FALLBACK_MODEL")
    groq_api_key: SecretStr = Field(default=SecretStr(""), alias="GROQ_API_KEY")
    openrouter_api_key: SecretStr = Field(default=SecretStr(""), alias="OPENROUTER_API_KEY")

    # Server
    app_env: str = Field(default="development", alias="APP_ENV")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_redact_phi: bool = Field(default=True, alias="LOG_REDACT_PHI")

    # Voice & Audio Pipeline
    default_language: str = Field(default="hi-IN", alias="DEFAULT_LANGUAGE")
    supported_languages: str = Field(
        default="hi-IN,kn-IN,ta-IN,en-IN", alias="SUPPORTED_LANGUAGES"
    )
    audio_sample_rate: int = Field(default=16000, alias="AUDIO_SAMPLE_RATE")
    vad_threshold: float = Field(default=0.6, alias="VAD_THRESHOLD")
    barge_in_vad_threshold: float = Field(default=0.70, alias="BARGE_IN_VAD_THRESHOLD")
    barge_in_min_speech_ms: int = Field(default=192, alias="BARGE_IN_MIN_SPEECH_MS")
    endpoint_silence_ms: int = Field(default=1350, alias="ENDPOINT_SILENCE_MS")

    # Safety & Synthetic Guardrails
    synthetic_data_only: bool = Field(default=True, alias="SYNTHETIC_DATA_ONLY")
    danger_sign_partial_matching: bool = Field(
        default=True, alias="DANGER_SIGN_PARTIAL_MATCHING"
    )

    # Optional Persistence (Agent 3 owns Supabase schema; we only read optional URL if syncing)
    supabase_url: str = Field(default="", alias="SUPABASE_URL")
    supabase_service_role_key: SecretStr = Field(
        default=SecretStr(""), alias="SUPABASE_SERVICE_ROLE_KEY"
    )

    @field_validator("llm_provider", "llm_fallback_provider", mode="before")
    @classmethod
    def _clean_provider(cls, value: object) -> str:
        if not isinstance(value, str):
            return "gemini"
        # Strip inline comments if dotenv did not strip them
        cleaned = value.split("#", 1)[0].strip().lower()
        return cleaned or "gemini"

    @field_validator("llm_model", "gnani_stt_model", "gnani_tts_model", mode="before")
    @classmethod
    def _clean_model(cls, value: object) -> str:
        if not isinstance(value, str):
            return ""
        return value.split("#", 1)[0].strip()

    @property
    def effective_stt_ws_url(self) -> str:
        return self.gnani_stt_ws_url.strip() or DEFAULT_GNANI_STT_WS_URL

    @property
    def effective_tts_ws_url(self) -> str:
        return self.gnani_tts_ws_url.strip() or DEFAULT_GNANI_TTS_WS_URL

    @property
    def effective_llm_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        if self.llm_provider == "gemini":
            return "gemini-3.1-flash-lite"
        if self.llm_provider == "groq":
            return "llama-3.1-8b-instant"
        return "gemini-3.1-flash-lite"

    @property
    def supported_language_list(self) -> list[str]:
        return [
            item.strip()
            for item in self.supported_languages.split(",")
            if item.strip()
        ]

    @property
    def prisma_language_candidates(self) -> list[str]:
        """Gnani Prisma v3.0 accepts 2-4 BCP-47 hints when lang_code='indic-auto'."""
        langs = self.supported_language_list
        if len(langs) < 2:
            return ["hi-IN", "en-IN"]
        return langs[:4]

    def validate_live_credentials(self) -> list[str]:
        """Return names of missing required env vars for live voice operation (never values)."""
        missing: list[str] = []
        if not self.gnani_api_key.get_secret_value().strip():
            missing.append("GNANI_API_KEY")
        if self.llm_provider == "gemini" and not self.gemini_api_key.get_secret_value().strip():
            missing.append("GEMINI_API_KEY")
        elif self.llm_provider == "groq" and not self.groq_api_key.get_secret_value().strip():
            missing.append("GROQ_API_KEY")
        return missing


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached singleton settings loader."""
    return Settings()

