import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import supprimer_tag_lieu


def creer_mocks(rowcount):
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value = curseur
    curseur.rowcount = rowcount

    return connexion, curseur


def test_supprimer_tag_lieu_succes():
    connexion, curseur = creer_mocks(1)

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_tag_lieu(1, 3)

    assert resultat is True

    curseur.execute.assert_called_once()
    requete, parametres = curseur.execute.call_args.args

    assert "DELETE FROM place_tags" in requete
    assert "WHERE place_id = %s AND tag_id = %s" in requete
    assert parametres == (1, 3)

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()


def test_supprimer_tag_lieu_inexistant():
    connexion, curseur = creer_mocks(0)

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_tag_lieu(1, 99)

    assert resultat is False
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()


def test_supprimer_tag_lieu_erreur_sql():
    connexion, curseur = creer_mocks(0)
    curseur.execute.side_effect = Exception("Erreur SQL simulée")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL simulée"),
    ):
        supprimer_tag_lieu(1, 3)

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()



