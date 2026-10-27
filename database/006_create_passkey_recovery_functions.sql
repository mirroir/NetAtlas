-- ============================================================
-- NETATLAS - RECUPERATION ADMINISTRATIVE PASSKEY
-- Migration 006 - Autorisation locale SSH
-- ============================================================

BEGIN;

CREATE OR REPLACE FUNCTION public.creer_autorisation_recuperation_admin(
    p_user_id integer,
    p_token_hash bytea,
    p_requested_by text
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    v_id bigint;
BEGIN
    -- Réserver la récupération au compte administrateur historique.
    IF p_user_id IS DISTINCT FROM 2 THEN
        RAISE EXCEPTION 'Administrateur non autorisé.';
    END IF;

    IF p_token_hash IS NULL
       OR octet_length(p_token_hash) <> 32 THEN
        RAISE EXCEPTION 'Empreinte du jeton invalide.';
    END IF;

    IF p_requested_by IS NULL
       OR length(btrim(p_requested_by)) = 0
       OR length(p_requested_by) > 128 THEN
        RAISE EXCEPTION 'Identité système invalide.';
    END IF;

    -- Verrouiller le compte administrateur.
    PERFORM 1
    FROM public.users
    WHERE id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Compte administrateur introuvable.';
    END IF;

    -- Vérifier le rôle actuel.
    PERFORM 1
    FROM public.role_user ru
    JOIN public.roles r ON r.id = ru.role_id
    WHERE ru.user_id = p_user_id
      AND r.nom = 'admin';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Compte non administrateur.';
    END IF;

    -- Invalider les anciennes autorisations.
    UPDATE public.passkey_recovery
    SET consumed_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id
      AND consumed_at IS NULL;

    -- Créer une autorisation valable cinq minutes.
    INSERT INTO public.passkey_recovery (
        user_id,
        token_hash,
        expires_at,
        requested_by
    )
    VALUES (
        p_user_id,
        p_token_hash,
        CURRENT_TIMESTAMP + INTERVAL '300 seconds',
        p_requested_by
    )
    RETURNING id INTO v_id;

    -- Journaliser dans la même transaction.
    INSERT INTO public.passkey_recovery_audit (
        user_id,
        action,
        requested_by
    )
    VALUES (
        p_user_id,
        'requested',
        p_requested_by
    );

    RETURN v_id;
END;
$$;

-- Empêcher toute exécution publique.
REVOKE ALL ON FUNCTION
    public.creer_autorisation_recuperation_admin(
        integer, bytea, text
    )
FROM PUBLIC;

-- Réserver l'exécution au compte technique SSH.
GRANT EXECUTE ON FUNCTION
    public.creer_autorisation_recuperation_admin(
        integer, bytea, text
    )
TO "netatlas-recovery";

COMMIT;
