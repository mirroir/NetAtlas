"""Tests de validation des challenges WebAuthn."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import (
    consommer_challenge_webauthn,
    enregistrer_challenge_webauthn,
)

CHALLENGE_HASH = b"a" * 32
SESSION_BINDING_HASH = b"b" * 32


@pytest.mark.parametrize(
    "challenge_hash",
    [b"", b"court", None, "a" * 32],
)
def test_challenge_hash_invalide(challenge_hash):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Empreinte du challenge invalide"),
    ):
        enregistrer_challenge_webauthn(
            challenge_hash,
            SESSION_BINDING_HASH,
            "authentication",
        )

    connexion.assert_not_called()


@pytest.mark.parametrize(
    "session_binding_hash",
    [b"", b"court", None, "b" * 32],
)
def test_session_binding_hash_invalide(session_binding_hash):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Empreinte de tentative invalide"),
    ):
        enregistrer_challenge_webauthn(
            CHALLENGE_HASH,
            session_binding_hash,
            "authentication",
        )

    connexion.assert_not_called()


@pytest.mark.parametrize(
    "operation",
    ["", "login", "register", None],
)
def test_operation_webauthn_invalide(operation):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Opération WebAuthn invalide"),
    ):
        enregistrer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            operation,
        )

    connexion.assert_not_called()


def test_enregistrement_sans_utilisateur_refuse():
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Utilisateur obligatoire"),
    ):
        enregistrer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "registration",
        )

    connexion.assert_not_called()


@pytest.mark.parametrize(
    "duree",
    [0, -1, 301, None, "60"],
)
def test_duree_challenge_invalide(duree):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Durée du challenge invalide"),
    ):
        enregistrer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "authentication",
            duree_secondes=duree,
        )

    connexion.assert_not_called()

def test_enregistrer_challenge_succes():
    with patch("database.connexion_db") as connexion_db:
        connexion = connexion_db.return_value
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.fetchone.return_value = (42,)

        resultat = enregistrer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "registration",
            user_id=3,
            duree_secondes=60,
        )

    assert resultat == 42

    requete, parametres = curseur.execute.call_args.args

    assert "INSERT INTO webauthn_challenges" in requete
    assert "RETURNING id" in requete
    assert parametres == (
        CHALLENGE_HASH,
        SESSION_BINDING_HASH,
        3,
        "registration",
        60,
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_enregistrer_challenge_erreur_sql():
    with patch("database.connexion_db") as connexion_db:
        connexion = connexion_db.return_value
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.execute.side_effect = RuntimeError("Erreur SQL simulée")

        with pytest.raises(RuntimeError, match="Erreur SQL simulée"):
            enregistrer_challenge_webauthn(
                CHALLENGE_HASH,
                SESSION_BINDING_HASH,
                "authentication",
            )

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()


def test_enregistrer_challenge_fermeture_connexion():
    with patch("database.connexion_db") as connexion_db:
        connexion = connexion_db.return_value
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.fetchone.return_value = (7,)

        enregistrer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "authentication",
        )

    connexion.close.assert_called_once()

def test_consommer_challenge_succes():
    with patch("database.connexion_db") as connexion_db:
        connexion = connexion_db.return_value
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.fetchone.return_value = (42,)

        resultat = consommer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "registration",
            user_id=3,
        )

    assert resultat is True

    requete, parametres = curseur.execute.call_args.args

    assert "UPDATE webauthn_challenges" in requete
    assert "SET consumed_at = CURRENT_TIMESTAMP" in requete
    assert "session_binding_hash = %s" in requete
    assert "operation = %s" in requete
    assert "user_id IS NOT DISTINCT FROM %s" in requete
    assert "expires_at > CURRENT_TIMESTAMP" in requete
    assert "consumed_at IS NULL" in requete

    assert parametres == (
        CHALLENGE_HASH,
        SESSION_BINDING_HASH,
        "registration",
        3,
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    "situation",
    [
        "challenge_deja_consomme",
        "challenge_expire",
        "mauvaise_session",
        "mauvaise_operation",
        "mauvais_utilisateur",
        "challenge_inconnu",
    ],
)
def test_consommer_challenge_refuse(situation):
    """Simule les situations où aucune ligne SQL n'est modifiée."""
    with patch("database.connexion_db") as connexion_db:
        connexion = connexion_db.return_value
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.fetchone.return_value = None

        resultat = consommer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "registration",
            user_id=3,
        )

    assert resultat is False, situation
    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()


def test_consommer_challenge_erreur_sql():
    with patch("database.connexion_db") as connexion_db:
        connexion = connexion_db.return_value
        curseur = connexion.cursor.return_value.__enter__.return_value
        curseur.execute.side_effect = RuntimeError("Erreur SQL simulée")

        with pytest.raises(RuntimeError, match="Erreur SQL simulée"):
            consommer_challenge_webauthn(
                CHALLENGE_HASH,
                SESSION_BINDING_HASH,
                "authentication",
            )

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    "challenge_hash",
    [b"", b"court", None, "a" * 32],
)
def test_consommation_challenge_hash_invalide(challenge_hash):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Empreinte du challenge invalide"),
    ):
        consommer_challenge_webauthn(
            challenge_hash,
            SESSION_BINDING_HASH,
            "authentication",
        )

    connexion.assert_not_called()


@pytest.mark.parametrize(
    "session_binding_hash",
    [b"", b"court", None, "b" * 32],
)
def test_consommation_session_hash_invalide(session_binding_hash):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Empreinte de tentative invalide"),
    ):
        consommer_challenge_webauthn(
            CHALLENGE_HASH,
            session_binding_hash,
            "authentication",
        )

    connexion.assert_not_called()


@pytest.mark.parametrize(
    "operation",
    ["", "login", "register", None],
)
def test_consommation_operation_invalide(operation):
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Opération WebAuthn invalide"),
    ):
        consommer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            operation,
        )

    connexion.assert_not_called()


def test_consommation_enregistrement_sans_utilisateur():
    with (
        patch("database.connexion_db") as connexion,
        pytest.raises(ValueError, match="Utilisateur obligatoire"),
    ):
        consommer_challenge_webauthn(
            CHALLENGE_HASH,
            SESSION_BINDING_HASH,
            "registration",
        )

    connexion.assert_not_called()


