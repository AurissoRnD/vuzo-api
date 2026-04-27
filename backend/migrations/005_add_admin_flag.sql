-- Migration 005: Add is_admin flag to users table
-- Run in Supabase SQL Editor

ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN NOT NULL DEFAULT false;

-- To grant admin access to a user (run manually):
-- UPDATE users SET is_admin = true WHERE email = 'your-admin@email.com';
