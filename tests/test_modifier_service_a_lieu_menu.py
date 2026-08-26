import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import modifier_service_a_lieu


def test_modifier_service_a_lieu_succes(monkeypatch, capsys):
    reponses = iter(["1", "3", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with patch("menu.modifier_service_lieu", return_value=True):
        modifier_service_a_lieu()

    sortie = capsys.readouterr().out

    assert "Service du lieu modifié avec succès." in sortie


def test_modifier_service_a_lieu_inexistant(monkeypatch, capsys):
    reponses = iter(["1", "99", "5"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with patch("menu.modifier_service_lieu", return_value=False):
        modifier_service_a_lieu()

    sortie = capsys.readouterr().out

    assert "Association service-lieu inexistante" in sortie


def test_modifier_service_a_lieu_saisie_invalide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "abc")

    modifier_service_a_lieu()

    sortie = capsys.readouterr().out

    assert "Erreur : les identifiants doivent être des nombres." in sortie


