-- Vuzo API: Initial Schema
-- Run this in your Supabase SQL Editor

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- USERS
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_email ON users (email);

-- ============================================================
-- API KEYS (Vuzo keys issued to users)
-- ============================================================
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_prefix TEXT NOT NULL,
    key_hash TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    is_active BOOLEAN NOT NULL DEFAULT true,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 60,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_prefix ON api_keys (key_prefix);
CREATE INDEX idx_api_keys_user ON api_keys (user_id);

-- ============================================================
-- CREDITS (user balances in USD)
-- ============================================================
CREATE TABLE credits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- CREDIT TRANSACTIONS (top-ups, deductions, refunds)
-- ============================================================
CREATE TYPE transaction_type AS ENUM ('topup', 'usage', 'refund');

CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    amount NUMERIC(12, 6) NOT NULL,
    type transaction_type NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_credit_transactions_user ON credit_transactions (user_id);
CREATE INDEX idx_credit_transactions_created ON credit_transactions (created_at);

-- ============================================================
-- MODEL PRICING (provider cost + Vuzo markup)
-- ============================================================
CREATE TABLE model_pricing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    model_name TEXT UNIQUE NOT NULL,
    input_price_per_million NUMERIC(10, 4) NOT NULL,
    output_price_per_million NUMERIC(10, 4) NOT NULL,
    vuzo_markup_percent NUMERIC(5, 2) NOT NULL DEFAULT 20.00,
    is_active BOOLEAN NOT NULL DEFAULT true,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_model_pricing_model ON model_pricing (model_name);

-- ============================================================
-- USAGE LOGS (per-request token tracking)
-- ============================================================
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    provider_cost NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    vuzo_cost NUMERIC(12, 6) NOT NULL DEFAULT 0.000000,
    response_time_ms INTEGER NOT NULL DEFAULT 0,
    status_code INTEGER NOT NULL DEFAULT 200,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_usage_logs_user ON usage_logs (user_id);
CREATE INDEX idx_usage_logs_created ON usage_logs (created_at);
CREATE INDEX idx_usage_logs_model ON usage_logs (model);

-- ============================================================
-- PROVIDER KEYS (Vuzo's master keys, encrypted at rest)
-- ============================================================
CREATE TABLE provider_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT UNIQUE NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- SEED DATA: Model Pricing
-- ============================================================

-- OpenAI models
INSERT INTO model_pricing (provider, model_name, input_price_per_million, output_price_per_million, vuzo_markup_percent) VALUES
    ('openai', 'gpt-4o', 2.5000, 10.0000, 20.00),
    ('openai', 'gpt-4o-mini', 0.1500, 0.6000, 20.00),
    ('openai', 'gpt-4.1', 2.0000, 8.0000, 20.00),
    ('openai', 'gpt-4.1-mini', 0.4000, 1.6000, 20.00),
    ('openai', 'gpt-4.1-nano', 0.1000, 0.4000, 20.00);

-- Anthropic models
INSERT INTO model_pricing (provider, model_name, input_price_per_million, output_price_per_million, vuzo_markup_percent) VALUES
    ('anthropic', 'claude-sonnet-4-20250514', 3.0000, 15.0000, 20.00),
    ('anthropic', 'claude-haiku-4-5', 1.0000, 5.0000, 20.00),
    ('anthropic', 'claude-opus-4-5', 5.0000, 25.0000, 20.00);

-- Google models
INSERT INTO model_pricing (provider, model_name, input_price_per_million, output_price_per_million, vuzo_markup_percent) VALUES
    ('google', 'gemini-2.0-flash', 0.1000, 0.4000, 20.00),
    ('google', 'gemini-3-flash', 0.5000, 3.0000, 20.00);
