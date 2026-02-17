-- Add Supabase Auth ID to users table
-- Links our custom users table to Supabase Auth (auth.users)

ALTER TABLE users
    ADD COLUMN supabase_auth_id UUID UNIQUE;

CREATE INDEX idx_users_supabase_auth ON users (supabase_auth_id);
