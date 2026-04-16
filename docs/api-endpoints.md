# Vuzo API — Endpoint Reference

**API Base URL:** `https://vuzo-api.onrender.com`
**Dashboard:** `https://vuzo-api-1.onrender.com`

---

## Auth

| Header | Format | When to use |
|--------|--------|-------------|
| `Authorization` | `Bearer <supabase_jwt>` | After login/register via web |
| `Authorization` | `Bearer vz-sk_<key>` | Vuzo API key (installer + OpenClaw) |

Endpoints marked **JWT or API Key** accept either. Endpoints marked **API Key only** require a `vz-sk_` key.

---

## Summary

| # | Method | Path | Auth | Purpose |
|---|--------|------|------|---------|
| 1 | POST | /v1/auth/register | None | Register new user |
| 2 | POST | /v1/auth/login | None | Login |
| 3 | POST | /v1/auth/refresh | None | Refresh JWT |
| 4 | POST | /v1/api-keys | JWT or API Key | Create API key |
| 5 | GET | /v1/api-keys | JWT or API Key | List API keys |
| 6 | DELETE | /v1/api-keys/{key_id} | JWT or API Key | Revoke API key |
| 7 | GET | /v1/billing/balance | JWT or API Key | Check credit balance |
| 8 | POST | /v1/billing/topup | JWT or API Key | Add credits (dev only) |
| 9 | GET | /v1/billing/transactions | JWT or API Key | List transactions |
| 10 | POST | /v1/billing/checkout | JWT or API Key | Create Polar checkout |
| 11 | POST | /v1/webhooks/polar | Signature only | Polar webhook receiver |
| 12 | GET | /v1/models | None | List all models + pricing |
| 13 | GET | /v1/models/{model_name} | None | Single model pricing |
| 14 | POST | /v1/chat/completions | API Key only | LLM proxy |
| 15 | GET | /v1/usage | JWT or API Key | Usage logs |
| 16 | GET | /v1/usage/summary | JWT or API Key | Aggregated usage stats |
| 17 | GET | /v1/usage/daily | JWT or API Key | Daily usage breakdown |
| 18 | POST | /v1/setup/installer | None | Installer login/register |
| 19 | GET | /health | None | Health check |

---

## 1. `POST /v1/auth/register`

**Auth:** None

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "message": "Registration successful",
  "user_id": "<supabase_uuid>",
  "session": {
    "access_token": "<jwt>",
    "refresh_token": "<token>",
    "expires_in": 3600
  },
  "api_key": "vz-sk_xxxxxxxxxxxxxxxx"
}
```

**Notes:**
- Creates Supabase auth account + Vuzo user record
- Auto-creates a `Default` API key — returned once only, store immediately
- Sets credit balance to $0 — **free credits only granted via installer**

---

## 2. `POST /v1/auth/login`

**Auth:** None

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword"
}
```

**Response:**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<token>",
  "expires_in": 3600,
  "user": {
    "id": "<supabase_uuid>",
    "email": "user@example.com"
  }
}
```

**Errors:** `401` if credentials invalid.

---

## 3. `POST /v1/auth/refresh`

**Auth:** None

**Request body:**
```json
{
  "refresh_token": "<token>"
}
```

**Response:**
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<token>",
  "expires_in": 3600
}
```

**Errors:** `401` if refresh token invalid or expired.

---

## 4. `POST /v1/api-keys`

**Auth:** JWT or API Key

**Request body:**
```json
{
  "name": "My Key"
}
```

**Response:**
```json
{
  "id": "<uuid>",
  "name": "My Key",
  "key": "vz-sk_xxxxxxxxxxxxxxxx",
  "key_prefix": "vz-sk_xx",
  "created_at": "2026-04-16T00:00:00Z"
}
```

**Notes:** Full key returned once only — store immediately.

---

## 5. `GET /v1/api-keys`

**Auth:** JWT or API Key

**Response:**
```json
[
  {
    "id": "<uuid>",
    "name": "OpenClaw",
    "key_prefix": "vz-sk_xx",
    "is_active": true,
    "rate_limit_rpm": 60,
    "created_at": "2026-04-16T00:00:00Z",
    "last_used_at": "2026-04-16T10:00:00Z"
  }
]
```

