import os

import psycopg
from dotenv import load_dotenv

load_dotenv("/home/dymoon/lab/NetAtlas/config/.env")

def connexion_db():
    environnement = os.getenv("NETATLAS_ENV")
    nom_base = os.getenv("DB_NAME")

    # Garde-fou de sécurité pour les tests
    if environnement == "test" and nom_base != "netatlas_test":
        raise RuntimeError(
            "SECURITE NETATLAS : "
            "en mode TEST, seule la base netatlas_test est autorisee."
        )

    connexion = psycopg.connect(
        dbname=nom_base,
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT")
    )

    return connexion



def get_categories():
    connexion = connexion_db()
    
    try:
        curseur = connexion.cursor()

        curseur.execute("""
          SELECT id, name, description
          FROM categories
          ORDER BY id;
        """)
        
        categories = curseur.fetchall()
        curseur.close()

        return categories

    finally:
        connexion.close()

#===========================================================#
#                                                           #
#              *                             *              #
#               *  Récupération des villes  *               #
#              *                             *              #
#===========================================================#

def get_villes():
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute("""
          SELECT
           v.id,
           v.name,
           r.name,
           p.name,
           v.latitude,
           v.longitude,
           v.population
         FROM villes v
         JOIN regions r ON v.region_id = r.id
         JOIN pays p ON r.country_id = p.id
         ORDER BY v.name;
        """)

        villes = curseur.fetchall()
        curseur.close()

        return villes

    finally:
        connexion.close()


# ==========================================
#       Recherche d'une ville
# ==========================================


def rechercher_ville(nom_ville):
    nom_ville = nom_ville.strip()

    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute("""
            SELECT
                v.id,
                v.name,
                r.name,
                p.name,
                v.latitude,
                v.longitude,
                v.population
            FROM villes v
            JOIN regions r ON v.region_id = r.id
            JOIN pays p ON r.country_id = p.id
            WHERE v.name ILIKE %s
            ORDER BY v.name;
        """, (f"%{nom_ville}%",))

        villes = curseur.fetchall()

        curseur.close()

        return villes

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche de la ville : {erreur}")
        return []

    finally:
        connexion.close()


#============================================================#
#                                                            #
#                *                         *                 #
#                 * Récupération des pays *                  # 
#                *                         *                 #
#============================================================#


def get_pays():
    connexion = connexion_db()

    try:
        cursor = connexion.cursor()

        cursor.execute("""
            SELECT id, name, iso2, iso3, continent,
              capital, currency, language, population
            FROM pays
            ORDER BY name;
        """)

        pays = cursor.fetchall()

        cursor.close()

        return pays

    except psycopg.Error as erreur:
        print(f"Erreur lors de la récupération des pays : {erreur}")
        return []

    finally:
        connexion.close()


def rechercher_lieux_par_ville(nom_ville):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute("""
            SELECT
                v.name,
                c.name,
                p.name,
                p.address,
                p.phone,
                p.website
            FROM places p
            JOIN villes v ON p.ville_id = v.id
            JOIN categories c ON p.category_id = c.id
            WHERE v.name ILIKE %s
            ORDER BY c.name, p.name;
        """, (f"%{nom_ville}%",))

        lieux = curseur.fetchall()
        curseur.close()

        return lieux

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche des lieux : {erreur}")
        return []

    finally:
        connexion.close()

def suggerer_villes(recherche):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        requete = """
            SELECT name, similarity(name, %s) AS score
            FROM villes
            WHERE similarity(name, %s) > 0.40
            ORDER BY score DESC
            LIMIT 3;
        """

        curseur.execute(requete, (recherche, recherche))
        suggestions = curseur.fetchall()

        return suggestions

    finally:
        connexion.close()



def rechercher_global(terme):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        requete = """
            SELECT
                p.name,
                v.name,
                c.name,
                p.address,
                p.phone,
                p.website,
                GREATEST(
                  similarity(p.name, %s),
                  similarity(v.name, %s),
                  similarity(c.name, %s)
               ) AS score   
            FROM places p
            JOIN villes v ON p.ville_id = v.id
            JOIN categories c ON p.category_id = c.id
            WHERE
                p.name ILIKE %s
                OR v.name ILIKE %s
                OR c.name ILIKE %s
                OR similarity(p.name, %s) > 0.30
                OR similarity(v.name, %s) > 0.30
                OR similarity(c.name, %s) > 0.30 
                ORDER BY score DESC, p.name
                LIMIT 20;
        """
        motif = f"%{terme}%"

        curseur.execute(
                requete,
                (
                    terme, terme, terme,
                    motif, motif, motif,
                    terme, terme, terme
                )
             )        

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche globale : {erreur}")
        return []

    finally:
        connexion.close()


