"""Tests PostgreSQL des politiques RLS de récupération Passkey."""

from tests.test_admin_passkey_recovery_integration import (
    executer_sql_recuperation,
)


def test_rls_active_pour_role_applicatif():
    """Le rôle applicatif est effectivement soumis à RLS."""
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        SET ROLE netatlas_test_user;

        DO $$
        BEGIN
            IF current_user <> 'netatlas_test_user' THEN
                RAISE EXCEPTION 'Rôle applicatif incorrect';
            END IF;

            IF NOT row_security_active(
                'public.webauthn_challenges'::regclass
            ) THEN
                RAISE EXCEPTION 'RLS inactive pour le rôle applicatif';
            END IF;
        END;
        $$;

        RESET ROLE;

        ROLLBACK;
        """
    )

    assert "DO" in sortie


def test_rls_masque_challenge_recuperation():
    """Un challenge admin_recovery existant reste invisible."""
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        CREATE TEMP TABLE test_rls_cible (
            challenge_hash bytea NOT NULL
        ) ON COMMIT DROP;

        GRANT SELECT ON TABLE test_rls_cible TO netatlas_test_user;


        DO $$
        DECLARE
            v_admin_id integer;
            v_recovery_id bigint;
            v_challenge_hash bytea;
        BEGIN
            SELECT admin_user_id
            INTO STRICT v_admin_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            v_challenge_hash := decode(md5(random()::text) || md5(random()::text), 'hex');

            INSERT INTO public.passkey_recovery (
                user_id, token_hash, expires_at, requested_by
            )
            VALUES (
                v_admin_id,
                decode(md5(random()::text) || md5(random()::text), 'hex'),
                clock_timestamp() + INTERVAL '300 seconds',
                'pytest_rls_select'
            )
            RETURNING id INTO v_recovery_id;

            INSERT INTO public.webauthn_challenges (
                challenge_hash,
                session_binding_hash,
                user_id,
                operation,
                expires_at,
                recovery_id
            )
            VALUES (
                v_challenge_hash,
                decode(md5(random()::text) || md5(random()::text), 'hex'),
                v_admin_id,
                'admin_recovery',
                clock_timestamp() + INTERVAL '60 seconds',
                v_recovery_id
            );

            INSERT INTO test_rls_cible VALUES (v_challenge_hash);
        END;
        $$;

        SET ROLE netatlas_test_user;

        DO $$
        DECLARE
            v_challenge_hash bytea;
        BEGIN
            SELECT challenge_hash
            INTO STRICT v_challenge_hash
            FROM test_rls_cible;

            IF EXISTS (
                SELECT 1
                FROM public.webauthn_challenges
                WHERE challenge_hash = v_challenge_hash
            ) THEN
                RAISE EXCEPTION 'Challenge admin_recovery visible';
            END IF;
        END;
        $$;

        RESET ROLE;

        ROLLBACK;
        """
    )

    assert sortie.count("DO") == 2


