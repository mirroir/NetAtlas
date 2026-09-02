import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import supprimer_avis


def test_supprimer_avis_succes():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.rowcount = 1

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_avis(1, 1)

    assert resultat is True
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_supprimer_avis_non_autorise():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.rowcount = 0

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_avis(1, 2)

    assert resultat is False
    connexion.commit.assert_called_once()
    connexion.close.assert_called_once()


def test_supprimer_avis_erreur_sql():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.execute.side_effect = Exception("Erreur SQL")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL"),
    ):
        supprimer_avis(1, 1)

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()



def test_supprimer_avis_autre_utilisateur_refuse():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.rowcount = 0

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_avis(2, 2)

    assert resultat is False

    args = curseur.execute.call_args
    assert args.args[1] == (2, 2)

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_supprimer_avis_inexistant():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.rowcount = 0

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_avis(9999, 1)

    assert resultat is False
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()




