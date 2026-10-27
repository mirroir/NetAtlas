"""Tests PostgreSQL de récupération Passkey administrateur."""

import os
import subprocess
import textwrap

import pytest


def executer_sql_recuperation(sql):
    """Exécute un scénario SQL privilégié dans la base de test."""

    if (
        os.getenv("NETATLAS_ENV") != "test"
        or os.getenv("DB_NAME") != "netatlas_test"
    ):
        pytest.fail(
            "SECURITE NETATLAS : base netatlas_test obligatoire."
        )

    script = textwrap.dedent(sql).strip()

    if not script.startswith("BEGIN;"):
        pytest.fail("Le scénario doit commencer par BEGIN;")

    if not script.endswith("ROLLBACK;"):
        pytest.fail("Le scénario doit terminer par ROLLBACK;")

    mode = os.getenv("NETATLAS_SQL_TEST_MODE", "local")

    environnement = os.environ.copy()

    if mode == "local":
        commande = [
            "sudo",
            "-n",
            "-u",
            "postgres",
            "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-P",
            "pager=off",
            "-d",
            "netatlas_test",
        ]

        # Ne pas transmettre les identifiants applicatifs
        # à la connexion PostgreSQL privilégiée.
        environnement.pop("PGPASSWORD", None)

    elif mode == "ci":
        if os.getenv("GITHUB_ACTIONS") != "true":
            pytest.fail(
                "Mode SQL CI autorisé uniquement dans GitHub Actions."
            )

        if os.getenv("NETATLAS_SQL_ADMIN_DB") != "netatlas_test":
            pytest.fail(
                "Base PostgreSQL administrateur CI invalide."
            )

        mot_de_passe = os.getenv("NETATLAS_SQL_ADMIN_PASSWORD")

        if not mot_de_passe:
            pytest.fail(
                "Mot de passe PostgreSQL administrateur CI absent."
            )

        environnement["PGPASSWORD"] = mot_de_passe

        commande = [
            "psql",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-P",
            "pager=off",
            "-h",
            "localhost",
            "-p",
            "5432",
            "-U",
            "postgres",
            "-d",
            "netatlas_test",
        ]

    else:
        pytest.fail(
            "Mode d'exécution SQL non autorisé."
        )

    try:
        resultat = subprocess.run(
            commande,
            input=script,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
            env=environnement,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("Délai PostgreSQL dépassé.")

    assert resultat.returncode == 0, (
        f"Erreur PostgreSQL :\n"
        f"{resultat.stdout}\n{resultat.stderr}"
    )

    return resultat.stdout + resultat.stderr


def test_recuperation_refuse_jeton_inexistant():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            resultat bigint;
        BEGIN
            SELECT public.finaliser_recuperation_passkey_admin(
                decode(repeat('a', 64), 'hex'),
                decode(repeat('b', 64), 'hex'),
                decode(repeat('c', 64), 'hex'),
                decode(repeat('d', 64), 'hex'),
                decode(repeat('e', 64), 'hex'),
                0
            )
            INTO resultat;

            IF resultat IS NOT NULL THEN
                RAISE EXCEPTION
                    'Jeton inexistant accepte';
            END IF;

            RAISE NOTICE 'TEST OK : jeton inexistant refuse';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : jeton inexistant refuse" in sortie


def test_recuperation_refuse_jeton_expire():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        INSERT INTO public.passkey_recovery (
            user_id,
            token_hash,
            expires_at,
            requested_by
        )
        SELECT
            admin_user_id,
            decode(repeat('9', 64), 'hex'),
            clock_timestamp() - INTERVAL '60 seconds',
            'pytest_jeton_expire'
        FROM public.passkey_recovery_config
        WHERE id = 1;

        DO $$
        DECLARE
            resultat bigint;
        BEGIN
            SELECT public.finaliser_recuperation_passkey_admin(
                decode(repeat('9', 64), 'hex'),
                decode(repeat('a', 64), 'hex'),
                decode(repeat('b', 64), 'hex'),
                decode(repeat('c', 64), 'hex'),
                decode(repeat('d', 64), 'hex'),
                0
            )
            INTO resultat;

            IF resultat IS NOT NULL THEN
                RAISE EXCEPTION
                    'Jeton expire accepte';
            END IF;

            RAISE NOTICE 'TEST OK : jeton expire refuse';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : jeton expire refuse" in sortie


def test_recuperation_refuse_jeton_consomme():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        INSERT INTO public.passkey_recovery (
            user_id,
            token_hash,
            expires_at,
            consumed_at,
            requested_by
        )
        SELECT
            admin_user_id,
            decode(repeat('1', 64), 'hex'),
            clock_timestamp() + INTERVAL '300 seconds',
            clock_timestamp(),
            'pytest_jeton_consomme'
        FROM public.passkey_recovery_config
        WHERE id = 1;

        DO $$
        DECLARE
            resultat bigint;
        BEGIN
            SELECT public.finaliser_recuperation_passkey_admin(
                decode(repeat('1', 64), 'hex'),
                decode(repeat('2', 64), 'hex'),
                decode(repeat('3', 64), 'hex'),
                decode(repeat('4', 64), 'hex'),
                decode(repeat('5', 64), 'hex'),
                0
            )
            INTO resultat;

            IF resultat IS NOT NULL THEN
                RAISE EXCEPTION
                    'Jeton consomme accepte';
            END IF;

            RAISE NOTICE 'TEST OK : jeton consomme refuse';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : jeton consomme refuse" in sortie

def test_recuperation_refuse_challenge_inexistant():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            admin_id integer;
            recovery_id bigint;
            resultat bigint;
            credentials_avant bigint;
            credentials_apres bigint;
        BEGIN
            SELECT admin_user_id
            INTO STRICT admin_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            SELECT count(*)
            INTO credentials_avant
            FROM public.webauthn_credentials
            WHERE user_id = admin_id;

            INSERT INTO public.passkey_recovery (
                user_id,
                token_hash,
                expires_at,
                requested_by
            )
            VALUES (
                admin_id,
                decode(md5('pytest-challenge-inexistant-' || txid_current()::text) || md5('pytest-challenge-inexistant-suite-' || txid_current()::text), 'hex'),
                clock_timestamp() + INTERVAL '300 seconds',
                'pytest_challenge_inexistant'
            )
            RETURNING id INTO recovery_id;

            SELECT public.finaliser_recuperation_passkey_admin(
                (
                    SELECT token_hash
                    FROM public.passkey_recovery
                    WHERE id = recovery_id
                ),
                decode(repeat('b1', 32), 'hex'),
                decode(repeat('c1', 32), 'hex'),
                decode(repeat('d1', 32), 'hex'),
                decode(repeat('e1', 32), 'hex'),
                0
            )
            INTO resultat;

            IF resultat IS NOT NULL THEN
                RAISE EXCEPTION
                    'Challenge inexistant accepte';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.passkey_recovery
                WHERE id = recovery_id
                  AND consumed_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Jeton consomme sans challenge';
            END IF;

            SELECT count(*)
            INTO credentials_apres
            FROM public.webauthn_credentials
            WHERE user_id = admin_id;

            IF credentials_avant <> credentials_apres THEN
                RAISE EXCEPTION
                    'Nombre de Passkeys modifie';
            END IF;

            RAISE NOTICE
                'TEST OK : challenge inexistant refuse';

            RAISE NOTICE
                'TEST OK : jeton conserve et Passkeys intactes';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : challenge inexistant refuse" in sortie
    assert "TEST OK : jeton conserve et Passkeys intactes" in sortie

def test_recuperation_finalisation_complete():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            v_admin_id integer;
            v_recovery_id bigint;
            v_credential_db_id bigint;
            v_second_resultat bigint;
            v_credentials_avant bigint;
            v_credentials_apres bigint;
            v_audit_avant bigint;
            v_audit_apres bigint;
            v_token_hash bytea;
            v_challenge_hash bytea;
            v_session_hash bytea;
            v_credential_id bytea;
        BEGIN
            SELECT admin_user_id
            INTO STRICT v_admin_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            v_token_hash := decode(repeat('a4', 32), 'hex');
            v_challenge_hash := decode(repeat('b4', 32), 'hex');
            v_session_hash := decode(repeat('c4', 32), 'hex');
            v_credential_id := decode(repeat('d4', 32), 'hex');

            SELECT count(*)
            INTO v_credentials_avant
            FROM public.webauthn_credentials
            WHERE user_id = v_admin_id;

            SELECT count(*)
            INTO v_audit_avant
            FROM public.passkey_recovery_audit
            WHERE user_id = v_admin_id
              AND action = 'completed';

            INSERT INTO public.passkey_recovery (
                user_id,
                token_hash,
                expires_at,
                requested_by
            )
            VALUES (
                v_admin_id,
                v_token_hash,
                clock_timestamp() + INTERVAL '300 seconds',
                'pytest_finalisation_complete'
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
                v_session_hash,
                v_admin_id,
                'admin_recovery',
                clock_timestamp() + INTERVAL '60 seconds',
                v_recovery_id
            );

            SELECT public.finaliser_recuperation_passkey_admin(
                v_token_hash,
                v_challenge_hash,
                v_session_hash,
                v_credential_id,
                decode(repeat('e4', 32), 'hex'),
                0
            )
            INTO v_credential_db_id;

            IF v_credential_db_id IS NULL THEN
                RAISE EXCEPTION
                    'Finalisation valide refusee';
            END IF;

            SELECT count(*)
            INTO v_credentials_apres
            FROM public.webauthn_credentials
            WHERE user_id = v_admin_id;

            IF v_credentials_apres <> v_credentials_avant + 1 THEN
                RAISE EXCEPTION
                    'Nombre de Passkeys incorrect';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM public.passkey_recovery
                WHERE id = v_recovery_id
                  AND consumed_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Jeton SSH non consomme';
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM public.webauthn_challenges
                WHERE recovery_id = v_recovery_id
                  AND consumed_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Challenge non consomme';
            END IF;

            SELECT count(*)
            INTO v_audit_apres
            FROM public.passkey_recovery_audit
            WHERE user_id = v_admin_id
              AND action = 'completed';

            IF v_audit_apres <> v_audit_avant + 1 THEN
                RAISE EXCEPTION
                    'Audit completed absent';
            END IF;

            SELECT public.finaliser_recuperation_passkey_admin(
                v_token_hash,
                v_challenge_hash,
                v_session_hash,
                decode(repeat('f4', 32), 'hex'),
                decode(repeat('e4', 32), 'hex'),
                0
            )
            INTO v_second_resultat;

            IF v_second_resultat IS NOT NULL THEN
                RAISE EXCEPTION
                    'Reutilisation du jeton acceptee';
            END IF;

            RAISE NOTICE
                'TEST OK : finalisation complete et atomique';

            RAISE NOTICE
                'TEST OK : reutilisation du jeton refusee';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : finalisation complete et atomique" in sortie
    assert "TEST OK : reutilisation du jeton refusee" in sortie

def test_recuperation_atomicite_apres_erreur_sql():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            v_admin_id integer;
            v_recovery_id bigint;
            v_resultat bigint;
            v_audit_avant bigint;
            v_audit_apres bigint;
            v_token_hash bytea;
            v_challenge_hash bytea;
            v_session_hash bytea;
            v_credential_id bytea;
            v_doublon_refuse boolean := false;
        BEGIN
            SELECT admin_user_id
            INTO STRICT v_admin_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            v_token_hash := decode(repeat('a5', 32), 'hex');
            v_challenge_hash := decode(repeat('b5', 32), 'hex');
            v_session_hash := decode(repeat('c5', 32), 'hex');
            v_credential_id := decode(repeat('d5', 32), 'hex');

            SELECT count(*)
            INTO v_audit_avant
            FROM public.passkey_recovery_audit
            WHERE user_id = v_admin_id
              AND action = 'completed';

            INSERT INTO public.passkey_recovery (
                user_id,
                token_hash,
                expires_at,
                requested_by
            )
            VALUES (
                v_admin_id,
                v_token_hash,
                clock_timestamp() + INTERVAL '300 seconds',
                'pytest_atomicite_erreur'
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
                v_session_hash,
                v_admin_id,
                'admin_recovery',
                clock_timestamp() + INTERVAL '60 seconds',
                v_recovery_id
            );

            -- Première insertion : crée le doublon fictif.
            INSERT INTO public.webauthn_credentials (
                user_id,
                credential_id,
                public_key,
                sign_count
            )
            VALUES (
                v_admin_id,
                v_credential_id,
                decode(repeat('e5', 32), 'hex'),
                0
            );

            -- Deuxième insertion : doit échouer.
            BEGIN
                SELECT public.finaliser_recuperation_passkey_admin(
                    v_token_hash,
                    v_challenge_hash,
                    v_session_hash,
                    v_credential_id,
                    decode(repeat('f5', 32), 'hex'),
                    0
                )
                INTO v_resultat;

            EXCEPTION
                WHEN unique_violation THEN
                    v_doublon_refuse := true;
            END;

            IF NOT v_doublon_refuse THEN
                RAISE EXCEPTION
                    'ECHEC : doublon non refuse';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.passkey_recovery
                WHERE id = v_recovery_id
                  AND consumed_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : jeton consomme apres erreur';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM public.webauthn_challenges
                WHERE recovery_id = v_recovery_id
                  AND consumed_at IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : challenge consomme apres erreur';
            END IF;

            SELECT count(*)
            INTO v_audit_apres
            FROM public.passkey_recovery_audit
            WHERE user_id = v_admin_id
              AND action = 'completed';

            IF v_audit_apres <> v_audit_avant THEN
                RAISE EXCEPTION
                    'ECHEC : audit completed apres erreur';
            END IF;

            RAISE NOTICE
                'TEST OK : doublon de Passkey refuse';

            RAISE NOTICE
                'TEST OK : atomicite preservee apres erreur SQL';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : doublon de Passkey refuse" in sortie
    assert "TEST OK : atomicite preservee apres erreur SQL" in sortie

def test_recuperation_privileges_postgresql():
    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            v_proprietaire text;
            v_application boolean;
            v_application_ci boolean;
            v_service_ssh boolean;
            v_public boolean;
        BEGIN
            SELECT
                pg_get_userbyid(p.proowner),
                has_function_privilege(
                    'netatlas_test_user',
                    p.oid,
                    'EXECUTE'
                ),
                has_function_privilege(
                    'netatlas-recovery',
                    p.oid,
                    'EXECUTE'
                ),
                COALESCE(
                    (
                        SELECT bool_or(
                            a.grantee = 0
                            AND a.privilege_type = 'EXECUTE'
                        )
                        FROM aclexplode(p.proacl) AS a
                    ),
                    false
                )
            INTO
                v_proprietaire,
                v_application,
                v_service_ssh,
                v_public
            FROM pg_proc AS p
            WHERE p.oid = (
                'public.finaliser_recuperation_passkey_admin('
                || 'bytea,bytea,bytea,bytea,bytea,integer)'
            )::regprocedure;

            IF NOT FOUND THEN
                RAISE EXCEPTION
                    'ECHEC : fonction de finalisation introuvable';
            END IF;

            IF v_proprietaire IS DISTINCT FROM 'postgres' THEN
                RAISE EXCEPTION
                    'ECHEC : proprietaire incorrect';
            END IF;

            IF v_application IS DISTINCT FROM false THEN
                RAISE EXCEPTION
                    'ECHEC : execution autorisee pour application';
            END IF;

            IF v_service_ssh IS DISTINCT FROM false THEN
                RAISE EXCEPTION
                    'ECHEC : execution autorisee pour service SSH';
            END IF;

            IF v_public IS DISTINCT FROM false THEN
                RAISE EXCEPTION
                    'ECHEC : execution autorisee pour PUBLIC';
            END IF;

            -- Verification du compte applicatif GitHub Actions.
            -- Le role peut etre absent sur la VM locale.

            IF EXISTS (
                SELECT 1
                FROM pg_roles
                WHERE rolname = 'netatlas_ci_user'
            ) THEN
                SELECT has_function_privilege(
                    'netatlas_ci_user',
                    (
                        'public.finaliser_recuperation_passkey_admin('
                        || 'bytea,bytea,bytea,bytea,bytea,integer)'
                    )::regprocedure,
                    'EXECUTE'
                )
                INTO v_application_ci;

                IF v_application_ci IS DISTINCT FROM false THEN
                    RAISE EXCEPTION
                        'ECHEC : execution autorisee pour application CI';
                END IF;

                RAISE NOTICE
                    'TEST OK : privileges du compte CI securises';
            END IF;

            RAISE NOTICE
                'TEST OK : proprietaire postgres confirme';

            RAISE NOTICE
                'TEST OK : privileges de finalisation securises';
        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : proprietaire postgres confirme" in sortie
    assert "TEST OK : privileges de finalisation securises" in sortie

def test_identifier_admin_recuperation_passkey_sql():
    """Vérifie les contrôles SQL de la migration 013."""

    sortie = executer_sql_recuperation(
        """
        BEGIN;

        DO $$
        DECLARE
            v_admin_id integer;
            v_nom text;
            v_token_valide bytea;
            v_token_expire bytea;
            v_token_consomme bytea;
            v_token_inconnu bytea;
        BEGIN
            SELECT admin_user_id
            INTO v_admin_id
            FROM public.passkey_recovery_config
            WHERE id = 1;

            IF v_admin_id IS DISTINCT FROM 3 THEN
                RAISE EXCEPTION
                    'ECHEC : administrateur de test incorrect';
            END IF;

            v_token_valide := decode(
                replace(gen_random_uuid()::text, '-', '')
                || replace(gen_random_uuid()::text, '-', ''),
                'hex'
            );

            v_token_expire := decode(
                replace(gen_random_uuid()::text, '-', '')
                || replace(gen_random_uuid()::text, '-', ''),
                'hex'
            );

            v_token_consomme := decode(
                replace(gen_random_uuid()::text, '-', '')
                || replace(gen_random_uuid()::text, '-', ''),
                'hex'
            );

            v_token_inconnu := decode(
                replace(gen_random_uuid()::text, '-', '')
                || replace(gen_random_uuid()::text, '-', ''),
                'hex'
            );

            INSERT INTO public.passkey_recovery (
                user_id,
                token_hash,
                expires_at,
                requested_by
            )
            VALUES
                (
                    v_admin_id,
                    v_token_valide,
                    CURRENT_TIMESTAMP + INTERVAL '300 seconds',
                    'test_sql_013'
                ),
                (
                    v_admin_id,
                    v_token_expire,
                    CURRENT_TIMESTAMP - INTERVAL '1 second',
                    'test_sql_013'
                ),
                (
                    v_admin_id,
                    v_token_consomme,
                    CURRENT_TIMESTAMP + INTERVAL '300 seconds',
                    'test_sql_013'
                );

            UPDATE public.passkey_recovery
            SET consumed_at = CURRENT_TIMESTAMP
            WHERE token_hash = v_token_consomme;

            -- Jeton valide.
            SELECT user_id, nom
            INTO v_admin_id, v_nom
            FROM public.identifier_admin_recuperation_passkey(
                v_token_valide
            );

            IF v_admin_id IS DISTINCT FROM 3
               OR v_nom IS NULL THEN
                RAISE EXCEPTION
                    'ECHEC : jeton valide refuse';
            END IF;

            RAISE NOTICE 'TEST OK : jeton valide accepte';

            -- Vérification réelle sous le rôle applicatif.
            EXECUTE 'SET LOCAL ROLE netatlas_test_user';

            IF NOT EXISTS (
                SELECT 1
                FROM public.identifier_admin_recuperation_passkey(
                    v_token_valide
                )
                WHERE user_id = 3
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : jeton valide refuse au role applicatif';
            END IF;

            EXECUTE 'RESET ROLE';

            RAISE NOTICE
                'TEST OK : jeton valide accepte par role applicatif';

            -- Jeton expiré.
            IF EXISTS (
                SELECT 1
                FROM public.identifier_admin_recuperation_passkey(
                    v_token_expire
                )
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : jeton expire accepte';
            END IF;

            RAISE NOTICE 'TEST OK : jeton expire refuse';

            -- Jeton consommé.
            IF EXISTS (
                SELECT 1
                FROM public.identifier_admin_recuperation_passkey(
                    v_token_consomme
                )
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : jeton consomme accepte';
            END IF;

            RAISE NOTICE 'TEST OK : jeton consomme refuse';

            -- Jeton inconnu.
            IF EXISTS (
                SELECT 1
                FROM public.identifier_admin_recuperation_passkey(
                    v_token_inconnu
                )
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : jeton inconnu accepte';
            END IF;

            RAISE NOTICE 'TEST OK : jeton inconnu refuse';

            -- Empreinte invalide.
            IF EXISTS (
                SELECT 1
                FROM public.identifier_admin_recuperation_passkey(
                    decode('00', 'hex')
                )
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : empreinte invalide acceptee';
            END IF;

            RAISE NOTICE 'TEST OK : empreinte invalide refusee';

            -- Vérification des permissions.
            IF NOT has_function_privilege(
                'netatlas_test_user',
                'public.identifier_admin_recuperation_passkey(bytea)',
                'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : role applicatif non autorise';
            END IF;

            IF has_function_privilege(
                'netatlas-recovery',
                'public.identifier_admin_recuperation_passkey(bytea)',
                'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : role SSH autorise';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM pg_proc AS p
                CROSS JOIN LATERAL aclexplode(p.proacl) AS a
                WHERE p.oid = (
                    'public.identifier_admin_recuperation_passkey(bytea)'
                )::regprocedure
                  AND a.grantee = 0
                  AND a.privilege_type = 'EXECUTE'
            ) THEN
                RAISE EXCEPTION
                    'ECHEC : acces PUBLIC autorise';
            END IF;

            RAISE NOTICE 'TEST OK : permissions SQL securisees';

        END
        $$;

        ROLLBACK;
        """
    )

    assert "TEST OK : jeton valide accepte" in sortie
    assert "TEST OK : jeton expire refuse" in sortie
    assert "TEST OK : jeton consomme refuse" in sortie
    assert "TEST OK : jeton inconnu refuse" in sortie
    assert "TEST OK : empreinte invalide refusee" in sortie
    assert "TEST OK : permissions SQL securisees" in sortie
    assert "TEST OK : jeton valide accepte par role applicatif" in sortie
