from menu import afficher_menu_connexion, afficher_recherche_globale


def main():
    """Lance le CLI public sans authentification locale."""
    while True:
        afficher_menu_connexion()
        choix = input("Votre choix : ").strip()

        if choix == "1":
            afficher_recherche_globale()

        elif choix == "0":
            print("\nÀ bientôt sur NetAtlas !\n")
            return

        else:
            print("\nChoix invalide. Essaie encore.\n")


if __name__ == "__main__":
    main()
