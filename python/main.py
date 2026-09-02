from getpass import getpass

from menu import (
    afficher_categories,
    afficher_detail_lieu,
    afficher_lieux_par_ville,
    afficher_menu,
    afficher_menu_connexion,
    afficher_pays,
    afficher_recherche_globale,
    afficher_recherche_ville,
    afficher_villes,
    ajouter_tag_a_lieu,
    choisir_utilisateur,
    menu_mes_commentaires,
)

from database import authentifier_utilisateur


def connexion_administrateur():
    afficher_menu_connexion()

    pin = getpass("PIN Administrateur : ")

    session = authentifier_utilisateur(
        "Administrateur",
        pin,
        "admin",
    )

    if session is None:
        print("\nPIN incorrect. Accès refusé.")
        return None

    print(f"\nBienvenue {session['nom']} !")
    return session


def main():
    user_id = choisir_utilisateur()

    if user_id is None:
        print("\nImpossible de démarrer sans utilisateur.")
        return

    while True:
        afficher_menu()

        choix = input("Fait ton choix coco : ")

        if choix == "1":
            afficher_categories()

        elif choix == "2":
            afficher_pays()

        elif choix == "3":
            afficher_villes()

        elif choix == "4":
            afficher_recherche_ville()
        
        elif choix == "5":
            afficher_lieux_par_ville()
            
        elif choix == "6":
            afficher_recherche_globale()

        elif choix == "7":
            afficher_detail_lieu()

        elif choix == "8":
            ajouter_tag_a_lieu()

        elif choix == "9":
            menu_mes_commentaires(user_id)

        elif choix == "10":
            print("Au revoir !")
            break
            

        else:
            print("\nChoix invalide. Essaie encore.\n")


if __name__ == "__main__":
    main()
