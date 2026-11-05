-- ============================================================
-- NETATLAS - SESSIONS IAM SECURISEES
-- Migration 019
-- ============================================================

CREATE TABLE IF NOT EXISTS public.iam_sessions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    user_id INTEGER NOT NULL
        REFERENCES public.users(id) ON DELETE CASCADE,

    token_hash BYTEA NOT NULL UNIQUE
        CHECK (octet_length(token_hash) = 32),

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    last_activity_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    expires_at TIMESTAMPTZ NOT NULL,

    idle_timeout_seconds INTEGER NOT NULL
        CHECK (idle_timeout_seconds BETWEEN 60 AND 86400),

    revoked_at TIMESTAMPTZ,

    revocation_reason TEXT,

    CONSTRAINT iam_sessions_expiration_check
        CHECK (expires_at > created_at),

    CONSTRAINT iam_sessions_activity_check
        CHECK (
            last_activity_at >= created_at
            AND last_activity_at <= expires_at
        ),

    CONSTRAINT iam_sessions_revocation_check
        CHECK (
            revoked_at IS NULL
            OR revoked_at >= created_at
        ),

    CONSTRAINT iam_sessions_revocation_reason_check
        CHECK (
            revoked_at IS NOT NULL
            OR revocation_reason IS NULL
        )
);

CREATE INDEX IF NOT EXISTS idx_iam_sessions_user_id
    ON public.iam_sessions (user_id);

CREATE INDEX IF NOT EXISTS idx_iam_sessions_expires_at
    ON public.iam_sessions (expires_at);

CREATE INDEX IF NOT EXISTS idx_iam_sessions_active_user
    ON public.iam_sessions (user_id, expires_at)
    WHERE revoked_at IS NULL;
