try:
    from .database import (
        get_categories,
        get_pays,
        get_place_details,
        get_place_services,
        get_place_tags,
        get_villes,
        rechercher_global,
        rechercher_lieux_par_ville,
        rechercher_ville,
        suggerer_villes,
    )
except ImportError:
    from database import (
        get_categories,
        get_pays,
        get_place_details,
        get_place_services,
        get_place_tags,
        get_villes,
        rechercher_global,
        rechercher_lieux_par_ville,
        rechercher_ville,
        suggerer_villes,
    )


def afficher_categories():
    categories = get_categories()

    print("\n=== CATÉGORIES NETATLAS ===\n")

    for categorie in categories:
        id_categorie, nom, description = categorie

        print(f"{id_categorie} - {nom}")

        if description:
            print(f"   {description}")

    print()


def afficher_pays():
    pays = get_pays()

    print("\n=== Pays NetAtlas ===\n")

    for pays_item in pays:
        id_pays, nom, iso2, iso3, continent, capital, currency, language, population = pays_item

        print(f"{id_pays} - {nom}")
        print(f" ISO2 : {iso2}")
        print(f" ISO3 : {iso3}")
        print(f" Continent : {continent}")
        print(f" Capitale : {capital}")
        print(f" Monnaie : {currency}")
        print(f" Langue : {language}")
        print(f" Population : {population}")
        print()


def afficher_villes():
    villes = get_villes()

    print("\n=== Villes NetAtlas ===\n")

    for ville in villes:
        id_ville, nom, region, pays, latitude, longitude, population = ville

        print(f"{id_ville} - {nom}")
        print(f" Région : {region}")
        print(f" Pays : {pays}")
        print(f" Latitude : {latitude}")
        print(f" Longitude : {longitude}")
        print(f" Population : {population}")
        print()



def afficher_recherche_ville():
    nom_ville = input("\nNom de la ville : ")

    villes = rechercher_ville(nom_ville)

    if villes:
        print("\n=== Résultat de la recherche ===\n")

        for ville in villes:
            id_ville, nom, region, pays, latitude, longitude, population = ville

            print(f"{id_ville} - {nom}")
            print(f" Région : {region}")
            print(f" Pays : {pays}")
            print(f" Latitude : {latitude}")
            print(f" Longitude : {longitude}")
            print(f" Population : {population}")
            print()

    else:
        print("\nAucune ville trouvée dans NetAtlas.\n")

        suggestions = suggerer_villes(nom_ville)

        if suggestions:
            print("\n=== Suggestions NetAtlas ===\n")

            for index, (nom, score) in enumerate(suggestions, start=1):
                print(f"{index} - {nom}")

            print("0 - Annuler")

            choix = input("\nVotre choix : ")

            if choix == "0":
                print("\nRecherche annulée.\n")

            elif choix.isdigit():
                index = int(choix) - 1

                if 0 <= index < len(suggestions):
                    ville_corrigee = suggestions[index][0]

                    print(f"\nRecherche relancée avec : {ville_corrigee}\n")

                    villes = rechercher_ville(ville_corrigee)

                    for ville in villes:
                        id_ville, nom, region, pays, latitude, longitude, population = ville

                        print(f"{id_ville} - {nom}")
                        print(f" Région : {region}")
                        print(f" Pays : {pays}")
                        print(f" Latitude : {latitude}")
                        print(f" Longitude : {longitude}")
                        print(f" Population : {population}")
                        print()

                else:
                    print("\nChoix invalide.\n")

            else:
                print("\nChoix invalide.\n")

        else:
            print("Aucune suggestion disponible.\n")



def afficher_lieux_par_ville():
    nom_ville = input("Nom de la ville : ")

    lieux = rechercher_lieux_par_ville(nom_ville)

    if lieux:
        print("\n=== Lieux trouvés dans NetAtlas ===\n")
        print(f"Ville : {lieux[0][1]}\n")

        for numero, lieu_data in enumerate(lieux, start=1):
            identifiant, _ville, _categorie, lieu, _adresse, _telephone, _site = lieu_data
            print(f"{numero} - {lieu}")

        choix = input(
            "\nEntrez le numéro du lieu à consulter "
            "(Entrée pour revenir au menu) : "
        ).strip()

        if choix == "":
            return

        if not choix.isdigit():
            print("\nChoix invalide.\n")
            return

        index = int(choix) - 1

        if not 0 <= index < len(lieux):
            print("\nChoix invalide.\n")
            return

        identifiant = lieux[index][0]
        place = get_place_details(identifiant)

        if place is not None:
            afficher_place(place)

    else:
        print("\nAucun lieu trouvé dans NetAtlas.")

        suggestions = suggerer_villes(nom_ville)

        if suggestions:
            print("\n=== Suggestions NetAtlas ===\n")

            for index, (nom, score) in enumerate(suggestions, start=1):
                print(f"{index} - {nom}")

            print("0 - Annuler")

            choix = input("\nVotre choix : ")

            if choix == "0":
                print("\nRecherche annulée.\n")

            elif choix.isdigit():
                index = int(choix) - 1

                if 0 <= index < len(suggestions):
                    ville_corrigee = suggestions[index][0]

                    print(f"\nRecherche relancée avec : {ville_corrigee}\n")

                    lieux = rechercher_lieux_par_ville(ville_corrigee)

                    if lieux:
                        print("=== Lieux trouvés dans NetAtlas ===\n")
                        print(f"Ville : {lieux[0][1]}\n")

                        for numero, lieu_data in enumerate(lieux, start=1):
                            (
                                identifiant,
                                _ville,
                                _categorie,
                                lieu,
                                _adresse,
                                _telephone,
                                _site,
                            ) = lieu_data

                            print(f"{numero} - {lieu}")

                        choix_lieu = input(
                            "\nEntrez le numéro du lieu à consulter "
                            "(Entrée pour revenir au menu) : "
                        ).strip()

                        if choix_lieu == "":
                            return

                        if not choix_lieu.isdigit():
                            print("\nChoix invalide.\n")
                            return

                        index_lieu = int(choix_lieu) - 1

                        if not 0 <= index_lieu < len(lieux):
                            print("\nChoix invalide.\n")
                            return

                        identifiant = lieux[index_lieu][0]
                        place = get_place_details(identifiant)

                        if place is not None:
                            afficher_place(place)


                    else:
                        print("\nAucun lieu trouvé pour cette ville.\n")

                else:
                    print("\nChoix invalide.\n")

            else:
                print("\nChoix invalide.\n")

        else:
            print("\nAucune suggestion disponible.\n")



