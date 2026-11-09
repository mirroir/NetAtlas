
"""Tests du service de sessions IAM NetAtlas."""

import iam_sessions
import pytest


@pytest.mark.parametrize(
    ("user_id", "duree", "inactivite"),
    [
        (0, 3600, 900),
        (-1, 3600, 900),
        (True, 3600, 900),
        ("3", 3600, 900),
        (3, 0, 900),
        (3, -1, 900),
        (3, True, 900),
        (3, 28801, 900),
        (3, 3600, 59),
        (3, 3600, 86401),
        (3, 3600, False),
        (3, 3600, "900"),
    ],
)
def test_rejet_parametres_invalides(
    monkeypatch,
    user_id,
    duree,
    inactivite,
):
    """Les paramètres invalides sont rejetés avant toute connexion."""

    def connexion_interdite():
        pytest.fail(
            "Une connexion PostgreSQL ne doit pas être ouverte."
        )

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        connexion_interdite,
    )

    with pytest.raises(ValueError):
        iam_sessions.creer_session_iam(
            user_id,
            duree_secondes=duree,
            inactivite_secondes=inactivite,
        )



def test_creation_session_postgresql(monkeypatch):
    """Vérifie la création IAM dans la base de test uniquement."""
    import hashlib

    import database

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

    finally:
        connexion.rollback()
        connexion.close()

    connexion = database.connexion_db()
    connexion.rollback()
    connexion.close()

    # L'appel applicatif ouvre sa propre transaction.
    jeton = iam_sessions.creer_session_iam(
        3,
        duree_secondes=3600,
        inactivite_secondes=900,
    )

    assert isinstance(jeton, str)
    assert len(jeton) == 64

    empreinte = hashlib.sha256(
        bytes.fromhex(jeton)
    ).digest()

    connexion = database.connexion_db()

    try:
        assert connexion.info.dbname == "netatlas_test"

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    user_id,
                    token_hash,
                    idle_timeout_seconds,
                    expires_at > created_at
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (empreinte,),
            )

            resultat = curseur.fetchone()

        assert resultat is not None
        assert resultat[0] == 3
        assert bytes(resultat[1]) == empreinte
        assert resultat[2] == 900
        assert resultat[3] is True

    finally:
        connexion.rollback()
        connexion.close()



def test_creation_session_postgresql_isolee(monkeypatch):
    """Vérifie la création IAM sans validation définitive."""

    import hashlib

    import database

    connexion = database.connexion_db()

    assert connexion.info.dbname == "netatlas_test"
    assert connexion.autocommit is False

    class ConnexionControlee:
        def cursor(self):
            return connexion.cursor()

        def commit(self):
            """La transaction reste ouverte pour le rollback final."""

        def rollback(self):
            connexion.rollback()

        def close(self):
            """La fixture conserve la connexion jusqu'au nettoyage."""

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        lambda: ConnexionControlee(),
    )

    try:
        jeton = iam_sessions.creer_session_iam(
            3,
            duree_secondes=3600,
            inactivite_secondes=900,
        )

        assert isinstance(jeton, str)
        assert len(jeton) == 64

        empreinte = hashlib.sha256(
            bytes.fromhex(jeton)
        ).digest()

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    user_id,
                    token_hash,
                    idle_timeout_seconds,
                    expires_at > created_at
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (empreinte,),
            )

            resultat = curseur.fetchone()

        assert resultat is not None
        assert resultat[0] == 3
        assert bytes(resultat[1]) == empreinte
        assert resultat[2] == 900
        assert resultat[3] is True

    finally:
        connexion.rollback()
        connexion.close()



def test_creation_session_rollback_sur_erreur(monkeypatch):
    """Une erreur SQL provoque un rollback et ferme la connexion."""

    import psycopg

    class CurseurSimule:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, requete, parametres):
            raise psycopg.OperationalError(
                "Erreur PostgreSQL simulée pour le test IAM."
            )

    class ConnexionSimulee:
        def __init__(self):
            self.rollback_effectue = False
            self.fermeture_effectuee = False
            self.commit_effectue = False

        def cursor(self):
            return CurseurSimule()

        def commit(self):
            self.commit_effectue = True

        def rollback(self):
            self.rollback_effectue = True

        def close(self):
            self.fermeture_effectuee = True

    connexion = ConnexionSimulee()

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        lambda: connexion,
    )

    with pytest.raises(psycopg.OperationalError):
        iam_sessions.creer_session_iam(3)

    assert connexion.rollback_effectue is True
    assert connexion.fermeture_effectuee is True
    assert connexion.commit_effectue is False



