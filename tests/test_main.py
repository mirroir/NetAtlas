import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

import main


@pytest.fixture(autouse=True)
def utilisateur_connecte(monkeypatch):
    monkeypatch.setattr(main, "choisir_utilisateur", lambda: 1)


def test_main_quitter(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "10")

    main.main()

def test_main_choix_categories(monkeypatch):
    choix = iter(["1", "10"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(main, "afficher_categories",
                        lambda: appels.append("categories"))

    main.main()

    assert appels == ["categories"]


@pytest.mark.parametrize(
    "choix_menu, nom_fonction",
    [
        ("2", "afficher_pays"),
        ("3", "afficher_villes"),
        ("4", "afficher_recherche_ville"),
        ("5", "afficher_lieux_par_ville"),
        ("6", "afficher_recherche_globale"),
        ("7", "afficher_detail_lieu"),
        ("8", "ajouter_tag_a_lieu"),
    ],
)
def test_main_routage_options(monkeypatch, choix_menu, nom_fonction):
    choix = iter([choix_menu, "10"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        nom_fonction,
        lambda: appels.append(nom_fonction),
    )

    main.main()

    assert appels == [nom_fonction]


def test_main_menu_mes_commentaires(monkeypatch):
    choix = iter(["9", "10"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        "menu_mes_commentaires",
        lambda user_id: appels.append(user_id),
    )

    main.main()

    assert appels == [1]


def test_main_choix_invalide(monkeypatch, capsys):
    choix = iter(["0", "10"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    main.main()

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie

def test_execution_directe_main(monkeypatch):
    import runpy

    monkeypatch.setattr("builtins.input", lambda _: "10")

    runpy.run_path("python/main.py", run_name="__main__")


