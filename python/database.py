import os

import psycopg
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from dotenv import load_dotenv

password_hasher = PasswordHasher()

load_dotenv("/home/dymoon/lab/NetAtlas/config/.env")


def hash_pin(pin):
    return password_hasher.hash(pin)

def valider_pin(pin):
    return pin.isdigit() and 4 <= len(pin) <= 6

def verifier_pin(pin, pin_hash):
    try:
        return password_hasher.verify(pin_hash, pin)
    except VerifyMismatchError:
        return False

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


def creer_utilisateur(nom, pin, role_nom="utilisateur"):
    if not nom.strip():
        raise ValueError("Le nom de profil ne peut pas être vide.")

    if not valider_pin(pin):
        raise ValueError("Le PIN doit contenir entre 4 et 6 chiffres.")

    pin_hash = hash_pin(pin)
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO users (nom, pin_hash)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (nom.strip(), pin_hash),
            )

            user_id = curseur.fetchone()[0]

            curseur.execute(
                """
                INSERT INTO role_user (user_id, role_id)
                SELECT %s, id
                FROM roles
                WHERE nom = %s;
                """,
                (user_id, role_nom),
            )

        connexion.commit()
        return user_id

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def authentifier_utilisateur(nom, pin, role_nom):
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT u.id, u.nom, u.pin_hash
                FROM users u
                JOIN role_user ru ON ru.user_id = u.id
                JOIN roles r ON r.id = ru.role_id
                WHERE u.nom = %s
                  AND r.nom = %s;
                """,
                (nom.strip(), role_nom),
            )

            resultat = curseur.fetchone()

        if resultat is None:
            return None

        user_id, nom_utilisateur, pin_hash = resultat

        if not verifier_pin(pin, pin_hash):
            return None

        return {
            "user_id": user_id,
            "nom": nom_utilisateur,
            "role": role_nom,
        }

    finally:
        connexion.close()


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


def rechercher_pays_ou_ville(terme):
    """Recherche un pays ou une ville."""
    terme = terme.strip()

    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT
                'ville' AS type_resultat,
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

            UNION ALL

            SELECT
                'pays' AS type_resultat,
                p.id,
                p.name,
                NULL,
                p.name,
                NULL,
                NULL,
                NULL
            FROM pays p
            WHERE p.name ILIKE %s

            ORDER BY 3;
            """,
            (
                f"%{terme}%",
                f"%{terme}%",
            ),
        )

        resultats = curseur.fetchall()

        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche pays/ville : {erreur}")
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
                p.id,
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
                p.id,
                p.name,
                v.name,
                c.name,
                p.address,
                p.phone,
                p.website,
                GREATEST(
                  similarity(p.name, %s),
                  similarity(v.name, %s),
                  similarity(c.name, %s),
                  similarity(pa.name, %s),
                  similarity(p.description, %s)
               ) AS score   
            FROM places p
            JOIN villes v ON p.ville_id = v.id
            JOIN categories c ON p.category_id = c.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            WHERE
                p.name ILIKE %s
                OR v.name ILIKE %s
                OR c.name ILIKE %s
                OR pa.name ILIKE %s
                OR p.description ILIKE %s
                OR similarity(p.name, %s) > 0.30
                OR similarity(v.name, %s) > 0.30
                OR similarity(c.name, %s) > 0.30
                OR similarity(pa.name, %s) > 0.30
                OR similarity(p.description, %s) > 0.30
                OR EXISTS (
                 SELECT 1
                 FROM place_tags pt
                 JOIN tags t ON t.id = pt.tag_id
                 WHERE pt.place_id = p.id
                  AND (
                   t.name ILIKE %s
                   OR similarity(t.name, %s) > 0.30
                  )
                )
                OR EXISTS (
                 SELECT 1
                 FROM place_services ps
                 JOIN services s ON s.id = ps.service_id
                 WHERE ps.place_id = p.id
                  AND (
                   s.name ILIKE %s
                   OR similarity(s.name, %s) > 0.30
                  )
                )
                ORDER BY score DESC, p.name
                LIMIT 20;
        """
        motif = f"%{terme}%"

        curseur.execute(
                requete,
                (
                    terme, terme, terme, terme, terme,
                    motif, motif, motif, motif, motif,
                    terme, terme, terme, terme, terme,
                    motif, terme, motif, terme,
                ),
             )        

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche globale : {erreur}")
        return []

    finally:
        connexion.close()


def get_place_details(place_id):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        requete = """
            SELECT
                p.id,
                p.name,
                p.description,
                p.address,
                p.latitude,
                p.longitude,
                p.phone,
                p.email,
                p.website,
                p.is_active,
                v.name AS ville,
                c.name AS categorie
            FROM places p
            JOIN villes v ON p.ville_id = v.id
            JOIN categories c ON p.category_id = c.id
            WHERE p.id = %s;
        """

        curseur.execute(requete, (place_id,))
        place = curseur.fetchone()
        curseur.close()

        return place

    except psycopg.Error as erreur:
        print(f"Erreur lors de la récupération du lieu : {erreur}")
        return None

    finally:
        connexion.close()


def get_place_tags(place_id):
    """Retourne les tags associés à un lieu."""
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        requete = """
            SELECT t.name
            FROM place_tags pt
            JOIN tags t ON t.id = pt.tag_id
            WHERE pt.place_id = %s
            ORDER BY t.name;
        """

        curseur.execute(requete, (place_id,))
        tags = curseur.fetchall()
        curseur.close()

        return [tag[0] for tag in tags]

    except psycopg.Error as erreur:
        print(f"Erreur lors de la récupération des tags : {erreur}")
        return []

    finally:
        connexion.close()


def get_place_tags_with_ids(place_id):
    """Retourne les identifiants et noms des tags associés à un lieu."""
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            SELECT t.id, t.name
            FROM tags t
            JOIN place_tags pt ON pt.tag_id = t.id
            WHERE pt.place_id = %s
            ORDER BY t.name;
            """,
            (place_id,),
        )
        return curseur.fetchall()

    finally:
        curseur.close()
        connexion.close()

