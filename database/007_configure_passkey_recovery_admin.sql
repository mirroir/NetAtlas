-- ============================================================
-- NETATLAS - CONFIGURATION ADMINISTRATEUR DE RECUPERATION
-- Migration 007
-- ============================================================

BEGIN;

-- Configuration protégée de la récupération administrative.
CREATE TABLE public.passkey_recovery_config (
    id integer PRIMARY KEY CHECK (id = 1),
    admin_user_id integer NOT NULL
        REFERENCES public.users(id) ON DELETE RESTRICT
);

-- Configuration propre à la base de test.
INSERT INTO public.passkey_recovery_config (
    id,
    admin_user_id
)
VALUES (1, 3);

-- Aucun accès direct aux comptes applicatifs.
REVOKE ALL ON TABLE public.passkey_recovery_config
FROM PUBLIC;

-- Mise à jour de la fonction existante.
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
    v_admin_user_id integer;
BEGIN
    -- Lire l'administrateur autorisé dans la configuration protégée.
    SELECT admin_user_id
    INTO v_admin_user_id
    FROM public.passkey_recovery_config
    WHERE id = 1;

    IF v_admin_user_id IS NULL
       OR p_user_id IS DISTINCT FROM v_admin_user_id THEN
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

    -- Vérifier le rôle administrateur.
    PERFORM 1
    FROM public.role_user ru
    JOIN public.roles r ON r.id = ru.role_id
    WHERE ru.user_id = p_user_id
      AND r.nom = 'admin';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Compte non administrateur.';
    END IF;

    -- Invalider les autorisations précédentes.
    UPDATE public.passkey_recovery
    SET consumed_at = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id
      AND consumed_at IS NULL;

    -- Créer une autorisation temporaire.
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

    -- Journaliser la demande.
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

-- Réaffirmer les permissions minimales.
REVOKE ALL ON FUNCTION
    public.creer_autorisation_recuperation_admin(
        integer, bytea, text
    )
FROM PUBLIC;

GRANT EXECUTE ON FUNCTION
    public.creer_autorisation_recuperation_admin(
        integer, bytea, text
    )
TO "netatlas-recovery";

COMMIT;
