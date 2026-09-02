import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_places_with_ids


def test_get_places_with_ids_plusieurs_lieux():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchall.return_value = [
        (4, "Marché de Saint-Pierre"),
        (1, "Marché Test NetAtlas"),
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_places_with_ids()

    assert resultat == [
        (4, "Marché de Saint-Pierre"),
        (1, "Marché Test NetAtlas"),
    ]
    connexion.close.assert_called_once()


def test_get_places_with_ids_aucun_lieu():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchall.return_value = []

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_places_with_ids()

    assert resultat == []
    connexion.close.assert_called_once()


def test_get_places_with_ids_erreur_sql():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.execute.side_effect = Exception("Erreur SQL simulée")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL simulée"),
    ):
        get_places_with_ids()

    connexion.close.assert_called_once()


