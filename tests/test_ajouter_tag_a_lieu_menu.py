import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import menu


def test_ajouter_tag_a_lieu_categorie_introuvable(monkeypatch, capsys):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: None,
    )

    menu.ajouter_tag_a_lieu(999)

    sortie = capsys.readouterr().out

    assert "Impossible de déterminer la catégorie du lieu." in sortie

def test_ajouter_tag_a_lieu_aucun_tag_disponible(monkeypatch, capsys):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: 1,
    )
    monkeypatch.setattr(
        menu,
        "get_tags_by_category",
        lambda category_id: [(1, "Marché forain")],
    )
    monkeypatch.setattr(
        menu,
        "get_place_tags_with_ids",
        lambda place_id: [(1, "Marché forain")],
    )

    menu.ajouter_tag_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Aucun tag disponible pour ce lieu." in sortie


def test_ajouter_tag_a_lieu_retour(monkeypatch):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: 1,
    )
    monkeypatch.setattr(
        menu,
        "get_tags_by_category",
        lambda category_id: [(1, "Marché forain")],
    )
    monkeypatch.setattr(
        menu,
        "get_place_tags_with_ids",
        lambda place_id: [],
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda message: "0",
    )

    menu.ajouter_tag_a_lieu(1)


def test_ajouter_tag_a_lieu_choix_non_numerique(monkeypatch, capsys):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: 1,
    )
    monkeypatch.setattr(
        menu,
        "get_tags_by_category",
        lambda category_id: [(1, "Marché forain")],
    )
    monkeypatch.setattr(
        menu,
        "get_place_tags_with_ids",
        lambda place_id: [],
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda message: "abc",
    )

    menu.ajouter_tag_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Choix invalide." in sortie


def test_ajouter_tag_a_lieu_choix_hors_limites(monkeypatch, capsys):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: 1,
    )
    monkeypatch.setattr(
        menu,
        "get_tags_by_category",
        lambda category_id: [(1, "Marché forain")],
    )
    monkeypatch.setattr(
        menu,
        "get_place_tags_with_ids",
        lambda place_id: [],
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda message: "2",
    )

    menu.ajouter_tag_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Choix invalide." in sortie

def test_ajouter_tag_a_lieu_succes(monkeypatch, capsys):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: 1,
    )
    monkeypatch.setattr(
        menu,
        "get_tags_by_category",
        lambda category_id: [(4, "Tag disponible pytest")],
    )
    monkeypatch.setattr(
        menu,
        "get_place_tags_with_ids",
        lambda place_id: [],
    )
    monkeypatch.setattr(
        menu,
        "ajouter_tag_lieu",
        lambda place_id, tag_id: True,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda message: "1",
    )

    menu.ajouter_tag_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Tag ajouté au lieu avec succès." in sortie

def test_ajouter_tag_a_lieu_echec_ajout(monkeypatch, capsys):
    monkeypatch.setattr(
        menu,
        "get_place_category_id",
        lambda place_id: 1,
    )
    monkeypatch.setattr(
        menu,
        "get_tags_by_category",
        lambda category_id: [(4, "Tag disponible pytest")],
    )
    monkeypatch.setattr(
        menu,
        "get_place_tags_with_ids",
        lambda place_id: [],
    )
    monkeypatch.setattr(
        menu,
        "ajouter_tag_lieu",
        lambda place_id, tag_id: False,
    )
    monkeypatch.setattr(
        "builtins.input",
        lambda message: "1",
    )

    menu.ajouter_tag_a_lieu(1)

    sortie = capsys.readouterr().out

    assert "Ce tag est déjà associé au lieu." in sortie


