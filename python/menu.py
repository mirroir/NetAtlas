try:
    from .database import (
        ajouter_avis,
        get_avis_by_place,
        get_avis_by_user,
        get_place_details,
        get_place_services,
        get_place_tags,
        get_places_with_ids,
        rechercher_global,
        supprimer_avis,
    )
except ImportError:
    from database import (
        ajouter_avis,
        get_avis_by_place,
        get_avis_by_user,
        get_place_details,
        get_place_services,
        get_place_tags,
        get_places_with_ids,
        rechercher_global,
        supprimer_avis,
    )


def afficher_menu_connexion():
    print("\n" + "=" * 45)
    print("      BIENVENUE SUR NETATLAS")
    print("=" * 45)
    print()
    print("1 - Connexion Administrateur")
    print("2 - Connexion Utilisateur")
    print("3 - Créer un profil")
    print("4 - Accès temporaire")
    print("0 - Quitter")
    print()








def afficher_recherche_globale(user_id=None):
    terme = input("\nTerme à rechercher : ").strip()

    if not terme:
        print("\nRecherche vide.\n")
        return

    resultats = rechercher_global(terme)

    if not resultats:
        print("\nAucun résultat trouvé.\n")
        return

    seuil_affichage = 0.50

    resultats_principaux = [
        resultat for resultat in resultats
        if resultat[7] >= seuil_affichage
    ]

    resultats_secondaires = [
        resultat for resultat in resultats
        if resultat[7] < seuil_affichage
    ]

    if resultats_secondaires:
       print(
          f"\n{len(resultats_secondaires)} résultat(s) "
          "moins pertinent(s) disponible(s)."
       )
       print("A - Afficher les autres résultats")

    print("\n=== RÉSULTATS DE LA RECHERCHE GLOBALE ===\n")

    for numero, resultat in enumerate(resultats_principaux, start=1):
        (
            _place_id,
            lieu,
            ville,
            categorie,
            adresse,
            telephone,
            site,
            score,
        ) = resultat

        print(f"{numero} - {lieu}")
        print(f"    Ville       : {ville}")
        print(f"    Catégorie   : {categorie}")
        print(f"    Adresse     : {adresse or 'Non renseignée'}")
        print(f"    Téléphone   : {telephone or 'Non renseigné'}")
        print(f"    Site web    : {site or 'Non renseigné'}")
        print(f"    Pertinence  : {score * 100:.0f}%")
        print()

    print("0 - Retour")

    choix = input("\nChoisissez un lieu : ").strip()

    if choix.lower() == "a" and resultats_secondaires:
        print("\n=== AUTRES RÉSULTATS ===\n")

        for numero, resultat in enumerate(resultats_secondaires, start=1):
            lieu = resultat[1]
            ville = resultat[2]
            score = resultat[7]

            print(
                f"{numero} - {lieu} "
                f"({ville}) - Pertinence : {score * 100:.0f}%"
            )

        print("\n0 - Retour")

        choix_secondaire = input(
            "\nChoisissez un lieu : "
        ).strip()

        if choix_secondaire == "0":
            return

        if not choix_secondaire.isdigit():
            print("\nChoix invalide.\n")
            return

        index_secondaire = int(choix_secondaire) - 1

        if not 0 <= index_secondaire < len(resultats_secondaires):
            print("\nChoix invalide.\n")
            return

        place_id = resultats_secondaires[index_secondaire][0]
        place = get_place_details(place_id)

        if place is None:
            print("\nAucun lieu trouvé.\n")
            return

        afficher_place(place)
        return

    if choix == "0":
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

    avis = get_avis_by_place(identifiant)

    print("\n=== DETAIL DU LIEU ===\n")
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

    print("\n=== COMMENTAIRES UTILISATEURS ===")

    if avis:
        for _, commentaire, auteur in avis:
            print(f"\n{auteur} :")
            print(f"  {commentaire}")
    else:
        print("\nAucun commentaire.")

    print()






def ajouter_commentaire_a_lieu(user_id):
    lieux = get_places_with_ids()

    if not lieux:
        print("\nAucun lieu disponible.")
        return

    print("\nLieux disponibles :\n")
    for numero, (_, nom) in enumerate(lieux, start=1):
        print(f"    {numero} - {nom}")

    try:
        choix_lieu = int(input("\nChoisissez un lieu : "))
    except ValueError:
        print("\nErreur : le choix doit être un nombre.")
        return

    if choix_lieu < 1 or choix_lieu > len(lieux):
        print("\nErreur : choix de lieu invalide.")
        return

    place_id = lieux[choix_lieu - 1][0]

    commentaire = input("\nVotre commentaire : ").strip()

    if not commentaire:
        print("\nErreur : le commentaire ne peut pas être vide.")
        return

    ajouter_avis(place_id, user_id, commentaire)
    print("\nCommentaire ajouté avec succès.")


def supprimer_commentaire_a_lieu(user_id):

    avis = get_avis_by_user(user_id)

    if not avis:
        print("\nVous n'avez aucun commentaire à supprimer.")
        return

    print("\nVos commentaires :\n")

    for numero, (_, commentaire, nom_lieu) in enumerate(avis, start=1):
        print(f"    {numero} - {nom_lieu}")
        print(f"        {commentaire}")

    try:
        choix = int(input("\nChoisissez le commentaire à supprimer : "))
    except ValueError:
        print("\nErreur : le choix doit être un nombre.")
        return

    if choix < 1 or choix > len(avis):
        print("\nErreur : choix de commentaire invalide.")
        return

    avis_id = avis[choix - 1][0]

    confirmation = input(
        "\nConfirmer la suppression ? (o/n) : "
    ).strip().lower()

    if confirmation != "o":
        print("\nSuppression annulée.")
        return

    if supprimer_avis(avis_id, user_id):
        print("\nCommentaire supprimé avec succès.")
    else:
        print("\nImpossible de supprimer ce commentaire.")


def menu_mes_commentaires(user_id):
    while True:
        print("\n=== MES COMMENTAIRES ===\n")
        print("1 - Voir mes commentaires")
        print("2 - Ajouter un commentaire")
        print("3 - Supprimer un commentaire")
        print("4 - Retour au menu principal")

        choix = input("\nVotre choix : ").strip()

        if choix == "1":
            avis = get_avis_by_user(user_id)

            if not avis:
                print("\nVous n'avez aucun commentaire.")
                continue

            print("\nVos commentaires :\n")

            for numero, (_, commentaire, nom_lieu) in enumerate(
                avis,
                start=1,
            ):
                print(f"{numero} - {nom_lieu}")
                print(f"    {commentaire}")

        elif choix == "2":
            ajouter_commentaire_a_lieu(user_id)

        elif choix == "3":
            supprimer_commentaire_a_lieu(user_id)

        elif choix == "4":
            return

        else:
            print("\nChoix invalide.")



def afficher_menu():
    print("=" * 45)
    print("            NetAtlas -> Ver. 1")
    print("=" * 45)
    print()

    print("1 - Recherche globale")
    print("2 - Mes commentaires")
    print("3 - Déconnexion")
    print()


def afficher_menu_temporaire():
    print("=" * 45)
    print("        NetAtlas -> Accès temporaire")
    print("=" * 45)
    print()
    print(
        "NOTE : pour ajouter des tags ou des commentaires, "
        "créez un profil depuis le menu d'accueil."
    )
    print()

    print("1 - Recherche globale")
    print("2 - Retour au menu principal")
    print()



