-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Row-Level Security context
-- The application sets the tenant context per request via the repository layer:
--   SELECT set_config('app.tenant_id', '<uuid>', true);   -- transaction-local
-- RLS policies reference current_setting('app.tenant_id', true)::uuid
--
-- IMPORTANT (production): the application MUST connect as a NON-superuser,
-- NON-owner role. Superusers and the table owner bypass RLS even with
-- FORCE ROW LEVEL SECURITY, so tenant isolation would not be enforced.
-- Provision a dedicated app role with only DML privileges, e.g.:
--
--   CREATE ROLE cctv_app LOGIN PASSWORD '...';
--   GRANT USAGE ON SCHEMA public TO cctv_app;
--   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO cctv_app;
--   ALTER DEFAULT PRIVILEGES IN SCHEMA public
--     GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO cctv_app;
--
-- Run migrations as the owner/admin role; run the API/worker as cctv_app.
