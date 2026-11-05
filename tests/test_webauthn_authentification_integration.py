
"""Tests PostgreSQL réels de la finalisation d'authentification Passkey."""

import hashlib
import os
import secrets
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import (
    connexion_db,
    enregistrer_challenge_webauthn,
    enregistrer_credential_webauthn,
    finaliser_authentification_webauthn,
)

USER_ID = 3
PUBLIC_KEY = b"public-key-authentification-integration"


@pytest.fixture
def donnees_authentification():
    """Prépare et nettoie une Passkey et un challenge temporaires."""
    if (
        os.getenv("NETATLAS_ENV") != "test"
        or os.getenv("DB_NAME") != "netatlas_test"
    ):
        pytest.fail("Base de test NetAtlas obligatoire.")

    credential_id = secrets.token_bytes(32)
    challenge_hash = hashlib.sha256(secrets.token_bytes(32)).digest()
    session_hash = hashlib.sha256(secrets.token_bytes(32)).digest()

    challenge_db_id = None

    try:
        enregistrer_credential_webauthn(
            user_id=USER_ID,
            credential_id=credential_id,
            public_key=PUBLIC_KEY,
            sign_count=5,
        )

        challenge_db_id = enregistrer_challenge_webauthn(
            challenge_hash=challenge_hash,
            session_binding_hash=session_hash,
            operation="authentication",
        )

        yield credential_id, challenge_hash, session_hash, challenge_db_id

    finally:
        connexion = connexion_db()

        try:
            with connexion.cursor() as curseur:
                curseur.execute(
                    "DELETE FROM webauthn_challenges WHERE challenge_hash = %s",
                    (challenge_hash,),
                )
                curseur.execute(
                    "DELETE FROM webauthn_credentials WHERE credential_id = %s",
                    (credential_id,),
                )

            connexion.commit()

        except Exception:
            connexion.rollback()
            raise

        finally:
            connexion.close()


def test_authentification_postgresql_reussie(donnees_authentification):
    """Vérifie la transaction et les données réellement enregistrées."""
    credential_id, challenge_hash, session_hash, challenge_db_id = (
        donnees_authentification
    )

    resultat = finaliser_authentification_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        compteur_precedent=5,
        nouveau_compteur=6,
        role_nom="admin",
    )


    assert isinstance(resultat, dict)
    assert resultat["user_id"] == USER_ID
    assert resultat["role"] == "admin"

    connexion = connexion_db()
    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT nom FROM users WHERE id = %s",
                (USER_ID,),
            )
            utilisateur = curseur.fetchone()
            assert utilisateur is not None
            assert resultat["nom"] == utilisateur[0]
    finally:
        connexion.close()

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )
            assert curseur.fetchone()[0] == 6

            curseur.execute(
                """
                SELECT consumed_at
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )
            assert curseur.fetchone()[0] is not None

    finally:
        connexion.close()

def test_authentification_postgresql_challenge_expire_refuse(
    donnees_authentification,
):
    """Un challenge expiré est refusé sans modifier la Passkey."""
    credential_id, challenge_hash, session_hash, challenge_db_id = (
        donnees_authentification
    )

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE webauthn_challenges
                SET expires_at = CURRENT_TIMESTAMP - INTERVAL '1 minute'
                WHERE id = %s
                """,
                (challenge_db_id,),
            )

            assert curseur.rowcount == 1

        connexion.commit()

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()

    resultat = finaliser_authentification_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        compteur_precedent=5,
        nouveau_compteur=6,
        role_nom="admin",
    )

    assert resultat is False

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )

            assert curseur.fetchone()[0] == 5

            curseur.execute(
                """
                SELECT consumed_at,
                       expires_at < CURRENT_TIMESTAMP
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )

            consumed_at, est_expire = curseur.fetchone()

            assert consumed_at is None
            assert est_expire is True

    finally:
        connexion.close()

def test_authentification_postgresql_rejeu_refuse(donnees_authentification):
    """Un challenge déjà consommé ne doit pas être réutilisable."""
    credential_id, challenge_hash, session_hash, challenge_db_id = (
        donnees_authentification
    )

    premiere = finaliser_authentification_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        compteur_precedent=5,
        nouveau_compteur=6,
        role_nom="admin",
    )

    assert premiere is not False

    seconde = finaliser_authentification_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        compteur_precedent=6,
        nouveau_compteur=7,
        role_nom="admin",
    )

    assert seconde is False

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )
            assert curseur.fetchone()[0] == 6

            curseur.execute(
                """
                SELECT consumed_at
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )
            assert curseur.fetchone()[0] is not None

    finally:
        connexion.close()