def test_rls_refuse_insertion_challenge_recuperation():
    """Le rôle applicatif ne peut pas insérer admin_recovery."""
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        CREATE TEMP TABLE test_rls_cible (
            user_id integer NOT NULL,
            recovery_id bigint NOT NULL
        ) ON COMMIT DROP;

        GRANT SELECT ON TABLE test_rls_cible TO netatlas_test_user;


        INSERT INTO public.passkey_recovery (
            user_id, token_hash, expires_at, requested_by
        )
        SELECT
            admin_user_id,
            decode(md5(random()::text) || md5(random()::text), 'hex'),
            clock_timestamp() + INTERVAL '300 seconds',
            'pytest_rls_insert'
        FROM public.passkey_recovery_config
        WHERE id = 1
        RETURNING user_id, id;

        INSERT INTO test_rls_cible
        SELECT user_id, id
        FROM public.passkey_recovery
        WHERE requested_by = 'pytest_rls_insert'
        ORDER BY id DESC
        LIMIT 1;

        SET ROLE netatlas_test_user;

        DO $$
        DECLARE
            v_user_id integer;
            v_recovery_id bigint;
            v_refus boolean := false;
            v_message_erreur text;
        BEGIN
            SELECT user_id, recovery_id
            INTO STRICT v_user_id, v_recovery_id
            FROM test_rls_cible;

            BEGIN
                INSERT INTO public.webauthn_challenges (
                    challenge_hash,
                    session_binding_hash,
                    user_id,
                    operation,
                    expires_at,
                    recovery_id
                )
                VALUES (
                    decode(md5(random()::text) || md5(random()::text), 'hex'),
                    decode(md5(random()::text) || md5(random()::text), 'hex'),
                    v_user_id,
                    'admin_recovery',
                    clock_timestamp() + INTERVAL '60 seconds',
                    v_recovery_id
                );

            EXCEPTION
                WHEN insufficient_privilege THEN
                    GET STACKED DIAGNOSTICS
                        v_message_erreur = MESSAGE_TEXT;

                    IF position(
                        'row-level security policy' IN v_message_erreur
                    ) > 0 THEN
                        v_refus := true;
                    ELSE
                        RAISE;
                    END IF;
            END;

            IF NOT v_refus THEN
                RAISE EXCEPTION
                    'INSERT admin_recovery autorisé à tort';
            END IF;
        END;
        $$;

        RESET ROLE;

        ROLLBACK;
        """
    )

    assert "DO" in sortie

def test_rls_refuse_transformation_challenge():
    """Un challenge ordinaire ne peut pas devenir admin_recovery."""
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        CREATE TEMP TABLE test_rls_cible (
            challenge_hash bytea NOT NULL,
            recovery_id bigint NOT NULL
        ) ON COMMIT DROP;

        GRANT SELECT ON TABLE test_rls_cible TO netatlas_test_user;

        DO $$
        DECLARE
            v_user_id integer;
            v_challenge_hash bytea;
            v_recovery_id bigint;
        BEGIN
            SELECT admin_user_id
            INTO STRICT v_user_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            v_challenge_hash := decode(
                md5(random()::text) || md5(random()::text),
                'hex'
            );

            INSERT INTO public.passkey_recovery (
                user_id,
                token_hash,
                expires_at,
                requested_by
            )
            VALUES (
                v_user_id,
                decode(
                    md5(random()::text) || md5(random()::text),
                    'hex'
                ),
                clock_timestamp() + INTERVAL '300 seconds',
                'pytest_rls_update'
            )
            RETURNING id INTO v_recovery_id;

            INSERT INTO public.webauthn_challenges (
                challenge_hash,
                session_binding_hash,
                user_id,
                operation,
                expires_at
            )
            VALUES (
                v_challenge_hash,
                decode(
                    md5(random()::text) || md5(random()::text),
                    'hex'
                ),
                v_user_id,
                'registration',
                clock_timestamp() + INTERVAL '60 seconds'
            );

            INSERT INTO test_rls_cible (
                challenge_hash,
                recovery_id
            )
            VALUES (
                v_challenge_hash,
                v_recovery_id
            );
        END;
        $$;

        SET ROLE netatlas_test_user;

        DO $$
        DECLARE
            v_challenge_hash bytea;
            v_recovery_id bigint;
            v_refus boolean := false;
            v_message_erreur text;
        BEGIN
            SELECT challenge_hash, recovery_id
            INTO STRICT v_challenge_hash, v_recovery_id
            FROM test_rls_cible;

            BEGIN
                UPDATE public.webauthn_challenges
                SET
                    operation = 'admin_recovery',
                    recovery_id = v_recovery_id
                WHERE challenge_hash = v_challenge_hash;

            EXCEPTION
                WHEN insufficient_privilege THEN
                    GET STACKED DIAGNOSTICS
                        v_message_erreur = MESSAGE_TEXT;

                    IF position(
                        'row-level security policy' IN v_message_erreur
                    ) > 0 THEN
                        v_refus := true;
                    ELSE
                        RAISE;
                    END IF;
            END;

            IF NOT v_refus THEN
                RAISE EXCEPTION
                    'UPDATE vers admin_recovery autorisé à tort';
            END IF;
        END;
        $$;

        RESET ROLE;

        DO $$
        DECLARE
            v_challenge_hash bytea;
        BEGIN
            SELECT challenge_hash
            INTO STRICT v_challenge_hash
            FROM test_rls_cible;

            IF NOT EXISTS (
                SELECT 1
                FROM public.webauthn_challenges
                WHERE challenge_hash = v_challenge_hash
                  AND operation = 'registration'
                  AND recovery_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Challenge initial modifié malgré le refus RLS';
            END IF;
        END;
        $$;

        ROLLBACK;
        """
    )

    assert sortie.count("DO") == 3

def test_rls_refuse_suppression_challenge_recuperation():
    """Le rôle applicatif ne peut pas supprimer un challenge existant."""
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        CREATE TEMP TABLE test_rls_cible (
            challenge_hash bytea NOT NULL
        ) ON COMMIT DROP;

        GRANT SELECT ON TABLE test_rls_cible TO netatlas_test_user;


        DO $$
        DECLARE
            v_admin_id integer;
            v_recovery_id bigint;
            v_challenge_hash bytea;
        BEGIN
            SELECT admin_user_id
            INTO STRICT v_admin_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            v_challenge_hash := decode(md5(random()::text) || md5(random()::text), 'hex');

            INSERT INTO public.passkey_recovery (
                user_id, token_hash, expires_at, requested_by
            )
            VALUES (
                v_admin_id,
                decode(md5(random()::text) || md5(random()::text), 'hex'),
                clock_timestamp() + INTERVAL '300 seconds',
                'pytest_rls_delete'
            )
            RETURNING id INTO v_recovery_id;

            INSERT INTO public.webauthn_challenges (
                challenge_hash,
                session_binding_hash,
                user_id,
                operation,
                expires_at,
                recovery_id
            )
            VALUES (
                v_challenge_hash,
                decode(md5(random()::text) || md5(random()::text), 'hex'),
                v_admin_id,
                'admin_recovery',
                clock_timestamp() + INTERVAL '60 seconds',
                v_recovery_id
            );

            INSERT INTO test_rls_cible VALUES (v_challenge_hash);
        END;
        $$;

        SET ROLE netatlas_test_user;

        DO $$
        DECLARE
            v_challenge_hash bytea;
            v_nombre integer;
        BEGIN
            SELECT challenge_hash
            INTO STRICT v_challenge_hash
            FROM test_rls_cible;

            DELETE FROM public.webauthn_challenges
            WHERE challenge_hash = v_challenge_hash;

            GET DIAGNOSTICS v_nombre = ROW_COUNT;

            IF v_nombre <> 0 THEN
                RAISE EXCEPTION
                    'Suppression admin_recovery autorisée';
            END IF;
        END;
        $$;

        RESET ROLE;

        DO $$
        DECLARE
            v_challenge_hash bytea;
        BEGIN
            SELECT challenge_hash
            INTO STRICT v_challenge_hash
            FROM test_rls_cible;

            IF NOT EXISTS (
                SELECT 1
                FROM public.webauthn_challenges
                WHERE challenge_hash = v_challenge_hash
            ) THEN
                RAISE EXCEPTION
                    'Challenge supprimé malgré la protection RLS';
            END IF;
        END;
        $$;

        ROLLBACK;
        """
    )

    assert sortie.count("DO") == 3
