import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_place_category_id


def test_get_place_category_id_lieu_existant():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = (1,)

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_place_category_id(1)

    assert resultat == 1
    connexion.close.assert_called_once()


def test_get_place_category_id_lieu_inexistant():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.return_value = None

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_place_category_id(999)

    assert resultat is None
    connexion.close.assert_called_once()


def test_get_place_category_id_erreur_sql():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.execute.side_effect = Exception("Erreur SQL simulée")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL simulée"),
    ):
        get_place_category_id(1)

    connexion.close.assert_called_once()



