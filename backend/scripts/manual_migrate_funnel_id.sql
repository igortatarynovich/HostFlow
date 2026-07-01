-- Manual migration: add funnel_id to candidate_profiles and ensure funnels tables exist.
-- Run this on production if alembic migrations haven't been applied.
-- PostgreSQL syntax.

-- 1. Create funnels table if not exists
CREATE TABLE IF NOT EXISTS funnels (
    id VARCHAR(36) PRIMARY KEY,
    tenant_id VARCHAR(36) NOT NULL,
    type VARCHAR(32) NOT NULL,
    name VARCHAR(255) NOT NULL,
    is_default BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS ix_funnels_tenant_id ON funnels(tenant_id);
CREATE INDEX IF NOT EXISTS ix_funnels_type ON funnels(type);

-- 2. Create funnel_stages table if not exists
CREATE TABLE IF NOT EXISTS funnel_stages (
    id VARCHAR(36) PRIMARY KEY,
    funnel_id VARCHAR(36) NOT NULL REFERENCES funnels(id) ON DELETE CASCADE,
    code VARCHAR(64) NOT NULL,
    label VARCHAR(255) NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    is_terminal BOOLEAN NOT NULL DEFAULT false,
    UNIQUE(funnel_id, code)
);
CREATE INDEX IF NOT EXISTS ix_funnel_stages_funnel_id ON funnel_stages(funnel_id);

-- 3. Add funnel_id to candidate_profiles if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'candidate_profiles' AND column_name = 'funnel_id'
    ) THEN
        ALTER TABLE candidate_profiles ADD COLUMN funnel_id VARCHAR(36);
        CREATE INDEX ix_candidate_profiles_funnel_id ON candidate_profiles(funnel_id);
    END IF;
END $$;
