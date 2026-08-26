import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import modifier_service_lieu


def creer_mocks(rowcount):
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value = curseur
    curseur.rowcount = rowcount

    return connexion, curseur


def test_modifier_service_lieu_succes():
    connexion, curseur = creer_mocks(1)

    with patch("database.connexion_db", return_value=connexion):
        resultat = modifier_service_lieu(1, 3, 5)

    assert resultat is True

    curseur.execute.assert_called_once()

    requete, parametres = curseur.execute.call_args.args

    assert "UPDATE place_services" in requete
    assert "SET service_id = %s" in requete
    assert "WHERE place_id = %s AND service_id = %s" in requete
    assert parametres == (5, 1, 3)

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()


def test_modifier_service_lieu_inexistant():
    connexion, curseur = creer_mocks(0)

    with patch("database.connexion_db", return_value=connexion):
        resultat = modifier_service_lieu(1, 99, 5)

    assert resultat is False
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()


def test_modifier_service_lieu_erreur_sql():
    connexion, curseur = creer_mocks(0)
    curseur.execute.side_effect = Exception("Erreur SQL simulée")

    with (
      patch("database.connexion_db", return_value=connexion),
      pytest.raises(Exception, match="Erreur SQL simulée"),
    ):
      modifier_service_lieu(1, 3, 5)

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()



