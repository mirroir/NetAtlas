import sys
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for
from psycopg.errors import UniqueViolation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))


from database import (
    ajouter_avis,
    authentifier_utilisateur,
    creer_utilisateur,
    enregistrer_reaction,
    get_avis_by_place,
    get_place_details,
    get_place_reactions,
    get_place_services,
    get_place_tags,
    get_user_reaction,
    rechercher_global,
)

app = Flask(__name__)

# Clé provisoire pour le développement local.
# Elle sera placée dans une variable d'environnement avant la mise en ligne.
app.secret_key = "netatlas-dev-secret"


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
            session["user_id"] = utilisateur["user_id"]
            session["nom"] = utilisateur["nom"]
            session["role"] = utilisateur["role"]

            return redirect(url_for("espace_utilisateur"))

    return render_template(
        "connexion_utilisateur.html",
        erreur=erreur,
    )


# ============================================================
# ESPACE UTILISATEUR
# ============================================================


@app.route("/utilisateur")
def espace_utilisateur():
    if "user_id" not in session:
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
    if "user_id" not in session:
        return redirect(url_for("connexion_utilisateur"))

    return redirect(
        url_for(
            "recherche_globale_web",
            origine="utilisateur",
        )
    )

@app.route("/recherche/globale/<origine>", methods=["GET", "POST"])
def recherche_globale_web(origine):
    if origine == "utilisateur" and "user_id" not in session:
        return redirect(url_for("connexion_utilisateur"))

    resultats = []
    terme = ""

    if request.method == "POST":
        terme = request.form["terme"].strip()

        if terme:
            resultats = rechercher_global(terme)

    return render_template(
        "recherche_globale.html",
        resultats=resultats,
        terme=terme,
        origine=origine,
    )



@app.route("/lieu/<int:place_id>/<origine>", methods=["GET", "POST"])
def detail_lieu(place_id, origine):
    source = request.args.get("source")
    if origine == "utilisateur" and "user_id" not in session:
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
        if origine != "utilisateur" or "user_id" not in session:
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
    user_id = session.get("user_id")

    if user_id is None:
        return redirect(url_for("accueil"))

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
