-- ============================================================
-- NETATLAS - MIGRATION 022
-- Registre des migrations PostgreSQL
-- ============================================================
--
-- Historique des migrations executees ou verifiees.
-- Aucune migration historique n'est inscrite automatiquement.
--
-- Execution reservee au role d'administration.
-- ============================================================

BEGIN;

CREATE TABLE public.schema_migrations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    migration_key VARCHAR(255) NOT NULL UNIQUE,

    file_path TEXT NOT NULL,

    checksum_sha256 CHAR(64) NOT NULL,

    application_mode VARCHAR(20) NOT NULL,

    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT schema_migrations_checksum_format
        CHECK (checksum_sha256 ~ '^[0-9a-f]{64}$'),

    CONSTRAINT schema_migrations_application_mode
        CHECK (
            application_mode IN (
                'executed',
                'baseline'
            )
        ),

    CONSTRAINT schema_migrations_file_path_not_empty
        CHECK (LENGTH(BTRIM(file_path)) > 0)
);

COMMENT ON TABLE public.schema_migrations IS
    'Historique controle des migrations PostgreSQL NetAtlas';

COMMENT ON COLUMN public.schema_migrations.application_mode IS
    'executed : migration executee ; baseline : historique verifie';

REVOKE ALL ON TABLE public.schema_migrations FROM PUBLIC;

REVOKE ALL ON SEQUENCE
    public.schema_migrations_id_seq
FROM PUBLIC;

COMMIT;
