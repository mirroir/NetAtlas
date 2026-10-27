-- ============================================================
-- NETATLAS V0.1 CORE
-- Migration 014 : isolation RLS des challenges de récupération
-- administrateur
--
-- Les opérations applicatives ordinaires restent autorisées.
-- Les challenges admin_recovery sont réservés aux fonctions
-- privilégiées PostgreSQL.
-- ============================================================

BEGIN;

-- ------------------------------------------------------------
-- 1. Activer la sécurité au niveau des lignes.
-- ------------------------------------------------------------

ALTER TABLE public.webauthn_challenges
ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------
-- 2. Autoriser la lecture des challenges ordinaires.
-- ------------------------------------------------------------

CREATE POLICY webauthn_challenges_app_select
ON public.webauthn_challenges
FOR SELECT
TO netatlas_test_user
USING (
    operation IN ('registration', 'authentication')
);

-- ------------------------------------------------------------
-- 3. Autoriser l'insertion de challenges ordinaires.
-- ------------------------------------------------------------

CREATE POLICY webauthn_challenges_app_insert
ON public.webauthn_challenges
FOR INSERT
TO netatlas_test_user
WITH CHECK (
    operation IN ('registration', 'authentication')
    AND recovery_id IS NULL
);

-- ------------------------------------------------------------
-- 4. Autoriser la modification des challenges ordinaires.
-- ------------------------------------------------------------

CREATE POLICY webauthn_challenges_app_update
ON public.webauthn_challenges
FOR UPDATE
TO netatlas_test_user
USING (
    operation IN ('registration', 'authentication')
)
WITH CHECK (
    operation IN ('registration', 'authentication')
    AND recovery_id IS NULL
);

-- ------------------------------------------------------------
-- 5. Ne créer aucune politique DELETE.
-- L'absence de politique interdit la suppression directe.
-- ------------------------------------------------------------

COMMIT;
