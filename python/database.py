import os
import re

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

        # Priorité aux correspondances directes.
        mot_exact = rf"\m{re.escape(terme)}\M"
        curseur.execute(
            """
            SELECT DISTINCT
                p.id,
                p.name,
                v.name,
                c.name,
                p.address,
                p.phone,
                p.website,
                1.0 AS score
            FROM places p
            JOIN villes v ON p.ville_id = v.id
            JOIN categories c ON p.category_id = c.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            LEFT JOIN territoires tr ON r.territoire_id = tr.id
            WHERE
                p.name ~* %s
                OR v.name ~* %s
                OR c.name ~* %s
                OR pa.name ~* %s
                OR r.name ~* %s
                OR tr.name ~* %s
                OR EXISTS (
                  SELECT 1
                  FROM place_tags pt
                  JOIN tags t ON t.id = pt.tag_id
                  WHERE pt.place_id = p.id
                  AND t.name ~* %s
                )
                OR EXISTS (
                  SELECT 1
                  FROM place_services ps
                  JOIN services s ON s.id = ps.service_id
                  WHERE ps.place_id = p.id
                   AND s.name ~* %s
               )
            ORDER BY p.name
            LIMIT 20
            """,
           (
               mot_exact,
               mot_exact,
               mot_exact,
               mot_exact,
               mot_exact,
               mot_exact,
               mot_exact,
               mot_exact,
           ),
        )

        resultats_exacts = curseur.fetchall()

        if resultats_exacts:
           curseur.close()
           return resultats_exacts


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
                    CASE
                        WHEN p.name ILIKE %s THEN 0.90
                        WHEN v.name ILIKE %s THEN 0.85
                        WHEN c.name ILIKE %s THEN 0.85
                        ELSE 0.0
                    END,
                    similarity(p.name, %s),
                    similarity(r.name, %s),
                    similarity(tr.name, %s),
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
            LEFT JOIN territoires tr ON r.territoire_id = tr.id
            WHERE
                p.name ILIKE %s
                OR v.name ILIKE %s
                OR c.name ILIKE %s
                OR pa.name ILIKE %s
                OR r.name ILIKE %s
                OR tr.name ILIKE %s
                OR p.description ILIKE %s
                OR similarity(p.name, %s) > 0.30
                OR similarity(r.name, %s) > 0.25
                OR similarity(tr.name, %s) > 0.25
                OR similarity(v.name, %s) > 0.25
                OR similarity(c.name, %s) > 0.30
                OR similarity(pa.name, %s) > 0.25
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
                    # Priorité aux correspondances partielles
                    motif, motif, motif,

                    # Calcul de similarité
                    terme, terme, terme, terme, terme, terme, terme,

                    # Recherche partielle
                    motif, motif, motif, motif, motif, motif, motif,

                    # Recherche approximative
                    terme, terme, terme, terme, terme, terme, terme,

                    # Tags et services
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


def get_pays_par_categorie(categorie):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                pa.id,
                pa.name
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            WHERE LOWER(c.name) = LOWER(%s)
            ORDER BY pa.name
            """,
            (categorie,),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche des pays par catégorie : {erreur}")
        return []

    finally:
        connexion.close()


def get_regions_par_categorie_et_pays(categorie, pays):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                r.id,
                r.name
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            WHERE LOWER(c.name) = LOWER(%s)
              AND LOWER(pa.name) = LOWER(%s)
            ORDER BY r.name
            """,
            (categorie, pays),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(
            "Erreur lors de la recherche des régions "
            f"par catégorie et pays : {erreur}"
        )
        return []

    finally:
        connexion.close()

def get_villes_par_categorie_pays_region(categorie, pays, region):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                v.id,
                v.name
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            WHERE LOWER(c.name) = LOWER(%s)
              AND LOWER(pa.name) = LOWER(%s)
              AND LOWER(r.name) = LOWER(%s)
            ORDER BY v.name
            """,
            (categorie, pays, region),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(
            "Erreur lors de la recherche des villes "
            f"par catégorie, pays et région : {erreur}"
        )
        return []

    finally:
        connexion.close()

def get_lieux_par_categorie_pays_region_ville(categorie, pays, region, ville):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                p.id,
                p.name,
                v.name,
                c.name,
                p.address,
                p.phone,
                p.website
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            WHERE LOWER(c.name) = LOWER(%s)
              AND LOWER(pa.name) = LOWER(%s)
              AND LOWER(r.name) = LOWER(%s)
              AND LOWER(v.name) = LOWER(%s)
            ORDER BY p.name
            """,
            (categorie, pays, region, ville),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(
            "Erreur lors de la recherche des lieux "
            f"par catégorie, pays, région et ville : {erreur}"
        )
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

