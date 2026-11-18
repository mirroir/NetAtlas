
"""Gestion des sessions IAM sécurisées de NetAtlas."""

import hashlib
import secrets

from database import connexion_db

DUREE_SESSION_SECONDES = 8 * 60 * 60
INACTIVITE_SESSION_SECONDES = 15 * 60

class SessionIAMInvalide(ValueError):
    """Ancienne session IAM inutilisable pour une rotation."""

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


def renouveler_session_iam(
    user_id: int,
    ancien_jeton: str | None = None,
    *,
    duree_secondes: int = DUREE_SESSION_SECONDES,
    inactivite_secondes: int = INACTIVITE_SESSION_SECONDES,
) -> str:
    """Crée une session IAM et révoque l'ancienne atomiquement."""

    if (
        not isinstance(user_id, int)
        or isinstance(user_id, bool)
        or user_id <= 0
    ):
        raise ValueError("Identifiant utilisateur invalide.")

    if (
        not isinstance(duree_secondes, int)
        or isinstance(duree_secondes, bool)
        or not 0 < duree_secondes <= DUREE_SESSION_SECONDES
    ):
        raise ValueError("Durée de session invalide.")

    if (
        not isinstance(inactivite_secondes, int)
        or isinstance(inactivite_secondes, bool)
        or not 60 <= inactivite_secondes <= 86400
    ):
        raise ValueError("Délai d'inactivité invalide.")

    ancienne_empreinte = None

    if ancien_jeton is not None:
        if not isinstance(ancien_jeton, str) or len(ancien_jeton) != 64:
            raise ValueError("Ancien jeton IAM invalide.")

        try:
            ancienne_empreinte = hashlib.sha256(
                bytes.fromhex(ancien_jeton)
            ).digest()
        except ValueError as erreur:
            raise ValueError("Ancien jeton IAM invalide.") from erreur

    nouveau_jeton = secrets.token_hex(32)
    nouvelle_empreinte = hashlib.sha256(
        bytes.fromhex(nouveau_jeton)
    ).digest()

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            if ancienne_empreinte is not None:
                curseur.execute(
                    """
                    UPDATE public.iam_sessions
                    SET
                        revoked_at = statement_timestamp(),
                        revocation_reason = 'rotation_session'
                    WHERE token_hash = %s
                      AND user_id = %s
                      AND revoked_at IS NULL
                      AND expires_at > statement_timestamp()
                      AND last_activity_at
                          + (idle_timeout_seconds * INTERVAL '1 second')
                          > statement_timestamp()
                    """,
                    (ancienne_empreinte, user_id),
                )

                if curseur.rowcount != 1:
                    raise SessionIAMInvalide(
                        "Rotation IAM refusée : ancienne session invalide."
                    )

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
                    nouvelle_empreinte,
                    duree_secondes,
                    inactivite_secondes,
                ),
            )

        connexion.commit()
        return nouveau_jeton

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()



def valider_session_iam(jeton: str) -> dict | None:
    """Valide une session IAM et actualise son activité atomiquement."""

    if not isinstance(jeton, str) or len(jeton) != 64:
        return None

    try:
        jeton_brut = bytes.fromhex(jeton)
    except ValueError:
        return None

    empreinte = hashlib.sha256(jeton_brut).digest()

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:

            curseur.execute(
                """
                UPDATE public.iam_sessions AS s
                SET last_activity_at = GREATEST(
                    s.last_activity_at,
                    statement_timestamp()
                )
                FROM public.users AS u
                WHERE s.token_hash = %s
                  AND u.id = s.user_id
                  AND s.revoked_at IS NULL
                  AND s.expires_at > statement_timestamp()
                  AND s.last_activity_at
                      + (s.idle_timeout_seconds * INTERVAL '1 second')
                      > statement_timestamp()
                RETURNING
                    s.user_id,
                    u.nom
                """,
                (empreinte,),
            )

            resultat = curseur.fetchone()

        connexion.commit()

        if resultat is None:
            return None

        return {
            "user_id": resultat[0],
            "nom": resultat[1],
        }

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def revoquer_session_iam(jeton: str) -> bool:
    """Révoque une session IAM par son jeton opaque."""

    if not isinstance(jeton, str) or len(jeton) != 64:
        return False

    try:
        jeton_brut = bytes.fromhex(jeton)
    except ValueError:
        return False

    empreinte = hashlib.sha256(jeton_brut).digest()
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET
                    revoked_at = statement_timestamp(),
                    revocation_reason = 'revocation_utilisateur'
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                RETURNING id
                """,
                (empreinte,),
            )

            resultat = curseur.fetchone()

        connexion.commit()
        return resultat is not None

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()
