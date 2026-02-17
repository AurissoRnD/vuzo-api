# Vuzo API -- Internal Documentation

## 1. Architecture Overview

Vuzo is an LLM API proxy service. Users get a single Vuzo API key (`vz-sk_...`) and use it to call OpenAI, Anthropic (Claude), and Google (Gemini) models through Vuzo's unified endpoint. Vuzo forwards requests to the correct provider using its own master keys, tracks token usage from every response, and charges the user a marked-up price.

### Request Flow

```
User Application
    │
    │  POST /v1/chat/completions
    │  Authorization: Bearer vz-sk_...
    │  Body: { model: "gpt-4o", messages: [...] }
    ▼
┌──────────────────────────────────┐
│          Vuzo API Server         │
│                                  │
│  1. Rate limiter checks RPM      │
│  2. Auth middleware validates key │
│  3. Look up model pricing in DB  │
│  4. Check user credit balance    │
│  5. Route to correct provider    │
└────────────┬─────────────────────┘
             │
             │  Forward request with Vuzo's
             │  master API key for this provider
             ▼
┌──────────────────────────────────┐
│    LLM Provider (OpenAI, etc.)   │
│                                  │
│  Returns response + token usage  │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│       Vuzo Post-Processing       │
│                                  │
│  1. Extract token counts         │
│  2. Calculate cost (with markup) │
│  3. Deduct from user's credits   │
│  4. Log usage to database        │
│  5. Return response to user      │
└──────────────────────────────────┘
```

---

## 2. Project Structure

```
Vuzo-api/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, lifespan, middleware, router mounts
│   ├── config.py                   # Pydantic Settings (loads .env)
│   ├── dependencies.py             # Shared FastAPI dependencies
│   │
│   ├── middleware/
│   │   ├── auth.py                 # Vuzo API key validation (for LLM proxy)
│   │   ├── jwt_auth.py             # Supabase JWT validation (for dashboard)
│   │   └── rate_limiter.py         # In-memory sliding-window rate limiter
│   │
│   ├── models/
│   │   ├── schemas.py              # All Pydantic request/response models
│   │   └── database.py             # Supabase client + httpx async client pool
│   │
│   ├── routers/
│   │   ├── proxy.py                # POST /v1/chat/completions (the core LLM proxy)
│   │   ├── auth.py                 # POST /v1/auth/register, login, refresh
│   │   ├── api_keys.py             # CRUD for Vuzo API keys
│   │   ├── usage.py                # GET usage logs + summary
│   │   ├── billing.py              # GET balance, POST topup, GET transactions
│   │   ├── polar.py                # Polar checkout + webhook
│   │   └── models_list.py          # GET /v1/models (public pricing)
│   │
│   ├── services/
│   │   ├── providers/
│   │   │   ├── base.py             # Abstract BaseProvider interface
│   │   │   ├── openai.py           # OpenAI provider implementation
│   │   │   ├── anthropic.py        # Anthropic/Claude provider implementation
│   │   │   └── google.py           # Google/Gemini provider implementation
│   │   ├── billing_service.py      # Credit balance operations
│   │   ├── usage_service.py        # Usage log read/write
│   │   ├── key_service.py          # API key generation and management
│   │   └── pricing_service.py      # Model pricing lookup + provider key decryption
│   │
│   └── utils/
│       ├── crypto.py               # Key generation, SHA-256 hashing, Fernet encryption
│       └── pricing.py              # Cost calculation (Decimal math)
│
├── migrations/
│   ├── 001_initial_schema.sql      # All tables + seed pricing data
│   └── 002_add_supabase_auth_id.sql
│
├── frontend/                       # React + Vite + TypeScript dashboard SPA
├── docs/
│   └── INTERNALS.md                # This file
├── .env.example
├── requirements.txt
├── run.py                          # Uvicorn runner
└── README.md
```

---

## 3. Database Schema

All tables live in the `public` schema of Supabase (PostgreSQL).

### 3.1 `users`

