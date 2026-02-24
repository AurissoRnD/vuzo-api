# Vuzo — Architecture & Repository Connections

This document explains how the two repositories that make up Vuzo connect and relate to each other. It is intended for the engineering team.

---

## The Two Repositories

| Repository | Location | Purpose |
|------------|----------|---------|
| `Vuzo-api` | This repo | FastAPI backend + React dashboard. The actual product users sign up to. |
| `vuzo-python` | Separate repo / `../vuzo-python` | Official Python SDK. A pip-installable wrapper around the Vuzo REST API. |

They are **independent deployable units** — the SDK is just a client library. The API has no knowledge of the SDK; the SDK has no direct database access.

---

## How They Connect

```
┌─────────────────────────────────────────────────────────────────────┐
│                         vuzo-python SDK                             │
│                                                                     │
│  from vuzo import Vuzo                                              │
│  client = Vuzo("vz-sk_...")                                         │
│                                                                     │
│  client.chat.complete(...)  ──────────────────────────────────────► │
│  client.models.list()       ──────────────────────────────────────► │
│  client.usage.summary()     ──────────────────────────────────────► │
│  client.billing.get_balance() ────────────────────────────────────► │
│  client.api_keys.create(...)  ────────────────────────────────────► │
└─────────────────────────────────────────────────────────────────────┘
             │  HTTPS requests with Authorization: Bearer vz-sk_...
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Vuzo-api / backend/                         │
│                                                                     │
│  POST   /v1/chat/completions   ◄── main proxy endpoint              │
│  GET    /v1/models             ◄── list models + pricing            │
│  GET    /v1/models/{name}      ◄── single model details             │
│  GET    /v1/usage/logs         ◄── per-request log                  │
│  GET    /v1/usage/summary      ◄── aggregated totals                │
│  GET    /v1/usage/daily        ◄── day-by-day breakdown             │
│  GET    /v1/billing/balance    ◄── credit balance                   │
│  GET    /v1/billing/transactions ◄── transaction history            │
│  POST   /v1/api-keys           ◄── create key                       │
│  GET    /v1/api-keys           ◄── list keys                        │
│  DELETE /v1/api-keys/{id}      ◄── delete key                       │
└─────────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            Supabase                                 │
│  Tables: users, api_keys, credit_transactions, usage_logs,          │
│          model_pricing, rate_limit_requests                         │
└─────────────────────────────────────────────────────────────────────┘
             │
             ├──► OpenAI API   (gpt-4o, gpt-4o-mini, gpt-4.1, …)
             ├──► xAI API      (grok-3, grok-3-mini, grok-2)
             ├──► Google API   (gemini-2.0-flash, gemini-3-flash)
             └──► Anthropic API (claude-sonnet-4, …)
```

---

## Full Request Flow (chat.complete)

```
Developer code
  │
  │  client.chat.complete("gpt-4o-mini", "Hello!")
  ▼
vuzo-python / chat.py
  │  POST https://vuzo-api.onrender.com/v1/chat/completions
  │  Headers: Authorization: Bearer vz-sk_abc123
  │  Body: { model: "gpt-4o-mini", messages: [...] }
  ▼
Vuzo-api / backend/app/middleware/auth.py
  │  Validates vz-sk_ key against Supabase api_keys table
  │  Extracts user_id
  ▼
Vuzo-api / backend/app/middleware/rate_limiter.py
  │  Checks rate_limit_requests table (Supabase)
  │  Returns 429 if user exceeded 60 RPM
  ▼
Vuzo-api / backend/app/routers/proxy.py
  │  Looks up model in model_pricing table
  │  Selects provider (OpenAI / xAI / Google / Anthropic)
  │  Checks and deducts credits (billing_service)
  │  Calls provider API
  │  Normalises response to OpenAI format
  │  Logs usage (usage_service)
  ▼
vuzo-python / chat.py
  │  Parses response into ChatCompletion Pydantic model
  ▼
Developer code
     response.choices[0].message.content  → "Hello! How can I help?"
```

---

## SDK ↔ API Endpoint Mapping

| SDK method | HTTP method | Vuzo API path | Auth required |
|------------|-------------|---------------|---------------|
| `chat.complete(model, prompt)` | POST | `/v1/chat/completions` | Yes |
| `chat.create(model, messages)` | POST | `/v1/chat/completions` | Yes |
| `chat.stream(model, messages)` | POST | `/v1/chat/completions` (SSE) | Yes |
| `models.list()` | GET | `/v1/models` | No |
| `models.get(name)` | GET | `/v1/models/{name}` | No |
| `usage.list(limit, offset)` | GET | `/v1/usage/logs` | Yes |
| `usage.summary()` | GET | `/v1/usage/summary` | Yes |
| `usage.daily(start, end)` | GET | `/v1/usage/daily` | Yes |
| `billing.get_balance()` | GET | `/v1/billing/balance` | Yes |
| `billing.transactions()` | GET | `/v1/billing/transactions` | Yes |
| `api_keys.list()` | GET | `/v1/api-keys` | Yes |
| `api_keys.create(name)` | POST | `/v1/api-keys` | Yes |
| `api_keys.delete(id)` | DELETE | `/v1/api-keys/{id}` | Yes |

