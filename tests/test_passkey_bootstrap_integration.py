import hashlib
from unittest.mock import patch

import psycopg

import database


class ConnexionTest:
    """Conserve toutes les écritures dans une transaction annulable."""

    def __init__(self, connexion):
        self.connexion = connexion

    def cursor(self):
        return self.connexion.cursor()

    def commit(self):
        # Ne jamais valider définitivement les écritures du test.
        pass

    def close(self):
        # La connexion réelle reste ouverte jusqu'au rollback final.
        pass

    def rollback(self):
        self.connexion.rollback()


def test_amorcage_passkey_transaction_reelle():
    connexion = database.connexion_db()
    connexion_test = ConnexionTest(connexion)

    user_id = 3
    token_hash = hashlib.sha256(b"jeton-integration-test").digest()
    challenge_hash = hashlib.sha256(b"challenge-integration-test").digest()
    session_hash = hashlib.sha256(b"session-integration-test").digest()

    try:
        with patch("database.connexion_db", return_value=connexion_test):
            amorcage_id = database.creer_amorcage_passkey_admin(
                user_id,
                token_hash,
            )

            assert amorcage_id > 0
            assert database.verifier_amorcage_passkey_admin(
                user_id,
                token_hash,
            )

            challenge_id = database.enregistrer_challenge_webauthn(
                challenge_hash=challenge_hash,
                session_binding_hash=session_hash,
                operation="registration",
                user_id=user_id,
            )

            assert challenge_id > 0

            credential_id = database.finaliser_amorcage_passkey_admin(
                user_id=user_id,
                token_hash=token_hash,
                challenge_hash=challenge_hash,
                session_binding_hash=session_hash,
                credential_id=b"credential-integration-test",
                public_key=b"public-key-integration-test",
            )

            assert credential_id > 0

            # Le jeton ne doit plus être valide.
            assert not database.verifier_amorcage_passkey_admin(
                user_id,
                token_hash,
            )

            # Une seconde finalisation doit être refusée.
            assert database.finaliser_amorcage_passkey_admin(
                user_id=user_id,
                token_hash=token_hash,
                challenge_hash=challenge_hash,
                session_binding_hash=session_hash,
                credential_id=b"credential-integration-test-2",
                public_key=b"public-key-integration-test",
            ) is False

    finally:
        # Annule toutes les écritures, même si une assertion échoue.
        connexion.rollback()
        connexion.close()

def _preparer_amorcage_integration(connexion_test, suffixe):
    """Prépare un jeton et un challenge dans la transaction de test."""
    token_hash = hashlib.sha256(f"token-{suffixe}".encode()).digest()
    challenge_hash = hashlib.sha256(f"challenge-{suffixe}".encode()).digest()
    session_hash = hashlib.sha256(f"session-{suffixe}".encode()).digest()

    with patch("database.connexion_db", return_value=connexion_test):
        assert database.creer_amorcage_passkey_admin(3, token_hash) > 0
        assert (
            database.enregistrer_challenge_webauthn(
                challenge_hash=challenge_hash,
                session_binding_hash=session_hash,
                operation="registration",
                user_id=3,
            )
            > 0
        )

    return token_hash, challenge_hash, session_hash


def _finaliser_integration(connexion_test, empreintes, credential_id):
    token_hash, challenge_hash, session_hash = empreintes

    with patch("database.connexion_db", return_value=connexion_test):
        return database.finaliser_amorcage_passkey_admin(
            user_id=3,
            token_hash=token_hash,
            challenge_hash=challenge_hash,
            session_binding_hash=session_hash,
            credential_id=credential_id,
            public_key=b"public-key-integration-test",
        )


def test_amorcage_refuse_jeton_expire():
    connexion = database.connexion_db()
    connexion_test = ConnexionTest(connexion)

    try:
        empreintes = _preparer_amorcage_integration(
            connexion_test, "jeton-expire"
        )

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE passkey_bootstrap
                SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 second'
                WHERE user_id = 3 AND token_hash = %s
                """,
                (empreintes[0],),
            )

        assert (
            _finaliser_integration(
                connexion_test, empreintes, b"credential-jeton-expire"
            )
            is False
        )
    finally:
        connexion.rollback()
        connexion.close()


def test_amorcage_refuse_challenge_expire():
    connexion = database.connexion_db()
    connexion_test = ConnexionTest(connexion)

    try:
        empreintes = _preparer_amorcage_integration(
            connexion_test, "challenge-expire"
        )

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE webauthn_challenges
                SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 second'
                WHERE user_id = 3 AND challenge_hash = %s
                """,
                (empreintes[1],),
            )

        assert (
            _finaliser_integration(
                connexion_test, empreintes, b"credential-challenge-expire"
            )
            is False
        )
    finally:
        connexion.rollback()
        connexion.close()


