# Vuzo API — Endpoint Reference

Base URL: `https://vuzo-api-1.onrender.com`

---

## Auth Headers

| Header | Format | Used for |
|--------|--------|---------|
| `Authorization` | `Bearer <supabase_jwt>` | After login/register |
| `Authorization` | `Bearer vz-<key>` | Vuzo API key |

---

## 1. Registration & Login

### Register
`POST /v1/auth/register`

Creates an account + auto-generates a `vz-*` API key + grants **200K token starter credit ($0.40)**.
**The API key is returned once only — store it immediately.**

```json
// Request
{
  "email": "user@example.com",
  "password": "yourpassword"
}

// Response
{
  "message": "Registration successful",
  "user_id": "<supabase_uid>",
  "session": {
    "access_token": "<jwt>",
    "refresh_token": "<token>",
    "expires_in": 3600
  },
  "api_key": "vz-abc123_xxxxxxxxxxxxxxxx",
  "starter_credits": {
    "usd": 0.40,
    "tokens": 200000
  }
}
```

---

### Login
`POST /v1/auth/login`

```json
// Request
{
  "email": "user@example.com",
  "password": "yourpassword"
}

// Response
{
  "access_token": "<jwt>",
  "refresh_token": "<token>",
  "expires_in": 3600,
  "user": {
    "id": "<supabase_uid>",
    "email": "user@example.com"
  }
}
```

---

### Refresh Token
`POST /v1/auth/refresh`

```json
// Request
{ "refresh_token": "<token>" }

// Response
{
  "access_token": "<new_jwt>",
  "refresh_token": "<new_token>",
  "expires_in": 3600
}
```

---

## 2. API Key Management

All endpoints require `Authorization: Bearer <jwt_or_vz_key>`.

### Create API Key
`POST /v1/api-keys`

Generates an additional `vz-*` key. **Full key returned only once.**

```json
// Request
{ "name": "My Key" }

// Response
{
  "id": "key_id",
  "name": "My Key",
  "key": "vz-abc123_xxxxxxxxxxxxxxxx",
  "key_prefix": "vz-abc123",
  "created_at": "2026-04-10T00:00:00Z"
}
```

---

### List API Keys
`GET /v1/api-keys`

```json
// Response
[
  {
    "id": "key_id",
    "name": "My Key",
    "key_prefix": "vz-abc123",
    "is_active": true,
    "rate_limit_rpm": 60,
    "created_at": "2026-04-10T00:00:00Z",
    "last_used_at": "2026-04-10T12:00:00Z"
  }
]
```

---

### Revoke API Key
`DELETE /v1/api-keys/{key_id}`

Returns `204 No Content` on success.

---

## 3. Dashboard — Credits & Billing

All endpoints require `Authorization: Bearer <jwt_or_vz_key>`.

### Credit Balance
`GET /v1/billing/balance`

```json
// Response
{
  "balance_usd": 0.38,
  "balance_credits": 380000
}
```

---

### Transaction History
`GET /v1/billing/transactions`

Query params: `limit` (1–200, default 50), `offset` (default 0)

```json
// Response
[
  {
    "id": "txn_id",
    "type": "topup",
    "amount": 0.40,
    "description": "Starter allowance — 200,000 tokens",
    "created_at": "2026-04-10T00:00:00Z"
  },
  {
    "id": "txn_id",
    "type": "usage",
    "amount": -0.0012,
    "description": "gpt-4o usage",
    "created_at": "2026-04-10T12:00:00Z"
  }
]
```

---

### Top-up — Create Checkout Session
`POST /v1/billing/checkout`

```json
// Request (preset tier)
{ "tier": "30" }

// Request (custom amount, min $10)
{ "amount": 25.00 }

// Response
{ "checkout_url": "https://polar.sh/checkout/..." }
```

Tiers: `"10"`, `"30"`, `"50"` (USD).

---

## 4. Dashboard — Usage Stats

All endpoints require `Authorization: Bearer <jwt_or_vz_key>`.  
Date format: ISO 8601 — e.g. `2026-04-01T00:00:00Z`

### Usage Logs (paginated)
`GET /v1/usage`

Query params: `model`, `provider`, `start_date`, `end_date`, `limit` (1–200, default 50), `offset`

