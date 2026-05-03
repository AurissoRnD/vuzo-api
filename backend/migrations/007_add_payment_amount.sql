-- Migration 007: Add payment_amount to credit_transactions
-- Tracks the actual cash received, which may differ from credits issued
-- (e.g. Starter: paid $19, credited $10)
-- Run in Supabase SQL Editor

ALTER TABLE credit_transactions
  ADD COLUMN IF NOT EXISTS payment_amount NUMERIC(12, 6) NULL;

-- NULL means payment_amount = amount (regular top-ups where cash = credits)
-- Set value only for package purchases where they differ
