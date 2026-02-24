# Vuzo API

Unified LLM API proxy. One key for OpenAI, xAI (Grok), Google (Gemini), and Anthropic (Claude).

**Live:** [vuzo-api.onrender.com](https://vuzo-api.onrender.com) · **Dashboard:** [vuzo-dashboard.onrender.com](https://vuzo-dashboard.onrender.com)

## Quick Start (local)

```bash
# Backend
cd backend
cp .env.example .env    # fill in your values
pip install -r requirements.txt
python run.py            # starts on http://localhost:8000

# Frontend (separate terminal)
cd frontend
cp .env.example .env    # set VITE_API_BASE_URL=http://localhost:8000
npm install
npm run dev              # starts on http://localhost:5173
```

## How It Works

1. Users sign up and get a Vuzo API key (`vz-sk_...`).
2. Send requests to `POST /v1/chat/completions` with any supported model name.
3. Vuzo routes the request to the correct provider (OpenAI, xAI, Google, Anthropic).
4. Token usage is tracked and credits are deducted per request using a configurable markup.

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/v1/chat/completions` | API key | OpenAI-compatible LLM proxy |
| GET | `/v1/models` | — | List all models + pricing |
| GET | `/v1/models/{model_name}` | — | Single model pricing details |
| POST | `/v1/api-keys` | JWT | Create a new API key |
| GET | `/v1/api-keys` | JWT | List your API keys |
| DELETE | `/v1/api-keys/{key_id}` | JWT | Revoke an API key |
| GET | `/v1/usage` | JWT | Usage logs (filterable) |
| GET | `/v1/usage/summary` | JWT | Aggregated usage summary |
| GET | `/v1/usage/daily` | JWT | Per-day, per-model breakdown |
| GET | `/v1/billing/balance` | JWT | Check credit balance |
| GET | `/v1/billing/transactions` | JWT | Transaction history |
| POST | `/v1/billing/checkout` | JWT | Create Polar checkout session (production top-up) |
| POST | `/v1/webhooks/polar` | — | Polar webhook (credits user on payment) |
| GET | `/health` | — | Health check |

## Environment Variables

Backend config lives in `backend/.env`. See `backend/.env.example` for all required values.

Frontend config lives in `frontend/.env`. See `frontend/.env.example`.

## Deployment

Deployed on [Render](https://render.com) via `render.yaml` — two services:
- `vuzo-api` — Python/FastAPI backend (`backend/` root dir)
- `vuzo-dashboard` — React SPA (`frontend/` root dir)

## Docs

- [INTERNAL.md](INTERNAL.md) — architecture, DB schema, auth, billing, pricing
- [CHANGELOG.md](CHANGELOG.md) — version history
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — how this repo and the Python SDK connect

---

## Document History

| Date | Change |
|------|--------|
| 2026-02-19 | Updated quick start commands to reference `backend/` folder; added all new endpoints to table; fixed env file references |
| 2026-02-17 | Initial document created |
