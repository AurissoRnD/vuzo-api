from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ── Shared ──────────────────────────────────────────────────

class TransactionType(str, Enum):
    topup = "topup"
    usage = "usage"
    refund = "refund"


# ── Chat Completions (OpenAI-compatible) ────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str | list | None = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[str | list[str]] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None


class UsageInfo(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: UsageInfo


# ── Normalized usage result from providers ──────────────────

class ProviderUsageResult(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    provider_response: dict = {}


# ── API Key management ──────────────────────────────────────

class APIKeyCreateRequest(BaseModel):
    name: str = "Default"


class APIKeyCreateResponse(BaseModel):
    id: str
    name: str
    key: str = Field(description="Full API key — shown only once")
    key_prefix: str
    created_at: datetime


class APIKeyListItem(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    rate_limit_rpm: int
    created_at: datetime
    last_used_at: Optional[datetime] = None


# ── Billing ─────────────────────────────────────────────────

class BalanceResponse(BaseModel):
    user_id: str
    balance: float


class TopUpRequest(BaseModel):
    amount: float = Field(gt=0, description="Amount in USD to add")


class TopUpResponse(BaseModel):
    user_id: str
    amount: float
    new_balance: float
    transaction_id: str


class TransactionItem(BaseModel):
    id: str
    amount: float
    type: TransactionType
    description: str
    created_at: datetime


# ── Usage ───────────────────────────────────────────────────

class UsageLogItem(BaseModel):
    id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    provider_cost: float
    vuzo_cost: float
    response_time_ms: int
    created_at: datetime


class UsageSummary(BaseModel):
    total_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    total_provider_cost: float
    total_vuzo_cost: float


# ── Models listing ──────────────────────────────────────────

class ModelPricingItem(BaseModel):
    provider: str
    model_name: str
    input_price_per_million: float
    output_price_per_million: float
    vuzo_input_price_per_million: float
    vuzo_output_price_per_million: float
    vuzo_markup_percent: float


# ── Auth context attached to requests ───────────────────────

class AuthContext(BaseModel):
    user_id: str
    api_key_id: str
    rate_limit_rpm: int
