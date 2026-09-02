import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import ajouter_commentaire_a_lieu

LIEUX = [
    (1, "Marché de Saint-Pierre"),
    (4, "Marché Test NetAtlas"),
]


def test_ajouter_commentaire_succes(monkeypatch, capsys):
    reponses = iter(["1", "Très bon marché"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.ajouter_avis") as mock_ajouter,
    ):
        ajouter_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Commentaire ajouté avec succès." in sortie
    mock_ajouter.assert_called_once_with(1, 1, "Très bon marché")


def test_ajouter_commentaire_aucun_lieu(capsys):
    with (
        patch("menu.get_places_with_ids", return_value=[]),
        patch("menu.ajouter_avis") as mock_ajouter,
    ):
        ajouter_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Aucun lieu disponible." in sortie
    mock_ajouter.assert_not_called()


def test_ajouter_commentaire_choix_non_numerique(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "abc")

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.ajouter_avis") as mock_ajouter,
    ):
        ajouter_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Erreur : le choix doit être un nombre." in sortie
    mock_ajouter.assert_not_called()


def test_ajouter_commentaire_choix_invalide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "99")

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.ajouter_avis") as mock_ajouter,
    ):
        ajouter_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Erreur : choix de lieu invalide." in sortie
    mock_ajouter.assert_not_called()


def test_ajouter_commentaire_vide(monkeypatch, capsys):
    reponses = iter(["1", "   "])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.ajouter_avis") as mock_ajouter,
    ):
        ajouter_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Erreur : le commentaire ne peut pas être vide." in sortie
    mock_ajouter.assert_not_called()




