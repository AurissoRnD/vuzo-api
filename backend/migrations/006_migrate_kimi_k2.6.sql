-- Migration 006: Migrate from kimi-k2.5 to kimi-k2.6
-- Run in Supabase SQL Editor

-- Disable kimi-k2.5
UPDATE model_pricing SET is_active = false WHERE model_name = 'kimi-k2.5';

-- Insert kimi-k2.6 if not already present, otherwise update pricing
INSERT INTO model_pricing (provider, model_name, input_price_per_million, output_price_per_million, vuzo_markup_percent, is_active)
VALUES ('moonshot', 'kimi-k2.6', 0.95, 4.00, 20.0, true)
ON CONFLICT (model_name) DO UPDATE
  SET input_price_per_million  = 0.95,
      output_price_per_million = 4.00,
      vuzo_markup_percent      = 20.0,
      is_active                = true;
