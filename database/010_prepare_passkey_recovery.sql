-- ============================================================
-- NETATLAS - RECUPERATION PASSKEY
-- Migration 010 - Unicite des challenges de recuperation
-- ============================================================

BEGIN;

-- Une autorisation SSH ne peut etre associee
-- qu'a un seul challenge WebAuthn de recuperation.
--
-- Les operations WebAuthn classiques conservent
-- recovery_id = NULL et ne sont pas concernees.

CREATE UNIQUE INDEX
    webauthn_challenges_recovery_id_unique_idx
ON public.webauthn_challenges (recovery_id)
WHERE recovery_id IS NOT NULL;

COMMIT;