def test_authentification_postgresql_compteur_incoherent_refuse(
    donnees_authentification,
):
    """Un compteur inférieur est refusé sans consommer le challenge."""
    credential_id, challenge_hash, session_hash, challenge_db_id = (
        donnees_authentification
    )

    resultat = finaliser_authentification_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        compteur_precedent=5,
        nouveau_compteur=4,
        role_nom="admin",
    )

    assert resultat is False

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )
            assert curseur.fetchone()[0] == 5

            curseur.execute(
                """
                SELECT consumed_at
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )
            assert curseur.fetchone()[0] is None

    finally:
        connexion.close()


def test_authentification_postgresql_rollback_apres_challenge(
    donnees_authentification,
):
    """Une erreur après consommation annule toute la transaction."""
    credential_id, challenge_hash, session_hash, challenge_db_id = (
        donnees_authentification
    )

    connexion_reelle = connexion_db()

    class CurseurInstrumente:
        def __init__(self, curseur):
            self._curseur = curseur

        def __enter__(self):
            self._curseur.__enter__()
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return self._curseur.__exit__(exc_type, exc_value, traceback)

        def execute(self, requete, parametres=None):
            requete_normalisee = " ".join(requete.split()).upper()

            if (
                "UPDATE WEBAUTHN_CREDENTIALS" in requete_normalisee
                and "SET SIGN_COUNT" in requete_normalisee
            ):
                raise RuntimeError("Erreur SQL contrôlée après challenge")

            return self._curseur.execute(requete, parametres)

        def fetchone(self):
            return self._curseur.fetchone()

    curseur_original = connexion_reelle.cursor

    def curseur_instrumente():
        return CurseurInstrumente(curseur_original())

    with (
        patch("database.connexion_db", return_value=connexion_reelle),
        patch.object(connexion_reelle, "cursor", side_effect=curseur_instrumente),
        pytest.raises(
            RuntimeError,
            match="Erreur SQL contrôlée après challenge",
        ),
    ):
        finaliser_authentification_webauthn(
            challenge_hash=challenge_hash,
            session_binding_hash=session_hash,
            credential_id=credential_id,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )
            assert curseur.fetchone()[0] == 5

            curseur.execute(
                """
                SELECT consumed_at
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )
            assert curseur.fetchone()[0] is None

    finally:
        connexion.close()


def test_authentification_postgresql_concurrente(donnees_authentification):
    """Deux authentifications concurrentes : une seule doit réussir."""
    credential_id, challenge_hash, session_hash, challenge_db_id = (
        donnees_authentification
    )

    def authentifier():
        return finaliser_authentification_webauthn(
            challenge_hash=challenge_hash,
            session_binding_hash=session_hash,
            credential_id=credential_id,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        resultats = list(executor.map(lambda _: authentifier(), range(2)))

    reussites = [resultat for resultat in resultats if resultat is not False]
    refus = [resultat for resultat in resultats if resultat is False]

    assert len(reussites) == 1
    assert len(refus) == 1

    assert isinstance(reussites[0], dict)
    assert reussites[0]["user_id"] == USER_ID
    assert reussites[0]["role"] == "admin"

    connexion = connexion_db()
    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT nom FROM users WHERE id = %s",
                (USER_ID,),
            )
            utilisateur = curseur.fetchone()
            assert utilisateur is not None
            assert reussites[0]["nom"] == utilisateur[0]
    finally:
        connexion.close()

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )
            assert curseur.fetchone()[0] == 6

            curseur.execute(
                """
                SELECT consumed_at
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )
            assert curseur.fetchone()[0] is not None

    finally:
        connexion.close()

def test_authentification_postgresql_role_non_attribue_refuse(
    donnees_authentification,
):
    """Une Passkey ne permet pas de revendiquer un rôle non attribué."""
    (
        credential_id,
        challenge_hash,
        session_hash,
        challenge_db_id,
    ) = donnees_authentification

    resultat = finaliser_authentification_webauthn(
        challenge_hash=challenge_hash,
        session_binding_hash=session_hash,
        credential_id=credential_id,
        public_key=PUBLIC_KEY,
        compteur_precedent=5,
        nouveau_compteur=6,
        role_nom="utilisateur",
    )

    assert resultat is False

    connexion = connexion_db()
    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )
            assert curseur.fetchone()[0] == 5

            curseur.execute(
                """
                SELECT consumed_at
                FROM webauthn_challenges
                WHERE id = %s
                """,
                (challenge_db_id,),
            )
            assert curseur.fetchone()[0] is None
    finally:
        connexion.close()


def test_authentification_utilisateur_elevation_admin_refusee(monkeypatch):
    """Une Passkey utilisateur ne permet pas d'obtenir le rôle admin."""
    from unittest.mock import MagicMock

    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    # Passkey valide appartenant à un utilisateur standard.
    curseur.fetchone.side_effect = [
        (840, 310, b"cle-publique-utilisateur", 5),
        None,  # Aucun rôle admin attribué à cet utilisateur.
    ]

    monkeypatch.setattr(
        "database.connexion_db",
        lambda: connexion,
    )

    resultat = finaliser_authentification_webauthn(
        challenge_hash=b"a" * 32,
        session_binding_hash=b"b" * 32,
        credential_id=b"credential-utilisateur",
        public_key=b"cle-publique-utilisateur",
        compteur_precedent=5,
        nouveau_compteur=6,
        role_nom="admin",
    )

    assert resultat is False
    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()

    # Vérifier que la fonction a contrôlé le rôle administrateur.
    requete_role = curseur.execute.call_args_list[1]
    assert "JOIN role_user" in requete_role.args[0]
    assert requete_role.args[1] == (310, "admin")

    # Aucune modification du challenge ni du compteur Passkey.
    assert curseur.execute.call_count == 2
