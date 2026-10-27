"""Création locale d'une demande de récupération Passkey NetAtlas."""

import hashlib
import os
import pwd
import secrets
import sys

import psycopg

BASE_AUTORISEE = "netatlas_test"
UTILISATEUR_SYSTEME = "netatlas-recovery"
SOCKET_POSTGRESQL = "/var/run/postgresql"


def verifier_identite_systeme():
    """Vérifier l'identité Linux effective du processus."""

    identifiant_effectif = os.geteuid()

    if identifiant_effectif == 0:
        raise RuntimeError("Exécution en tant que root interdite.")

    utilisateur = pwd.getpwuid(identifiant_effectif).pw_name

    if utilisateur != UTILISATEUR_SYSTEME:
        raise RuntimeError("Compte système non autorisé.")


def main():
    """Créer une demande temporaire de récupération administrative."""

    verifier_identite_systeme()

    jeton = secrets.token_bytes(32)
    empreinte = hashlib.sha256(jeton).digest()

    with psycopg.connect(
        dbname=BASE_AUTORISEE,
        user=UTILISATEUR_SYSTEME,
        host=SOCKET_POSTGRESQL,
        connect_timeout=5,
    ) as connexion, connexion.cursor() as curseur:
        curseur.execute(
            """
                SELECT public.demander_recuperation_passkey_admin(
                    %s,
                    %s
                )
                """,
            (
                empreinte,
                UTILISATEUR_SYSTEME,
            ),
        )

        resultat = curseur.fetchone()

        if resultat is None:
            raise RuntimeError(
                "Aucune autorisation de récupération créée."
            )

        autorisation_id = resultat[0]

    print()
    print("NETATLAS - RECUPERATION ADMINISTRATIVE")
    print("------------------------------------")
    print("Autorisation créée avec succès.")
    print(f"Base PostgreSQL : {BASE_AUTORISEE}")
    print(f"Identifiant autorisation : {autorisation_id}")
    print("Durée de validité : 300 secondes")
    print()
    print(f"Jeton de récupération : {jeton.hex()}")
    print()
    print("Conservez ce jeton confidentiel.")
    print("Il ne peut être utilisé que pendant cinq minutes.")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, psycopg.Error, KeyError) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        sys.exit(1)
