
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

import iam_sessions
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
            datetime.now(UTC)
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
        datetime.now(UTC)
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


@pytest.fixture
def connexion_rotation_iam(connexion_iam, monkeypatch):
    """Exécute la rotation dans une transaction de test isolée."""

    class ConnexionControlee:
        def __init__(self):
            self.savepoint_rotation = False

        def cursor(self):
            return connexion_iam.cursor()

        def commit(self):
            """Empêche toute validation définitive."""

        def rollback(self):
            try:
                with connexion_iam.cursor() as curseur:
                    curseur.execute(
                        "ROLLBACK TO SAVEPOINT avant_rotation_iam"
                    )
            except psycopg.errors.InvalidSavepointSpecification:
                connexion_iam.rollback()

        def close(self):
            """La fixture ferme réellement la connexion."""

    connexion_controlee = ConnexionControlee()

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        lambda: connexion_controlee,
    )

    return connexion_iam

def test_rotation_iam_postgresql_reelle(connexion_rotation_iam):
    """La rotation révoque l'ancien jeton et crée le nouveau."""

    ancien_jeton = secrets.token_hex(32)
    ancienne_empreinte = hashlib.sha256(
        bytes.fromhex(ancien_jeton)
    ).digest()

    creer_session(
        connexion_rotation_iam,
        token_hash=ancienne_empreinte,
    )

    nouveau_jeton = iam_sessions.renouveler_session_iam(
        3,
        ancien_jeton=ancien_jeton,
    )

    nouvelle_empreinte = hashlib.sha256(
        bytes.fromhex(nouveau_jeton)
    ).digest()

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute(
            """
            SELECT token_hash, revoked_at, revocation_reason
            FROM public.iam_sessions
            WHERE token_hash IN (%s, %s)
            """,
            (ancienne_empreinte, nouvelle_empreinte),
        )

        resultats = curseur.fetchall()

    assert len(resultats) == 2

    sessions = {
        bytes(empreinte): (revocation, raison)
        for empreinte, revocation, raison in resultats
    }

    assert sessions[ancienne_empreinte][0] is not None
    assert sessions[ancienne_empreinte][1] == "rotation_session"
    assert sessions[nouvelle_empreinte][0] is None

def test_rotation_iam_ancien_jeton_inexistant(connexion_rotation_iam):
    """Un jeton inconnu ne permet pas de créer une session IAM."""

    ancien_jeton = secrets.token_hex(32)
    ancienne_empreinte = hashlib.sha256(
        bytes.fromhex(ancien_jeton)
    ).digest()

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute("SAVEPOINT avant_rotation_iam")

    with pytest.raises(
        ValueError,
        match="ancienne session invalide",
    ):
        iam_sessions.renouveler_session_iam(
            3,
            ancien_jeton=ancien_jeton,
        )

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute(
            """
            SELECT COUNT(*)
            FROM public.iam_sessions
            WHERE token_hash = %s
            """,
            (ancienne_empreinte,),
        )
        nombre_sessions = curseur.fetchone()[0]

    assert nombre_sessions == 0

def test_rotation_iam_isolation_utilisateurs(connexion_rotation_iam):
    """La rotation ne révoque pas la session d'un autre utilisateur."""

    ancien_jeton = secrets.token_hex(32)
    ancienne_empreinte = hashlib.sha256(
        bytes.fromhex(ancien_jeton)
    ).digest()

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute(
            """
            INSERT INTO public.users (nom, email)
            VALUES (%s, %s)
            RETURNING id
            """,
            (
                "TestIsolationIAM",
                f"iam-isolation-{secrets.token_hex(12)}@example.invalid",
            ),
        )
        autre_utilisateur_id = curseur.fetchone()[0]

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
                CURRENT_TIMESTAMP + INTERVAL '1 hour',
                900
            )
            """,
            (autre_utilisateur_id, ancienne_empreinte),
        )

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute("SAVEPOINT avant_rotation_iam")

    with pytest.raises(
        ValueError,
        match="ancienne session invalide",
    ):
        iam_sessions.renouveler_session_iam(
            3,
            ancien_jeton=ancien_jeton,
        )

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute(
            """
            SELECT user_id, revoked_at
            FROM public.iam_sessions
            WHERE token_hash = %s
            """,
            (ancienne_empreinte,),
        )
        ancienne_session = curseur.fetchone()

    assert ancienne_session == (autre_utilisateur_id, None)

@pytest.mark.parametrize(
    "type_expiration",
    ["absolue", "inactivite"],
)
def test_rotation_iam_refuse_session_expiree(
    connexion_rotation_iam,
    type_expiration,
):
    """Une session expirée ne peut pas être renouvelée."""

    ancien_jeton = secrets.token_hex(32)
    ancienne_empreinte = hashlib.sha256(
        bytes.fromhex(ancien_jeton)
    ).digest()

    session_id = creer_session(
        connexion_rotation_iam,
        token_hash=ancienne_empreinte,
    )

    with connexion_rotation_iam.cursor() as curseur:
        if type_expiration == "absolue":
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET
                    created_at = statement_timestamp()
                        - INTERVAL '2 hours',
                    last_activity_at = statement_timestamp()
                        - INTERVAL '90 minutes',
                    expires_at = statement_timestamp()
                        - INTERVAL '1 minute'
                WHERE id = %s
                """,
                (session_id,),
            )
        else:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET
                    created_at = statement_timestamp()
                        - INTERVAL '30 minutes',
                    last_activity_at = statement_timestamp()
                        - INTERVAL '16 minutes'
                WHERE id = %s
                """,
                (session_id,),
            )

        curseur.execute(
            """
            SELECT created_at, last_activity_at, expires_at
            FROM public.iam_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        created_at, last_activity_at, expires_at = curseur.fetchone()

        assert created_at <= last_activity_at <= expires_at

        curseur.execute("SAVEPOINT avant_rotation_iam")

    with pytest.raises(
        ValueError,
        match="ancienne session invalide",
    ):
        iam_sessions.renouveler_session_iam(
            3,
            ancien_jeton=ancien_jeton,
        )

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute(
            """
            SELECT revoked_at, revocation_reason
            FROM public.iam_sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        resultat = curseur.fetchone()

    assert resultat == (None, None)

def test_rotation_iam_rollback_postgresql_reel(
    connexion_rotation_iam,
    monkeypatch,
):
    """Une insertion refusée annule la révocation précédente."""

    ancien_jeton = secrets.token_hex(32)
    jeton_en_conflit = secrets.token_hex(32)

    ancienne_empreinte = hashlib.sha256(
        bytes.fromhex(ancien_jeton)
    ).digest()

    empreinte_en_conflit = hashlib.sha256(
        bytes.fromhex(jeton_en_conflit)
    ).digest()

    ancien_id = creer_session(
        connexion_rotation_iam,
        token_hash=ancienne_empreinte,
    )

    creer_session(
        connexion_rotation_iam,
        token_hash=empreinte_en_conflit,
    )

    monkeypatch.setattr(
        iam_sessions.secrets,
        "token_hex",
        lambda _taille: jeton_en_conflit,
    )

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute("SAVEPOINT avant_rotation_iam")

    with pytest.raises(psycopg.errors.UniqueViolation):
        iam_sessions.renouveler_session_iam(
            3,
            ancien_jeton=ancien_jeton,
        )

    with connexion_rotation_iam.cursor() as curseur:
        curseur.execute(
            """
            SELECT revoked_at, revocation_reason
            FROM public.iam_sessions
            WHERE id = %s
            """,
            (ancien_id,),
        )

        resultat = curseur.fetchone()

    assert resultat == (None, None)
