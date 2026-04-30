# SimplerClaw — Product Features
**April 2026**

---

## What SimplerClaw Does

SimplerClaw is the AI infrastructure layer behind OpenClaw. It sits between the OpenClaw app and the AI model — handling access, billing, usage tracking, and real-time communication — so users never need to manage their own provider accounts or API keys.

When someone installs OpenClaw via the SimplerClaw installer, everything is set up automatically. They just use OpenClaw normally, and SimplerClaw handles the rest behind the scenes.

---

## Core Features

### 1. Automatic Key Provisioning
When a user installs OpenClaw, SimplerClaw automatically:
- Creates their account
- Issues a unique `vz-sk_` API key
- Injects it into their OpenClaw configuration
- Balance starts at $0 — user tops up via CardTransaction

No manual setup. No separate accounts. One installer, done.

---

### 2. AI Model Access
SimplerClaw currently provides access to **Moonshot kimi-k2.6** — a state-of-the-art multimodal model supporting text, image, and video input with a 256K context window.

All requests route through SimplerClaw's infrastructure using a single master key. Users never need a Moonshot account.

**Coming soon:** OpenAI (GPT-4o, GPT-4.1), Google (Gemini), Anthropic (Claude)

---

### 3. Credit-Based Billing
Users top up their balance via **CardTransaction** and are charged per request based on token usage.

- Pricing: Moonshot's provider rate + 35% markup
- Credits stored in USD with 6 decimal precision (sub-cent accuracy)
- Top-up amounts: $10, $25, $50, $100, $150, $200, $300
- Full transaction history available in the dashboard

---

### 4. Usage Tracking
Every AI request is logged with full detail:
- Model used
- Input and output token counts
- Cost charged to the user
- Provider cost (what we paid)
- Response latency
- Timestamp

Users can view per-request logs, daily breakdowns, and all-time summaries from their dashboard.

---

### 5. User Dashboard
A web dashboard at `simplerclaw.com` gives users full visibility into their account:

| Page | What it shows |
|---|---|
| Dashboard | Balance, total requests, total spend, token usage |
| API Keys | Active keys, token limits, last used time |
| Usage | Per-request log, daily summary, cost breakdown |
| Billing | Top up credits, transaction history |
| Models | Available models and pricing |
| Docs | Integration guide and code examples |

---

### 6. Real-Time Balance Tracking (WebSocket)

This is one of SimplerClaw's most distinctive features — a persistent real-time connection between the app and our backend.

**How it works:**
When the OpenClaw app launches, it opens a WebSocket connection to SimplerClaw using the user's key. This connection stays open and receives live events as things happen.

**Events the app receives:**

| Event | When it fires |
|---|---|
| `stream_start` | The moment the AI starts generating a response |
| `stream_delta` | After each chunk of the AI's response — for real-time balance animation |
| `usage` | When the full response is complete — authoritative balance update |
| `low_balance` | Balance drops below $1.00 |
| `low_tokens` | Balance drops below $0.50 |
| `out_of_tokens` | Balance drops below $0.01 |
| `topup` | The instant a payment is confirmed — balance jumps immediately |
| `ping` | Every 30 seconds — keeps connection alive |

**What this enables:**
- Balance bar that depletes in real time as the AI types (like a health bar in a game)
- Instant balance jump the moment a top-up is processed — no need to refresh or wait for the next message
- Low balance alerts delivered directly to the app as native notifications
- No polling — all push-based, zero wasted requests

**The two-phase balance display:**
1. While the AI is typing → balance decreases smoothly with each chunk (`stream_delta`)
2. When complete → balance snaps to the exact authoritative value (`usage`)

This gives a fluid, real-time feel without sacrificing accuracy.

---

### 7. Per-Key Token Limits
Each API key can have an optional token cap. OpenClaw keys are issued with a 500,000 token limit by default.

- Enforced on every request before it reaches the AI
- If the limit is hit, the request is rejected with a clear error message
- Admin can renew a key and carry forward the remaining token budget

---

### 8. Single-Device Session Enforcement
A user can only be logged in on one device at a time. Logging in from a new device automatically signs out the previous session. This prevents unauthorised key sharing.

---

### 9. Rate Limiting
Each API key has a default rate limit of 60 requests per minute, enforced at the infrastructure level. Limits are configurable per key.

---

### 10. Admin Portal
A separate admin-only portal at `/admin` gives the business full visibility and control:

**Visibility:**
- Total revenue (all-time top-ups received)
- Provider cost (what we paid Moonshot)
- Gross profit and margin %
- Daily activity chart (top-ups vs. charges vs. costs)
- Per-user breakdown: balance, spend, tokens, keys
- Per-key breakdown: usage, revenue generated, token burn rate
- Full usage log across all users
- Full transaction ledger across all users

**Controls:**
- Enable or disable any user account instantly
- Enable or disable any API key instantly
- Renew a key (revokes old, issues new with remaining token budget carried forward)

---

## Security

- API keys stored as SHA-256 hashes — plaintext never saved
- Provider master keys encrypted at rest (Fernet encryption)
- All secrets in environment variables — never in code
- Webhook signatures verified (HMAC-SHA256)
- Admin access gated by a separate database flag — not just a password
- Rate limiting enforced at infrastructure level

---

## What's Live Today

| Feature | Status |
|---|---|
| Installer-based onboarding | ✅ Live |
| kimi-k2.6 via Moonshot | ✅ Live |
| Credit billing via CardTransaction | ✅ Live |
| User dashboard | ✅ Live |
| Admin portal | ✅ Live |
| Real-time WebSocket events | ✅ Live |
| stream_delta for health-bar UI | ✅ Live (app integration in progress) |
| OpenAI / Google / Anthropic models | 🔜 Coming soon |

---

*SimplerClaw is built and operated by the Aurisso team.*
