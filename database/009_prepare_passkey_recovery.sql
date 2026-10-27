-- ============================================================
-- NETATLAS - MIGRATION 009
-- Préparation des challenges de récupération Passkey
-- ============================================================

BEGIN;

-- Associer éventuellement un challenge à une autorisation SSH.
ALTER TABLE public.webauthn_challenges
ADD COLUMN recovery_id BIGINT;

-- Garantir l'existence de l'autorisation associée.
ALTER TABLE public.webauthn_challenges
ADD CONSTRAINT webauthn_challenges_recovery_id_fkey
FOREIGN KEY (recovery_id)
REFERENCES public.passkey_recovery(id)
ON DELETE RESTRICT;

-- Autoriser l'opération spécifique à la récupération.
ALTER TABLE public.webauthn_challenges
DROP CONSTRAINT webauthn_challenges_operation_check;

ALTER TABLE public.webauthn_challenges
ADD CONSTRAINT webauthn_challenges_operation_check
CHECK (
    operation IN (
        'registration',
        'authentication',
        'admin_recovery'
    )
);

-- Imposer un utilisateur pour toute récupération.
ALTER TABLE public.webauthn_challenges
ADD CONSTRAINT webauthn_challenges_recovery_user_check
CHECK (
    operation <> 'admin_recovery'
    OR user_id IS NOT NULL
);

-- Réserver recovery_id aux challenges de récupération.
ALTER TABLE public.webauthn_challenges
ADD CONSTRAINT webauthn_challenges_recovery_binding_check
CHECK (
    (
        operation = 'admin_recovery'
        AND recovery_id IS NOT NULL
    )
    OR
    (
        operation <> 'admin_recovery'
        AND recovery_id IS NULL
    )
);

-- Accélérer la recherche des challenges liés à une récupération.
CREATE INDEX webauthn_challenges_recovery_id_idx
ON public.webauthn_challenges(recovery_id)
WHERE recovery_id IS NOT NULL;

COMMIT;
