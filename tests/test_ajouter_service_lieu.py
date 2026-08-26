import pathlib
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "python"))

from database import ajouter_service_lieu


def test_ajouter_service_lieu_succes():
    connexion = MagicMock()
    curseur = MagicMock()
    connexion.cursor.return_value = curseur
    curseur.rowcount = 1

    with patch("database.connexion_db", return_value=connexion):
        resultat = ajouter_service_lieu(1, 1)

    curseur.execute.assert_called_once_with(
        """
            INSERT INTO place_services (place_id, service_id)
            VALUES (%s, %s)
            ON CONFLICT (place_id, service_id) DO
            NOTHING
            """,
        (1, 1),
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()

    assert resultat is True

def test_ajouter_service_lieu_erreur():
    connexion = MagicMock()
    curseur = MagicMock()
    connexion.cursor.return_value = curseur

    curseur.execute.side_effect = Exception("Erreur SQL")

    with (
      patch("database.connexion_db", return_value=connexion), 
      pytest.raises(Exception, match="Erreur SQL"),
    ):
      ajouter_service_lieu(1, 1)

    connexion.commit.assert_not_called()
    connexion.rollback.assert_called_once()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()

def test_ajouter_service_lieu_doublon():
    connexion = MagicMock()
    curseur = MagicMock()
    connexion.cursor.return_value = curseur

    curseur.rowcount = 0

    with patch("database.connexion_db", return_value=connexion):
        resultat = ajouter_service_lieu(1, 2)

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    curseur.close.assert_called_once()
    connexion.close.assert_called_once()

    assert resultat is False



