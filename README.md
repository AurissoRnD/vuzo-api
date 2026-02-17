# Vuzo API

Unified LLM API proxy service. One API key for OpenAI, Claude, and Gemini.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Copy env template and fill in your values
cp .env.example .env

# Run the SQL migration against your Supabase project (via SQL editor in dashboard)
# See migrations/001_initial_schema.sql

# Start the server
python run.py
```

## How It Works

1. Users get a Vuzo API key (`vz-...` format).
2. Send requests to `POST /v1/chat/completions` with any supported model name.
3. Vuzo routes the request to the correct provider (OpenAI, Anthropic, Google).
4. Token usage is tracked and credits are deducted with a configurable markup.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/chat/completions` | OpenAI-compatible LLM proxy |
| GET | `/v1/models` | List available models + pricing |
| POST | `/v1/api-keys` | Create a new API key |
| GET | `/v1/api-keys` | List your API keys |
| DELETE | `/v1/api-keys/{key_id}` | Revoke an API key |
| GET | `/v1/usage` | Usage logs (filterable) |
| GET | `/v1/usage/summary` | Aggregated usage summary |
| GET | `/v1/billing/balance` | Check credit balance |
| POST | `/v1/billing/topup` | Add credits |
| GET | `/v1/billing/transactions` | Transaction history |

## Environment Variables

See `.env.example` for all required configuration.
