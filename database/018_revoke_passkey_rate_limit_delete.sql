
-- ============================================================
-- Migration 018 - Réduction des privilèges du limiteur Passkey
-- ============================================================
-- Révoque uniquement le droit de suppression des compteurs.
-- Les droits SELECT, INSERT et UPDATE restent inchangés.

REVOKE DELETE ON TABLE public.passkey_rate_limits
FROM netatlas_test_user;
