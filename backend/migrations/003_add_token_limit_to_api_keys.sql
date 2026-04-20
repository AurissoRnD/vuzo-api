-- Add optional token limit to API keys.
-- NULL means unlimited. The installer sets 500,000 for OpenClaw keys.
ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS token_limit INTEGER DEFAULT NULL;
