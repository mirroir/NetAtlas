import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import ajouter_avis


def test_ajouter_avis_succes():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (42,)

    with patch("database.connexion_db", return_value=connexion):
        avis_id = ajouter_avis(1, 1, "Très bon marché")

    assert avis_id == 42
    curseur.execute.assert_called_once()
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_ajouter_avis_erreur_sql():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.execute.side_effect = Exception("Erreur SQL")

    with ( 
       patch("database.connexion_db", return_value=connexion),
       pytest.raises(Exception, match="Erreur SQL"),
    ):
       ajouter_avis(1, 1, "Très bon marché")

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()



def test_ajouter_avis_parametres_sql():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (7,)

    with patch("database.connexion_db", return_value=connexion):
        avis_id = ajouter_avis(1, 1, "Produits frais et accueil agréable")

    assert avis_id == 7

    args = curseur.execute.call_args
    assert args.args[1] == (
        1,
        1,
        "Produits frais et accueil agréable",
    )



def test_ajouter_avis_commentaire_vide():
    with pytest.raises(
        ValueError,
        match="Le commentaire ne peut pas être vide!",
    ):
        ajouter_avis(1, 1, "   ")

def test_ajouter_avis_user_inexistant():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.execute.side_effect = Exception("foreign key violation")

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(Exception, match="foreign key violation"),
    ):
        ajouter_avis(
            1,
            9999,
            "Commentaire interdit",
        )

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()

def test_ajouter_avis_chaine_ressemblant_injection_sql():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (99,)

    commentaire = "'); DROP TABLE avis; --"

    with patch("database.connexion_db", return_value=connexion):
        avis_id = ajouter_avis(1, 1, commentaire)

    assert avis_id == 99

    args = curseur.execute.call_args

    assert args.args[1] == (
        1,
        1,
        commentaire,
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_ajouter_avis_1000_caracteres_accepte():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (42,)

    commentaire = "a" * 1000

    with patch("database.connexion_db", return_value=connexion):
        avis_id = ajouter_avis(1, 1, commentaire)

    assert avis_id == 42
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_ajouter_avis_1001_caracteres_refuse():
    commentaire = "a" * 1001

    with pytest.raises(
        ValueError,
        match="Le commentaire ne peut pas dépasser 1000 caractères!",
    ):
        ajouter_avis(1, 1, commentaire)



def test_ajouter_avis_unicode_et_caracteres_speciaux():
    connexion = MagicMock()
    curseur = MagicMock()

    connexion.cursor.return_value.__enter__.return_value = curseur
    curseur.fetchone.return_value = (77,)

    commentaire = "Très bon marché ! 😊 L'accueil était excellent.\nÀ refaire."

    with patch("database.connexion_db", return_value=connexion):
        avis_id = ajouter_avis(1, 1, commentaire)

    assert avis_id == 77

    args = curseur.execute.call_args
    assert args.args[1] == (
        1,
        1,
        commentaire,
    )

    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()



