import pathlib
import sys

sys.path.append(str(pathlib.Path(__file__).resolve().parents[1] / "python"))

import database


def obtenir_tables(tables_demandees):
    connexion = database.connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY(%s)
            ORDER BY table_name;
            """,
            (tables_demandees,),
        )

        return [ligne[0] for ligne in curseur.fetchall()]

    finally:
        connexion.close()



def test_tables_services_existent():
    tables = obtenir_tables(["services", "place_services"])

    assert tables == ["place_services", "services"]

def test_tables_tags_existent():
    tables = obtenir_tables(["tags", "place_tags"])

    assert tables == ["place_tags", "tags"]


def obtenir_cle_primaire(table):
    connexion = database.connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.table_name = %s
              AND tc.constraint_type = 'PRIMARY KEY'
            ORDER BY kcu.ordinal_position;
            """,
            (table,),
        )

        return [ligne[0] for ligne in curseur.fetchall()]

    finally:
        connexion.close()



def test_place_services_cle_primaire_composite():
    colonnes = obtenir_cle_primaire("place_services")

    assert colonnes == ["place_id", "service_id"]

def test_place_tags_cle_primaire_composite():
    colonnes = obtenir_cle_primaire("place_tags")

    assert colonnes == ["place_id", "tag_id"]

def obtenir_cles_etrangeres(table):
    connexion = database.connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT
                a.attname AS colonne,
                confrelid::regclass::text AS table_referencee,
                af.attname AS colonne_referencee,
                CASE confdeltype
                    WHEN 'c' THEN 'CASCADE'
                    WHEN 'r' THEN 'RESTRICT'
                    WHEN 'n' THEN 'SET NULL'
                    WHEN 'd' THEN 'SET DEFAULT'
                    WHEN 'a' THEN 'NO ACTION'
                END AS delete_rule
            FROM pg_constraint c
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid
             AND a.attnum = c.conkey[1]
            JOIN pg_attribute af
              ON af.attrelid = c.confrelid
             AND af.attnum = c.confkey[1]
            WHERE c.contype = 'f'
              AND c.conrelid = %s::regclass
            ORDER BY a.attname;
            """,
            (table,),
        )

        return curseur.fetchall()

    finally:
        connexion.close()



def test_place_services_cles_etrangeres_cascade():
    contraintes = obtenir_cles_etrangeres("place_services")

    assert contraintes == [
        ("place_id", "places", "id", "CASCADE"),
        ("service_id", "services", "id", "CASCADE"),
    ]




def test_place_tags_cles_etrangeres_cascade():
    contraintes = obtenir_cles_etrangeres("place_tags")

    assert contraintes == [
        ("place_id", "places", "id", "CASCADE"),
        ("tag_id", "tags", "id", "CASCADE"),
    ]



