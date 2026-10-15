import os
import sys
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from psycopg.errors import UniqueViolation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))


from database import (
    ajouter_avis,
    authentifier_utilisateur,
    creer_utilisateur,
    enregistrer_reaction,
    get_avis_by_place,
    get_contexte_recherche,
    get_lieux_par_categorie_pays_territoire_ville,
    get_pays_par_categorie,
    get_place_details,
    get_place_reactions,
    get_place_services,
    get_place_tags,
    get_territoires_par_categorie_et_pays,
    get_user_reaction,
    get_villes_par_categorie_pays_territoire,
    rechercher_global,
)

app = Flask(__name__)

# ============================================================
# SECURITE DES COOKIES DE SESSION
# ============================================================

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# HTTP autorisé uniquement pour le développement local.
# En production, NETATLAS_WEB_HTTPS doit être activé.
app.config["SESSION_COOKIE_SECURE"] = (
    os.getenv("NETATLAS_WEB_HTTPS") == "1"
)

# ============================================================
# GARDE-FOU HTTPS EN PRODUCTION
# ============================================================

web_env = os.getenv("NETATLAS_WEB_ENV", "development")

if web_env not in ("development", "production"):
    raise RuntimeError(
        "SECURITE NETATLAS : environnement Web invalide."
    )

if (
    web_env == "production"
    and not app.config["SESSION_COOKIE_SECURE"]
):
    raise RuntimeError(
        "SECURITE NETATLAS : "
        "HTTPS obligatoire en production."
    )


# Clé secrète chargée depuis l'environnement.
# Aucune valeur de secours codée en dur.
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError(
        "SECURITE NETATLAS : "
        "FLASK_SECRET_KEY est absente de l'environnement."
    )

csrf = CSRFProtect()

app.config["WTF_CSRF_CHECK_DEFAULT"] = True
csrf.init_app(app)

def est_utilisateur_connecte():
    return (
        session.get("user_id") is not None
        and session.get("role") == "utilisateur"
    )


# ============================================================
# ACCUEIL
# ============================================================


@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/acces")
def acces():
    return render_template("acces.html")


# ============================================================
# ACCÈS TEMPORAIRE
# ============================================================


@app.route("/temporaire")
def temporaire():
    return render_template("temporaire.html")


@app.route("/temporaire/consultation")
def consultation_temporaire():
    return redirect(
      url_for(
        "recherche_globale_web",
        origine="temporaire",
      )
    )


# ============================================================
# CRÉATION DE PROFIL
# ============================================================


@app.route("/profil/creer", methods=["GET", "POST"])
def creer_profil():
    message = None
    erreur = None

    if request.method == "POST":
        nom = request.form["nom"]
        pin = request.form["pin"]

        try:
            creer_utilisateur(nom, pin)

        except ValueError as exc:
            erreur = str(exc)

        except UniqueViolation:
            erreur = "Ce nom de profil existe déjà."

        else:
            message = "Profil créé avec succès."

    return render_template(
        "creer_profil.html",
        message=message,
        erreur=erreur,
    )


# ============================================================
# CONNEXION UTILISATEUR
# ============================================================


@app.route("/connexion/utilisateur", methods=["GET", "POST"])
def connexion_utilisateur():
    # Si l'utilisateur est déjà connecté,
    # inutile de lui redemander son nom et son PIN.
    if (
        request.method == "GET"
        and "user_id" in session
        and session.get("role") == "utilisateur"
    ):
        return redirect(url_for("espace_utilisateur"))

    erreur = None

    if request.method == "POST":
        nom = request.form["nom"]
        pin = request.form["pin"]

        utilisateur = authentifier_utilisateur(
            nom,
            pin,
            "utilisateur",
        )

        if utilisateur is None:
            erreur = "Nom de profil ou PIN incorrect."

        else:
            session.clear()

            session["user_id"] = utilisateur["user_id"]
            session["nom"] = utilisateur["nom"]
            session["role"] = utilisateur["role"]

            return redirect(url_for("espace_utilisateur"))

    return render_template(
        "connexion_utilisateur.html",
        erreur=erreur,
    )


# ============================================================
# CONNEXION ADMINISTRATEUR
# ============================================================


@app.route("/connexion/admin", methods=["GET", "POST"])
def connexion_admin():
    if (
        request.method == "GET"
        and session.get("user_id")
        and session.get("role") == "admin"
    ):
        return redirect(url_for("espace_admin"))

    erreur = None

    if request.method == "POST":
        nom = request.form["nom"]
        pin = request.form["pin"]

        administrateur = authentifier_utilisateur(
            nom,
            pin,
            "admin",
        )

        if administrateur is None:
            erreur = "Nom de compte ou PIN incorrect."

        else:
            session.clear()
            session["user_id"] = administrateur["user_id"]
            session["nom"] = administrateur["nom"]
            session["role"] = administrateur["role"]

            return redirect(url_for("espace_admin"))

    return render_template(
        "connexion_admin.html",
        erreur=erreur,
    )


# ============================================================
# ESPACE ADMINISTRATEUR
# ============================================================


@app.route("/admin")
def espace_admin():
    if (
        "user_id" not in session
        or session.get("role") != "admin"
    ):
        return redirect(url_for("connexion_admin"))

    return render_template(
        "espace_admin.html",
        nom=session.get("nom"),
    )


# ============================================================
# ESPACE UTILISATEUR
# ============================================================


@app.route("/utilisateur")
def espace_utilisateur():
    if not est_utilisateur_connecte():
        return redirect(url_for("connexion_utilisateur"))

    return render_template(
        "espace_utilisateur.html",
        nom=session["nom"],
    )

@app.route("/deconnexion")
def deconnexion():
    session.clear()

    return redirect(url_for("accueil"))