Stores Vuzo user accounts. Linked to Supabase Auth via `supabase_auth_id`.

| Column             | Type         | Description                                    |
|--------------------|--------------|------------------------------------------------|
| `id`               | UUID (PK)    | Internal Vuzo user ID                          |
| `supabase_auth_id` | UUID (unique)| Supabase Auth UUID (`auth.users.id`)           |
| `email`            | TEXT (unique) | User's email                                   |
| `name`             | TEXT          | Display name                                   |
| `is_active`        | BOOLEAN       | Whether the account is enabled                 |
| `created_at`       | TIMESTAMPTZ   | Account creation timestamp                     |

### 3.2 `api_keys`

Vuzo API keys issued to users. The actual key is never stored -- only a SHA-256 hash and a lookup prefix.

| Column           | Type        | Description                                     |
|------------------|-------------|-------------------------------------------------|
| `id`             | UUID (PK)   | Key record ID                                   |
| `user_id`        | UUID (FK)   | References `users.id`                           |
| `key_prefix`     | TEXT         | First 8 chars of the key (for fast DB lookup)   |
| `key_hash`       | TEXT         | SHA-256 hash of the full key                    |
| `name`           | TEXT         | User-assigned label (e.g. "Production")         |
| `is_active`      | BOOLEAN      | False = revoked                                 |
| `rate_limit_rpm` | INTEGER      | Max requests per minute for this key            |
| `created_at`     | TIMESTAMPTZ  | When the key was created                        |
| `last_used_at`   | TIMESTAMPTZ  | Updated on every authenticated request          |

### 3.3 `credits`

One row per user. Stores the current USD credit balance.

| Column       | Type           | Description                    |
|--------------|----------------|--------------------------------|
| `id`         | UUID (PK)      | Row ID                         |
| `user_id`    | UUID (FK, unique) | References `users.id`       |
| `balance`    | NUMERIC(12,6)  | Current balance in USD         |
| `updated_at` | TIMESTAMPTZ    | Last balance change timestamp  |

### 3.4 `credit_transactions`

Audit log of every balance change: top-ups, usage deductions, refunds.

| Column        | Type             | Description                                      |
|---------------|------------------|--------------------------------------------------|
| `id`          | UUID (PK)        | Transaction ID                                   |
| `user_id`     | UUID (FK)        | References `users.id`                            |
| `amount`      | NUMERIC(12,6)    | Positive = top-up, negative = usage deduction    |
| `type`        | ENUM             | `topup`, `usage`, or `refund`                    |
| `description` | TEXT             | Human-readable note (e.g. "gpt-4o: 500in + 200out") |
| `created_at`  | TIMESTAMPTZ      | When the transaction occurred                    |

### 3.5 `model_pricing`

Defines the cost per model and Vuzo's markup percentage.

| Column                    | Type          | Description                                    |
|---------------------------|---------------|------------------------------------------------|
| `id`                      | UUID (PK)     | Row ID                                         |
| `provider`                | TEXT          | `openai`, `anthropic`, or `google`             |
| `model_name`              | TEXT (unique) | Exact model identifier (e.g. `gpt-4o`)         |
| `input_price_per_million`  | NUMERIC(10,4) | Provider's cost per 1M input tokens (USD)     |
| `output_price_per_million` | NUMERIC(10,4) | Provider's cost per 1M output tokens (USD)    |
| `vuzo_markup_percent`      | NUMERIC(5,2)  | Vuzo's markup (e.g. `20.00` = 20%)            |
| `is_active`               | BOOLEAN       | Whether the model is available                  |
| `updated_at`              | TIMESTAMPTZ   | Last pricing update                             |

### 3.6 `usage_logs`

One row per LLM request. The core of usage tracking and billing audit.

