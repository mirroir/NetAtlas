-- ============================================================
-- NETATLAS - RECUPERATION PASSKEY
-- Migration 011 - Preparation securisee du challenge
-- ============================================================

BEGIN;

CREATE FUNCTION public.preparer_recuperation_passkey_admin(
    p_token_hash bytea,
    p_challenge_hash bytea,
    p_session_binding_hash bytea
)
RETURNS TABLE (
    user_id integer,
    nom text
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    v_admin_id integer;
    v_recovery_id bigint;
    v_expires_at timestamptz;
    v_nom text;
BEGIN
    -- Validation des empreintes.
    IF p_token_hash IS NULL
       OR octet_length(p_token_hash) <> 32
       OR p_challenge_hash IS NULL
       OR octet_length(p_challenge_hash) <> 32
       OR p_session_binding_hash IS NULL
       OR octet_length(p_session_binding_hash) <> 32 THEN
        RETURN;
    END IF;

    -- Administrateur autorise par configuration.
    SELECT c.admin_user_id
    INTO v_admin_id
    FROM public.passkey_recovery_config c
    WHERE c.id = 1;

    IF v_admin_id IS NULL THEN
        RETURN;
    END IF;

    -- Verrouiller le compte administrateur.
    SELECT u.nom
    INTO v_nom
    FROM public.users u
    WHERE u.id = v_admin_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Verifier le role administrateur actuel.
    PERFORM 1
    FROM public.role_user ru
    JOIN public.roles r ON r.id = ru.role_id
    WHERE ru.user_id = v_admin_id
      AND r.nom = 'admin';

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Verrouiller l'autorisation SSH correspondante.
    SELECT pr.id, pr.expires_at
    INTO v_recovery_id, v_expires_at
    FROM public.passkey_recovery pr
    WHERE pr.token_hash = p_token_hash
      AND pr.user_id = v_admin_id
      AND pr.consumed_at IS NULL
      AND pr.expires_at > clock_timestamp()
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN;
    END IF;

    -- Une autorisation ne peut produire qu'un seul challenge.
    IF EXISTS (
        SELECT 1
        FROM public.webauthn_challenges wc
        WHERE wc.recovery_id = v_recovery_id
    ) THEN
        RETURN;
    END IF;

    -- Creer le challenge avec une expiration maximale de 60 s.
    INSERT INTO public.webauthn_challenges (
        challenge_hash,
        session_binding_hash,
        user_id,
        operation,
        expires_at,
        recovery_id
    )
    VALUES (
        p_challenge_hash,
        p_session_binding_hash,
        v_admin_id,
        'admin_recovery',
        LEAST(
            clock_timestamp() + INTERVAL '60 seconds',
            v_expires_at
        ),
        v_recovery_id
    );

    user_id := v_admin_id;
    nom := v_nom;

    RETURN NEXT;
END;
$$;

-- Retirer l'autorisation implicite accordee a PUBLIC.
REVOKE ALL ON FUNCTION
    public.preparer_recuperation_passkey_admin(
        bytea, bytea, bytea
    )
FROM PUBLIC;

-- Autoriser uniquement le compte applicatif de test.
GRANT EXECUTE ON FUNCTION
    public.preparer_recuperation_passkey_admin(
        bytea, bytea, bytea
    )
TO netatlas_test_user;

COMMIT;
