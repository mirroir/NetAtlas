
-- ============================================================
-- NETATLAS V0.1 CORE
-- Migration 017 - Revocation de la preparation Passkey historique
--
-- Objectif :
-- Supprimer l'acces applicatif a l'ancienne preparation
-- sans modifier la preparation securisee introduite par 016.
-- ============================================================

BEGIN;

REVOKE EXECUTE ON FUNCTION
    public.preparer_recuperation_passkey_admin(
        bytea,
        bytea,
        bytea
    )
FROM netatlas_test_user;

COMMIT;