---

## Authentication

The API uses two auth mechanisms depending on the caller:

| Caller | Auth method | Where issued |
|--------|------------|--------------|
| Python SDK / curl / OpenAI SDK | `vz-sk_` API key in `Authorization: Bearer` header | Vuzo dashboard or `api_keys.create()` |
| Vuzo dashboard (React frontend) | Supabase JWT in `Authorization: Bearer` header | Supabase Auth (signup/login) |

Both paths flow through the same middleware stack (`auth.py` → `rate_limiter.py` → router). The auth middleware determines which user is making the request and attaches `user_id` for downstream use.

---

## Billing Flow

Credits are stored in Supabase (`users.credit_balance`). Each chat request deducts cost based on `model_pricing` table rates.

Top-up flow (via Polar payments):
```
Frontend Billing page
  │  POST /v1/billing/checkout  { tier: "10" }
  ▼
backend/app/routers/polar.py
  │  Reads POLAR_PRODUCT_10 from backend config (never exposed to frontend)
  │  POSTs to Polar API to create checkout session
  │  Returns { checkout_url }
  ▼
Frontend opens checkout_url in new tab
  │  User pays on Polar
  ▼
Polar sends webhook to POST /v1/webhooks/polar
  │  Signature verified with POLAR_WEBHOOK_SECRET
  │  order.created event: credits added to user balance via billing_service.add_credits()
  ▼
User balance updated in Supabase
```

---

## Key Design Principle: Product IDs Stay in the Backend

Polar product IDs (`POLAR_PRODUCT_10`, etc.) are backend env vars. The frontend sends a `tier` string ("10"/"30"/"50") or a custom `amount`. The backend resolves the Polar product ID from config and creates the checkout. This means:

- Product IDs cannot be scraped from the frontend source or network traffic.
- Changing a Polar product only requires a backend env var update — no frontend redeploy.
- The frontend has no opinion about what Polar products exist.

---

## Environment Variables — Which Repo Owns What

### `Vuzo-api/backend/.env` (backend — never sent to browser)

| Variable | Purpose |
|----------|---------|
| `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` | Database + auth |
| `PROVIDER_ENCRYPTION_KEY` | Fernet key for encrypting stored provider API keys |
| `POLAR_ACCESS_TOKEN` | Polar org access token for creating checkouts |
| `POLAR_WEBHOOK_SECRET` | Verifies incoming Polar webhook signatures |
| `POLAR_PRODUCT_10/30/50/CUSTOM` | Polar product IDs for each top-up tier |
| `FRONTEND_URL` | CORS allowed origin |
| `APP_ENV`, `APP_DEBUG`, `APP_PORT` | Runtime settings |

### `Vuzo-api/frontend/.env` (frontend — bundled into browser JS)

| Variable | Purpose |
|----------|---------|
| `VITE_SUPABASE_URL` | Supabase project URL for client-side auth |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key for client-side auth |
| `VITE_API_BASE_URL` | Vuzo API base URL for all API calls |

> The frontend `.env` intentionally contains **no secrets** and **no Polar product IDs**. Everything sensitive lives in the backend.

---

## Repo Boundaries

```
What the SDK knows about:
  ✓ REST API endpoint paths
  ✓ Request/response schemas
  ✓ Error status codes
  ✗ Supabase tables
  ✗ Provider API keys
  ✗ Polar product IDs
  ✗ Billing logic

What the API knows about:
  ✓ Everything in Supabase
  ✓ Provider integrations
  ✓ Billing and credit deduction
  ✗ Which SDK version is calling it  ← by design; backwards-compatible API
```

---

## Versioning

| Component | Version | PyPI |
|-----------|---------|------|
| Vuzo API | 1.2.0 (internal) | n/a |
| vuzo Python SDK | 0.2.0 | [pypi.org/project/vuzo](https://pypi.org/project/vuzo/) |

The API does not version its URLs (no `/v2/`). Breaking changes are avoided; the SDK is expected to work with any version of the API that implements the same endpoint contracts.

---

## Document History

| Date | Change |
|------|--------|
| 2026-02-19 | Updated billing flow to reflect tier-based checkout (product IDs now backend-only); updated env variable table |
| 2026-02-19 | Initial document created — full request flow, SDK ↔ API mapping, auth model, billing flow, env variable ownership, repo boundaries, versioning |
