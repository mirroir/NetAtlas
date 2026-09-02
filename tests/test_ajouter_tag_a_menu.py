import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import ajouter_tag_a_lieu

LIEUX = [
    (1, "Marché Test NetAtlas"),
    (4, "Marché de Saint-Pierre"),
]

TAGS = [
    (1, "Marché forain"),
    (2, "Producteurs locaux"),
    (3, "Produits frais"),
]


def test_ajouter_tag_a_lieu_succes(monkeypatch, capsys):
    reponses = iter(["2", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.get_place_category_id", return_value=1),
        patch("menu.get_tags_by_category", return_value=TAGS),
        patch("menu.ajouter_tag_lieu", return_value=True) as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Lieux disponibles :" in sortie
    assert "1 - Marché Test NetAtlas" in sortie
    assert "2 - Marché de Saint-Pierre" in sortie
    assert "Tags disponibles :" in sortie
    assert "1 - Marché forain" in sortie
    assert "2 - Producteurs locaux" in sortie
    assert "3 - Produits frais" in sortie
    assert "Tag ajouté au lieu avec succès." in sortie

    mock_ajouter.assert_called_once_with(4, 3)


def test_ajouter_tag_a_lieu_deja_existant(monkeypatch, capsys):
    reponses = iter(["1", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch(
            "menu.get_places_with_ids",
            return_value=[(4, "Marché de Saint-Pierre")],
        ),
        patch("menu.get_place_category_id", return_value=1),
        patch("menu.get_tags_by_category", return_value=TAGS),
        patch("menu.ajouter_tag_lieu", return_value=False) as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Impossible d'ajouter ce tag au lieu." in sortie
    mock_ajouter.assert_called_once_with(4, 3)


def test_ajouter_tag_a_lieu_choix_non_numerique(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "abc")

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.get_place_category_id") as mock_category,
        patch("menu.get_tags_by_category") as mock_tags,
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Erreur : le choix doit être un nombre." in sortie
    mock_category.assert_not_called()
    mock_tags.assert_not_called()
    mock_ajouter.assert_not_called()


def test_ajouter_tag_a_lieu_choix_inexistant(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "3")

    with (
        patch("menu.get_places_with_ids", return_value=LIEUX),
        patch("menu.get_place_category_id") as mock_category,
        patch("menu.get_tags_by_category") as mock_tags,
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Erreur : choix de lieu invalide." in sortie
    mock_category.assert_not_called()
    mock_tags.assert_not_called()
    mock_ajouter.assert_not_called()


def test_ajouter_tag_a_lieu_sans_categorie(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "1")

    with (
        patch(
            "menu.get_places_with_ids",
            return_value=[(4, "Marché de Saint-Pierre")],
        ),
        patch("menu.get_place_category_id", return_value=None),
        patch("menu.get_tags_by_category") as mock_tags,
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Aucune" in sortie
    assert "ce lieu." in sortie
    mock_tags.assert_not_called()
    mock_ajouter.assert_not_called()


def test_ajouter_tag_a_lieu_identifiant_tag_invalide(monkeypatch, capsys):
    reponses = iter(["1", "abc"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch(
            "menu.get_places_with_ids",
            return_value=[(4, "Marché de Saint-Pierre")],
        ),
        patch("menu.get_place_category_id", return_value=1),
        patch("menu.get_tags_by_category", return_value=TAGS),
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Erreur : le choix doit être un nombre." in sortie
    mock_ajouter.assert_not_called()


def test_ajouter_tag_a_lieu_aucun_lieu(capsys):
    with (
        patch("menu.get_places_with_ids", return_value=[]),
        patch("menu.get_place_category_id") as mock_category,
        patch("menu.get_tags_by_category") as mock_tags,
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Aucun lieu disponible." in sortie
    mock_category.assert_not_called()
    mock_tags.assert_not_called()
    mock_ajouter.assert_not_called()


def test_ajouter_tag_a_lieu_aucun_tag(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "1")

    with (
        patch(
            "menu.get_places_with_ids",
            return_value=[(4, "Marché de Saint-Pierre")],
        ),
        patch("menu.get_place_category_id", return_value=1),
        patch("menu.get_tags_by_category", return_value=[]),
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Aucun tag disponible." in sortie
    mock_ajouter.assert_not_called()


def test_ajouter_tag_a_lieu_choix_tag_invalide(monkeypatch, capsys):
    reponses = iter(["1", "99"])
    monkeypatch.setattr("builtins.input", lambda _: next(reponses))

    with (
        patch(
            "menu.get_places_with_ids",
            return_value=[(4, "Marché de Saint-Pierre")],
        ),
        patch("menu.get_place_category_id", return_value=1),
        patch("menu.get_tags_by_category", return_value=TAGS),
        patch("menu.ajouter_tag_lieu") as mock_ajouter,
    ):
        ajouter_tag_a_lieu()

    sortie = capsys.readouterr().out

    assert "Erreur : choix de tag invalide." in sortie
    mock_ajouter.assert_not_called()



