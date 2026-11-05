
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import psycopg
import pytest

import database


@pytest.fixture
def connexion_iam():
    """Isole les tests IAM dans la base PostgreSQL de test."""
    connexion = database.connexion_db()

    try:
        assert connexion.info.dbname == "netatlas_test"
        assert connexion.autocommit is False

        with connexion.cursor() as curseur:
            curseur.execute("SELECT current_user")
            utilisateur = curseur.fetchone()[0]

        assert utilisateur in {
            "netatlas_test_user",
            "netatlas_ci_user",
        }

        yield connexion

    finally:
        connexion.rollback()
        connexion.close()


def creer_session(
    connexion,
    *,
    token_hash=None,
    idle=900,
    expires_at=None,
):
    """Insère une session IAM sans commit définitif."""
    if token_hash is None:
        token_hash = hashlib.sha256(
            secrets.token_bytes(32)
        ).digest()

    if expires_at is None:
        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(hours=8)
        )

    with connexion.cursor() as curseur:
        curseur.execute(
            """
            INSERT INTO public.iam_sessions (
                user_id,
                token_hash,
                expires_at,
                idle_timeout_seconds
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                3,
                token_hash,
                expires_at,
                idle,
            ),
        )

        return curseur.fetchone()[0]


def test_creation_session_valide(connexion_iam):
    """Une session valide peut être créée et consultée."""
    session_id = creer_session(connexion_iam)

    with connexion_iam.cursor() as curseur:
        curseur.execute(
            """
            SELECT
                user_id,
                idle_timeout_seconds,
                revoked_at
            FROM public.iam_sessions
            WHERE id = %s
            """,
            (session_id,),
        )

        resultat = curseur.fetchone()

    assert resultat == (3, 900, None)


@pytest.mark.parametrize(
    (
        "token_hash",
        "idle",
        "expiration",
        "contrainte",
    ),
    [
        (
            b"court",
            900,
            8,
            "iam_sessions_token_hash_check",
        ),
        (
            b"a" * 32,
            30,
            8,
            "iam_sessions_idle_timeout_seconds_check",
        ),
        (
            b"b" * 32,
            900,
            -1,
            "iam_sessions_expiration_check",
        ),
    ],
)


def test_rejet_contraintes(
    connexion_iam,
    token_hash,
    idle,
    expiration,
    contrainte,
):
    """Vérifie le rejet des données IAM incorrectes."""
    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=expiration)
    )

    with (
        pytest.raises(psycopg.errors.CheckViolation) as erreur,
        connexion_iam.transaction(),
    ):
        creer_session(
            connexion_iam,
            token_hash=token_hash,
            idle=idle,
            expires_at=expires_at,
        )

    contrainte_observee = erreur.value.diag.constraint_name

    if contrainte == "iam_sessions_expiration_check":
        assert contrainte_observee in {
            "iam_sessions_expiration_check",
            "iam_sessions_activity_check",
        }
    else:
        assert contrainte_observee == contrainte


def test_rejet_empreinte_dupliquee(connexion_iam):
    """Deux sessions ne peuvent pas partager une empreinte."""
    token_hash = hashlib.sha256(
        b"iam-duplicata"
    ).digest()

    creer_session(
        connexion_iam,
        token_hash=token_hash,
    )

    with (
        pytest.raises(psycopg.errors.UniqueViolation),
        connexion_iam.transaction(),
    ):
        creer_session(
            connexion_iam,
            token_hash=token_hash,
        )


def test_revocation_session(connexion_iam):
    """Une session peut être révoquée sans être supprimée."""
    session_id = creer_session(connexion_iam)

    with connexion_iam.cursor() as curseur:
        curseur.execute(
            """
            UPDATE public.iam_sessions
            SET
                revoked_at = CURRENT_TIMESTAMP,
                revocation_reason = 'test_revocation'
            WHERE id = %s
            RETURNING revoked_at, revocation_reason
            """,
            (session_id,),
        )

        resultat = curseur.fetchone()

    assert resultat is not None

    revoked_at, raison = resultat

    assert revoked_at is not None
    assert raison == "test_revocation"


def test_suppression_interdite_compte_applicatif(connexion_iam):
    """Le compte de test ne doit pas pouvoir supprimer les sessions."""
    with connexion_iam.cursor() as curseur:
        curseur.execute("SELECT current_user")
        utilisateur = curseur.fetchone()[0]

    assert utilisateur in {
        "netatlas_test_user",
        "netatlas_ci_user",
    }

    with (
        pytest.raises(psycopg.errors.InsufficientPrivilege),
        connexion_iam.transaction(),
        connexion_iam.cursor() as curseur,
    ):
        curseur.execute(
            """
            DELETE FROM public.iam_sessions
            WHERE id = -1
            """
        )