| Column            | Type          | Description                               |
|-------------------|---------------|-------------------------------------------|
| `id`              | UUID (PK)     | Log entry ID                              |
| `user_id`         | UUID (FK)     | Who made the request                      |
| `api_key_id`      | UUID (FK)     | Which key was used                        |
| `provider`        | TEXT          | `openai`, `anthropic`, or `google`        |
| `model`           | TEXT          | Model name used                           |
| `input_tokens`    | INTEGER       | Tokens in the prompt/input                |
| `output_tokens`   | INTEGER       | Tokens in the completion/output           |
| `total_tokens`    | INTEGER       | `input_tokens + output_tokens`            |
| `provider_cost`   | NUMERIC(12,6) | What the provider charged Vuzo (USD)      |
| `vuzo_cost`       | NUMERIC(12,6) | What Vuzo charged the user (USD)          |
| `response_time_ms`| INTEGER       | End-to-end latency in milliseconds        |
| `status_code`     | INTEGER       | HTTP status from the provider             |
| `created_at`      | TIMESTAMPTZ   | When the request was made                 |

### 3.7 `provider_keys`

Vuzo's own master API keys for each provider, encrypted at rest with Fernet.

| Column              | Type        | Description                               |
|---------------------|-------------|-------------------------------------------|
| `id`                | UUID (PK)   | Row ID                                    |
| `provider`          | TEXT (unique)| `openai`, `anthropic`, or `google`       |
| `api_key_encrypted` | TEXT        | Fernet-encrypted API key ciphertext       |
| `is_active`         | BOOLEAN     | Whether this provider is enabled          |
| `created_at`        | TIMESTAMPTZ | When the key was added                    |

---

## 4. Authentication Model

Vuzo uses **dual authentication**:

### 4.1 Vuzo API Key Auth (for LLM proxy)

Used by: `POST /v1/chat/completions`

```
Authorization: Bearer vz-sk_a1b2c3d4e5f6...
```

- Key format: `vz-sk_` prefix + 48 hex characters (generated by `secrets.token_hex(24)`)
- First 8 characters stored as `key_prefix` for fast DB lookup
- Full key is SHA-256 hashed and stored as `key_hash`
- On auth: look up by prefix, verify full hash, check `is_active` + user `is_active`
- Implementation: `app/middleware/auth.py` -> `validate_api_key()`

### 4.2 Supabase JWT Auth (for dashboard)

Used by: Dashboard API endpoints (api-keys, billing, usage)

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

- Supabase Auth handles sign-up/sign-in and issues JWTs
- Backend decodes the JWT, extracts `sub` (Supabase Auth user UUID)
- Looks up the Vuzo user by `supabase_auth_id` column
- Implementation: `app/middleware/jwt_auth.py` -> `validate_session()`

### 4.3 How the dual auth dependency works

The `get_current_user_id()` dependency in `app/dependencies.py` inspects the Bearer token:
- If it starts with `vz-` → validates as API key
- Otherwise → validates as Supabase JWT

This allows the same endpoints (api-keys, billing, usage) to be called from both the frontend dashboard (JWT) and programmatically via API key.

---

## 5. Token Usage Tracking

### 5.1 How each provider reports tokens

Each LLM provider returns token counts in a different format in their API response:

| Provider  | Response Field for Input Tokens     | Response Field for Output Tokens          |
|-----------|-------------------------------------|-------------------------------------------|
| OpenAI    | `usage.prompt_tokens`               | `usage.completion_tokens`                 |
| Anthropic | `usage.input_tokens`                | `usage.output_tokens`                     |
| Google    | `usageMetadata.promptTokenCount`    | `usageMetadata.candidatesTokenCount`      |

### 5.2 Normalization

Each provider service extracts these fields and returns a normalized `ProviderUsageResult`:

```python
class ProviderUsageResult(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    provider_response: dict = {}
```

**OpenAI extraction** (in `services/providers/openai.py`):
```python
usage = data.get("usage", {})
ProviderUsageResult(
    input_tokens=usage.get("prompt_tokens", 0),
    output_tokens=usage.get("completion_tokens", 0),
    provider_response=data,
)
```

