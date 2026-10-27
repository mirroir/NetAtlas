-- ============================================================
-- NETATLAS - LIMITATION DES TENTATIVES PASSKEY
-- Migration 004
-- ============================================================

CREATE TABLE IF NOT EXISTS public.passkey_rate_limits (
    key_hash BYTEA PRIMARY KEY
        CHECK (octet_length(key_hash) = 32),

    attempts INTEGER NOT NULL DEFAULT 0
        CHECK (attempts >= 0),

    window_started_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_passkey_rate_limits_updated_at
    ON public.passkey_rate_limits (updated_at);
