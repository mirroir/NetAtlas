import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_tags_with_ids


def test_get_tags_with_ids():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchall.return_value = [
        (1, "Marché forain"),
        (2, "Producteurs locaux"),
        (3, "Produits frais"),
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_tags_with_ids()

    assert resultat == [
        (1, "Marché forain"),
        (2, "Producteurs locaux"),
        (3, "Produits frais"),
    ]

    curseur.execute.assert_called_once()
    connexion.close.assert_called_once()


def test_get_tags_with_ids_vide():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchall.return_value = []

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_tags_with_ids()

    assert resultat == []
    connexion.close.assert_called_once()


def test_get_tags_with_ids_erreur_sql():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.execute.side_effect = Exception("Erreur SQL simulée")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL simulée"),
    ):
        get_tags_with_ids()

    connexion.close.assert_called_once()


