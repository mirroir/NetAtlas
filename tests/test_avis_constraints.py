import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).parent.parent / "python"))

from psycopg.errors import CheckViolation

from database import connexion_db


@pytest.fixture
def user_id_test():
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            SELECT id
            FROM users
            ORDER BY id
            LIMIT 1;
            """
        )
        return curseur.fetchone()[0]
    finally:
        curseur.close()
        connexion.close()


def test_commentaire_vide_refuse_par_postgresql(user_id_test):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        with pytest.raises(CheckViolation):
            curseur.execute(
                """
                INSERT INTO avis (place_id, user_id, commentaire)
                VALUES (%s, %s, %s)
                """,
                (1, user_id_test, ""),
            )

        connexion.rollback()
    finally:
        curseur.close()
        connexion.close()


def test_commentaire_espaces_refuse_par_postgresql(user_id_test):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        with pytest.raises(CheckViolation):
            curseur.execute(
                """
                INSERT INTO avis (place_id, user_id, commentaire)
                VALUES (%s, %s, %s)
                """,
                (1, user_id_test, ""),
            )

        connexion.rollback()
    finally:
        curseur.close()
        connexion.close()



def test_commentaire_1000_caracteres_accepte_par_postgresql(user_id_test):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            INSERT INTO avis (place_id, user_id, commentaire)
            VALUES (%s, %s, %s)
            """,
            (1, user_id_test, "a" * 1000),
        )

        connexion.rollback()
    finally:
        curseur.close()
        connexion.close()


def test_commentaire_1001_caracteres_refuse_par_postgresql(user_id_test):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        with pytest.raises(CheckViolation):
            curseur.execute(
                """
                INSERT INTO avis (place_id, user_id, commentaire)
                VALUES (%s, %s, %s)
                """,
                (1, user_id_test, "a" * 1001),
            )

        connexion.rollback()
    finally:
        curseur.close()
        connexion.close()



