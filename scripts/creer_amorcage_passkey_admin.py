"""Création locale d'une autorisation temporaire Passkey administrateur."""

import hashlib
import os
import secrets
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "python"))

from database import (  # noqa: RUF100
    creer_amorcage_passkey_admin,
    get_admin_passkey_bootstrap,
)

ADMIN_ID = 2
DUREE_SECONDES = 300


def main():
    """Génère un jeton temporaire pour la première Passkey admin."""

    if os.getenv("DB_NAME") != "netatlas":
        raise RuntimeError(
            "SECURITE : amorçage autorisé uniquement sur la base netatlas."
        )

    if os.getenv("NETATLAS_ENV") == "test":
        raise RuntimeError(
            "SECURITE : amorçage interdit en environnement de test."
        )

    administrateur = get_admin_passkey_bootstrap(ADMIN_ID)

    if administrateur is None:
        raise RuntimeError(
            "Amorçage refusé : administrateur absent, "
            "rôle incorrect ou Passkey déjà enregistrée."
        )

    jeton = secrets.token_bytes(32)
    empreinte = hashlib.sha256(jeton).digest()

    identifiant = creer_amorcage_passkey_admin(
        user_id=ADMIN_ID,
        token_hash=empreinte,
        duree_secondes=DUREE_SECONDES,
    )

    if not identifiant:
        raise RuntimeError("Échec de création du jeton d'amorçage.")

    print("\n=== NETATLAS - AMORÇAGE PASSKEY ADMIN ===")
    print(f"Compte : {administrateur['nom']}")
    print(f"Identifiant : {ADMIN_ID}")
    print(f"Validité : {DUREE_SECONDES} secondes")
    print(f"Jeton temporaire : {jeton.hex()}")
    print("\nNe communique jamais ce jeton.")
    print("Il expirera automatiquement après cinq minutes.")


if __name__ == "__main__":
    main()
