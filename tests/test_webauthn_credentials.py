import sys
from pathlib import Path

import pytest
from psycopg.errors import CheckViolation, ForeignKeyViolation, UniqueViolation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from database import connexion_db


def test_creation_credential_webauthn():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            # Utilisateur temporaire propre au test
            curseur.execute(
                """
                INSERT INTO users (nom)
                VALUES (%s)
                RETURNING id
                """,
                ("Utilisateur WebAuthn pytest",),
            )

            user_id = curseur.fetchone()[0]

            # Enregistrement d'une Passkey fictive
            curseur.execute(
                """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key)
                VALUES (%s, %s, %s)
                RETURNING id, sign_count
                """,
                (
                    user_id,
                    b"credential-test-netatlas",
                    b"public-key-test-netatlas",
                ),
            )

            credential_id, sign_count = curseur.fetchone()

            assert credential_id is not None
            assert sign_count == 0

    finally:
        # Aucune donnée de test conservée
        connexion.rollback()
        connexion.close()



def test_credential_webauthn_unique():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO users (nom)
                VALUES (%s)
                RETURNING id
                """,
                ("Utilisateur WebAuthn unicite pytest",),
            )

            user_id = curseur.fetchone()[0]

            curseur.execute(
                """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key)
                VALUES (%s, %s, %s)
                """,
                (
                    user_id,
                    b"credential-unique-pytest",
                    b"public-key-pytest",
                ),
            )

            with pytest.raises(UniqueViolation):
                curseur.execute(
                    """
                    INSERT INTO webauthn_credentials
                        (user_id, credential_id, public_key)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        user_id,
                        b"credential-unique-pytest",
                        b"autre-public-key-pytest",
                    ),
                )

    finally:
        connexion.rollback()
        connexion.close()



def test_credential_webauthn_utilisateur_inexistant():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur, pytest.raises(ForeignKeyViolation):
            # Un identifiant négatif ne peut pas correspondre
            # à un utilisateur créé normalement.
            curseur.execute(
                    """
                    INSERT INTO webauthn_credentials
                        (user_id, credential_id, public_key)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        -1,
                        b"credential-fk-pytest",
                        b"public-key-fk-pytest",
                    ),
                )

    finally:
        connexion.rollback()
        connexion.close()



def test_credential_webauthn_compteur_negatif_refuse():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO users (nom)
                VALUES (%s)
                RETURNING id
                """,
                ("Utilisateur WebAuthn compteur pytest",),
            )

            user_id = curseur.fetchone()[0]

            with pytest.raises(CheckViolation):
                curseur.execute(
                    """
                    INSERT INTO webauthn_credentials
                        (user_id, credential_id, public_key, sign_count)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        user_id,
                        b"credential-compteur-pytest",
                        b"public-key-compteur-pytest",
                        -1,
                    ),
                )

    finally:
        connexion.rollback()
        connexion.close()



def test_compteur_webauthn_diminution_refusee():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO users (nom)
                VALUES (%s)
                RETURNING id
                """,
                ("Utilisateur WebAuthn compteur SQL pytest",),
            )
            user_id = curseur.fetchone()[0]

            curseur.execute(
                """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key, sign_count)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    b"credential-diminution-pytest",
                    b"public-key-diminution-pytest",
                    10,
                ),
            )

            curseur.execute(
                """
                UPDATE webauthn_credentials
                SET sign_count = %s
                WHERE credential_id = %s
                  AND sign_count <= %s
                RETURNING id
                """,
                (5, b"credential-diminution-pytest", 5),
            )

            assert curseur.fetchone() is None

            curseur.execute(
                """
                SELECT sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (b"credential-diminution-pytest",),
            )

            assert curseur.fetchone()[0] == 10

    finally:
        connexion.rollback()
        connexion.close()


def test_compteur_webauthn_identique_non_nul_refuse():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO users (nom)
                VALUES (%s)
                RETURNING id
                """,
                ("Utilisateur WebAuthn compteur identique pytest",),
            )
            user_id = curseur.fetchone()[0]

            curseur.execute(
                """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key, sign_count)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    user_id,
                    b"credential-identique-pytest",
                    b"public-key-identique-pytest",
                    5,
                ),
            )

            curseur.execute(
                """
                UPDATE webauthn_credentials
                SET sign_count = %s
                WHERE credential_id = %s
                  AND (sign_count = 0 AND %s = 0
                       OR sign_count < %s)
                RETURNING id
                """,
                (5, b"credential-identique-pytest", 5, 5),
            )

            assert curseur.fetchone() is None

    finally:
        connexion.rollback()
        connexion.close()


