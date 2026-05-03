# SimplerClaw — Project Overview
**Prepared for internal review | April 2026**

---

## What Is SimplerClaw?

SimplerClaw is an AI infrastructure platform built for users of the OpenClaw AI agent. It acts as a managed gateway between OpenClaw and the underlying AI models — specifically Moonshot's **kimi-k2.6** — so that users never need to manage provider API keys, billing accounts, or token quotas themselves.

From the user's perspective:
- They install OpenClaw via the SimplerClaw installer wizard
- They register or log in — an API key is automatically issued and injected into their OpenClaw setup
- They top up credits from the dashboard and use OpenClaw normally
- We track every token they consume, charge accordingly, and they can view it all in real time

From the business perspective:
- Every AI request goes through our infrastructure, billed at a 20% markup over provider cost
- We control key issuance, revocation, token caps, and user access centrally
- The admin portal gives full visibility into revenue, costs, profit, and per-user activity

---

## Live URLs

| Service | URL |
|---|---|
| User Dashboard | https://vuzo-api-1.onrender.com |
| Admin Portal | https://vuzo-api-1.onrender.com/admin |
| Backend API | https://vuzo-api.onrender.com |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18 + TypeScript, Vite, Tailwind CSS |
| Backend | FastAPI (Python 3.12), Uvicorn |
| Database | Supabase (managed PostgreSQL) |
| Auth | Supabase Auth (email/password + JWT) |
| Hosting | Render.com (2 services: API + static dashboard) |
| AI Provider | Moonshot (`kimi-k2.6`) via REST proxy |
| Payments | CardTransaction (primary), Polar (secondary) |

---

## How It Works — End to End

### 1. User Onboarding (Installer Flow)

The user runs the SimplerClaw installer wizard on their machine. The installer calls:

- `POST /v1/setup/installer`

This endpoint supports both account creation and login:

- **`type=register`**
  - Creates Supabase Auth account
  - Creates internal `users` + `credits` records (starting balance is `0.00`)
  - Issues a fresh OpenClaw API key
- **`type=login`**
  - Authenticates existing account
  - Rotates OpenClaw API key (revoke old key, issue new key)
  - Enforces single-device session behavior

The user never needs to manually create or paste API keys in OpenClaw setup.

#### Installer Setup Request

```json
{
  "type": "register",
  "email": "user@example.com",
  "password": "strong_password",
  "key_name": "OpenClaw"
}
```

`type` can be `register` or `login`.

#### Installer Setup Response (Current)

```json
{
  "api_key": "vz-sk_...",
  "models": ["kimi-k2.6"],
  "openclaw_config": {
    "base_url": "https://vuzo-api.onrender.com/v1",
    "provider_name": "vuzo",
    "models": ["kimi-k2.6"]
  },
  "dashboard_url": "https://vuzo-api-1.onrender.com#refresh_token=...",
  "web_payment": {
    "has_paid_via_web": true,
    "latest": {
      "transaction_id": "uuid",
      "package": "starter",
      "credits_amount": 10.0,
      "payment_amount": 19.0,
      "paid_at": "2026-05-03T10:00:00Z"
    }
  },
  "session": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600
  }
}
```

`web_payment.has_paid_via_web` is derived from `credit_transactions` package-purchase history (`starter`, `popular`, `pro`) and is returned for both register and login responses.

---

### 2. API Keys

Every user has one or more `vz-sk_` keys. These are:

- **48 random hex characters** after the prefix (96-bit entropy — cryptographically secure)
- **Never stored in plaintext** — only the SHA-256 hash is saved in the database
- **Shown once** at creation; if lost, a new one must be issued
- **Per-key token limits** — OpenClaw keys start with a 500K token cap
- **Per-key rate limits** — default 60 requests per minute
- **Revocable** — admin or user can disable a key instantly

---

### 3. AI Request Flow

When OpenClaw sends a request:

```
OpenClaw → vz-sk_ key → SimplerClaw API → Moonshot kimi-k2.6
```

In detail:
1. Request arrives at `POST /v1/chat/completions` with the user's `vz-sk_` key
2. We validate the key (prefix lookup → SHA-256 hash comparison)
3. We check the user's credit balance (minimum $0.001 required)
4. We check the key's token limit (if applicable)
5. We forward the request to Moonshot using our single master API key
6. The response streams back to the user in real time
7. After the stream completes, we log usage and deduct credits