def afficher_recherche_globale():
    terme = input("\nTerme à rechercher : ").strip()

    if not terme:
        print("\nRecherche vide.\n")
        return

    resultats = rechercher_global(terme)

    if not resultats:
        print("\nAucun résultat trouvé.\n")
        return

    print("\n=== RÉSULTATS DE LA RECHERCHE GLOBALE ===\n")

    for _place_id, lieu, ville, categorie, adresse, telephone, site, score in resultats:
        print(f"Lieu       : {lieu}")
        print(f"Ville      : {ville}")
        print(f"Catégorie  : {categorie}")
        print(f"Adresse    : {adresse or 'Non renseignée'}")
        print(f"Téléphone  : {telephone or 'Non renseigné'}")
        print(f"Site web   : {site or 'Non renseigné'}")
        print(f"Pertinence : {score:.2f}")
        print()


def afficher_place(place):
    """Affiche les informations détaillées d'un lieu."""
    (
        identifiant,
        nom,
        description,
        adresse,
        latitude,
        longitude,
        telephone,
        email,
        site,
        actif,
        _ville,
        categorie,
    ) = place

    if latitude is not None and longitude is not None:
        point_gps = f"{latitude}, {longitude}"
    else:
        point_gps = "Non renseigné"

    tags = get_place_tags(identifiant)

    if tags:
        tags_affiches = ", ".join(tags)
    else:
        tags_affiches = "Aucun"

    services = get_place_services(identifiant)

    if services:
        services_affiches = ", ".join(services)

    else:
        services_affiches = "Aucun"

    print("\n=== DÉTAIL DU LIEU ===\n")
    print(f"Identifiant : {identifiant}")
    print(f"Nom         : {nom}")
    print(f"Catégorie   : {categorie}")
    print(f"Adresse     : {adresse or 'Non renseignée'}")
    print(f"Point GPS   : {point_gps}")
    print(f"Description : {description or 'Non renseignée'}")
    print(f"Téléphone   : {telephone or 'Non renseigné'}")
    print(f"Email       : {email or 'Non renseigné'}")
    print(f"Site web    : {site or 'Non renseigné'}")
    print(f"Tags        : {tags_affiches}")
    print(f"Services    : {services_affiches}")
    print(f"Actif       : {'Oui' if actif else 'Non'}")
    print()


def afficher_detail_lieu():
    terme = input("\nNom ou terme à rechercher : ").strip()

    if not terme:
        print("\nRecherche vide.\n")
        return

    resultats = rechercher_global(terme)

    if not resultats:
        print("\nAucun lieu trouvé.\n")
        return

    print("\n=== LIEUX TROUVÉS ===\n")

    for numero, resultat in enumerate(resultats, start=1):
        place_id, nom, ville, categorie, *_ = resultat
        print(f"{numero} - {nom} - {ville} - {categorie}")

    print("0 - Annuler")

    choix = input("\nVotre choix : ").strip()

    if choix == "0":
        print("\nRecherche annulée.\n")
        return

    if not choix.isdigit():
        print("\nChoix invalide.\n")
        return

    index = int(choix) - 1

    if not 0 <= index < len(resultats):
        print("\nChoix invalide.\n")
        return

    place_id = resultats[index][0]

    place = get_place_details(place_id)

    if place is None:
        print("\nAucun lieu trouvé.\n")
        return

    afficher_place(place)


def afficher_menu():
    print("=" * 45)
    print("            NetAtlas -> Ver. 1")
    print("=" * 45)
    print()

    print("1 - Voir les catégories")
    print("2 - Voir les pays")
    print("3 - Voir les villes")
    print("4 - Rechercher une ville")
    print("5 - Rechercher les lieux d'une ville")
    print("6 - Recherche globale")
    print("7 - Afficher les détails d'un lieu")
    print("8 - Quitter")
    print()