def get_tags_with_ids():
    """Retourne la liste des tags avec leur identifiant et leur nom."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, name
                FROM tags
                ORDER BY name;
                """
            )
            return curseur.fetchall()
    finally:
        connexion.close()


def get_tags_by_category(category_id):
    """Retourne les tags appartenant à une catégorie donnée."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, name
                FROM tags
                WHERE category_id = %s
                ORDER BY name;
                """,
                (category_id,),
            )
            return curseur.fetchall()
    finally:
        connexion.close()



def get_places_with_ids():
    """Retourne la liste des lieux avec leur identifiant et leur nom."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, name
                FROM places
                ORDER BY name;
                """
            )
            return curseur.fetchall()
    finally:
        connexion.close()


def get_place_category_id(place_id):
    """Retourne l'identifiant de catégorie d'un lieu."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT category_id
                FROM places
                WHERE id = %s;
                """,
                (place_id,),
            )
            resultat = curseur.fetchone()
            return resultat[0] if resultat else None
    finally:
        connexion.close()



def ajouter_tag_lieu(place_id, tag_id):
    """Associe un tag existant à un lieu."""

    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            INSERT INTO place_tags (place_id, tag_id)
            VALUES (%s, %s)
            ON CONFLICT (place_id, tag_id) DO NOTHING
            """,
            (place_id, tag_id),
        )

        ajoute = curseur.rowcount > 0

        connexion.commit()
        return ajoute

    except Exception:
        connexion.rollback()
        raise

    finally:
        curseur.close()
        connexion.close()


def supprimer_tag_lieu(place_id, tag_id):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            DELETE FROM place_tags
            WHERE place_id = %s AND tag_id = %s
            """,
            (place_id, tag_id),
        )

        supprime = curseur.rowcount > 0

        connexion.commit()
        return supprime

    except Exception:
        connexion.rollback()
        raise

    finally:
        curseur.close()
        connexion.close()



def get_place_services(place_id):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        requete = """
            SELECT s.name
            FROM services s
            JOIN place_services ps ON ps.service_id = s.id
            WHERE ps.place_id = %s
            ORDER BY s.id;
        """

        curseur.execute(requete, (place_id,))
        resultats = curseur.fetchall()
        curseur.close()

        return [service[0] for service in resultats]

    except psycopg.Error as erreur:
        print(f"Erreur lors de la récupération des services : {erreur}")
        return []

    finally:
        connexion.close()

