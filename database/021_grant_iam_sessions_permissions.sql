-- ============================================================
-- NETATLAS - PERMISSIONS DES SESSIONS IAM
-- Migration 021
-- ============================================================

-- Acces minimal du role applicatif aux sessions IAM.
GRANT SELECT, INSERT, UPDATE
ON TABLE public.iam_sessions
TO netatlas_user;

-- Utilisation de l'identifiant automatique des sessions.
GRANT USAGE
ON SEQUENCE public.iam_sessions_id_seq
TO netatlas_user;