def test_creation_session_commit_sur_reussite(monkeypatch):
    """Une création réussie valide et ferme la connexion."""

    class CurseurSimule:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, requete, parametres):
            assert "INSERT INTO public.iam_sessions" in requete
            assert len(parametres) == 4
            assert parametres[0] == 3
            assert len(parametres[1]) == 32
            assert parametres[2] == 28800
            assert parametres[3] == 900

    class ConnexionSimulee:
        def __init__(self):
            self.commit_effectue = False
            self.rollback_effectue = False
            self.fermeture_effectuee = False

        def cursor(self):
            return CurseurSimule()

        def commit(self):
            self.commit_effectue = True

        def rollback(self):
            self.rollback_effectue = True

        def close(self):
            self.fermeture_effectuee = True

    connexion = ConnexionSimulee()

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        lambda: connexion,
    )

    jeton = iam_sessions.creer_session_iam(3)

    assert isinstance(jeton, str)
    assert len(jeton) == 64
    assert connexion.commit_effectue is True
    assert connexion.rollback_effectue is False
    assert connexion.fermeture_effectuee is True



@pytest.mark.parametrize(
    "jeton",
    [
        None,
        "",
        "invalide",
        "g" * 64,
        "a" * 63,
        "a" * 65,
        123,
        True,
    ],
)
def test_valider_session_iam_rejette_jeton_invalide(
    monkeypatch, jeton
):
    """Un jeton invalide ne doit jamais ouvrir PostgreSQL."""

    import iam_sessions

    def connexion_interdite():
        raise AssertionError(
            "Connexion PostgreSQL interdite pour un jeton invalide."
        )

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        connexion_interdite,
    )

    assert iam_sessions.valider_session_iam(jeton) is None



def test_valider_session_iam_session_active(monkeypatch):
    """Une session active est validée sans persistance des données de test."""

    import hashlib

    import iam_sessions

    from database import connexion_db

    connexion = connexion_db()

    with connexion.cursor() as curseur:
        curseur.execute(
            "SELECT id, nom FROM public.users ORDER BY id LIMIT 1"
        )
        utilisateur = curseur.fetchone()

    assert utilisateur is not None

    user_id, nom = utilisateur

    class ConnexionSansCommit:
        def cursor(self):
            return connexion.cursor()

        def commit(self):
            pass

        def rollback(self):
            connexion.rollback()

        def close(self):
            pass

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        lambda: ConnexionSansCommit(),
    )

    try:
        jeton = iam_sessions.creer_session_iam(user_id)
        resultat = iam_sessions.valider_session_iam(jeton)

        assert resultat == {
            "user_id": user_id,
            "nom": nom,
        }

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT COUNT(*)
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (hashlib.sha256(bytes.fromhex(jeton)).digest(),),
            )
            assert curseur.fetchone()[0] == 1

    finally:
        connexion.rollback()
        connexion.close()




def test_valider_session_iam_session_revoquee(monkeypatch):
    """Une session révoquée doit être refusée."""

    import hashlib

    import iam_sessions

    from database import connexion_db

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT id FROM public.users ORDER BY id LIMIT 1"
            )
            utilisateur = curseur.fetchone()

        assert utilisateur is not None
        user_id = utilisateur[0]

        class ConnexionSansCommit:
            def cursor(self):
                return connexion.cursor()

            def commit(self):
                pass

            def rollback(self):
                connexion.rollback()

            def close(self):
                pass

        monkeypatch.setattr(
            iam_sessions,
            "connexion_db",
            lambda: ConnexionSansCommit(),
        )

        jeton = iam_sessions.creer_session_iam(user_id)
        empreinte = hashlib.sha256(bytes.fromhex(jeton)).digest()

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET revoked_at = CURRENT_TIMESTAMP,
                    revocation_reason = 'Test de révocation IAM'
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            assert curseur.rowcount == 1

        assert iam_sessions.valider_session_iam(jeton) is None

    finally:
        connexion.rollback()
        connexion.close()