**Anthropic extraction** (in `services/providers/anthropic.py`):
```python
usage = data.get("usage", {})
ProviderUsageResult(
    input_tokens=usage.get("input_tokens", 0),
    output_tokens=usage.get("output_tokens", 0),
    provider_response=data,
)
```

**Google extraction** (in `services/providers/google.py`):
```python
usage_meta = data.get("usageMetadata", {})
ProviderUsageResult(
    input_tokens=usage_meta.get("promptTokenCount", 0),
    output_tokens=usage_meta.get("candidatesTokenCount", 0),
    provider_response=data,
)
```

---

## 6. Cost Calculation

### 6.1 The Formula

All cost math uses Python's `Decimal` type for precision (in `app/utils/pricing.py`).

```
provider_cost = (input_tokens × input_price_per_million / 1,000,000)
              + (output_tokens × output_price_per_million / 1,000,000)

vuzo_cost = provider_cost × (1 + vuzo_markup_percent / 100)
```

The **provider_cost** is what the upstream provider (OpenAI, Anthropic, Google) charges Vuzo.
The **vuzo_cost** is what Vuzo charges the end user (provider cost + markup).

**Profit per request** = `vuzo_cost - provider_cost`

### 6.2 Worked Examples

#### Example 1: GPT-4o, 1000 input + 500 output tokens, 20% markup

```
Provider prices: $2.50 per 1M input, $10.00 per 1M output

provider_cost = (1000 × 2.50 / 1,000,000) + (500 × 10.00 / 1,000,000)
             = 0.002500 + 0.005000
             = $0.007500

vuzo_cost = 0.007500 × (1 + 20/100)
          = 0.007500 × 1.20
          = $0.009000

Vuzo profit = $0.009000 - $0.007500 = $0.001500
```

#### Example 2: Claude Sonnet, 5000 input + 2000 output tokens, 20% markup

```
Provider prices: $3.00 per 1M input, $15.00 per 1M output

provider_cost = (5000 × 3.00 / 1,000,000) + (2000 × 15.00 / 1,000,000)
             = 0.015000 + 0.030000
             = $0.045000

vuzo_cost = 0.045000 × 1.20
          = $0.054000

Vuzo profit = $0.054000 - $0.045000 = $0.009000
```

#### Example 3: Gemini 2.0 Flash, 10000 input + 3000 output tokens, 20% markup

```
Provider prices: $0.10 per 1M input, $0.40 per 1M output

provider_cost = (10000 × 0.10 / 1,000,000) + (3000 × 0.40 / 1,000,000)
             = 0.001000 + 0.001200
             = $0.002200

vuzo_cost = 0.002200 × 1.20
          = $0.002640

Vuzo profit = $0.002640 - $0.002200 = $0.000440
```

#### Example 4: Large request -- GPT-4o, 50K input + 4K output, 20% markup

```
provider_cost = (50000 × 2.50 / 1,000,000) + (4000 × 10.00 / 1,000,000)
             = 0.125000 + 0.040000
             = $0.165000

vuzo_cost = 0.165000 × 1.20
          = $0.198000

Vuzo profit = $0.198000 - $0.165000 = $0.033000
```

### 6.3 Quick Conversion: Dollars per 1K Tokens

To get a rough per-1K-token rate, divide the per-million price by 1000:

```
dollars_per_1k = price_per_million / 1000
```

For GPT-4o input: $2.50 / 1000 = $0.0025 per 1K tokens (provider) or $0.003 per 1K tokens (Vuzo at 20%).

---

## 7. Streaming

### 7.1 How it works

When `stream: true` is set in the request, Vuzo proxies SSE (Server-Sent Events) in real-time:

1. Vuzo opens an HTTP streaming connection to the provider
2. Each chunk from the provider is forwarded to the user immediately
3. Token usage is extracted from the **final chunk** of the stream
4. After the stream ends, Vuzo logs usage and deducts credits

### 7.2 Where each provider puts usage in streaming

