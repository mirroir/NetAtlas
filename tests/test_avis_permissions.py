import os

import psycopg
from dotenv import load_dotenv

load_dotenv(".env.test")


def test_netatlas_user_peut_supprimer_avis():
    connexion = psycopg.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT has_table_privilege(
                    current_user,
                    'public.avis',
                    'DELETE'
                );
                """
            )

            resultat = curseur.fetchone()[0]

        assert resultat is True

    finally:
        connexion.close()