def ajouter_service_lieu(place_id, service_id):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            INSERT INTO place_services (place_id, service_id)
            VALUES (%s, %s)
            ON CONFLICT (place_id, service_id) DO
            NOTHING
            """,
            (place_id, service_id),
        )

        ajoute = curseur.rowcount > 0

        connexion.commit()
        return ajoute

    except Exception:
        connexion.rollback()
        raise

    finally:
        curseur.close()
        connexion.close()


def supprimer_service_lieu(place_id, service_id):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            DELETE FROM place_services
            WHERE place_id = %s AND service_id = %s
            """,
            (place_id, service_id),
        )

        supprime = curseur.rowcount > 0

        connexion.commit()
        return supprime

    except Exception:
        connexion.rollback()
        raise

    finally:
        curseur.close()
        connexion.close()

def modifier_service_lieu(place_id, ancien_service_id, nouveau_service_id):
    connexion = connexion_db()
    curseur = connexion.cursor()

    try:
        curseur.execute(
            """
            UPDATE place_services
            SET service_id = %s
            WHERE place_id = %s AND service_id = %s
            """,
            (nouveau_service_id, place_id, ancien_service_id),
        )

        modifie = curseur.rowcount > 0

        connexion.commit()
        return modifie

    except Exception:
        connexion.rollback()
        raise

    finally:
        curseur.close()
        connexion.close()

def ajouter_avis(place_id, user_id, commentaire):
    if not commentaire.strip():
        raise ValueError("Le commentaire ne peut pas être vide!")

    if len(commentaire) > 1000:
        raise ValueError("Le commentaire ne peut pas dépasser 1000 caractères!")

    connexion = connexion_db()

    try:
        with connexion.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO avis (place_id, user_id, commentaire)
                VALUES (%s, %s, %s)
                RETURNING id;
                """,
                (place_id, user_id, commentaire),
            )

            avis_id = cursor.fetchone()[0]
            connexion.commit()
            return avis_id

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def get_users():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, nom, email
                FROM users
                ORDER BY nom, id;
                """
            )
            return curseur.fetchall()
    finally:
        connexion.close()

def get_avis_by_place(place_id):
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT a.id, a.commentaire, u.nom
                FROM avis a
                JOIN users u ON u.id = a.user_id
                WHERE a.place_id = %s
                ORDER BY a.id;
                """,
                (place_id,),
            )
            return curseur.fetchall()
    finally:
        connexion.close()


def supprimer_avis(avis_id, user_id):
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM avis
                WHERE id = %s
                  AND user_id = %s;
                """,
                (avis_id, user_id),
            )

            supprime = curseur.rowcount > 0

        connexion.commit()
        return supprime

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def get_avis_by_user(user_id):
    connexion = connexion_db()

    try:
        with connexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT a.id, a.commentaire, p.name
                FROM avis a
                JOIN places p ON p.id = a.place_id
                WHERE a.user_id = %s
                ORDER BY a.id;
                """,
                (user_id,),
            )
            return cursor.fetchall()

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def enregistrer_reaction(place_id, user_id, reaction):
    """Enregistre ou modifie la réaction d'un utilisateur pour un lieu."""

    if reaction not in (-1, 1):
        raise ValueError("La réaction doit être -1 ou 1.")

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO place_reactions (
                    place_id,
                    user_id,
                    reaction
                )
                VALUES (%s, %s, %s)
                ON CONFLICT (place_id, user_id)
                DO UPDATE SET reaction = EXCLUDED.reaction;
                """,
                (place_id, user_id, reaction),
            )

        connexion.commit()

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def get_place_reactions(place_id):
    """Retourne le nombre de likes et de dislikes d'un lieu."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE reaction = 1) AS likes,
                    COUNT(*) FILTER (WHERE reaction = -1) AS dislikes
                FROM place_reactions
                WHERE place_id = %s;
                """,
                (place_id,),
            )

            return curseur.fetchone()
    finally:
        connexion.close()

def get_user_reaction(place_id, user_id):
    """Retourne la réaction d'un utilisateur pour un lieu."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT reaction
                FROM place_reactions
                WHERE place_id = %s
                  AND user_id = %s;
                """,
                (place_id, user_id),
            )

            resultat = curseur.fetchone()

            if resultat is None:
                return None

            return resultat[0]
    finally:
        connexion.close()