| Provider  | Final chunk usage location                                    |
|-----------|---------------------------------------------------------------|
| OpenAI    | Last chunk's `usage` field (requires `stream_options.include_usage=true`) |
| Anthropic | `message_delta` event contains `usage.output_tokens`; `message_start` has `usage.input_tokens` |
| Google    | Last chunk's `usageMetadata` field                            |

### 7.3 Implementation

In `app/routers/proxy.py`, the `_stream_response()` generator:
- Yields each SSE chunk to the user as it arrives
- Captures the `ProviderUsageResult` from the final yield
- After the stream completes, calculates cost and logs usage

```python
async def _stream_response(request, provider, master_key, pricing, auth):
    start = time.time()
    final_usage = None

    async for chunk_str, usage in provider.chat_completion_stream(request, master_key):
        if usage is not None:
            final_usage = usage
        yield chunk_str

    # Stream done — now log usage and deduct credits
    if final_usage:
        provider_cost, vuzo_cost = calculate_cost(...)
        deduct_credits(auth.user_id, vuzo_cost, ...)
        log_usage(...)
```

---

## 8. Full Pricing Reference Table

All models seeded in the database with their provider cost, Vuzo cost (at 20% markup), and per-1K-token rates.

### Per 1,000,000 Tokens (USD)

| Provider   | Model                      | Input (Provider) | Input (Vuzo) | Output (Provider) | Output (Vuzo) |
|------------|----------------------------|------------------|--------------|--------------------|---------------|
| OpenAI     | gpt-4o                     | $2.5000          | $3.0000      | $10.0000           | $12.0000      |
| OpenAI     | gpt-4o-mini                | $0.1500          | $0.1800      | $0.6000            | $0.7200       |
| OpenAI     | gpt-4.1                    | $2.0000          | $2.4000      | $8.0000            | $9.6000       |
| OpenAI     | gpt-4.1-mini               | $0.4000          | $0.4800      | $1.6000            | $1.9200       |
| OpenAI     | gpt-4.1-nano               | $0.1000          | $0.1200      | $0.4000            | $0.4800       |
| Anthropic  | claude-sonnet-4-20250514   | $3.0000          | $3.6000      | $15.0000           | $18.0000      |
| Anthropic  | claude-haiku-4-5           | $1.0000          | $1.2000      | $5.0000            | $6.0000       |
| Anthropic  | claude-opus-4-5            | $5.0000          | $6.0000      | $25.0000           | $30.0000      |
| Google     | gemini-2.0-flash           | $0.1000          | $0.1200      | $0.4000            | $0.4800       |
| Google     | gemini-3-flash             | $0.5000          | $0.6000      | $3.0000            | $3.6000       |

### Per 1,000 Tokens (USD) -- Quick Reference

| Provider   | Model                      | Input (Vuzo)  | Output (Vuzo)  |
|------------|----------------------------|---------------|----------------|
| OpenAI     | gpt-4o                     | $0.003000     | $0.012000      |
| OpenAI     | gpt-4o-mini                | $0.000180     | $0.000720      |
| OpenAI     | gpt-4.1                    | $0.002400     | $0.009600      |
| OpenAI     | gpt-4.1-mini               | $0.000480     | $0.001920      |
| OpenAI     | gpt-4.1-nano               | $0.000120     | $0.000480      |
| Anthropic  | claude-sonnet-4-20250514   | $0.003600     | $0.018000      |
| Anthropic  | claude-haiku-4-5           | $0.001200     | $0.006000      |
| Anthropic  | claude-opus-4-5            | $0.006000     | $0.030000      |
| Google     | gemini-2.0-flash           | $0.000120     | $0.000480      |
| Google     | gemini-3-flash             | $0.000600     | $0.003600      |

### Dollar Cost Examples (at Vuzo pricing)

| Scenario                        | Model                    | Input Tokens | Output Tokens | Vuzo Cost    |
|---------------------------------|--------------------------|--------------|---------------|--------------|
| Quick chat reply                | gpt-4o-mini              | 200          | 100           | $0.000108    |
| Code generation                 | gpt-4o                   | 2,000        | 1,000         | $0.018000    |
| Long document summary           | claude-sonnet-4-20250514 | 20,000       | 2,000         | $0.108000    |
| Batch processing (cheap)        | gemini-2.0-flash         | 50,000       | 10,000        | $0.010800    |
| Complex reasoning               | claude-opus-4-5          | 10,000       | 5,000         | $0.210000    |

