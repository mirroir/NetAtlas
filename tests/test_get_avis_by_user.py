import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_avis_by_user


def test_get_avis_by_user_avec_resultats():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchall.return_value = [
        (1, "test2", "Marché de Saint-Pierre"),
        (2, "Très pratique", "Marché Test NetAtlas"),
    ]

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_avis_by_user(1)

    assert resultat == [
        (1, "test2", "Marché de Saint-Pierre"),
        (2, "Très pratique", "Marché Test NetAtlas"),
    ]

    args = curseur.execute.call_args
    assert args.args[1] == (1,)
    connexion.close.assert_called_once()


def test_get_avis_by_user_sans_resultat():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchall.return_value = []

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_avis_by_user(1)

    assert resultat == []
    connexion.close.assert_called_once()



def test_get_avis_by_user_erreur_sql():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.execute.side_effect = Exception("Erreur SQL")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="Erreur SQL"),
    ):
        get_avis_by_user(1)

    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()



