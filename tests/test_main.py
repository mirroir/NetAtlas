import runpy
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

import main


def test_main_quitter(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "0")

    main.main()

    assert "À bientôt sur NetAtlas !" in capsys.readouterr().out


def test_main_recherche_publique(monkeypatch):
    choix = iter(["1", "0"])
    appels = []

    monkeypatch.setattr("builtins.input", lambda _: next(choix))
    monkeypatch.setattr(
        main,
        "afficher_recherche_globale",
        lambda: appels.append("recherche"),
    )

    main.main()

    assert appels == ["recherche"]


def test_main_choix_invalide(monkeypatch, capsys):
    choix = iter(["2", "3", "4", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    main.main()

    sortie = capsys.readouterr().out

    assert sortie.count("Choix invalide") == 3


def test_execution_directe_main(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "0")

    runpy.run_path("python/main.py", run_name="__main__")


def test_cli_sans_authentification_pin():
    """Le CLI ne doit exposer aucune ancienne fonction de connexion."""

    for nom_fonction in (
        "connexion_administrateur",
        "connexion_utilisateur",
        "creer_profil",
        "menu_principal",
        "menu_temporaire",
    ):
        assert not hasattr(main, nom_fonction)
