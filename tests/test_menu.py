import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

import menu


def test_afficher_menu_connexion(capsys):
    menu.afficher_menu_connexion()

    sortie = capsys.readouterr().out

    assert "BIENVENUE SUR NETATLAS" in sortie
    assert "1 - Connexion Administrateur" in sortie
    assert "2 - Connexion Utilisateur" in sortie
    assert "3 - Créer un profil" in sortie
    assert "4 - Accès temporaire" in sortie
    assert "0 - Quitter" in sortie


def test_afficher_recherche_globale_vide(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "   ")

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "Recherche vide" in sortie


def test_afficher_recherche_globale_sans_resultat(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "inconnu")
    monkeypatch.setattr(menu, "rechercher_global", lambda _: [])

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "Aucun résultat trouvé" in sortie


def test_afficher_recherche_globale_avec_resultats(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "ferme")

    donnees = [
        (
            1,
            "Ferme NetAtlas",
            "Saint-Pierre",
            "Agriculture",
            "10 rue Exemple",
            "0262123456",
            "https://exemple.test",
            0.95,
        )
    ]

    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "RÉSULTATS DE LA RECHERCHE GLOBALE" in sortie
    assert "Ferme NetAtlas" in sortie
    assert "Saint-Pierre" in sortie
    assert "Agriculture" in sortie
    assert "10 rue Exemple" in sortie
    assert "0262123456" in sortie
    assert "https://exemple.test" in sortie
    assert "Pertinence" in sortie
    assert "95" in sortie


def test_afficher_place_sans_coordonnees(capsys):
    place = (
        1,
        "Ferme NetAtlas",
        "Ferme locale de test",
        "10 rue Exemple",
        None,
        None,
        "0262123456",
        "contact@exemple.test",
        "https://exemple.test",
        True,
        "Saint-Pierre",
        "Agriculture",
    )

    menu.afficher_place(place)

    sortie = capsys.readouterr().out

    assert "Ferme NetAtlas" in sortie
    assert "Non renseigné" in sortie


def test_afficher_place_avec_coordonnees(capsys):
    place = (
        4,
        "Marché de Saint-Pierre",
        "Marché forain",
        "Saint-Pierre",
        -21.339220,
        55.458830,
        None,
        None,
        None,
        True,
        "Saint-Pierre",
        "Agriculture",
    )

    menu.afficher_place(place)

    sortie = capsys.readouterr().out

    assert "Marché de Saint-Pierre" in sortie
    assert "-21.33922" in sortie
    assert "55.45883" in sortie


def test_afficher_menu_temporaire(capsys):
    menu.afficher_menu_temporaire()

    sortie = capsys.readouterr().out

    assert "NetAtlas -> Accès temporaire" in sortie
    assert "NOTE : pour ajouter des tags ou des commentaires" in sortie
    assert "créez un profil depuis le menu d'accueil." in sortie
    assert "1 - Recherche globale" in sortie
    assert "2 - Retour au menu principal" in sortie
    assert "Mes Commentaires" not in sortie
    assert "Déconnexion" not in sortie



def test_recherche_globale_masque_resultat_moins_pertinent(monkeypatch, capsys):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        ),
        (
            1,
            "Marché Test NetAtlas",
            "Saint-Denis",
            "Agriculture",
            "Saint-Denis",
            None,
            None,
            0.33,
        ),
    ]

    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)

    reponses = iter(["Saint Piere", "0"])

    monkeypatch.setattr(
     "builtins.input",
     lambda _: next(reponses),
    )


    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "Marché de Saint-Pierre" in sortie
    assert "79%" in sortie
    assert "Marché Test NetAtlas" not in sortie
    assert "1 résultat(s) moins pertinent(s) disponible(s)." in sortie
    assert "A - Afficher les autres résultats" in sortie

def test_recherche_globale_affiche_autres_resultats(monkeypatch, capsys):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        ),
        (
            1,
            "Marché Test NetAtlas",
            "Saint-Denis",
            "Agriculture",
            "Saint-Denis",
            None,
            None,
            0.33,
        ),
    ]

    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)

    reponses = iter(["Saint Piere", "A", "0"])

    monkeypatch.setattr(
        "builtins.input",
        lambda _: next(reponses),
    )

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "=== AUTRES RÉSULTATS ===" in sortie
    assert "Marché Test NetAtlas" in sortie
    assert "Saint-Denis" in sortie
    assert "33%" in sortie


def test_recherche_globale_selectionne_resultat(monkeypatch):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        )
    ]

    place = (
        4,
        "Marché de Saint-Pierre",
        "Description test",
        "Saint-Pierre",
        "0262000000",
        None,
        None,
        None,
        None,
        None,
        None,
    )

    reponses = iter(["Réunion", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)
    monkeypatch.setattr(menu, "get_place_details", lambda _: place)
    monkeypatch.setattr(menu, "afficher_place", lambda _: None)

    menu.afficher_recherche_globale()

def test_recherche_globale_choix_hors_limite(monkeypatch, capsys):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        )
    ]

    reponses = iter(["Réunion", "99"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out
    assert "Choix invalide." in sortie

def test_recherche_globale_lieu_introuvable(monkeypatch, capsys):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        )
    ]

    reponses = iter(["Réunion", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)
    monkeypatch.setattr(menu, "get_place_details", lambda _: None)

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out
    assert "Aucun lieu trouvé." in sortie

def test_recherche_globale_choix_secondaire_non_numerique(monkeypatch, capsys):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        ),
        (
            1,
            "Marché Test NetAtlas",
            "Saint-Denis",
            "Agriculture",
            "Saint-Denis",
            None,
            None,
            0.33,
        ),
    ]

    reponses = iter(["marche", "A", "abc"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "Choix invalide." in sortie

def test_recherche_globale_choix_secondaire_hors_limites(monkeypatch, capsys):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        ),
        (
            1,
            "Marché Test NetAtlas",
            "Saint-Denis",
            "Agriculture",
            "Saint-Denis",
            None,
            None,
            0.33,
        ),
    ]

    reponses = iter(["marche", "A", "99"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "Choix invalide." in sortie

def test_recherche_globale_selection_secondaire_valide(monkeypatch):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        ),
        (
            1,
            "Marché Test NetAtlas",
            "Saint-Denis",
            "Agriculture",
            "Saint-Denis",
            None,
            None,
            0.33,
        ),
    ]

    lieu = ("lieu-test",)

    reponses = iter(["marche", "A", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)
    monkeypatch.setattr(menu, "get_place_details", lambda place_id: lieu)

    lieu_affiche = []

    monkeypatch.setattr(
        menu,
        "afficher_place",
        lambda place: lieu_affiche.append(place),
    )

    menu.afficher_recherche_globale()

    assert lieu_affiche == [lieu]

def test_recherche_globale_selection_secondaire_lieu_introuvable(
    monkeypatch, capsys
):
    donnees = [
        (
            4,
            "Marché de Saint-Pierre",
            "Saint-Pierre",
            "Agriculture",
            "Saint-Pierre",
            None,
            None,
            0.79,
        ),
        (
            1,
            "Marché Test NetAtlas",
            "Saint-Denis",
            "Agriculture",
            "Saint-Denis",
            None,
            None,
            0.33,
        ),
    ]

    reponses = iter(["marche", "A", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(reponses))
    monkeypatch.setattr(menu, "rechercher_global", lambda _: donnees)
    monkeypatch.setattr(menu, "get_place_details", lambda place_id: None)

    menu.afficher_recherche_globale()

    sortie = capsys.readouterr().out

    assert "Aucun lieu trouvé." in sortie


