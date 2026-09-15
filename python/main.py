from getpass import getpass

from menu import (
    afficher_menu,
    afficher_menu_connexion,
    afficher_menu_temporaire,
    afficher_recherche_globale,
    menu_mes_commentaires,
)
from psycopg.errors import UniqueViolation

from database import authentifier_utilisateur, creer_utilisateur


def main():
    while True:
        afficher_menu_connexion()
        choix = input("Votre choix : ").strip()

        if choix == "1":
           session = connexion_administrateur()

           if session is not None:
              menu_principal(session["user_id"])

        elif choix == "2":
          session = connexion_utilisateur()

          if session is not None:
             menu_principal(session["user_id"])

        elif choix == "3":
            creer_profil()

        elif choix == "4":
            menu_temporaire()

        elif choix == "0":
          print("\nÀ bientôt sur NetAtlas !\n")
          return

        else:
          print("\nChoix invalide. Essaie encore.\n")


def connexion_administrateur():
    print("\n=== CONNEXION ADMINISTRATEUR ===\n")

    nom = input("Nom de profil : ").strip()
    pin = getpass("PIN : ")

    session = authentifier_utilisateur(
        nom,
        pin,
        "admin",
    )

    if session is None:
        print("\nIdentifiants incorrects ou accès administrateur refusé.")
        return None

    print(f"\nBienvenue {session['nom']} !")
    return session

def connexion_utilisateur():
    print("\n=== CONNEXION UTILISATEUR ===\n")

    nom = input("Nom de profil : ").strip()
    pin = getpass("PIN : ")

    session = authentifier_utilisateur(
        nom,
        pin,
        "utilisateur",
    )

    if session is None:
        print("\nProfil introuvable, PIN incorrect ou accès refusé.")
        print("Si vous n’avez pas encore de profil, " "choisissez « Créer un profil » dans le menu d’accueil.")
        return None

    print(f"\nBienvenue {session['nom']} !")
    return session


def creer_profil():
    print("\n=== CRÉATION D'UN PROFIL ===\n")

    nom = input("Nom de profil : ").strip()

    if not nom:
        print("\nLe nom de profil ne peut pas être vide.")
        return

    pin = getpass("PIN : ")
    confirmation_pin = getpass("Confirmez le PIN : ")

    if pin != confirmation_pin:
        print("\nLes deux PIN ne correspondent pas.")
        return

    if not pin:
        print("\nLe PIN ne peut pas être vide.")
        return


    try:
        user_id = creer_utilisateur(nom, pin)
    except UniqueViolation:
        print("\nCe nom de profil existe déjà.")
        print("Veuillez choisir un autre nom.")
        return

    print(f"\nProfil créé avec succès ! ID utilisateur : {user_id}")
    print("Vous pouvez maintenant vous connecter avec l'option 2.")


def menu_temporaire():
    while True:
        afficher_menu_temporaire()
        choix = input("Votre choix : ").strip()

        if choix == "1":
            afficher_recherche_globale()

        elif choix == "2":
            print("\nRetour au menu d'accueil.\n")
            return

        else:
            print("\nChoix invalide. Essaie encore.\n")


def menu_principal(user_id):
    while True:
        afficher_menu()

        choix = input("Votre choix : ").strip()

        if choix == "1":
            afficher_recherche_globale(user_id=user_id)

        elif choix == "2":
            menu_mes_commentaires(user_id)


        elif choix == "3":
            print("\nDéconnexion réussie. Retour à l'accueil.\n")
            return

        else:
            print("\nChoix invalide. Essaie encore.\n")


if __name__ == "__main__":
    main()
