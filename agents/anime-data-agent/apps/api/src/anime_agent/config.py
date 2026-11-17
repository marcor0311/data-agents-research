"""Paths can be configured without depending on sibling repositories."""
import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def project_path(variable: str, default: str) -> Path:
    value = Path(os.environ.get(variable, default)).expanduser()
    return value.resolve() if value.is_absolute() else (ROOT / value).resolve()


@dataclass(frozen=True)
class Settings:
    dataset_path: Path
    conversation_db: Path
    agent_mode: str = 'rules'
    openai_model: str = 'gpt-5-mini'
    openai_api_key: str | None = field(default=None, repr=False)
    model_max_requests: int = 4
    model_max_tool_calls: int = 6
    model_max_output_tokens: int = 2048
    model_turn_timeout: int = 60
    model_max_input_chars: int = 60000

    def __post_init__(self):
        if self.agent_mode not in ('rules', 'openai'):
            raise ValueError('ANIME_AGENT_MODE debe ser rules u openai.')
        limits = [(self.model_max_requests, 1, 8), (self.model_max_tool_calls, 1, 12),
                  (self.model_max_output_tokens, 512, 4096), (self.model_turn_timeout, 10, 75),
                  (self.model_max_input_chars, 10000, 120000)]
        if any(not low <= value <= high for value, low, high in limits):
            raise ValueError('Límites del modelo fuera del rango permitido; revisá .env.example.')

    @classmethod
    def from_environment(cls):
        return cls(
            dataset_path=project_path("ANIME_DATASET_PATH", "data/processed/current.json"),
            conversation_db=project_path("ANIME_CONVERSATION_DB", "data/conversations.sqlite3"),
            agent_mode=os.environ.get('ANIME_AGENT_MODE', 'rules'),
            openai_model=os.environ.get('OPENAI_MODEL', 'gpt-5-mini'),
            openai_api_key=os.environ.get('OPENAI_API_KEY') or None,
            model_max_requests=int(os.environ.get('ANIME_MODEL_MAX_REQUESTS', '4')),
            model_max_tool_calls=int(os.environ.get('ANIME_MODEL_MAX_TOOL_CALLS', '6')),
            model_max_output_tokens=int(os.environ.get('ANIME_MODEL_MAX_OUTPUT_TOKENS', '2048')),
            model_turn_timeout=int(os.environ.get('ANIME_MODEL_TURN_TIMEOUT', '60')),
            model_max_input_chars=int(os.environ.get('ANIME_MODEL_MAX_INPUT_CHARS', '60000')),
        )
