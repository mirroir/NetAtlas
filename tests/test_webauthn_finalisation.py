"""Tests unitaires de la finalisation transactionnelle Passkey."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import finaliser_enregistrement_webauthn

CHALLENGE_HASH = b"a" * 32
SESSION_HASH = b"b" * 32
CREDENTIAL_ID = b"credential-finalisation-test"
PUBLIC_KEY = b"public-key-finalisation-test"


def finaliser():
    """Exécute la finalisation avec des paramètres de test valides."""
    return finaliser_enregistrement_webauthn(
        challenge_hash=CHALLENGE_HASH,
        session_binding_hash=SESSION_HASH,
        user_id=3,
        credential_id=CREDENTIAL_ID,
        public_key=PUBLIC_KEY,
        sign_count=0,
    )


def test_finalisation_reussie():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.side_effect = [(10,), (42,)]

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser()

    assert resultat == 42
    assert curseur.execute.call_count == 2

    premiere_requete = curseur.execute.call_args_list[0]
    seconde_requete = curseur.execute.call_args_list[1]

    assert "UPDATE webauthn_challenges" in premiere_requete.args[0]
    assert premiere_requete.args[1] == (
        CHALLENGE_HASH,
        SESSION_HASH,
        3,
    )

    assert "INSERT INTO webauthn_credentials" in seconde_requete.args[0]
    assert seconde_requete.args[1] == (
        3,
        CREDENTIAL_ID,
        PUBLIC_KEY,
        0,
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_finalisation_challenge_invalide():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser()

    assert resultat is False
    curseur.execute.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()


def test_finalisation_erreur_insertion():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.return_value = (10,)
    curseur.execute.side_effect = [
        None,
        RuntimeError("Insertion impossible"),
    ]

    with (
         patch("database.connexion_db", return_value=connexion),
         pytest.raises(RuntimeError, match="Insertion impossible"),
    ):
         finaliser()

    assert curseur.execute.call_count == 2
    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    ("parametre", "valeur"),
    [
        ("challenge_hash", b"court"),
        ("session_binding_hash", b"court"),
        ("user_id", 0),
        ("credential_id", b""),
        ("public_key", b""),
        ("sign_count", -1),
    ],
)
def test_finalisation_parametres_invalides(parametre, valeur):
    arguments = {
        "challenge_hash": CHALLENGE_HASH,
        "session_binding_hash": SESSION_HASH,
        "user_id": 3,
        "credential_id": CREDENTIAL_ID,
        "public_key": PUBLIC_KEY,
        "sign_count": 0,
    }
    arguments[parametre] = valeur

    with patch("database.connexion_db") as connexion, pytest.raises(ValueError):
        finaliser_enregistrement_webauthn(**arguments)

    connexion.assert_not_called()


