-- ============================================================
-- NETATLAS - RECUPERATION PASSKEY
-- Migration 008 - Demande SSH sans lecture directe
-- ============================================================

BEGIN;

-- Retirer les autorisations de l'ancienne interface.
REVOKE ALL ON FUNCTION
    public.creer_autorisation_recuperation_admin(
        integer, bytea, text
    )
FROM PUBLIC, "netatlas-recovery";

-- Nouvelle interface : l'administrateur est déterminé
-- exclusivement depuis la configuration protégée.
CREATE FUNCTION public.demander_recuperation_passkey_admin(
    p_token_hash bytea,
    p_requested_by text
)
RETURNS bigint
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, pg_temp
AS $$
DECLARE
    v_admin_id integer;
    v_autorisation_id bigint;
BEGIN
    IF p_token_hash IS NULL
       OR octet_length(p_token_hash) <> 32 THEN
        RAISE EXCEPTION 'Empreinte du jeton invalide.';
    END IF;

    IF p_requested_by IS NULL
       OR length(btrim(p_requested_by)) = 0
       OR length(p_requested_by) > 128 THEN
        RAISE EXCEPTION 'Identité système invalide.';
    END IF;

    -- Lire la configuration protégée.
    SELECT admin_user_id
    INTO v_admin_id
    FROM public.passkey_recovery_config
    WHERE id = 1;

    IF v_admin_id IS NULL THEN
        RAISE EXCEPTION 'Configuration de récupération absente.';
    END IF;

    -- Verrouiller le compte administrateur.
    PERFORM 1
    FROM public.users
    WHERE id = v_admin_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Compte administrateur introuvable.';
    END IF;

    -- Vérifier que le compte possède toujours le rôle admin.
    PERFORM 1
    FROM public.role_user ru
    JOIN public.roles r ON r.id = ru.role_id
    WHERE ru.user_id = v_admin_id
      AND r.nom = 'admin';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Compte non administrateur.';
    END IF;

    -- Invalider les demandes précédentes.
    UPDATE public.passkey_recovery
    SET consumed_at = CURRENT_TIMESTAMP
    WHERE user_id = v_admin_id
      AND consumed_at IS NULL;

    -- Créer la nouvelle demande.
    INSERT INTO public.passkey_recovery (
        user_id,
        token_hash,
        expires_at,
        requested_by
    )
    VALUES (
        v_admin_id,
        p_token_hash,
        CURRENT_TIMESTAMP + INTERVAL '300 seconds',
        p_requested_by
    )
    RETURNING id INTO v_autorisation_id;

    -- Journaliser la demande dans la même transaction.
    INSERT INTO public.passkey_recovery_audit (
        user_id,
        action,
        requested_by
    )
    VALUES (
        v_admin_id,
        'requested',
        p_requested_by
    );

    RETURN v_autorisation_id;
END;
$$;

-- PostgreSQL accorde EXECUTE à PUBLIC par défaut.
-- Nous supprimons ce droit dans la même transaction.
REVOKE ALL ON FUNCTION
    public.demander_recuperation_passkey_admin(bytea, text)
FROM PUBLIC;

-- Seul le rôle technique SSH peut demander une récupération.
GRANT EXECUTE ON FUNCTION
    public.demander_recuperation_passkey_admin(bytea, text)
TO "netatlas-recovery";

COMMIT;
