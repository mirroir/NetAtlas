-- ============================================================
-- NETATLAS V0.1 CORE
-- Migration 013 : identification sécurisée de l'administrateur
-- pendant une récupération Passkey.
--
-- Environnement initial : netatlas_test uniquement.
-- ============================================================

BEGIN;

CREATE FUNCTION public.identifier_admin_recuperation_passkey(
    p_token_hash bytea
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
BEGIN

    -- 1. Vérifier le format de l'empreinte.
    IF p_token_hash IS NULL
       OR octet_length(p_token_hash) <> 32 THEN
        RETURN;
    END IF;

    -- 2. Identifier l'administrateur configuré.
    SELECT c.admin_user_id
    INTO v_admin_id
    FROM public.passkey_recovery_config c
    WHERE c.id = 1;

    IF v_admin_id IS NULL THEN
        RETURN;
    END IF;

    -- 3. Vérifier le compte et son rôle administrateur.
    IF NOT EXISTS (
        SELECT 1
        FROM public.users u
        JOIN public.role_user ru
          ON ru.user_id = u.id
        JOIN public.roles r
          ON r.id = ru.role_id
        WHERE u.id = v_admin_id
          AND r.nom = 'admin'
    ) THEN
        RETURN;
    END IF;

    -- 4. Vérifier l'autorisation SSH temporaire.
    IF NOT EXISTS (
        SELECT 1
        FROM public.passkey_recovery pr
        WHERE pr.user_id = v_admin_id
          AND pr.token_hash = p_token_hash
          AND pr.consumed_at IS NULL
          AND pr.expires_at > clock_timestamp()
    ) THEN
        RETURN;
    END IF;

    -- 5. Retourner uniquement les informations nécessaires.
    RETURN QUERY
    SELECT u.id, u.nom::text
    FROM public.users u
    WHERE u.id = v_admin_id;

END;
$$;

-- ============================================================
-- Permissions minimales
-- ============================================================

REVOKE ALL ON FUNCTION
    public.identifier_admin_recuperation_passkey(bytea)
FROM PUBLIC;

GRANT EXECUTE ON FUNCTION
    public.identifier_admin_recuperation_passkey(bytea)
TO netatlas_test_user;

COMMIT;
