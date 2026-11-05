
"""Tests unitaires de la finalisation transactionnelle d'authentification Passkey."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import finaliser_authentification_webauthn

CHALLENGE_HASH = b"a" * 32
SESSION_HASH = b"b" * 32
CREDENTIAL_ID = b"credential-authentification-test"
PUBLIC_KEY = b"public-key-authentification-test"


def test_authentification_admin_reussie():
    """Une Passkey valide authentifie l'administrateur atomiquement."""
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.side_effect = [
        (3, 2, PUBLIC_KEY, 5),
        (2, "AdminNetAtlas"),
        (10,),
        (3,),
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser_authentification_webauthn(
            challenge_hash=CHALLENGE_HASH,
            session_binding_hash=SESSION_HASH,
            credential_id=CREDENTIAL_ID,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    assert resultat == {
        "user_id": 2,
        "nom": "AdminNetAtlas",
        "role": "admin",
    }

    requetes = [
        " ".join(appel.args[0].split())
        for appel in curseur.execute.call_args_list
    ]

    assert len(requetes) == 4
    assert "FROM webauthn_credentials" in requetes[0]
    assert "FOR UPDATE" in requetes[0]
    assert "role_user" in requetes[1]
    assert "UPDATE webauthn_challenges" in requetes[2]
    assert "UPDATE webauthn_credentials" in requetes[3]

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()

@pytest.mark.parametrize(
    ("passkey", "compteur_precedent", "nouveau_compteur"),
    [
        (None, 5, 6),
        ((3, 2, b"cle-publique-differente", 5), 5, 6),
        ((3, 2, PUBLIC_KEY, 5), 4, 6),
        ((3, 2, PUBLIC_KEY, 5), 5, 5),
        ((3, 2, PUBLIC_KEY, 5), 5, 4),
    ],
)
def test_authentification_passkey_refusee(
    passkey, compteur_precedent, nouveau_compteur
):
    """Refuse une Passkey inconnue ou des données incohérentes."""
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = passkey

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser_authentification_webauthn(
            challenge_hash=CHALLENGE_HASH,
            session_binding_hash=SESSION_HASH,
            credential_id=CREDENTIAL_ID,
            public_key=PUBLIC_KEY,
            compteur_precedent=compteur_precedent,
            nouveau_compteur=nouveau_compteur,
            role_nom="admin",
        )

    assert resultat is False
    curseur.execute.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()

def test_authentification_challenge_invalide():
    """Refuse un challenge expiré, consommé ou inexistant."""
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.side_effect = [
        (3, 2, PUBLIC_KEY, 5),
        (2, "AdminNetAtlas"),
        None,
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser_authentification_webauthn(
            challenge_hash=CHALLENGE_HASH,
            session_binding_hash=SESSION_HASH,
            credential_id=CREDENTIAL_ID,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    assert resultat is False
    assert curseur.execute.call_count == 3

    requete_challenge = curseur.execute.call_args_list[2].args[0]
    requete_normalisee = " ".join(requete_challenge.split())

    assert "UPDATE webauthn_challenges" in requete_normalisee
    assert "operation = 'authentication'" in requete_normalisee
    assert "expires_at > CURRENT_TIMESTAMP" in requete_normalisee
    assert "consumed_at IS NULL" in requete_normalisee

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()

def test_authentification_role_admin_revoque():
    """Refuse une authentification si le rôle administrateur est absent."""
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.side_effect = [
        (3, 2, PUBLIC_KEY, 5),
        None,
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser_authentification_webauthn(
            challenge_hash=CHALLENGE_HASH,
            session_binding_hash=SESSION_HASH,
            credential_id=CREDENTIAL_ID,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    assert resultat is False
    assert curseur.execute.call_count == 2

    requete_role = curseur.execute.call_args_list[1].args[0]
    assert "role_user" in requete_role
    assert "roles" in requete_role
    assert "FOR SHARE OF u, ru, r" in requete_role

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()

def test_authentification_erreur_postgresql():
    """Une erreur SQL déclenche un rollback et ferme la connexion."""
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.execute.side_effect = RuntimeError(
        "Erreur PostgreSQL simulée"
    )

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(RuntimeError, match="Erreur PostgreSQL simulée"),
    ):
        finaliser_authentification_webauthn(
            challenge_hash=CHALLENGE_HASH,
            session_binding_hash=SESSION_HASH,
            credential_id=CREDENTIAL_ID,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    ("champ", "valeur", "message"),
    [
        ("challenge_hash", b"court", "Empreinte WebAuthn invalide"),
        ("session_binding_hash", None, "Empreinte WebAuthn invalide"),
        ("credential_id", b"", "Identifiant Passkey invalide"),
        ("public_key", None, "Clé publique invalide"),
        ("role_nom", "superadmin", "Rôle WebAuthn invalide"),
    ],
)
def test_authentification_parametres_invalides(champ, valeur, message):
    """Rejette les paramètres invalides avant toute connexion SQL."""
    parametres = {
        "challenge_hash": CHALLENGE_HASH,
        "session_binding_hash": SESSION_HASH,
        "credential_id": CREDENTIAL_ID,
        "public_key": PUBLIC_KEY,
        "compteur_precedent": 5,
        "nouveau_compteur": 6,
        "role_nom": "admin",
    }
    parametres[champ] = valeur

    with (
        patch("database.connexion_db") as connexion_mock,
        pytest.raises(ValueError, match=message),
    ):
        finaliser_authentification_webauthn(**parametres)

    connexion_mock.assert_not_called()


def test_authentification_compteur_non_modifie():
    """Refuse l'authentification si la dernière mise à jour échoue."""
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchone.side_effect = [
        (3, 2, PUBLIC_KEY, 5),
        (2, "AdminNetAtlas"),
        (10,),
        None,
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser_authentification_webauthn(
            challenge_hash=CHALLENGE_HASH,
            session_binding_hash=SESSION_HASH,
            credential_id=CREDENTIAL_ID,
            public_key=PUBLIC_KEY,
            compteur_precedent=5,
            nouveau_compteur=6,
            role_nom="admin",
        )

    assert resultat is False
    assert curseur.execute.call_count == 4
    assert "UPDATE webauthn_credentials" in (
        curseur.execute.call_args_list[3].args[0]
    )
    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()
