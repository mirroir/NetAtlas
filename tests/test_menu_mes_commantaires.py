import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import menu_mes_commentaires

AVIS = [
    (1, "Très bon marché", "Marché de Saint-Pierre"),
]


def test_menu_mes_commentaires_affichage(monkeypatch, capsys):
    choix = iter(["1", "4"])
    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    with patch("menu.get_avis_by_user", return_value=AVIS):
        menu_mes_commentaires(1)

    sortie = capsys.readouterr().out

    assert "Très bon marché" in sortie
    assert "Marché de Saint-Pierre" in sortie


def test_menu_mes_commentaires_aucun_avis(monkeypatch, capsys):
    choix = iter(["1", "4"])
    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    with patch("menu.get_avis_by_user", return_value=[]):
        menu_mes_commentaires(1)

    sortie = capsys.readouterr().out

    assert "Vous n'avez aucun commentaire." in sortie


def test_menu_mes_commentaires_ajout(monkeypatch):
    choix = iter(["2", "4"])
    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    with patch("menu.ajouter_commentaire_a_lieu") as mock_ajouter:
        menu_mes_commentaires(1)

    mock_ajouter.assert_called_once()


def test_menu_mes_commentaires_suppression(monkeypatch):
    choix = iter(["3", "4"])
    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    with patch("menu.supprimer_commentaire_a_lieu") as mock_supprimer:
        menu_mes_commentaires(1)

    mock_supprimer.assert_called_once()


def test_menu_mes_commentaires_retour(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "4")

    menu_mes_commentaires(1)


def test_menu_mes_commentaires_choix_invalide(monkeypatch, capsys):
    choix = iter(["99", "4"])
    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    menu_mes_commentaires(1)

    sortie = capsys.readouterr().out

    assert "Choix invalide." in sortie



