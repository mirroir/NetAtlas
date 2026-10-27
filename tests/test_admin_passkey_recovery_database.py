"""Tests unitaires de la préparation de récupération Passkey."""

from unittest.mock import MagicMock

import pytest

from database import preparer_recuperation_passkey_admin


@pytest.fixture
def connexion_simulee(monkeypatch):
    """Remplacer PostgreSQL par une connexion simulée."""

    connexion = MagicMock()

    monkeypatch.setattr(
        "database.connexion_db",
        lambda: connexion,
    )

    return connexion


@pytest.mark.parametrize(
    "position",
    [0, 1, 2],
)
@pytest.mark.parametrize(
    "valeur",
    [
        None,
        "",
        b"",
        b"a" * 31,
        b"a" * 33,
    ],
)
def test_refuser_empreinte_invalide(
    connexion_simulee,
    position,
    valeur,
):
    """Refuser toute empreinte absente ou incorrecte."""

    empreintes = [b"a" * 32, b"b" * 32, b"c" * 32]
    empreintes[position] = valeur

    with pytest.raises(ValueError):
        preparer_recuperation_passkey_admin(*empreintes)

    connexion_simulee.cursor.assert_not_called()


def test_preparation_reussie(connexion_simulee):
    """Retourner l'administrateur autorisé par PostgreSQL."""

    curseur = connexion_simulee.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = (3, "AdminTest")

    resultat = preparer_recuperation_passkey_admin(
        b"a" * 32,
        b"b" * 32,
        b"c" * 32,
    )

    assert resultat == {
        "user_id": 3,
        "nom": "AdminTest",
    }

    assert curseur.execute.call_count == 1

    requete, parametres = curseur.execute.call_args.args

    assert "public.preparer_recuperation_passkey_admin" in requete
    assert parametres == (
        b"a" * 32,
        b"b" * 32,
        b"c" * 32,
    )

    connexion_simulee.commit.assert_called_once()
    connexion_simulee.close.assert_called_once()


def test_autorisation_absente(connexion_simulee):
    """Retourner None si PostgreSQL refuse la préparation."""

    curseur = connexion_simulee.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = None

    resultat = preparer_recuperation_passkey_admin(
        b"a" * 32,
        b"b" * 32,
        b"c" * 32,
    )

    assert resultat is None

    connexion_simulee.commit.assert_called_once()
    connexion_simulee.close.assert_called_once()


def test_erreur_postgresql(connexion_simulee):
    """Annuler la transaction si PostgreSQL échoue."""

    curseur = connexion_simulee.cursor.return_value.__enter__.return_value
    curseur.execute.side_effect = RuntimeError("Erreur PostgreSQL simulée")

    with pytest.raises(RuntimeError, match="Erreur PostgreSQL simulée"):
        preparer_recuperation_passkey_admin(
            b"a" * 32,
            b"b" * 32,
            b"c" * 32,
        )

    connexion_simulee.rollback.assert_called_once()
    connexion_simulee.close.assert_called_once()