def test_amorcage_refuse_jeton_deja_consomme():
    connexion = database.connexion_db()
    connexion_test = ConnexionTest(connexion)

    try:
        empreintes = _preparer_amorcage_integration(
            connexion_test, "jeton-consomme"
        )

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE passkey_bootstrap
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE user_id = 3 AND token_hash = %s
                """,
                (empreintes[0],),
            )

        assert (
            _finaliser_integration(
                connexion_test, empreintes, b"credential-jeton-consomme"
            )
            is False
        )
    finally:
        connexion.rollback()
        connexion.close()


def test_amorcage_annule_insertion_credential_en_erreur():
    connexion = database.connexion_db()
    connexion_test = ConnexionTest(connexion)

    try:
        empreintes = _preparer_amorcage_integration(
            connexion_test, "insertion-erreur"
        )

        # Une valeur NULL viole la contrainte NOT NULL de credential_id.
        # PostgreSQL doit refuser l'insertion et annuler la transaction.
        with (
            patch("database.connexion_db", return_value=connexion_test),
            __import__("pytest").raises(Exception),
        ):
            database.finaliser_amorcage_passkey_admin(
                user_id=3,
                token_hash=empreintes[0],
                challenge_hash=empreintes[1],
                session_binding_hash=empreintes[2],
                credential_id=b"credential-insertion-erreur",
                public_key=b"public-key-integration-test",
                sign_count=9223372036854775808,
            )

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT COUNT(*)
                FROM webauthn_credentials
                WHERE user_id = 3
                """
            )
            assert curseur.fetchone()[0] == 0
    finally:
        connexion.rollback()
        connexion.close()

def test_amorcage_rollback_apres_erreur_sql_reelle():
    """Une erreur d'insertion ne doit consommer ni jeton ni challenge."""
    import secrets

    import pytest

    user_id = 3
    token_hash = secrets.token_bytes(32)
    challenge_hash = secrets.token_bytes(32)
    session_hash = secrets.token_bytes(32)

    connexion = database.connexion_db()

    try:
        # Préparation réellement validée en base.
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO passkey_bootstrap
                    (user_id, token_hash, expires_at)
                VALUES (%s, %s, CURRENT_TIMESTAMP + INTERVAL '5 minutes')
                """,
                (user_id, token_hash),
            )
            curseur.execute(
                """
                INSERT INTO webauthn_challenges
                    (
                        user_id,
                        challenge_hash,
                        session_binding_hash,
                        operation,
                        expires_at
                    )
                VALUES (
                    %s, %s, %s, 'registration',
                    CURRENT_TIMESTAMP + INTERVAL '60 seconds'
                )
                """,
                (user_id, challenge_hash, session_hash),
            )

        connexion.commit()

        # L'insertion de la Passkey doit échouer : dépassement BIGINT.
        with pytest.raises(psycopg.errors.NumericValueOutOfRange):
            database.finaliser_amorcage_passkey_admin(
                user_id=user_id,
                token_hash=token_hash,
                challenge_hash=challenge_hash,
                session_binding_hash=session_hash,
                credential_id=b"credential-rollback-reel",
                public_key=b"public-key-rollback-reel",
                sign_count=9223372036854775808,
            )

        # Vérification après rollback de la fonction.
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT consumed_at IS NULL
                FROM passkey_bootstrap
                WHERE user_id = %s AND token_hash = %s
                """,
                (user_id, token_hash),
            )
            assert curseur.fetchone() == (True,)

            curseur.execute(
                """
                SELECT consumed_at IS NULL
                FROM webauthn_challenges
                WHERE user_id = %s AND challenge_hash = %s
                """,
                (user_id, challenge_hash),
            )
            assert curseur.fetchone() == (True,)

            curseur.execute(
                """
                SELECT COUNT(*)
                FROM webauthn_credentials
                WHERE user_id = %s
                  AND credential_id = %s
                """,
                (user_id, b"credential-rollback-reel"),
            )
            assert curseur.fetchone()[0] == 0

    finally:
        # Nettoyage limité aux enregistrements créés par ce test.
        connexion.rollback()

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM webauthn_challenges
                WHERE user_id = %s AND challenge_hash = %s
                """,
                (user_id, challenge_hash),
            )
            curseur.execute(
                """
                DELETE FROM passkey_bootstrap
                WHERE user_id = %s AND token_hash = %s
                """,
                (user_id, token_hash),
            )

        connexion.commit()
        connexion.close()
