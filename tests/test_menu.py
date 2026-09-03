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


def test_afficher_categories(monkeypatch, capsys):
    donnees = [
        (1, "Agriculture", "Producteurs locaux"),
        (2, "Transport", None),
    ]

    monkeypatch.setattr(menu, "get_categories", lambda: donnees)

    menu.afficher_categories()

    sortie = capsys.readouterr().out

    assert "CATÉGORIES NETATLAS" in sortie
    assert "1 - Agriculture" in sortie
    assert "Producteurs locaux" in sortie
    assert "2 - Transport" in sortie

def test_afficher_pays(monkeypatch, capsys):
    donnees = [
        (
            1,
            "France",
            "FR",
            "FRA",
            "Europe",
            "Paris",
            "Euro",
            "Français",
            68000000,
        )
    ]

    monkeypatch.setattr(menu, "get_pays", lambda: donnees)

    menu.afficher_pays()

    sortie = capsys.readouterr().out

    assert "Pays NetAtlas" in sortie
    assert "1 - France" in sortie
    assert "ISO2 : FR" in sortie
    assert "ISO3 : FRA" in sortie
    assert "Continent : Europe" in sortie
    assert "Capitale : Paris" in sortie
    assert "Monnaie : Euro" in sortie
    assert "Langue : Français" in sortie
    assert "Population : 68000000" in sortie

def test_afficher_villes(monkeypatch, capsys):
    donnees = [
        (
            1,
            "Saint-Pierre",
            "La Réunion",
            "France",
            -21.3393,
            55.4781,
            85000,
        )
    ]

    monkeypatch.setattr(menu, "get_villes", lambda: donnees)

    menu.afficher_villes()

    sortie = capsys.readouterr().out

    assert "Villes NetAtlas" in sortie
    assert "1 - Saint-Pierre" in sortie
    assert "Région : La Réunion" in sortie
    assert "Pays : France" in sortie
    assert "Latitude : -21.3393" in sortie
    assert "Longitude : 55.4781" in sortie
    assert "Population : 85000" in sortie


def test_afficher_recherche_ville_trouvee(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "Saint-Pierre")

    donnees = [
        (
            1,
            "Saint-Pierre",
            "La Réunion",
            "France",
            -21.3393,
            55.4781,
            85000,
        )
    ]

    monkeypatch.setattr(menu, "rechercher_ville", lambda _: donnees)

    menu.afficher_recherche_ville()

    sortie = capsys.readouterr().out

    assert "Résultat de la recherche" in sortie
    assert "Saint-Pierre" in sortie
    assert "La Réunion" in sortie
    assert "France" in sortie


def test_afficher_recherche_ville_suggestions_annulees(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    monkeypatch.setattr(menu, "rechercher_ville", lambda _: [])

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_recherche_ville()

    sortie = capsys.readouterr().out

    assert "Aucune ville trouvée" in sortie
    assert "Suggestions NetAtlas" in sortie
    assert "1 - Saint-Pierre" in sortie
    assert "2 - Saint-Paul" in sortie
    assert "Recherche annulée" in sortie


def test_afficher_recherche_ville_suggestion_selectionnee(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    def fausse_recherche(terme):
        appels.append(terme)

        if terme == "Saint-Piere":
            return []

        return [
            (
                1,
                "Saint-Pierre",
                "La Réunion",
                "France",
                -21.3393,
                55.4781,
                85000,
            )
        ]

    monkeypatch.setattr(menu, "rechercher_ville", fausse_recherche)

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_recherche_ville()

    sortie = capsys.readouterr().out

    assert appels == ["Saint-Piere", "Saint-Pierre"]
    assert "Saint-Pierre" in sortie
    assert "La Réunion" in sortie
    assert "France" in sortie


def test_afficher_recherche_ville_sans_suggestion(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "VilleInconnue")
    monkeypatch.setattr(menu, "rechercher_ville", lambda _: [])
    monkeypatch.setattr(menu, "suggerer_villes", lambda _: [])

    menu.afficher_recherche_ville()

    sortie = capsys.readouterr().out

    assert "Aucune ville trouvée" in sortie
    assert "Aucune suggestion disponible" in sortie

def test_afficher_recherche_ville_choix_invalide(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "99"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))
    monkeypatch.setattr(menu, "rechercher_ville", lambda _: [])

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_recherche_ville()

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie


def test_afficher_lieux_par_ville_trouves(monkeypatch, capsys):
    
    choix = iter (["Saint-Pierre", ""])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    donnees = [
        (
            1,
            "Saint-Pierre",
            "Agriculture",
            "Ferme NetAtlas",
            "10 rue Exemple",
            "0262123456",
            "https://exemple.test",
        )
    ]

    monkeypatch.setattr(
        menu,
        "rechercher_lieux_par_ville",
        lambda _: donnees,
    )

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Lieux trouvés dans NetAtlas" in sortie
    assert "Saint-Pierre" in sortie
    assert "Ferme NetAtlas" in sortie


def test_afficher_lieux_par_ville_suggestions_annulees(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "0"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))
    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: [])

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Aucun lieu trouvé" in sortie
    assert "Suggestions NetAtlas" in sortie
    assert "1 - Saint-Pierre" in sortie
    assert "2 - Saint-Paul" in sortie
    assert "Recherche annulée" in sortie


