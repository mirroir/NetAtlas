S - Permissions WebAuthn pour les tests
-- À exécuter uniquement sur netatlas_test.
-- Ne pas exécuter dans GitHub Actions ni en production.

GRANT SELECT, INSERT, UPDATE, DELETE
ON TABLE public.webauthn_challenges
TO netatlas_test_user;

GRANT USAGE, SELECT
ON SEQUENCE public.webauthn_challenges_id_seq
TO netatlas_test_user;