def normaliser_nom_tag(nom):
    """Normalise un nom de tag pour faciliter les comparaisons."""
    return " ".join(nom.strip().lower().split())


def rechercher_tag_exact(proposed_name, category_id):
    """Recherche un tag existant après normalisation du nom."""
    nom_normalise = normaliser_nom_tag(proposed_name)
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, name
                FROM tags
                WHERE category_id = %s
                  AND lower(regexp_replace(trim(name), '\\s+', ' ', 'g')) = %s
                LIMIT 1;
                """,
                (category_id, nom_normalise),
            )
            return curseur.fetchone()
    finally:
        connexion.close()


def rechercher_tags_similaires(proposed_name, category_id, seuil=0.50):
    """Recherche les tags similaires dans une catégorie donnée."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, name, similarity(name, %s) AS score
                FROM tags
                WHERE category_id = %s
                  AND similarity(name, %s) >= %s
                ORDER BY score DESC, name;
                """,
                (proposed_name, category_id, proposed_name, seuil),
            )
            return curseur.fetchall()
    finally:
        connexion.close()

def analyser_proposition_tag(nom, category_id):
    """Analyse un nom de tag avant une éventuelle proposition."""

    nom_normalise = normaliser_nom_tag(nom)

    tag_exact = rechercher_tag_exact(nom_normalise, category_id)

    if tag_exact:
        return {
            "statut": "existant",
            "tag": tag_exact,
            "similaires": [],
        }

    tags_similaires = rechercher_tags_similaires(
        nom_normalise,
        category_id,
    )

    if tags_similaires:
        return {
            "statut": "similaire",
            "tag": None,
            "similaires": tags_similaires,
        }

    return {
        "statut": "nouveau",
        "tag": None,
        "similaires": [],
    }


def rechercher_tag_proposal_pending(
    place_id,
    user_id,
    proposed_name,
    category_id,
):
    """Recherche une proposition identique déjà en attente."""
    nom_normalise = normaliser_nom_tag(proposed_name)
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id, proposed_name
                FROM tag_proposals
                WHERE place_id = %s
                  AND user_id = %s
                  AND category_id = %s
                  AND status = 'pending'
                  AND lower(
                      regexp_replace(trim(proposed_name), '\\s+', ' ', 'g')
                  ) = %s
                LIMIT 1;
                """,
                (
                    place_id,
                    user_id,
                    category_id,
                    nom_normalise,
                ),
            )
            return curseur.fetchone()
    finally:
        connexion.close()


def creer_tag_proposal(place_id, user_id, proposed_name, category_id):
    """Enregistre une proposition de tag en attente de modération."""
    proposition_existante = rechercher_tag_proposal_pending(
       place_id,
       user_id,
       proposed_name,
       category_id,
    ) 

    if proposition_existante:
       return proposition_existante[0]

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO tag_proposals (
                    place_id,
                    user_id,
                    proposed_name,
                    category_id
                )
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (place_id, user_id, proposed_name.strip(), category_id),
            )
            proposal_id = curseur.fetchone()[0]

        connexion.commit()
        return proposal_id
    finally:
        connexion.close()

def get_tag_proposals_pending():
    """Retourne les propositions de tags en attente de modération."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    tp.id,
                    tp.proposed_name,
                    tp.place_id,
                    tp.user_id,
                    tp.category_id,
                    tp.created_at
                FROM tag_proposals AS tp
                WHERE tp.status = 'pending'
                ORDER BY tp.created_at, tp.id;
                """
            )
            return curseur.fetchall()
    finally:
        connexion.close()

def rejeter_tag_proposal(proposal_id, moderator_id):
    """Refuse une proposition de tag en attente de modération."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE tag_proposals
                SET status = 'rejected',
                    moderated_by = %s,
                    moderated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'pending'
                RETURNING id;
                """,
                (moderator_id, proposal_id),
            )

            resultat = curseur.fetchone()

        connexion.commit()

        return resultat is not None
    finally:
        connexion.close()


def creer_tag(name, category_id):
    """Crée un nouveau tag et retourne son identifiant."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO tags (name, category_id)
                VALUES (%s, %s)
                RETURNING id;
                """,
                (name, category_id),
            )

            tag_id = curseur.fetchone()[0]

        connexion.commit()
        return tag_id
    finally:
        connexion.close()