---

## 9. Rate Limiting

The rate limiter (`app/middleware/rate_limiter.py`) uses a simple in-memory sliding window:

- Keyed by API key prefix (first 8 chars)
- Default: 60 requests per minute per key
- Each key can have a custom `rate_limit_rpm` value in the `api_keys` table
- Returns HTTP 429 when exceeded

For production scaling, replace with Redis-backed rate limiting.

---

## 10. Provider Key Management

Vuzo's master API keys (used to call OpenAI, Anthropic, Google) are stored encrypted:

1. Encrypt with Fernet symmetric encryption before INSERT
2. Store ciphertext in `provider_keys.api_key_encrypted`
3. Decrypt at request time in `pricing_service.get_provider_api_key()`

Generate the encryption key with:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set it as `PROVIDER_ENCRYPTION_KEY` in `.env`.

---

## 11. Using Your Vuzo API Key

Vuzo exposes an **OpenAI-compatible** `POST /v1/chat/completions` endpoint. Any code or SDK that works with OpenAI works with Vuzo -- just change the base URL and API key. The `model` field determines which provider handles the request.

### Available models

| Provider | Models |
|----------|--------|
| OpenAI   | `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` |
| xAI      | `grok-3`, `grok-3-mini`, `grok-2` |
| Google   | `gemini-2.0-flash`, `gemini-3-flash` |

### Example 1: Python with `requests`

```python
import requests

VUZO_API_KEY = "vz-sk_your_key_here"
VUZO_BASE_URL = "http://localhost:8000/v1"

response = requests.post(
    f"{VUZO_BASE_URL}/chat/completions",
    headers={
        "Authorization": f"Bearer {VUZO_API_KEY}",
        "Content-Type": "application/json",
    },
    json={
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": "Explain what an API proxy is in one sentence."}
        ],
    },
)

data = response.json()
print(data["choices"][0]["message"]["content"])
print(f"Tokens: {data['usage']['prompt_tokens']} in, {data['usage']['completion_tokens']} out")
```

### Example 2: OpenAI Python SDK

Since Vuzo is OpenAI-compatible, the official `openai` Python package works out of the box. Install it with `pip install openai`.

```python
from openai import OpenAI

client = OpenAI(
    api_key="vz-sk_your_key_here",
    base_url="http://localhost:8000/v1",
)

# Use any supported model -- OpenAI, Grok, or Gemini
response = client.chat.completions.create(
    model="grok-3",
    messages=[{"role": "user", "content": "What is 2+2?"}],
)

print(response.choices[0].message.content)
print(f"Tokens: {response.usage.prompt_tokens} in, {response.usage.completion_tokens} out")
```

Switching providers is just a model name change:

```python
# OpenAI
response = client.chat.completions.create(model="gpt-4o-mini", messages=[...])

# xAI Grok
response = client.chat.completions.create(model="grok-3-mini", messages=[...])

# Google Gemini
response = client.chat.completions.create(model="gemini-2.0-flash", messages=[...])
```

### Example 3: curl

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer vz-sk_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [{"role": "user", "content": "Hello from Vuzo!"}]
  }'
```

### Example 4: Streaming

```python
import requests

response = requests.post(
    "http://localhost:8000/v1/chat/completions",
    headers={"Authorization": "Bearer vz-sk_your_key_here"},
    json={
        "model": "grok-3",
        "messages": [{"role": "user", "content": "Write a haiku about APIs"}],
        "stream": True,
    },
    stream=True,
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

### Testing your key

A ready-made test script is included at the project root:

```bash
python test_key.py vz-sk_your_key_here
```

This sends a test request to one model from each provider and prints the response, token usage, and cost.
