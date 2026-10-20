"""Tests PostgreSQL réels des challenges WebAuthn."""

import hashlib
import secrets
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from concurrent.futures import ThreadPoolExecutor

from database import (
    connexion_db,
    consommer_challenge_webauthn,
    enregistrer_challenge_webauthn,
)


@pytest.fixture
def challenge_test():
    """Crée un challenge et supprime ses données après le test."""

    challenge_hash = hashlib.sha256(secrets.token_bytes(32)).digest()
    session_hash = hashlib.sha256(secrets.token_bytes(32)).digest()

    challenge_id = enregistrer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "authentication",
    )

    try:
        yield challenge_hash, session_hash, challenge_id

    finally:
        connexion = connexion_db()

        try:
            with connexion.cursor() as curseur:
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


def test_challenge_consommation_unique(challenge_test):
    challenge_hash, session_hash, _ = challenge_test

    premiere = consommer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "authentication",
    )

    seconde = consommer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "authentication",
    )

    assert premiere is True
    assert seconde is False


def test_challenge_mauvaise_session_refusee(challenge_test):
    challenge_hash, session_hash, _ = challenge_test

    mauvaise_session = hashlib.sha256(secrets.token_bytes(32)).digest()

    assert mauvaise_session != session_hash

    resultat = consommer_challenge_webauthn(
        challenge_hash,
        mauvaise_session,
        "authentication",
    )

    assert resultat is False

    # La mauvaise tentative ne doit pas consommer le challenge.
    assert consommer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "authentication",
    ) is True


def test_challenge_mauvaise_operation_refusee(challenge_test):
    challenge_hash, session_hash, _ = challenge_test

    resultat = consommer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "registration",
        user_id=3,
    )

    assert resultat is False

    assert consommer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "authentication",
    ) is True


def test_challenge_expire_refuse(challenge_test):
    challenge_hash, session_hash, challenge_id = challenge_test

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE webauthn_challenges
                SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 second'
                WHERE id = %s
                """,
                (challenge_id,),
            )

        connexion.commit()

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()

    assert consommer_challenge_webauthn(
        challenge_hash,
        session_hash,
        "authentication",
    ) is False

def test_challenge_consommation_concurrente(challenge_test):
    """Deux consommations simultanées : une seule doit réussir."""
    challenge_hash, session_hash, _ = challenge_test

    def consommer():
        return consommer_challenge_webauthn(
            challenge_hash,
            session_hash,
            "authentication",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultats = list(executor.map(lambda _: consommer(), range(2)))

    assert sorted(resultats) == [False, True]


