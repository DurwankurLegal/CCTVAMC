-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable Row-Level Security helper: app sets this per-request
-- Usage: SET LOCAL app.tenant_id = '<uuid>';
-- RLS policies reference current_setting('app.tenant_id')::uuid
