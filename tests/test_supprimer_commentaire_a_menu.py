import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import supprimer_commentaire_a_lieu

AVIS = [
    (7, "Très pratique le samedi", "Marché de Saint-Pierre"),
    (12, "Produits intéressants", "Marché Test NetAtlas"),
]


def test_supprimer_commentaire_succes(monkeypatch, capsys):
    reponses = iter(["1", "o"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch("menu.get_avis_by_user", return_value=AVIS),
        patch("menu.supprimer_avis", return_value=True) as mock_supprimer,
    ):
        supprimer_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Commentaire supprimé avec succès." in sortie
    mock_supprimer.assert_called_once_with(7, 1)


def test_supprimer_commentaire_annule(monkeypatch, capsys):
    reponses = iter(["1", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch("menu.get_avis_by_user", return_value=AVIS),
        patch("menu.supprimer_avis") as mock_supprimer,
    ):
        supprimer_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Suppression annulée." in sortie
    mock_supprimer.assert_not_called()


def test_supprimer_commentaire_aucun_avis(capsys):
    with (
        patch("menu.get_avis_by_user", return_value=[]),
        patch("menu.supprimer_avis") as mock_supprimer,
    ):
        supprimer_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Vous n'avez aucun commentaire à supprimer." in sortie
    mock_supprimer.assert_not_called()


def test_supprimer_commentaire_choix_non_numerique(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "abc")

    with (
        patch("menu.get_avis_by_user", return_value=AVIS),
        patch("menu.supprimer_avis") as mock_supprimer,
    ):
        supprimer_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Erreur : le choix doit être un nombre." in sortie
    mock_supprimer.assert_not_called()


def test_supprimer_commentaire_choix_invalide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "99")

    with (
        patch("menu.get_avis_by_user", return_value=AVIS),
        patch("menu.supprimer_avis") as mock_supprimer,
    ):
        supprimer_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Erreur : choix de commentaire invalide." in sortie
    mock_supprimer.assert_not_called()


def test_supprimer_commentaire_refuse(monkeypatch, capsys):
    reponses = iter(["1", "o"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch("menu.get_avis_by_user", return_value=AVIS),
        patch("menu.supprimer_avis", return_value=False) as mock_supprimer,
    ):
        supprimer_commentaire_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Impossible de supprimer ce commentaire." in sortie
    mock_supprimer.assert_called_once_with(7, 1)