The user's key is never exposed to Moonshot. All traffic flows through our single master key.

---

### 4. Pricing & Billing

**How we charge:**

```
Provider cost = (input tokens / 1M × input rate) + (output tokens / 1M × output rate)
User charge   = Provider cost × 1.20   (20% markup)
```

Credits are stored in USD with 6 decimal precision (e.g., `$0.000600` for a small request).

**How users top up:**

Users visit the Billing page and select an amount:

| Amount | Badge |
|---|---|
| $10 | — |
| $25 | — |
| $50 | — |
| $100 | Most Popular |
| $150 | — |
| $200 | — |
| $300 | Best Value |

Payment is processed via **CardTransaction**. On successful payment, the user's credit balance is updated immediately.

**What gets tracked:**
- Every request: model, provider, input tokens, output tokens, cost to us, cost to user, latency
- Every credit movement: top-ups, usage deductions, refunds — full audit trail

---

### 5. User Dashboard

The dashboard at `https://vuzo-api-1.onrender.com` gives users:

| Page | What it shows |
|---|---|
| **Dashboard** | Balance, total requests, total spend, token usage |
| **API Keys** | All keys with usage, limits, last used time; create/revoke |
| **Usage** | Per-request log with model, tokens, cost; daily summary |
| **Billing** | Top-up with card; full transaction history |
| **Models** | kimi-k2.6 (live) + coming soon: OpenAI, Google, Anthropic |
| **Docs** | Integration guide, code examples (Python, JS, cURL) |

---

### 6. Admin Portal

The admin portal at `https://vuzo-api-1.onrender.com/admin` is accessible only to accounts with the `is_admin` flag. It shows:

**Overview tab — business metrics:**
- Total revenue (all-time top-ups received)
- Total provider cost (what we paid Moonshot)
- Gross profit + margin %
- Daily activity chart (last 14 days: topups vs. charged vs. provider cost)

**Users tab:**
- Every registered user with: balance, keys, tokens consumed, total spent, total topped up
- Enable/disable any user account instantly

**API Keys tab:**
- Every key across all users with token usage bar, revenue generated
- Enable/disable individual keys
- Renew a key (revoke + reissue with remaining token budget carried forward)

**Usage Logs tab:**
- Every API request: user, model, tokens, cost, latency, timestamp

**Transactions tab:**
- Every credit movement: user, type (topup/usage/refund), amount, description, timestamp

---

## Security Highlights

| Area | Approach |
|---|---|
| API key storage | SHA-256 hash only — plaintext never persisted |
| Provider keys | Fernet-encrypted at rest in database |
| Secrets | All credentials in environment variables — never in code |
| Auth | Supabase JWT + HMAC webhook signature verification |
| Rate limiting | Sliding window (Supabase-backed — safe across multiple servers) |
| Single-device sessions | New login forces sign-out on existing device |
| Admin access | Separate `is_admin` flag; 403 for all non-admin access |

---

## Key Numbers

| Metric | Value |
|---|---|
| Starter credit per new user | $0.00 |
| Initial token cap (OpenClaw key) | Not enforced by default |
| Our markup over provider cost | 20% |
| Default rate limit | 60 requests/minute per key |
| Credit precision | 6 decimal places (USD) |
| Min balance to make a request | $0.001 |
| Min top-up amount | $10.00 |
| Max top-up amount | $300.00 |

---

## Current Status

- Platform is live and taking registrations
- kimi-k2.6 (Moonshot) is the active model
- CardTransaction payment processing integrated
- Admin portal operational
- More models coming soon: OpenAI (gpt-4o, gpt-4.1), Google (Gemini), Anthropic (Claude)

---

## Codebase

| Location | Contents |
|---|---|
| `backend/` | FastAPI application, routers, services, migrations |
| `frontend/` | React dashboard (user-facing) |
| `render.yaml` | Render.com deployment configuration |
| GitHub | `github.com/AurissoRnD/vuzo-api` |

---

*SimplerClaw is built and maintained by the Aurisso team.*
