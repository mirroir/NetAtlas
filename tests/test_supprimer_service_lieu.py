import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "python"))

from database import supprimer_service_lieu


def test_supprimer_service_lieu_succes():
    connexion = MagicMock()
    curseur = MagicMock()
    connexion.cursor.return_value = curseur
    curseur.rowcount = 1

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_service_lieu(1, 3)

    curseur.execute.assert_called_once_with(
        """
            DELETE FROM place_services
            WHERE place_id = %s AND service_id = %s
            """,
        (1, 3),
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()

    assert resultat is True


def test_supprimer_service_lieu_inexistant():
    connexion = MagicMock()
    curseur = MagicMock()
    connexion.cursor.return_value = curseur
    curseur.rowcount = 0

    with patch("database.connexion_db", return_value=connexion):
        resultat = supprimer_service_lieu(1, 999)

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()

    assert resultat is False


def test_supprimer_service_lieu_erreur():
    connexion = MagicMock()
    curseur = MagicMock()
    connexion.cursor.return_value = curseur

    curseur.execute.side_effect = Exception("Erreur SQL")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL"),
    ):
        supprimer_service_lieu(1, 3)

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()