def test_afficher_lieux_par_ville_suggestion_selectionnee(monkeypatch, capsys):
    choix = iter(["Saint-Piere","1",""])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    appels = []

    def fausse_recherche(nom_ville):
        appels.append(nom_ville)

        if nom_ville == "Saint-Piere":
            return []

        return [
            (
                1,
                "Saint-Pierre",
                "Agriculture",
                "Ferme NetAtlas",
                "10 rue Exemple",
                "0262123456",
                "https://exemple.test",
            )
        ]

    monkeypatch.setattr(
        menu,
        "rechercher_lieux_par_ville",
        fausse_recherche,
    )

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert appels == ["Saint-Piere", "Saint-Pierre"]
    assert "Recherche relancée avec : Saint-Pierre" in sortie
    assert "Ferme NetAtlas" in sortie


def test_afficher_recherche_ville_choix_non_numerique(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "abc"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))
    monkeypatch.setattr(menu, "rechercher_ville", lambda _: [])

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_recherche_ville()

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie


def test_afficher_lieux_par_ville_suggestion_sans_lieu(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    monkeypatch.setattr(
        menu,
        "rechercher_lieux_par_ville",
        lambda _: []
    )

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(
        menu,
        "suggerer_villes",
        lambda _: suggestions
    )

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Recherche relancée avec : Saint-Pierre" in sortie
    assert "Aucun lieu trouvé pour cette ville" in sortie


def test_afficher_lieux_par_ville_choix_hors_liste(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "99"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))
    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: [])

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie


def test_afficher_lieux_par_ville_choix_non_numerique(monkeypatch, capsys):
    choix = iter(["Saint-Piere", "abc"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))
    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: [])

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Choix invalide" in sortie


def test_afficher_lieux_par_ville_sans_suggestion(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "VilleInconnue")
    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: [])
    monkeypatch.setattr(menu, "suggerer_villes", lambda _: [])

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Aucun lieu trouvé" in sortie
    assert "Aucune suggestion disponible" in sortie


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
    assert "0.95" in sortie


