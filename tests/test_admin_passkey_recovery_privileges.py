
"""Tests PostgreSQL des privilèges de récupération Passkey."""

from tests.test_admin_passkey_recovery_integration import (
    executer_sql_recuperation,
)


def test_privileges_fonctions_recuperation_passkey():
    """Vérifier les droits applicatifs après migration 017."""
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            v_role text := 'netatlas_test_user';
        BEGIN
            IF has_function_privilege(
                v_role,
                'public.preparer_recuperation_passkey_admin(bytea,bytea,bytea)',
                'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'Preparation historique encore accessible';
            END IF;

            IF NOT has_function_privilege(
                v_role,
                'public.preparer_recuperation_passkey_admin_securisee(bytea,bytea,bytea,bytea)',
                'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'Preparation securisee inaccessible';
            END IF;

            IF has_function_privilege(
                v_role,
                'public.finaliser_recuperation_passkey_admin(bytea,bytea,bytea,bytea,bytea,integer)',
                'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'Finalisation accessible au role applicatif';
            END IF;

            IF NOT has_function_privilege(
                v_role,
                'public.identifier_admin_recuperation_passkey(bytea)',
                'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'Identification administrateur inaccessible';
            END IF;
        END;
        $$;

        ROLLBACK;
        """
    )

    assert "DO" in sortie
