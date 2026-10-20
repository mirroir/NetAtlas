import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import (
    enregistrer_credential_webauthn,
    get_credential_webauthn,
    mettre_a_jour_compteur_webauthn,
)


def test_enregistrer_credential_webauthn():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = (42,)

    with patch("database.connexion_db", return_value=connexion):
        resultat = enregistrer_credential_webauthn(
            user_id=3,
            credential_id=b"credential-test",
            public_key=b"public-key-test",
            sign_count=0,
        )

    assert resultat == 42

    curseur.execute.assert_called_once_with(
        """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key, sign_count)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
        (3, b"credential-test", b"public-key-test", 0),
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()



def test_enregistrer_credential_webauthn_erreur():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.execute.side_effect = RuntimeError(
        "Erreur PostgreSQL simulée"
    )

    with patch("database.connexion_db", return_value=connexion), pytest.raises(
        RuntimeError,
        match="Erreur PostgreSQL simulée",
    ):
        enregistrer_credential_webauthn(
            user_id=3,
            credential_id=b"credential-erreur-test",
            public_key=b"public-key-erreur-test",
        )

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()



def test_get_credential_webauthn_existante():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = (
        42,
        3,
        b"credential-test",
        b"public-key-test",
        0,
    )

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_credential_webauthn(
            b"credential-test"
        )

    assert resultat == {
        "id": 42,
        "user_id": 3,
        "credential_id": b"credential-test",
        "public_key": b"public-key-test",
        "sign_count": 0,
    }

    curseur.execute.assert_called_once()
    assert curseur.execute.call_args.args[1] == (
        b"credential-test",
    )

    connexion.close.assert_called_once()



def test_get_credential_webauthn_inexistante():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    # PostgreSQL ne trouve aucune Passkey
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_credential_webauthn(
            b"credential-inexistante"
        )

    assert resultat is None

    curseur.execute.assert_called_once()
    assert curseur.execute.call_args.args[1] == (
        b"credential-inexistante",
    )

    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()



def test_mettre_a_jour_compteur_webauthn():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    # PostgreSQL confirme qu'une Passkey a été mise à jour
    curseur.fetchone.return_value = (42,)

    with patch("database.connexion_db", return_value=connexion):
        resultat = mettre_a_jour_compteur_webauthn(
            credential_id=b"credential-test",
            sign_count=5,
        )

    assert resultat is True

    curseur.execute.assert_called_once()
    assert curseur.execute.call_args.args[1] == (
        5,
        b"credential-test",
        5,
        5,
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()



def test_mettre_a_jour_compteur_webauthn_inexistant():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    # PostgreSQL ne trouve aucune Passkey
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = mettre_a_jour_compteur_webauthn(
            credential_id=b"credential-inexistante",
            sign_count=5,
        )

    assert resultat is False

    curseur.execute.assert_called_once()
    assert curseur.execute.call_args.args[1] == (
        5,
        b"credential-inexistante",
        5,
        5,
    )

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()



def test_mettre_a_jour_compteur_webauthn_erreur():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    # Simulation d'une erreur pendant la requête PostgreSQL
    curseur.execute.side_effect = RuntimeError(
        "Erreur compteur WebAuthn simulée"
    )

    with patch(
        "database.connexion_db",
        return_value=connexion,
    ), pytest.raises(
        RuntimeError,
        match="Erreur compteur WebAuthn simulée",
    ):
        mettre_a_jour_compteur_webauthn(
            credential_id=b"credential-erreur-compteur",
            sign_count=5,
        )

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()


def test_mettre_a_jour_compteur_webauthn_condition_securisee():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = mettre_a_jour_compteur_webauthn(
            credential_id=b"credential-compteur-identique",
            sign_count=5,
        )

    assert resultat is False

    requete = curseur.execute.call_args.args[0]
    requete_normalisee = " ".join(requete.split())

    assert "sign_count = 0 AND %s = 0" in requete_normalisee
    assert "sign_count < %s" in requete_normalisee

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()