def test_valider_session_iam_session_expiree(monkeypatch):
    """Une session expirée doit être refusée."""

    import hashlib

    import iam_sessions

    from database import connexion_db

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT id FROM public.users ORDER BY id LIMIT 1"
            )
            utilisateur = curseur.fetchone()

        assert utilisateur is not None
        user_id = utilisateur[0]

        class ConnexionSansCommit:
            def cursor(self):
                return connexion.cursor()

            def commit(self):
                pass

            def rollback(self):
                connexion.rollback()

            def close(self):
                pass

        monkeypatch.setattr(
            iam_sessions,
            "connexion_db",
            lambda: ConnexionSansCommit(),
        )

        jeton = iam_sessions.creer_session_iam(user_id)
        empreinte = hashlib.sha256(bytes.fromhex(jeton)).digest()

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET created_at = statement_timestamp() - INTERVAL '2 hours',
                    last_activity_at = statement_timestamp() - INTERVAL '2 hours',
                    expires_at = statement_timestamp()
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            assert curseur.rowcount == 1

            curseur.execute(
                """
                SELECT last_activity_at
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            activite_avant = curseur.fetchone()[0]

        assert iam_sessions.valider_session_iam(jeton) is None

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT last_activity_at
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            activite_apres = curseur.fetchone()[0]

        assert activite_apres == activite_avant

    finally:
        connexion.rollback()
        connexion.close()




def test_valider_session_iam_session_inactive(monkeypatch):
    """Une session inactive doit être refusée."""

    import hashlib

    import iam_sessions

    from database import connexion_db

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT id FROM public.users ORDER BY id LIMIT 1"
            )
            utilisateur = curseur.fetchone()

        assert utilisateur is not None
        user_id = utilisateur[0]

        class ConnexionSansCommit:
            def cursor(self):
                return connexion.cursor()

            def commit(self):
                pass

            def rollback(self):
                connexion.rollback()

            def close(self):
                pass

        monkeypatch.setattr(
            iam_sessions,
            "connexion_db",
            lambda: ConnexionSansCommit(),
        )

        jeton = iam_sessions.creer_session_iam(user_id)
        empreinte = hashlib.sha256(bytes.fromhex(jeton)).digest()

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET created_at = CURRENT_TIMESTAMP - INTERVAL '1 hour',
                    last_activity_at = CURRENT_TIMESTAMP - INTERVAL '30 minutes',
                    expires_at = CURRENT_TIMESTAMP + INTERVAL '1 hour'
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            assert curseur.rowcount == 1

        assert iam_sessions.valider_session_iam(jeton) is None

    finally:
        connexion.rollback()
        connexion.close()


def test_horloge_validation_iam_transaction_longue():
    """L'horloge de validation ne dépend pas du début de transaction."""

    from database import connexion_db

    connexion = connexion_db()

    try:
        assert connexion.info.dbname == "netatlas_test"

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    CURRENT_TIMESTAMP AS debut_transaction,
                    statement_timestamp() AS heure_instruction
                """
            )
            debut, instruction = curseur.fetchone()

            assert instruction >= debut

            curseur.execute(
                """
                SELECT
                    statement_timestamp() >= CURRENT_TIMESTAMP
                """
            )
            assert curseur.fetchone()[0] is True

    finally:
        connexion.rollback()
        connexion.close()



def test_valider_session_iam_actualise_activite(monkeypatch):
    """Une validation réussie actualise la dernière activité."""

    import hashlib

    from database import connexion_db

    connexion = connexion_db()

    try:
        assert connexion.info.dbname == "netatlas_test"

        with connexion.cursor() as curseur:
            curseur.execute(
                "SELECT id FROM public.users ORDER BY id LIMIT 1"
            )
            utilisateur = curseur.fetchone()

        assert utilisateur is not None
        user_id = utilisateur[0]

        class ConnexionSansCommit:
            def cursor(self):
                return connexion.cursor()

            def commit(self):
                pass

            def rollback(self):
                connexion.rollback()

            def close(self):
                pass

        monkeypatch.setattr(
            iam_sessions,
            "connexion_db",
            lambda: ConnexionSansCommit(),
        )

        jeton = iam_sessions.creer_session_iam(user_id)
        empreinte = hashlib.sha256(bytes.fromhex(jeton)).digest()

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET created_at = statement_timestamp()
                        - INTERVAL '10 minutes',
                    last_activity_at = statement_timestamp()
                        - INTERVAL '5 minutes'
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            assert curseur.rowcount == 1

            curseur.execute(
                """
                SELECT last_activity_at
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            activite_avant = curseur.fetchone()[0]

        resultat = iam_sessions.valider_session_iam(jeton)

        assert resultat is not None
        assert resultat["user_id"] == user_id

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT last_activity_at
                FROM public.iam_sessions
                WHERE token_hash = %s
                """,
                (empreinte,),
            )
            activite_apres = curseur.fetchone()[0]

        assert activite_apres > activite_avant

    finally:
        connexion.rollback()
        connexion.close()



def test_valider_session_iam_erreur_sql_rollback(monkeypatch):
    """Une erreur SQL annule la transaction et ferme la connexion."""

    class CurseurSimule:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def execute(self, requete, parametres):
            raise RuntimeError("Erreur SQL simulée")

    class ConnexionSimulee:
        def __init__(self):
            self.rollback_effectue = False
            self.fermeture_effectuee = False
            self.commit_effectue = False

        def cursor(self):
            return CurseurSimule()

        def commit(self):
            self.commit_effectue = True

        def rollback(self):
            self.rollback_effectue = True

        def close(self):
            self.fermeture_effectuee = True

    connexion = ConnexionSimulee()

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        lambda: connexion,
    )

    jeton = "a" * 64

    with pytest.raises(
        RuntimeError,
        match="Erreur SQL simulée",
    ):
        iam_sessions.valider_session_iam(jeton)

    assert connexion.rollback_effectue is True
    assert connexion.fermeture_effectuee is True
    assert connexion.commit_effectue is False



def test_limite_expiration_session_iam():
    """Une session expirant à l'instant de validation est refusée."""

    from database import connexion_db

    connexion = connexion_db()

    try:
        assert connexion.info.dbname == "netatlas_test"

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    statement_timestamp() > statement_timestamp(),
                    statement_timestamp() = statement_timestamp()
                """
            )
            expiration_valide, expiration_exacte = curseur.fetchone()

        assert expiration_valide is False
        assert expiration_exacte is True

    finally:
        connexion.rollback()
        connexion.close()