```json
// Response
[
  {
    "id": "log_id",
    "model": "gpt-4o",
    "provider": "openai",
    "input_tokens": 512,
    "output_tokens": 128,
    "cost_usd": 0.0012,
    "created_at": "2026-04-10T12:00:00Z"
  }
]
```

---

### Usage Summary (totals)
`GET /v1/usage/summary`

Query params: `start_date`, `end_date`

```json
// Response
{
  "total_requests": 142,
  "total_input_tokens": 84000,
  "total_output_tokens": 21000,
  "total_cost_usd": 1.24
}
```

---

### Usage by Day
`GET /v1/usage/daily`

Query params: `model`, `provider`, `start_date`, `end_date`

```json
// Response
[
  {
    "date": "2026-04-10",
    "model": "gpt-4o",
    "provider": "openai",
    "requests": 18,
    "input_tokens": 9200,
    "output_tokens": 2400,
    "cost_usd": 0.18
  }
]
```

---

## 5. Available Models

Public — no auth required.

### List All Models
`GET /v1/models`

```json
// Response
[
  {
    "model_name": "gpt-4o",
    "provider": "openai",
    "vuzo_input_price_per_million": 6.00,
    "vuzo_output_price_per_million": 18.00,
    "vuzo_markup_percent": 20
  }
]
```

### Single Model Pricing
`GET /v1/models/{model_name}`

---

## 6. Health

`GET /health` — Public, no auth.

---

## Quick Reference

| Flow | Endpoint | Auth |
|------|----------|------|
| Register (+ auto key + 200K tokens) | `POST /v1/auth/register` | None |
| Login | `POST /v1/auth/login` | None |
| Refresh session | `POST /v1/auth/refresh` | None |
| Create additional API key | `POST /v1/api-keys` | JWT or API Key |
| List API keys | `GET /v1/api-keys` | JWT or API Key |
| Revoke API key | `DELETE /v1/api-keys/{key_id}` | JWT or API Key |
| Credit balance | `GET /v1/billing/balance` | JWT or API Key |
| Transaction history | `GET /v1/billing/transactions` | JWT or API Key |
| Top-up checkout | `POST /v1/billing/checkout` | JWT or API Key |
| Usage logs | `GET /v1/usage` | JWT or API Key |
| Usage summary | `GET /v1/usage/summary` | JWT or API Key |
| Usage by day | `GET /v1/usage/daily` | JWT or API Key |
| List models | `GET /v1/models` | None |
| Health check | `GET /health` | None |

---

## Token → Credit Conversion

Credits are stored as USD. Conversion reference (Vuzo blended pricing):

| Amount | Approximate tokens |
|--------|--------------------|
| $0.40 | ~200,000 (starter) |
| $1.00 | ~500,000 |
| $10.00 | ~5,000,000 |

---

## OpenClaw Integration

After registering, the `api_key` in the response (`vz-*`) is used to connect OpenClaw to Vuzo.

### How OpenClaw uses the key

OpenClaw reads its config from `settings.json`. Add the `vuzo` provider block and set your default model:

```json
{
  "models": {
    "mode": "merge",
    "providers": {
      "vuzo": {
        "api": "openai-completions",
        "api-key": "vz-YOUR_KEY_HERE",
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

### Config file location

Find yours by running:

```bash
openclaw config path
```

If that command doesn't exist, the file is in one of these locations depending on your OS:

| OS | Path |
|----|------|
| macOS | `~/Library/Application Support/openclaw/settings.json` |
| Linux (XDG) | `~/.config/openclaw/settings.json` |
| Linux (default) | `~/.openclaw/settings.json` |
| Windows | `%APPDATA%\openclaw\settings.json` |

Create the file and parent directory if they don't exist.

### Model reference format

All models are prefixed with `vuzo/` in OpenClaw:

```
vuzo/gpt-4o
vuzo/claude-sonnet-4-5
vuzo/gemini-pro
vuzo/grok-2
```

Use `GET /v1/models` to get the full list of available model names, then prefix each with `vuzo/`.

### Verification

Once configured, test the connection from within OpenClaw or run:

```bash
curl https://vuzo-api.onrender.com/v1/chat/completions \
  -H "Authorization: Bearer vz-YOUR_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o",
    "messages": [{ "role": "user", "content": "ping" }]
  }'
```

A valid response means the key is active and OpenClaw will route through Vuzo correctly.