def get_tag_proposal(proposal_id):
    """Retourne une proposition de tag à partir de son identifiant."""
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    id,
                    place_id,
                    user_id,
                    proposed_name,
                    category_id,
                    status
                FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )

            return curseur.fetchone()
    finally:
        connexion.close()


def obtenir_ou_creer_tag(name, category_id):
    """Retourne un tag existant ou crée un nouveau tag."""
    tag_existant = rechercher_tag_exact(
        name,
        category_id,
    )

    if tag_existant:
        return tag_existant[0]

    return creer_tag(
        name,
        category_id,
    )


def approuver_tag_proposal(proposal_id, moderator_id):
    """Approuve une proposition et associe le tag au lieu."""
    proposition = get_tag_proposal(proposal_id)

    if proposition is None:
        return False

    place_id = proposition[1]
    proposed_name = proposition[3]
    category_id = proposition[4]
    status = proposition[5]

    if status != "pending":
        return False

    tag_id = obtenir_ou_creer_tag(
        proposed_name,
        category_id,
    )

    ajouter_tag_lieu(
        place_id,
        tag_id,
    )

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE tag_proposals
                SET status = 'approved',
                    moderated_by = %s,
                    moderated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND status = 'pending'
                RETURNING id;
                """,
                (moderator_id, proposal_id),
            )

            resultat = curseur.fetchone()

        connexion.commit()

        return resultat is not None
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


def get_contexte_recherche(terme):
    connexion = connexion_db()

    contexte = {
        "pays": [],
        "regions": [],
        "villes": [],
        "categories": [],
        "lieux": [],
    }

    try:
        curseur = connexion.cursor()

        motif = f"%{terme}%"

        # Pays liés au terme recherché, quel que soit son point d'entrée :
        # pays, région, ville, catégorie ou lieu.
        curseur.execute(
            """
            SELECT DISTINCT
                pa.id,
                pa.name
            FROM pays pa
            LEFT JOIN regions r
                ON r.country_id = pa.id
            LEFT JOIN villes v
                ON v.region_id = r.id
            LEFT JOIN places p
                ON p.ville_id = v.id
            LEFT JOIN categories c
                ON p.category_id = c.id
            WHERE pa.name ILIKE %s
               OR r.name ILIKE %s
               OR v.name ILIKE %s
               OR c.name ILIKE %s
               OR p.name ILIKE %s
            ORDER BY pa.name
            """,
            (motif, motif, motif, motif, motif),
        )
        contexte["pays"] = curseur.fetchall()

        # Régions appartenant uniquement aux branches géographiques
        # concernées par le terme recherché.
        curseur.execute(
            """
            SELECT DISTINCT
                r.id,
                r.name
            FROM regions r
            JOIN pays pa
                ON r.country_id = pa.id
            LEFT JOIN villes v
                ON v.region_id = r.id
            LEFT JOIN places p
                ON p.ville_id = v.id
            LEFT JOIN categories c
                ON p.category_id = c.id
            WHERE pa.name ILIKE %s
               OR r.name ILIKE %s
               OR v.name ILIKE %s
               OR c.name ILIKE %s
               OR p.name ILIKE %s
            ORDER BY r.name
            """,
            (motif, motif, motif, motif, motif),
        )
        contexte["regions"] = curseur.fetchall()

        # Villes reliées au terme.
        curseur.execute(
            """
            SELECT DISTINCT
                v.id,
                v.name
            FROM villes v
            JOIN regions r
                ON v.region_id = r.id
            JOIN pays pa
                ON r.country_id = pa.id
            LEFT JOIN places p
                ON p.ville_id = v.id
            LEFT JOIN categories c
                ON p.category_id = c.id
            WHERE pa.name ILIKE %s
               OR r.name ILIKE %s
               OR v.name ILIKE %s
               OR c.name ILIKE %s
               OR p.name ILIKE %s
            ORDER BY v.name
            """,
            (motif, motif, motif, motif, motif),
        )
        contexte["villes"] = curseur.fetchall()

        # Catégories reliées au terme.
        curseur.execute(
            """
            SELECT DISTINCT
                c.id,
                c.name
            FROM categories c
            JOIN places p
                ON p.category_id = c.id
            JOIN villes v
                ON p.ville_id = v.id
            JOIN regions r
                ON v.region_id = r.id
            JOIN pays pa
                ON r.country_id = pa.id
            WHERE pa.name ILIKE %s
               OR r.name ILIKE %s
               OR v.name ILIKE %s
               OR c.name ILIKE %s
               OR p.name ILIKE %s
            ORDER BY c.name
            """,
            (motif, motif, motif, motif, motif),
        )
        contexte["categories"] = curseur.fetchall()

        # Lieux reliés au terme.
        curseur.execute(
            """
            SELECT DISTINCT
                p.id,
                p.name
            FROM places p
            JOIN categories c
                ON p.category_id = c.id
            JOIN villes v
                ON p.ville_id = v.id
            JOIN regions r
                ON v.region_id = r.id
            JOIN pays pa
                ON r.country_id = pa.id
            WHERE pa.name ILIKE %s
               OR r.name ILIKE %s
               OR v.name ILIKE %s
               OR c.name ILIKE %s
               OR p.name ILIKE %s
            ORDER BY p.name
            """,
            (motif, motif, motif, motif, motif),
        )
        contexte["lieux"] = curseur.fetchall()

        curseur.close()
        return contexte

    except psycopg.Error as erreur:
        print(f"Erreur lors de la recherche du contexte : {erreur}")
        return contexte

    finally:
        connexion.close()

def get_territoires_par_categorie_et_pays(categorie, pays):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                tr.id,
                tr.name
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            JOIN territoires tr ON r.territoire_id = tr.id
            WHERE LOWER(c.name) = LOWER(%s)
              AND LOWER(pa.name) = LOWER(%s)
            ORDER BY tr.name
            """,
            (categorie, pays),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(
            "Erreur lors de la recherche des territoires "
            f"par catégorie et pays : {erreur}"
        )
        return []

    finally:
        connexion.close()

