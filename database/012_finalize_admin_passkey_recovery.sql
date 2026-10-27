BEGIN;

-- ============================================================
-- NETATLAS V0.1 CORE
-- Migration 012 : finalisation atomique de la récupération
-- Passkey administrateur
--
-- IMPORTANT :
-- Cette fonction ne vérifie pas la cryptographie WebAuthn.
-- Son exécution reste interdite au rôle applicatif.
-- ============================================================

CREATE FUNCTION public.finaliser_recuperation_passkey_admin(
    p_token_hash bytea,
    p_challenge_hash bytea,
    p_session_binding_hash bytea,
    p_credential_id bytea,
    p_public_key bytea,
    p_sign_count integer
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    v_admin_id integer;
    v_recovery_id bigint;
    v_challenge_id bigint;
    v_credential_db_id bigint;
    v_requested_by text;
BEGIN

    -- --------------------------------------------------------
    -- 1. Validation des paramètres
    -- --------------------------------------------------------

    IF p_token_hash IS NULL
       OR octet_length(p_token_hash) <> 32
       OR p_challenge_hash IS NULL
       OR octet_length(p_challenge_hash) <> 32
       OR p_session_binding_hash IS NULL
       OR octet_length(p_session_binding_hash) <> 32
       OR p_credential_id IS NULL
       OR octet_length(p_credential_id) = 0
       OR p_public_key IS NULL
       OR octet_length(p_public_key) = 0
       OR p_sign_count IS NULL
       OR p_sign_count < 0
    THEN
        RETURN NULL;
    END IF;

    -- --------------------------------------------------------
    -- 2. Identifier l'administrateur configuré
    -- --------------------------------------------------------

    SELECT c.admin_user_id
    INTO v_admin_id
    FROM public.passkey_recovery_config c
    WHERE c.id = 1;

    IF v_admin_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- --------------------------------------------------------
    -- 3. Verrouiller le compte administrateur
    -- --------------------------------------------------------

    PERFORM 1
    FROM public.users u
    WHERE u.id = v_admin_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- --------------------------------------------------------
    -- 4. Vérifier le rôle administrateur
    -- --------------------------------------------------------

    PERFORM 1
    FROM public.role_user ru
    JOIN public.roles r
      ON r.id = ru.role_id
    WHERE ru.user_id = v_admin_id
      AND r.nom = 'admin';

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- --------------------------------------------------------
    -- 5. Verrouiller et vérifier l'autorisation SSH
    -- --------------------------------------------------------

    SELECT
        pr.id,
        pr.requested_by
    INTO
        v_recovery_id,
        v_requested_by
    FROM public.passkey_recovery pr
    WHERE pr.user_id = v_admin_id
      AND pr.token_hash = p_token_hash
      AND pr.consumed_at IS NULL
      AND pr.expires_at > clock_timestamp()
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- --------------------------------------------------------
    -- 6. Verrouiller et vérifier le challenge WebAuthn
    -- --------------------------------------------------------

    SELECT wc.id
    INTO v_challenge_id
    FROM public.webauthn_challenges wc
    WHERE wc.recovery_id = v_recovery_id
      AND wc.user_id = v_admin_id
      AND wc.operation = 'admin_recovery'
      AND wc.challenge_hash = p_challenge_hash
      AND wc.session_binding_hash = p_session_binding_hash
      AND wc.consumed_at IS NULL
      AND wc.expires_at > clock_timestamp()
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN NULL;
    END IF;

    -- --------------------------------------------------------
    -- 7. Enregistrer la nouvelle Passkey
    -- Les anciennes Passkeys sont conservées.
    -- --------------------------------------------------------

    INSERT INTO public.webauthn_credentials (
        user_id,
        credential_id,
        public_key,
        sign_count
    )
    VALUES (
        v_admin_id,
        p_credential_id,
        p_public_key,
        p_sign_count
    )
    RETURNING id
    INTO v_credential_db_id;

    -- --------------------------------------------------------
    -- 8. Consommer définitivement le challenge
    -- --------------------------------------------------------

    UPDATE public.webauthn_challenges
    SET consumed_at = clock_timestamp()
    WHERE id = v_challenge_id;

    -- --------------------------------------------------------
    -- 9. Consommer définitivement l'autorisation SSH
    -- --------------------------------------------------------

    UPDATE public.passkey_recovery
    SET consumed_at = clock_timestamp()
    WHERE id = v_recovery_id;

    -- --------------------------------------------------------
    -- 10. Journaliser la récupération
    -- --------------------------------------------------------

    INSERT INTO public.passkey_recovery_audit (
        user_id,
        action,
        requested_by
    )
    VALUES (
        v_admin_id,
        'completed',
        v_requested_by
    );

    RETURN v_credential_db_id;

END;
$$;

-- ============================================================
-- SÉCURITÉ : aucun accès applicatif à ce stade
-- ============================================================

REVOKE ALL ON FUNCTION
    public.finaliser_recuperation_passkey_admin(
        bytea,
        bytea,
        bytea,
        bytea,
        bytea,
        integer
    )
FROM PUBLIC;

-- Aucune permission accordée à netatlas_test_user.
-- Aucune permission accordée à netatlas-recovery.
--
-- L'exécution reste réservée au propriétaire de la fonction
-- et aux rôles disposant de privilèges supérieurs appropriés.

COMMIT;