---

## 6. `DELETE /v1/api-keys/{key_id}`

**Auth:** JWT or API Key

**Path param:** `key_id` — UUID of the key to revoke

**Response:**
```json
{
  "message": "API key revoked",
  "key_id": "<uuid>"
}
```

**Errors:** `404` if key not found or doesn't belong to user.

---

## 7. `GET /v1/billing/balance`

**Auth:** JWT or API Key

**Response:**
```json
{
  "user_id": "<uuid>",
  "balance": 1.00
}
```

Balance is in USD. $1.00 ≈ 500,000 tokens on mid-range models.

---

## 8. `POST /v1/billing/topup` ⚠️ Dev only

**Auth:** JWT or API Key

**Request body:**
```json
{
  "amount": 5.00
}
```

**Response:**
```json
{
  "user_id": "<uuid>",
  "amount": 5.00,
  "new_balance": 6.00,
  "transaction_id": "<uuid>"
}
```

**Notes:** Disabled in production — returns `403`. Use `/v1/billing/checkout` in production.

---

## 9. `GET /v1/billing/transactions`

**Auth:** JWT or API Key

**Query params:**
- `limit` (integer, default: 50, max: 200)
- `offset` (integer, default: 0)

**Response:**
```json
[
  {
    "id": "<uuid>",
    "amount": 1.00,
    "type": "topup",
    "description": "Free starter allowance — 500,000 tokens",
    "created_at": "2026-04-16T00:00:00Z"
  }
]
```

`type` is one of: `topup`, `usage`, `refund`

---

## 10. `POST /v1/billing/checkout`

**Auth:** JWT or API Key

**Request body** — provide `tier` OR `amount`, not both:
```json
{ "tier": "10" }
```
```json
{ "amount": 25.00 }
```

Valid tiers: `"10"`, `"30"`, `"50"` (USD).
Custom amount minimum: $10.

**Response:**
```json
{
  "checkout_url": "https://buy.polar.sh/..."
}
```

**Errors:** `400` if both/neither provided, invalid tier, or amount < $10. `503` if Polar not configured.

---

## 11. `POST /v1/webhooks/polar`

**Auth:** Webhook signature (`webhook-signature` header, HMAC-SHA256)

**Notes:**
- Processes `order.created` events only
- On valid Vuzo product order: credits the user's balance
- Returns `400` if signature invalid
- Returns `{"received": true}` for all other events (non-Vuzo products silently ignored)

---

## 12. `GET /v1/models`

**Auth:** None (public)

**Response:**
```json
[
  {
    "provider": "openai",
    "model_name": "gpt-4o",
    "input_price_per_million": 2.50,
    "output_price_per_million": 10.00,
    "vuzo_input_price_per_million": 2.75,
    "vuzo_output_price_per_million": 11.00,
    "vuzo_markup_percent": 10.0
  }
]
```

---

## 13. `GET /v1/models/{model_name}`

**Auth:** None (public)

**Path param:** `model_name` — e.g. `gpt-4o`, `claude-sonnet-4-5`

**Response:** Single object (same shape as above)

**Errors:** `404` if model not found.

---

## 14. `POST /v1/chat/completions`

**Auth:** API Key only (`vz-sk_`)

**Request body** (OpenAI-compatible):
```json
{
  "model": "gpt-4o",
  "messages": [
    { "role": "user", "content": "Hello" }
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "stream": false
}
```

| Field | Type | Required |
|-------|------|----------|
| `model` | string | Yes |
| `messages` | array | Yes |
| `temperature` | float | No |
| `top_p` | float | No |
| `max_tokens` | integer | No |
| `stream` | boolean | No (default: false) |
| `stop` | string or array | No |
| `frequency_penalty` | float | No |
| `presence_penalty` | float | No |

