import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

import main


def test_main_quitter(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "0")

    main.main()


def test_main_choix_categories(monkeypatch):
    choix = iter(["1", "10"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        "afficher_categories",
        lambda: appels.append("categories"),
    )

    main.menu_principal(1)

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

    main.menu_principal(1)

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

    main.menu_principal(1)

    assert appels == [1]


def test_main_choix_invalide(monkeypatch, capsys):
    choix = iter(["99", "10"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    main.menu_principal(1)

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie

def test_execution_directe_main(monkeypatch):
    import runpy

    monkeypatch.setattr("builtins.input", lambda _: "0")

    runpy.run_path("python/main.py", run_name="__main__")


def test_creer_profil_nom_deja_existant(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "UserNetAtlas")

    pins = iter(["1234", "1234"])
    monkeypatch.setattr(main, "getpass", lambda _: next(pins))

    def simuler_doublon(nom, pin):
        raise main.UniqueViolation()

    monkeypatch.setattr(main, "creer_utilisateur", simuler_doublon)

    main.creer_profil()

    sortie = capsys.readouterr().out

    assert "Ce nom de profil existe déjà." in sortie
    assert "Veuillez choisir un autre nom." in sortie



def test_creer_profil_succes(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "NouveauProfil")

    pins = iter(["1234", "1234"])
    monkeypatch.setattr(main, "getpass", lambda _: next(pins))

    monkeypatch.setattr(
        main,
        "creer_utilisateur",
        lambda nom, pin: 42,
    )

    main.creer_profil()

    sortie = capsys.readouterr().out

    assert "Profil créé avec succès" in sortie
    assert "ID utilisateur : 42" in sortie
    assert "Vous pouvez maintenant vous connecter avec l'option 2." in sortie



def test_creer_profil_nom_vide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "")

    main.creer_profil()

    sortie = capsys.readouterr().out

    assert "Le nom de profil ne peut pas être vide." in sortie



def test_creer_profil_pins_differents(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "NouveauProfil")

    pins = iter(["1234", "5678"])
    monkeypatch.setattr(main, "getpass", lambda _: next(pins))

    main.creer_profil()

    sortie = capsys.readouterr().out

    assert "Les deux PIN ne correspondent pas." in sortie



def test_creer_profil_pin_vide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "NouveauProfil")

    pins = iter(["", ""])
    monkeypatch.setattr(main, "getpass", lambda _: next(pins))

    main.creer_profil()

    sortie = capsys.readouterr().out

    assert "Le PIN ne peut pas être vide." in sortie



def test_main_connexion_administrateur_succes(monkeypatch):
    choix = iter(["1", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    session = {
        "user_id": 3,
        "nom": "Administrateur",
        "role": "admin",
    }

    monkeypatch.setattr(
        main,
        "connexion_administrateur",
        lambda: session,
    )

    appels = []

    monkeypatch.setattr(
        main,
        "menu_principal",
        lambda user_id: appels.append(user_id),
    )

    main.main()

    assert appels == [3]



def test_main_connexion_administrateur_refusee(monkeypatch):
    choix = iter(["1", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    monkeypatch.setattr(
        main,
        "connexion_administrateur",
        lambda: None,
    )

    appels = []

    monkeypatch.setattr(
        main,
        "menu_principal",
        lambda user_id: appels.append(user_id),
    )

    main.main()

    assert appels == []



def test_main_connexion_utilisateur_succes(monkeypatch):
    choix = iter(["2", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    session = {
        "user_id": 42,
        "nom": "UtilisateurTest",
        "role": "utilisateur",
    }

    monkeypatch.setattr(
        main,
        "connexion_utilisateur",
        lambda: session,
    )

    appels = []

    monkeypatch.setattr(
        main,
        "menu_principal",
        lambda user_id: appels.append(user_id),
    )

    main.main()

    assert appels == [42]



def test_main_connexion_utilisateur_refusee(monkeypatch):
    choix = iter(["2", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    monkeypatch.setattr(
        main,
        "connexion_utilisateur",
        lambda: None,
    )

    appels = []

    monkeypatch.setattr(
        main,
        "menu_principal",
        lambda user_id: appels.append(user_id),
    )

    main.main()

    assert appels == []



def test_main_creer_profil(monkeypatch):
    choix = iter(["3", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        "creer_profil",
        lambda: appels.append("creer_profil"),
    )

    main.main()

    assert appels == ["creer_profil"]



def test_main_choix_invalide_accueil(monkeypatch, capsys):
    choix = iter(["99", "0"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(choix),
    )

    main.main()

    sortie = capsys.readouterr().out

    assert "Choix invalide. Essaie encore." in sortie



def test_connexion_utilisateur_succes(monkeypatch, capsys):
    session_attendue = {
        "user_id": 42,
        "nom": "UtilisateurTest",
        "role": "utilisateur",
    }

    monkeypatch.setattr(
        "builtins.input",
        lambda _: "UtilisateurTest",
    )

    monkeypatch.setattr(
        main,
        "getpass",
        lambda _: "1234",
    )

    monkeypatch.setattr(
        main,
        "authentifier_utilisateur",
        lambda nom, pin, role: session_attendue,
    )

    session = main.connexion_utilisateur()

    sortie = capsys.readouterr().out

    assert session == session_attendue
    assert "Bienvenue UtilisateurTest !" in sortie



def test_connexion_utilisateur_refusee(monkeypatch, capsys):
    monkeypatch.setattr(
        "builtins.input",
        lambda _: "UtilisateurTest",
    )

    monkeypatch.setattr(
        main,
        "getpass",
        lambda _: "9999",
    )

    monkeypatch.setattr(
        main,
        "authentifier_utilisateur",
        lambda nom, pin, role: None,
    )

    session = main.connexion_utilisateur()

    sortie = capsys.readouterr().out

    assert session is None
    assert "Profil introuvable, PIN incorrect ou accès refusé." in sortie
    assert "Créer un profil" in sortie


def test_menu_temporaire_routage(monkeypatch):
    choix = iter(["1", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        "afficher_categories",
        lambda: appels.append("categories"),
    )

    main.menu_temporaire()

    assert appels == ["categories"]


def test_menu_temporaire_choix_invalide(monkeypatch, capsys):
    choix = iter(["99", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    main.menu_temporaire()

    sortie = capsys.readouterr().out

    assert "Choix invalide. Essaie encore." in sortie
    assert "Retour au menu d'accueil." in sortie


@pytest.mark.parametrize(
    ("choix_menu", "nom_fonction"),
    [
        ("2", "afficher_pays"),
        ("3", "afficher_villes"),
        ("4", "afficher_recherche_ville"),
        ("5", "afficher_lieux_par_ville"),
        ("6", "afficher_recherche_globale"),
        ("7", "afficher_detail_lieu"),
    ],
)
def test_menu_temporaire_routage_options(
    monkeypatch,
    choix_menu,
    nom_fonction,
):
    choix = iter([choix_menu, "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    monkeypatch.setattr(
        main,
        nom_fonction,
        lambda: appels.append(nom_fonction),
    )

    main.menu_temporaire()

    assert appels == [nom_fonction]


def test_main_acces_temporaire(monkeypatch):
    choix = iter(["4", "0"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(choix),
    )

    appele = {"temporaire": False}

    def faux_menu_temporaire():
        appele["temporaire"] = True

    monkeypatch.setattr(
        main,
        "menu_temporaire",
        faux_menu_temporaire,
    )

    main.main()

    assert appele["temporaire"] is True




