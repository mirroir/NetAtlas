"""Tests PostgreSQL réels de la finalisation Passkey."""

import hashlib
import os
import secrets
import sys
from pathlib import Path

import pytest
from psycopg.errors import UniqueViolation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import (
    connexion_db,
    enregistrer_challenge_webauthn,
    finaliser_enregistrement_webauthn,
)

USER_ID = 3


@pytest.fixture
def donnees_finalisation():
    """Prépare et nettoie les données temporaires du test."""
    if (
        os.getenv("NETATLAS_ENV") != "test"
        or os.getenv("DB_NAME") != "netatlas_test"
    ):
        pytest.fail("Base de test NetAtlas obligatoire.")

    challenge_hash = hashlib.sha256(secrets.token_bytes(32)).digest()
    session_hash = hashlib.sha256(secrets.token_bytes(32)).digest()
    credential_id = secrets.token_bytes(32)

    challenge_id = enregistrer_challenge_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        operation="registration",
        user_id=USER_ID,
    )

    try:
        yield challenge_hash, session_hash, credential_id, challenge_id
    finally:
        connexion = connexion_db()
        try:
            with connexion.cursor() as curseur:
                curseur.execute(
                    "DELETE FROM webauthn_credentials WHERE credential_id = %s",
                    (credential_id,),
                )
                curseur.execute(
                    "DELETE FROM webauthn_challenges WHERE id = %s",
                    (challenge_id,),
                )
            connexion.commit()
        except Exception:
            connexion.rollback()
            raise
        finally:
            connexion.close()


def test_finalisation_postgresql_reussie(donnees_finalisation):
    challenge_hash, session_hash, credential_id, challenge_id = (
        donnees_finalisation
    )

    resultat = finaliser_enregistrement_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        user_id=USER_ID,
        credential_id=credential_id,
        public_key=b"public-key-integration-test",
    )

    assert isinstance(resultat, int)
    assert resultat > 0

    connexion = connexion_db()
    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT consumed_at FROM webauthn_challenges WHERE id = %s",
                (challenge_id,),
            )
            assert curseur.fetchone()[0] is not None

            curseur.execute(
                "SELECT user_id FROM webauthn_credentials WHERE id = %s",
                (resultat,),
            )
            assert curseur.fetchone()[0] == USER_ID
    finally:
        connexion.close()


def test_finalisation_postgresql_rejeu_refuse(donnees_finalisation):
    challenge_hash, session_hash, credential_id, _ = donnees_finalisation

    premiere = finaliser_enregistrement_webauthn(
        challenge_hash,
        session_hash,
        USER_ID,
        credential_id,
        b"public-key-integration-test",
    )

    seconde = finaliser_enregistrement_webauthn(
        challenge_hash,
        session_hash,
        USER_ID,
        secrets.token_bytes(32),
        b"autre-public-key",
    )

    assert isinstance(premiere, int)
    assert seconde is False


def test_finalisation_postgresql_rollback(donnees_finalisation):
    challenge_hash, session_hash, credential_id, _ = donnees_finalisation

    premiere = finaliser_enregistrement_webauthn(
        challenge_hash,
        session_hash,
        USER_ID,
        credential_id,
        b"public-key-integration-test",
    )

    assert isinstance(premiere, int)

    second_challenge_hash = hashlib.sha256(secrets.token_bytes(32)).digest()
    second_session_hash = hashlib.sha256(secrets.token_bytes(32)).digest()

    second_challenge_id = enregistrer_challenge_webauthn(
        second_challenge_hash,
        second_session_hash,
        "registration",
        user_id=USER_ID,
    )

    try:
        with pytest.raises(UniqueViolation):
            finaliser_enregistrement_webauthn(
                second_challenge_hash,
                second_session_hash,
                USER_ID,
                credential_id,
                b"public-key-duplicate-test",
            )

        connexion = connexion_db()
        try:
            with connexion.cursor() as curseur:
                curseur.execute(
                    "SELECT consumed_at FROM webauthn_challenges WHERE id = %s",
                    (second_challenge_id,),
                )
                assert curseur.fetchone()[0] is None
        finally:
            connexion.close()

        nouvelle_credential = secrets.token_bytes(32)

        try:
            resultat = finaliser_enregistrement_webauthn(
                second_challenge_hash,
                second_session_hash,
                USER_ID,
                nouvelle_credential,
                b"public-key-after-rollback",
            )
            assert isinstance(resultat, int)
        finally:
            connexion = connexion_db()
            try:
                with connexion.cursor() as curseur:
                    curseur.execute(
                        "DELETE FROM webauthn_credentials WHERE credential_id = %s",
                        (nouvelle_credential,),
                    )
                connexion.commit()
            finally:
                connexion.close()
    finally:
        connexion = connexion_db()
        try:
            with connexion.cursor() as curseur:
                curseur.execute(
                    "DELETE FROM webauthn_challenges WHERE id = %s",
                    (second_challenge_id,),
                )
            connexion.commit()
        finally:
            connexion.close()