**Response (non-streaming):**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1744800000,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": { "role": "assistant", "content": "Hello!" },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 5,
    "total_tokens": 15
  }
}
```

**Response (streaming):** `text/event-stream` SSE, same OpenAI delta format.

**Errors:**
- `400` — model not found
- `402` — insufficient balance (top up at `/v1/billing/checkout`)
- `401` — invalid API key
- `429` — rate limit exceeded

**Notes:** Routes to OpenAI, Anthropic, Google, or xAI based on model. Deducts credits on completion. Logs all usage.

---

## 15. `GET /v1/usage`

**Auth:** JWT or API Key

**Query params:**
- `model` (string, optional)
- `provider` (string, optional) — `openai`, `anthropic`, `google`, `xai`
- `start_date` (ISO datetime, optional)
- `end_date` (ISO datetime, optional)
- `limit` (integer, default: 50, max: 200)
- `offset` (integer, default: 0)

**Response:**
```json
[
  {
    "id": "<uuid>",
    "provider": "openai",
    "model": "gpt-4o",
    "input_tokens": 100,
    "output_tokens": 50,
    "total_tokens": 150,
    "provider_cost": 0.000625,
    "vuzo_cost": 0.0006875,
    "response_time_ms": 1200,
    "created_at": "2026-04-16T10:00:00Z"
  }
]
```

---

## 16. `GET /v1/usage/summary`

**Auth:** JWT or API Key

**Query params:**
- `start_date` (ISO datetime, optional)
- `end_date` (ISO datetime, optional)

**Response:**
```json
{
  "total_requests": 42,
  "total_input_tokens": 10000,
  "total_output_tokens": 5000,
  "total_tokens": 15000,
  "total_provider_cost": 0.05,
  "total_vuzo_cost": 0.055
}
```

---

## 17. `GET /v1/usage/daily`

**Auth:** JWT or API Key

**Query params:**
- `model` (string, optional)
- `provider` (string, optional)
- `start_date` (ISO datetime, optional)
- `end_date` (ISO datetime, optional)

**Response:**
```json
[
  {
    "date": "2026-04-16",
    "model": "gpt-4o",
    "provider": "openai",
    "total_requests": 10,
    "input_tokens": 2000,
    "output_tokens": 1000,
    "total_cost": 0.015
  }
]
```

---

## 18. `POST /v1/setup/installer`

**Auth:** None

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "yourpassword",
  "key_name": "OpenClaw"
}
```

`key_name` is optional, defaults to `"OpenClaw"`.

**Response:**
```json
{
  "api_key": "vz-sk_xxxxxxxxxxxxxxxx",
  "models": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-5", "grok-3"],
  "openclaw_config": {
    "base_url": "https://vuzo-api.onrender.com/v1",
    "provider_name": "vuzo",
    "models": ["gpt-4o", "gpt-4o-mini", "claude-sonnet-4-5", "grok-3"]
  },
  "dashboard_url": "https://vuzo-api-1.onrender.com#access_token=<jwt>&refresh_token=<token>&token_type=bearer&type=signup"
}
```

**Notes:**
- Tries login first — auto-registers if account doesn't exist
- New accounts receive **$1.00 free credit (~500,000 tokens)**
- Revokes any existing active key with the same `key_name` before creating a new one (prevents accumulation on re-install)
- `dashboard_url` includes session tokens in the URL hash — load directly in WKWebView for auto-login
- API key returned once only — store in Keychain immediately

---

## 19. `GET /health`

**Auth:** None

**Response:**
```json
{
  "status": "ok",
  "service": "vuzo-api"
}
```

---

## OpenClaw Config Reference

After calling `/v1/setup/installer`, write this to `~/.openclaw/settings.json`:

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "vuzo": {
        "api": "openai-completions",
        "api-key": "<api_key from response>",
        "base-url": "https://vuzo-api.onrender.com/v1"
      }
    }
  },
  "agents": {
    "defaults": {
      "model": "vuzo/gpt-4o",
      "models": {
        "edit": "vuzo/gpt-4o",
        "summarize": "vuzo/gpt-4o"
      }
    }
  }
}
```

All model names must be prefixed with `vuzo/` — e.g. `gpt-4o` → `vuzo/gpt-4o`.
