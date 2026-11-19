-- ============================================================
-- NETATLAS - MIGRATION 020
-- Suppression définitive de l'ancienne authentification PIN
-- ============================================================
--
-- Préserve :
--   - Les comptes utilisateurs
--   - Les rôles
--   - Les identifiants Passkey / WebAuthn
--   - Les sessions IAM
--
-- Ne supprime aucune ligne de la table users.
-- ============================================================

BEGIN;

ALTER TABLE public.users
    DROP COLUMN IF EXISTS pin_hash RESTRICT;

COMMIT;