# ============================================================
# CONSULTATION UTILISATEUR CONNECTÉ
# ============================================================


@app.route("/utilisateur/consultation")
def consultation_utilisateur():
    if not est_utilisateur_connecte():
        return redirect(url_for("connexion_utilisateur"))

    return redirect(
        url_for(
            "recherche_globale_web",
            origine="utilisateur",
        )
    )

@app.route("/recherche/globale/<origine>", methods=["GET", "POST"])
def recherche_globale_web(origine):
    if origine == "utilisateur" and not est_utilisateur_connecte():
        return redirect(url_for("connexion_utilisateur"))

    resultats = []
    resultats_principaux = []
    resultats_secondaires = []

    terme = ""

    contexte = {
        "pays": [],
        "regions": [],
        "villes": [],
        "categories": [],
        "lieux": [],
    }

    pays_categorie = []
    pays_selectionne = ""

    territoires_categorie = []
    territoire_selectionne = ""


    villes_categorie = []
    ville_selectionnee = ""

    lieux_categorie = []

    if request.method == "POST":
        terme = request.form["terme"].strip()

        pays_selectionne = request.form.get(
            "pays",
            "",
        ).strip()

        territoire_selectionne = request.form.get(
            "territoire",
            "",
        ).strip()

        ville_selectionnee = request.form.get(
            "ville",
            "",
        ).strip()
        

        if terme:
            resultats = rechercher_global(terme)
            contexte = get_contexte_recherche(terme)

            pays_categorie = get_pays_par_categorie(terme)

            if pays_selectionne:
                territoires_categorie = (
                    get_territoires_par_categorie_et_pays(
                        terme,
                        pays_selectionne,
                    )
                )

            if pays_selectionne and territoire_selectionne:
                villes_categorie = (
                    get_villes_par_categorie_pays_territoire(
                        terme,
                        pays_selectionne,
                        territoire_selectionne,
                    )
                )

            if (
                pays_selectionne
                and territoire_selectionne
                and ville_selectionnee
            ):
                lieux_categorie = (
                    get_lieux_par_categorie_pays_territoire_ville(
                        terme,
                        pays_selectionne,
                        territoire_selectionne,
                        ville_selectionnee,
                    )
                )


            seuil_affichage = 0.50

            if pays_categorie:
                resultats_principaux = []
                resultats_secondaires = []
            else:
                resultats_principaux = [
                resultat
                for resultat in resultats
                if resultat[7] >= seuil_affichage
            ]

    resultats_secondaires = [
        resultat
        for resultat in resultats
        if resultat[7] < seuil_affichage
    ]



    return render_template(
        "recherche_globale.html",
        resultats=resultats,
        resultats_principaux=resultats_principaux,
        resultats_secondaires=resultats_secondaires,
        terme=terme,
        contexte=contexte,
        pays_contexte=contexte["pays"],
        regions_contexte=contexte["regions"],
        villes_contexte=contexte["villes"],
        categories_contexte=contexte["categories"],
        lieux_contexte=contexte["lieux"],
        pays_categorie=pays_categorie,
        pays_selectionne=pays_selectionne,
        territoires_categorie=territoires_categorie,
        territoire_selectionne=territoire_selectionne,
        villes_categorie=villes_categorie,
        ville_selectionnee=ville_selectionnee,
        lieux_categorie=lieux_categorie,
        origine=origine,
    )


@app.route("/lieu/<int:place_id>/<origine>", methods=["GET", "POST"])
def detail_lieu(place_id, origine):
    source = request.args.get("source")
    if origine == "utilisateur" and not est_utilisateur_connecte():
        return redirect(url_for("connexion_utilisateur"))

    erreur_commentaire = None

    lieu = get_place_details(place_id)

    if lieu is None:
        return redirect(
            url_for(
                "recherche_globale_web",
                origine=origine,
            )
        )

    if request.method == "POST":
        if origine != "utilisateur" or not est_utilisateur_connecte():
            return redirect(url_for("connexion_utilisateur"))

        action = request.form.get("action")

        if action == "commentaire":
            commentaire = request.form.get("commentaire", "")

            try:
                ajouter_avis(
                    place_id,
                    session["user_id"],
                    commentaire,
                )
            except ValueError as exc:
                erreur_commentaire = str(exc)
            else:
                return redirect(
                    url_for(
                        "detail_lieu",
                        place_id=place_id,
                        origine=origine,
                    )
                )

    tags = get_place_tags(place_id)
    services = get_place_services(place_id)
    avis = get_avis_by_place(place_id)


    reactions = get_place_reactions(place_id)

    reaction_utilisateur = None

    if origine == "utilisateur" and session.get("user_id"):
       reaction_utilisateur = get_user_reaction(
         place_id,
         session["user_id"],
       )


    return render_template(
        "detail_lieu.html",
        lieu=lieu,
        tags=tags,
        services=services,
        avis=avis,
        origine=origine,
        erreur_commentaire=erreur_commentaire,
        reactions=reactions,
        reaction_utilisateur=reaction_utilisateur,
        place_id=place_id,
        source=source,
    )

@app.post("/lieu/<int:place_id>/reaction")
def reaction_lieu(place_id):
    source = request.form.get("source")

    if not est_utilisateur_connecte():
        return redirect(url_for("connexion_utilisateur"))

    user_id = session["user_id"]

    reaction = request.form.get("reaction", type=int)

    enregistrer_reaction(
        place_id,
        user_id,
        reaction,
    )

    return redirect(
        url_for(
            "detail_lieu",
            place_id=place_id,
            origine="utilisateur",
            source=source,
        )
    )


# ============================================================
# LANCEMENT LOCAL
# ============================================================


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