def get_villes_par_categorie_pays_territoire(
    categorie,
    pays,
    territoire,
):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                v.id,
                v.name
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            JOIN territoires tr ON r.territoire_id = tr.id
            WHERE LOWER(c.name) = LOWER(%s)
              AND LOWER(pa.name) = LOWER(%s)
              AND LOWER(tr.name) = LOWER(%s)
            ORDER BY v.name
            """,
            (categorie, pays, territoire),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(
            "Erreur lors de la recherche des villes "
            f"par catégorie, pays et territoire : {erreur}"
        )
        return []

    finally:
        connexion.close()

def get_lieux_par_categorie_pays_territoire_ville(
    categorie,
    pays,
    territoire,
    ville,
):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT DISTINCT
                p.id,
                p.name
            FROM places p
            JOIN categories c ON p.category_id = c.id
            JOIN villes v ON p.ville_id = v.id
            JOIN regions r ON v.region_id = r.id
            JOIN pays pa ON r.country_id = pa.id
            JOIN territoires tr ON r.territoire_id = tr.id
            WHERE LOWER(c.name) = LOWER(%s)
              AND LOWER(pa.name) = LOWER(%s)
              AND LOWER(tr.name) = LOWER(%s)
              AND LOWER(v.name) = LOWER(%s)
            ORDER BY p.name
            """,
            (categorie, pays, territoire, ville),
        )

        resultats = curseur.fetchall()
        curseur.close()

        return resultats

    except psycopg.Error as erreur:
        print(
            "Erreur lors de la recherche des lieux "
            f"par catégorie, pays, territoire et ville : {erreur}"
        )
        return []

    finally:
        connexion.close()


def enregistrer_credential_webauthn(
    user_id,
    credential_id,
    public_key,
    sign_count=0,
):
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key, sign_count)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    credential_id,
                    public_key,
                    sign_count,
                ),
            )

            nouvel_id = curseur.fetchone()[0]

        connexion.commit()
        return nouvel_id

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()



def get_credential_webauthn(credential_id):
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT
                    id,
                    user_id,
                    credential_id,
                    public_key,
                    sign_count
                FROM webauthn_credentials
                WHERE credential_id = %s
                """,
                (credential_id,),
            )

            resultat = curseur.fetchone()

            if resultat is None:
                return None

            return {
                "id": resultat[0],
                "user_id": resultat[1],
                "credential_id": resultat[2],
                "public_key": resultat[3],
                "sign_count": resultat[4],
            }

    finally:
        connexion.close()



def mettre_a_jour_compteur_webauthn(
    credential_id,
    sign_count,
):
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE webauthn_credentials
                SET sign_count = %s
                WHERE credential_id = %s
                  AND (
                      (sign_count = 0 AND %s = 0)
                      OR sign_count < %s
                  )
                RETURNING id
                """,
                (sign_count, credential_id, sign_count, sign_count),
            )
            resultat = curseur.fetchone()

        if resultat is None:
            connexion.rollback()
            return False

        connexion.commit()
        return True

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


