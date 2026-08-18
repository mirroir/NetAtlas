import sys
import pytest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

import main


def test_main_quitter(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "7")

    main.main()

def test_main_choix_categories(monkeypatch):
    choix = iter(["1", "7"])

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
    ],
)
def test_main_routage_options(monkeypatch, choix_menu, nom_fonction):
    choix = iter([choix_menu, "7"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        nom_fonction,
        lambda: appels.append(nom_fonction),
    )

    main.main()

    assert appels == [nom_fonction]


def test_main_choix_invalide(monkeypatch, capsys):
    choix = iter(["99", "7"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    main.main()

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie

def test_execution_directe_main(monkeypatch):
    import runpy

    monkeypatch.setattr("builtins.input", lambda _: "7")

    runpy.run_path("python/main.py", run_name="__main__")


