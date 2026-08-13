from database import get_categories, get_pays, get_villes, rechercher_ville, rechercher_lieux_par_ville, suggerer_villes


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

        for ville, categorie, lieu, adresse, telephone, site in lieux:
            print(f"Ville      : {ville}")
            print(f"Catégorie  : {categorie}")
            print(f"Lieu       : {lieu}")
            print(f"Adresse    : {adresse}")
            print(f"Téléphone  : {telephone or 'Non renseigné'}")
            print(f"Site web   : {site or 'Non renseigné'}")
            print()

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

                        for ville, categorie, lieu, adresse, telephone, site in lieux:
                            print(f"Ville      : {ville}")
                            print(f"Catégorie  : {categorie}")
                            print(f"Lieu       : {lieu}")
                            print(f"Adresse    : {adresse}")
                            print(f"Téléphone  : {telephone or 'Non renseigné'}")
                            print(f"Site web   : {site or 'Non renseigné'}")
                            print()

                    else:
                        print("\nAucun lieu trouvé pour cette ville.\n")

                else:
                    print("\nChoix invalide.\n")

            else:
                print("\nChoix invalide.\n")

        else:
            print("\nAucune suggestion disponible.\n")


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
    print("6 - Quitter")
    print()