def enregistrer_challenge_webauthn(
    challenge_hash,
    session_binding_hash,
    operation,
    user_id=None,
    duree_secondes=60,
):
    """Enregistre un challenge WebAuthn temporaire."""

    if not isinstance(challenge_hash, bytes) or len(challenge_hash) != 32:
        raise ValueError("Empreinte du challenge invalide.")

    if (
        not isinstance(session_binding_hash, bytes)
        or len(session_binding_hash) != 32
    ):
        raise ValueError("Empreinte de tentative invalide.")

    if operation not in ("registration", "authentication"):
        raise ValueError("Opération WebAuthn invalide.")

    if operation == "registration" and user_id is None:
        raise ValueError("Utilisateur obligatoire pour l'enregistrement.")

    if not isinstance(duree_secondes, int) or not 1 <= duree_secondes <= 300:
        raise ValueError("Durée du challenge invalide.")

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                INSERT INTO webauthn_challenges (
                    challenge_hash,
                    session_binding_hash,
                    user_id,
                    operation,
                    expires_at
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    CURRENT_TIMESTAMP + (%s * INTERVAL '1 second')
                )
                RETURNING id
                """,
                (
                    challenge_hash,
                    session_binding_hash,
                    user_id,
                    operation,
                    duree_secondes,
                ),
            )

            nouvel_id = curseur.fetchone()[0]

        connexion.commit()
        return nouvel_id

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()

def consommer_challenge_webauthn(
    challenge_hash,
    session_binding_hash,
    operation,
    user_id=None,
):
    """Consomme une seule fois un challenge WebAuthn valide."""

    if not isinstance(challenge_hash, bytes) or len(challenge_hash) != 32:
        raise ValueError("Empreinte du challenge invalide.")

    if (
        not isinstance(session_binding_hash, bytes)
        or len(session_binding_hash) != 32
    ):
        raise ValueError("Empreinte de tentative invalide.")

    if operation not in ("registration", "authentication"):
        raise ValueError("Opération WebAuthn invalide.")

    if operation == "registration" and user_id is None:
        raise ValueError("Utilisateur obligatoire pour l'enregistrement.")

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE webauthn_challenges
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE challenge_hash = %s
                  AND session_binding_hash = %s
                  AND operation = %s
                  AND user_id IS NOT DISTINCT FROM %s
                  AND expires_at > CURRENT_TIMESTAMP
                  AND consumed_at IS NULL
                RETURNING id
                """,
                (
                    challenge_hash,
                    session_binding_hash,
                    operation,
                    user_id,
                ),
            )

            resultat = curseur.fetchone()

        if resultat is None:
            connexion.rollback()
            return False

        connexion.commit()
        return True

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()

def finaliser_enregistrement_webauthn(
    challenge_hash,
    session_binding_hash,
    user_id,
    credential_id,
    public_key,
    sign_count=0,
):
    """Consomme un challenge et enregistre une Passkey atomiquement."""

    if not isinstance(challenge_hash, bytes) or len(challenge_hash) != 32:
        raise ValueError("Empreinte du challenge invalide.")

    if (
        not isinstance(session_binding_hash, bytes)
        or len(session_binding_hash) != 32
    ):
        raise ValueError("Empreinte de tentative invalide.")

    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Utilisateur invalide.")

    if not isinstance(credential_id, bytes) or not credential_id:
        raise ValueError("Identifiant Passkey invalide.")

    if not isinstance(public_key, bytes) or not public_key:
        raise ValueError("Clé publique invalide.")

    if not isinstance(sign_count, int) or sign_count < 0:
        raise ValueError("Compteur WebAuthn invalide.")

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE webauthn_challenges
                SET consumed_at = CURRENT_TIMESTAMP
                WHERE challenge_hash = %s
                  AND session_binding_hash = %s
                  AND operation = 'registration'
                  AND user_id = %s
                  AND expires_at > CURRENT_TIMESTAMP
                  AND consumed_at IS NULL
                RETURNING id
                """,
                (
                    challenge_hash,
                    session_binding_hash,
                    user_id,
                ),
            )

            if curseur.fetchone() is None:
                connexion.rollback()
                return False

            curseur.execute(
                """
                INSERT INTO webauthn_credentials
                    (user_id, credential_id, public_key, sign_count)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    credential_id,
                    public_key,
                    sign_count,
                ),
            )

            credential_db_id = curseur.fetchone()[0]

        connexion.commit()
        return credential_db_id

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


