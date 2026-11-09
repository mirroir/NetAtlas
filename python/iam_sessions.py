
"""Gestion des sessions IAM sécurisées de NetAtlas."""

import hashlib
import secrets

from database import connexion_db

DUREE_SESSION_SECONDES = 8 * 60 * 60
INACTIVITE_SESSION_SECONDES = 15 * 60


def creer_session_iam(
    user_id: int,
    *,
    duree_secondes: int = DUREE_SESSION_SECONDES,
    inactivite_secondes: int = INACTIVITE_SESSION_SECONDES,
) -> str:
    """Crée une session PostgreSQL et retourne son jeton opaque."""

    if (
        not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
    ):
        raise ValueError("Identifiant utilisateur invalide.")

    if (
        not isinstance(duree_secondes, int)
        or isinstance(duree_secondes, bool)
        or duree_secondes <= 0
        or duree_secondes > DUREE_SESSION_SECONDES
    ):
        raise ValueError("Durée de session invalide.")

    if (
        not isinstance(inactivite_secondes, int)
        or isinstance(inactivite_secondes, bool)
        or not 60 <= inactivite_secondes <= 86400
    ):
        raise ValueError("Délai d'inactivité invalide.")

    jeton = secrets.token_hex(32)
    empreinte = hashlib.sha256(
        bytes.fromhex(jeton)
    ).digest()

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO public.iam_sessions (
                    user_id,
                    token_hash,
                    expires_at,
                    idle_timeout_seconds
                )
                VALUES (
                    %s,
                    %s,
                    CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'),
                    %s
                )
                """,
                (
                    user_id,
                    empreinte,
                    duree_secondes,
                    inactivite_secondes,
                ),
            )

        connexion.commit()
        return jeton

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()

