"""Shared typed contracts for HTTP, conversation and future MCP."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Filters(Model):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    formats: list[str] = Field(default_factory=list, max_length=10)
    genres: list[str] = Field(default_factory=list, max_length=10)
    genre_mode: Literal['all', 'any'] | None = None
    studio: str | None = Field(default=None, min_length=1, max_length=200)
    year_from: int | None = Field(default=None, ge=1900, le=2200)
    year_to: int | None = Field(default=None, ge=1900, le=2200)
    statuses: list[str] = Field(default_factory=list, max_length=3)
    min_score: float | None = Field(default=None, gt=0, le=10)
    min_votes: int | None = Field(default=None, ge=0)
    max_episodes: int | None = Field(default=None, ge=1)

    @model_validator(mode='after')
    def coherent(self):
        if self.year_from is not None and self.year_to is not None and self.year_from > self.year_to:
            raise ValueError('year_from must not exceed year_to')
        if len(self.genres) > 1 and self.genre_mode is None:
            raise ValueError('Specify genre_mode=all or any for multiple genres')
        return self


class Query(Model):
    kind: Literal['search', 'rank', 'detail', 'compare', 'aggregate'] = 'rank'
    filters: Filters = Field(default_factory=Filters)
    order_by: Literal['score', 'popularity', 'scored_by', 'title', 'start_year', 'episodes', 'duration_seconds', 'rank'] = 'score'
    direction: Literal['asc', 'desc'] | None = None
    limit: int = Field(default=10, ge=1, le=100)
    ids: list[int] = Field(default_factory=list, max_length=2)
    group_by: Literal['year', 'genre', 'studio'] = 'year'

    @model_validator(mode='after')
    def cardinality(self):
        if any(x <= 0 for x in self.ids) or len(self.ids) != len(set(self.ids)):
            raise ValueError('IDs must be positive and distinct')
        expected = {'detail': 1, 'compare': 2}.get(self.kind)
        if expected is not None and len(self.ids) != expected:
            raise ValueError(f'{self.kind} requires {expected} IDs')
        if expected is None and self.ids:
            raise ValueError('IDs only apply to detail or compare')
        return self


class Result(Model):
    contract_version: Literal['1.0'] = '1.0'
    status: Literal['result', 'empty']
    kind: str
    applied_query: Query
    total: int
    matched_total: int
    omitted_missing_metric: int = 0
    rows: list[dict] = Field(default_factory=list)
    groups: list[dict] = Field(default_factory=list)
    evidence: dict
    definitions: dict


class TurnRequest(Model):
    message: str = Field(min_length=1, max_length=2000)
    base_turn_id: str | None  # Required, explicit null for first turn.
    selected_ids: list[int] | None = Field(default=None, max_length=2)
    request_id: str | None = Field(default=None, min_length=1, max_length=100)


class ConversationState(Model):
    query: Query | None = None
    selected_ids: list[int] = Field(default_factory=list)
    load_id: str | None = None


class AgentResponse(Model):
    contract_version: Literal['1.0'] = '1.0'
    status: Literal['result', 'empty', 'clarification']
    explanation: str
    state: ConversationState
    result: Result | None = None
    visualization_action: Literal['create', 'update', 'retain']
    interpreter: Literal['bounded_rules', 'openai_tools'] = 'bounded_rules'
    model_run: dict | None = None


class SavedTurn(Model):
    id: str
    parent_turn_id: str | None
    created_at: str
    message: str
    response: AgentResponse


class ConversationHistory(Model):
    id: str
    created_at: str
    active_turn_id: str | None
    turns: list[SavedTurn]


class ActivateRequest(Model):
    turn_id: str
    expected_active_turn_id: str | None
