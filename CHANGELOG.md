# Changelog

All notable changes to the **Vuzo API** product are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

---

## [1.2.0] — 2026-02-19

### Changed
- **Security**: Polar product IDs moved from frontend env vars (`VITE_POLAR_PRODUCT_*`) to backend config (`POLAR_PRODUCT_*`). Product IDs are now resolved server-side; the frontend sends a `tier` ("10"/"30"/"50") or `amount` — never a product ID.
- `POST /v1/billing/checkout` request body changed from `{product_id, amount?}` to `{tier?, amount?}`.
- `backend/` folder created. All Python source (`app/`, `tests/`, `run.py`, `requirements.txt`, `migrations/`) moved under `backend/`. `render.yaml` updated with `rootDir: backend`.
- Python SDK docs page added to dashboard at `/sdk-docs`. Nav item "Python SDK" added to sidebar.
- Stale "Google (Gemini) — coming soon" label in OpenClaw docs fixed to "fully compatible".

### Added
- `POLAR_PRODUCT_10`, `POLAR_PRODUCT_30`, `POLAR_PRODUCT_50`, `POLAR_PRODUCT_CUSTOM` env vars in backend config.
- `docs/ARCHITECTURE.md` — explains how the Python SDK and Vuzo API connect.
- `CHANGELOG.md` (this file) for public change tracking.
- `vuzo-python/DOCS.md` — full SDK API reference.
- `vuzo-python/INTERNAL.md` — SDK development and contribution guide.

---

## [1.1.0] — 2026-02-19

### Added
- **Polar payments** — `POST /v1/billing/checkout` and `POST /v1/webhooks/polar`. Preset tiers ($10, $30, $50) and custom "Pay what you want" amounts (min $10). Webhook credits user balance on `order.created`.
- Billing dashboard updated with preset buttons and custom amount input.
- `GET /v1/models/{model_name}` — fetch a single model's pricing details directly.
- Supabase-backed rate limiter — replaced in-memory sliding window with `rate_limit_requests` table. Fails open if DB unreachable.
- `POST /v1/billing/topup` restricted to non-production (`APP_ENV != production`). In production, users must top up via Polar.
- Test suite (`tests/`) with pytest: `test_pricing.py`, `test_providers.py`, `test_crypto.py`, `test_schemas.py`, `test_rate_limiter.py`.

### Changed
- `GET /v1/models` response now uses `_row_to_item()` helper, keeping list and single-model endpoints consistent.
- INTERNAL.md — added changelog section, cleaned up OpenClaw notes, updated SDK ↔ API mapping table.

---

## [1.0.0] — 2026-02-17

### Added
- FastAPI backend with Supabase for auth, billing, usage, and API key management.
- `POST /v1/chat/completions` — OpenAI-compatible proxy endpoint routing to OpenAI, xAI (Grok), Google (Gemini), and Anthropic (Claude).
- Provider response normalisation — all provider responses converted to OpenAI format (choices, usage, finish_reason).
- Streaming (`stream: true`) support for all providers via SSE.
- `GET /v1/models` — list all available models with pricing.
- JWT auth middleware via Supabase JWT secret.
- Per-key rate limiter middleware (60 RPM default).
- Credit billing: deduct cost per request, track in `credit_transactions` table.
- Usage logging: every request stored in `usage_logs` table.
- React dashboard (`frontend/`) with pages: Dashboard, API Keys, Usage, Billing, Models, Docs.
- Deployed on Render: `vuzo-api` (Python) + `vuzo-dashboard` (static).
- `render.yaml` for one-click Render deployment.