def test_afficher_lieux_par_ville_choix_lieu_non_numerique(monkeypatch, capsys):
    choix = iter(["Saint-Pierre", "abc"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    lieux = [
        (
            1,
            "Saint-Pierre",
            "Agriculture",
            "Ferme NetAtlas",
            "10 rue Exemple",
            "0262123456",
            "https://exemple.test",
        )
    ]

    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: lieux)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Ferme NetAtlas" in sortie
    assert "Choix invalide" in sortie



def test_afficher_lieux_par_ville_choix_lieu_hors_limites(monkeypatch, capsys):
    choix = iter(["Saint-Pierre", "9"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    lieux = [
        (
            1,
            "Saint-Pierre",
            "Agriculture",
            "Ferme NetAtlas",
            "10 rue Exemple",
            "0262123456",
            "https://exemple.test",
        )
    ]

    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: lieux)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Ferme NetAtlas" in sortie
    assert "Choix invalide" in sortie


def test_afficher_lieux_par_ville_choix_lieu_valide(monkeypatch, capsys):
    choix = iter(["Saint-Pierre", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    lieux = [
        (
            1,
            "Saint-Pierre",
            "Agriculture",
            "Ferme NetAtlas",
            "10 rue Exemple",
            "0262123456",
            "https://exemple.test",
        )
    ]

    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", lambda _: lieux)

    place = (
        1,
        "Ferme NetAtlas",
        "Saint-Pierre",
        "Agriculture",
        "10 rue Exemple",
        "0262123456",
        "https://exemple.test",
    )

    monkeypatch.setattr(menu, "get_place_details", lambda _: place)

    appels = []

    monkeypatch.setattr(menu, "afficher_place", lambda p: appels.append(p))

    menu.afficher_lieux_par_ville()

    capsys.readouterr()

    assert appels == [place]



def test_afficher_lieux_par_ville_suggestion_choix_lieu_non_numerique(
    monkeypatch, capsys
):
    choix = iter(["Saint-Piere", "1", "abc"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    def fausse_recherche(nom_ville):
        if nom_ville == "Saint-Piere":
            return []

        return [
            (
                1,
                "Saint-Pierre",
                "Agriculture",
                "Ferme NetAtlas",
                "10 rue Exemple",
                "0262123456",
                "https://exemple.test",
            )
        ]

    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", fausse_recherche)

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Recherche relancée avec : Saint-Pierre" in sortie
    assert "Ferme NetAtlas" in sortie
    assert "Choix invalide" in sortie


def test_afficher_lieux_par_ville_suggestion_choix_lieu_hors_limites(
    monkeypatch, capsys
):
    choix = iter(["Saint-Piere", "1", "9"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    def fausse_recherche(nom_ville):
        if nom_ville == "Saint-Piere":
            return []

        return [
            (
                1,
                "Saint-Pierre",
                "Agriculture",
                "Ferme NetAtlas",
                "10 rue Exemple",
                "0262123456",
                "https://exemple.test",
            )
        ]

    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", fausse_recherche)

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    menu.afficher_lieux_par_ville()

    sortie = capsys.readouterr().out

    assert "Recherche relancée avec : Saint-Pierre" in sortie
    assert "Ferme NetAtlas" in sortie
    assert "Choix invalide" in sortie



def test_afficher_lieux_par_ville_suggestion_choix_lieu_valide(
    monkeypatch, capsys
):
    choix = iter(["Saint-Piere", "1", "1"])

    monkeypatch.setattr("builtins.input", lambda _: next(choix))

    def fausse_recherche(nom_ville):
        if nom_ville == "Saint-Piere":
            return []

        return [
            (
                1,
                "Saint-Pierre",
                "Agriculture",
                "Ferme NetAtlas",
                "10 rue Exemple",
                "0262123456",
                "https://exemple.test",
            )
        ]

    monkeypatch.setattr(menu, "rechercher_lieux_par_ville", fausse_recherche)

    suggestions = [
        ("Saint-Pierre", 0.92),
        ("Saint-Paul", 0.71),
    ]

    monkeypatch.setattr(menu, "suggerer_villes", lambda _: suggestions)

    place = (
        1,
        "Ferme NetAtlas",
        "Saint-Pierre",
        "Agriculture",
        "10 rue Exemple",
        "0262123456",
        "https://exemple.test",
    )

    monkeypatch.setattr(menu, "get_place_details", lambda _: place)

    appels = []

    monkeypatch.setattr(menu, "afficher_place", lambda p: appels.append(p))

    menu.afficher_lieux_par_ville()

    capsys.readouterr()

    assert appels == [place]


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
    assert "1 - Voir les catégories" in sortie
    assert "7 - Afficher les détails d'un lieu" in sortie
    assert "0 - Retour au menu d'accueil" in sortie



