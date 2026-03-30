-- Idempotent: add custom_field_values.created_at (ORM TimestampMixin; original table had only updated_at).
-- Use if `alembic upgrade head` reports no work but GET /leads still fails with
--   column custom_field_values.created_at does not exist

DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.tables
    WHERE table_schema = 'public' AND table_name = 'custom_field_values'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'custom_field_values' AND column_name = 'created_at'
  ) THEN
    ALTER TABLE custom_field_values ADD COLUMN created_at TIMESTAMPTZ;
    UPDATE custom_field_values SET created_at = updated_at WHERE created_at IS NULL;
    ALTER TABLE custom_field_values ALTER COLUMN created_at SET NOT NULL;
    ALTER TABLE custom_field_values ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;
    RAISE NOTICE 'custom_field_values.created_at added';
  ELSE
    RAISE NOTICE 'custom_field_values.created_at already present or table missing — skipped';
  END IF;
END $$;
