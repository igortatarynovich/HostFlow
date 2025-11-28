

BEGIN;

-- 1) Таблица доступа (access records)
CREATE TABLE IF NOT EXISTS candidate_portal_access (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    candidate_id UUID NOT NULL,
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_cpa_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    CONSTRAINT cpa_expires_future CHECK (expires_at > created_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cpa_token_hash ON candidate_portal_access(token_hash);
CREATE INDEX IF NOT EXISTS idx_cpa_candidate ON candidate_portal_access(candidate_id);
CREATE INDEX IF NOT EXISTS idx_cpa_active ON candidate_portal_access(tenant_id) WHERE is_enabled = TRUE;

-- 2) Таблица сессий (magic link sessions)
CREATE TABLE IF NOT EXISTS candidate_portal_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    candidate_id UUID NOT NULL,
    access_id UUID NOT NULL,
    token_hash TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    ip INET,
    user_agent TEXT,
    status TEXT NOT NULL DEFAULT 'active', -- active | revoked | expired
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_cps_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    CONSTRAINT fk_cps_access FOREIGN KEY (access_id) REFERENCES candidate_portal_access(id) ON DELETE CASCADE,
    CONSTRAINT cps_status_chk CHECK (status IN ('active','revoked','expired')),
    CONSTRAINT cps_expire_future CHECK (expires_at > issued_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_cps_token_hash ON candidate_portal_sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_cps_candidate ON candidate_portal_sessions(candidate_id);
CREATE INDEX IF NOT EXISTS idx_cps_status_active ON candidate_portal_sessions(tenant_id, status) WHERE status = 'active';

-- 3) Таблица согласий (RODO/consents)
CREATE TABLE IF NOT EXISTS candidate_consents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL,
    candidate_id UUID NOT NULL,
    consent_code TEXT NOT NULL,
    text_version TEXT NOT NULL,
    accepted BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address TEXT,
    user_agent TEXT,
    payload JSONB,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_cc_candidate FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    CONSTRAINT cc_revoked_after_accept CHECK (revoked_at IS NULL OR revoked_at >= accepted_at)
);

-- Уникальность активного согласия по коду и версии
CREATE UNIQUE INDEX IF NOT EXISTS uq_cc_active ON candidate_consents(candidate_id, consent_code, text_version)
WHERE revoked_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cc_candidate ON candidate_consents(candidate_id);

-- 4) Представление: активная сессия кандидата (для API /me)
CREATE OR REPLACE VIEW v_candidate_portal_active_sessions AS
SELECT s.*
FROM candidate_portal_sessions s
JOIN candidate_portal_access a ON a.id = s.access_id
WHERE s.status = 'active' AND s.expires_at > now() AND a.is_enabled = TRUE;

-- 5) Представление: сводка согласий кандидата
CREATE OR REPLACE VIEW v_candidate_consents_active AS
SELECT c.candidate_id,
       json_agg(json_build_object('code', c.consent_code, 'version', c.text_version, 'accepted_at', c.accepted_at) ORDER BY c.accepted_at DESC) AS consents
FROM candidate_consents c
WHERE c.revoked_at IS NULL
GROUP BY c.candidate_id;

-- 6) RLS политики
ALTER TABLE candidate_portal_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_portal_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE candidate_consents ENABLE ROW LEVEL SECURITY;

-- Изоляция по tenant
CREATE POLICY IF NOT EXISTS rls_cpa_tenant ON candidate_portal_access USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY IF NOT EXISTS rls_cps_tenant ON candidate_portal_sessions USING (tenant_id = current_setting('app.tenant_id')::uuid);
CREATE POLICY IF NOT EXISTS rls_cc_tenant ON candidate_consents USING (tenant_id = current_setting('app.tenant_id')::uuid);

-- Только владельцы записей-кандидаты (опционально, если применяется session candidate_id)
-- Пример: дать чтение кандидату своих согласий при установке current_setting('app.candidate_id')
CREATE POLICY IF NOT EXISTS rls_cc_candidate_read ON candidate_consents FOR SELECT USING (
    tenant_id = current_setting('app.tenant_id')::uuid AND
    ( current_setting('app.role', true) = 'CANDIDATE' AND candidate_id = current_setting('app.candidate_id')::uuid )
);

-- 7) Триггеры для авто-истечения сессий (upsert статус)
CREATE OR REPLACE FUNCTION trg_cps_auto_expire()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.expires_at <= now() THEN
    NEW.status := 'expired';
  END IF;
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS t_cps_auto_expire_insupd ON candidate_portal_sessions;
CREATE TRIGGER t_cps_auto_expire_insupd
BEFORE INSERT OR UPDATE ON candidate_portal_sessions
FOR EACH ROW EXECUTE FUNCTION trg_cps_auto_expire();

COMMIT;
