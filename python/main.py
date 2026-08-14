from menu import afficher_menu, afficher_categories, afficher_pays, afficher_villes, afficher_recherche_ville, afficher_lieux_par_ville, afficher_recherche_globale



def main():
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
            print("Nartrouv les gas !")
            break
            

        else:
            print("\nChoix invalide. Essaie encore.\n")


if __name__ == "__main__":
    main()
