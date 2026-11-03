-- ============================================================
-- NETATLAS V0.1 CORE
-- Migration 015 - Contexte temporaire de recuperation Passkey
-- ============================================================

BEGIN;

CREATE TABLE public.passkey_recovery_context (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    challenge_id bigint NOT NULL UNIQUE,

    context_hash bytea NOT NULL UNIQUE,

    challenge bytea NOT NULL,

    created_at timestamptz NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT passkey_recovery_context_challenge_fk
        FOREIGN KEY (challenge_id)
        REFERENCES public.webauthn_challenges(id)
        ON DELETE RESTRICT,

    CONSTRAINT passkey_recovery_context_hash_check
        CHECK (octet_length(context_hash) = 32),

    CONSTRAINT passkey_recovery_context_challenge_check
        CHECK (octet_length(challenge) BETWEEN 16 AND 1024)
);

ALTER TABLE public.passkey_recovery_context
    ENABLE ROW LEVEL SECURITY;

ALTER TABLE public.passkey_recovery_context
    FORCE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.passkey_recovery_context
    FROM PUBLIC, netatlas_test_user;

REVOKE ALL ON SEQUENCE
    public.passkey_recovery_context_id_seq
    FROM PUBLIC, netatlas_test_user;

COMMIT;
