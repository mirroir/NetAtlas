import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import choisir_utilisateur

UTILISATEURS = [
    (1, "Utilisateur Test", "test@netatlas.local"),
    (2, "Alice", "alice@netatlas.local"),
]


def test_choisir_utilisateur_valide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "2")

    with patch("menu.get_users", return_value=UTILISATEURS):
        user_id = choisir_utilisateur()

    sortie = capsys.readouterr().out

    assert user_id == 2
    assert "Bienvenue Alice !" in sortie


def test_choisir_utilisateur_aucun(capsys):
    with patch("menu.get_users", return_value=[]):
        user_id = choisir_utilisateur()

    sortie = capsys.readouterr().out

    assert user_id is None
    assert "Aucun utilisateur disponible." in sortie


def test_choisir_utilisateur_non_numerique(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "abc")

    with patch("menu.get_users", return_value=UTILISATEURS):
        user_id = choisir_utilisateur()

    sortie = capsys.readouterr().out

    assert user_id is None
    assert "Erreur : le choix doit être un nombre." in sortie


def test_choisir_utilisateur_invalide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "99")

    with patch("menu.get_users", return_value=UTILISATEURS):
        user_id = choisir_utilisateur()

    sortie = capsys.readouterr().out

    assert user_id is None
    assert "Erreur : utilisateur invalide." in sortie




