import hashlib
import os
import secrets
import sys
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_wtf.csrf import CSRFProtect
from psycopg.errors import UniqueViolation
from webauthn import options_to_json
from webauthn.helpers.exceptions import WebAuthnException

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

import hmac
from functools import wraps

from webauthn_service import (
    generer_options_enregistrement,
    verifier_enregistrement,
)
from werkzeug.middleware.proxy_fix import ProxyFix

from database import (
    ajouter_avis,
    authentifier_utilisateur,
    creer_utilisateur,
    enregistrer_challenge_webauthn,
    enregistrer_reaction,
    finaliser_amorcage_passkey_admin,
    finaliser_enregistrement_webauthn,
    get_admin_passkey_bootstrap,
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
    verifier_amorcage_passkey_admin,
    verifier_limites_combinees_passkey,
)

app = Flask(__name__)

# ============================================================
# REVERSE PROXY CADDY
# ============================================================

# Un seul reverse proxy de confiance devant Flask.
# Flask doit rester accessible uniquement sur 127.0.0.1.
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
)

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
# PASSKEY - PREPARATION ENREGISTREMENT ADMINISTRATEUR
# ============================================================


@app.post("/admin/passkey/enregistrement/options")
def options_enregistrement_passkey_admin():
    """Prépare l'enregistrement d'une Passkey administrateur."""

    if (
        session.get("user_id") is None
        or session.get("role") != "admin"
    ):
        return redirect(url_for("connexion_admin"))

    # Invalider toute ancienne tentative avant d'en préparer une nouvelle.
    session.pop("passkey_registration", None)

    user_id = session["user_id"]
    nom = session["nom"]

    # Générer les options WebAuthn.
    options = generer_options_enregistrement(
        user_id=user_id,
        nom=nom,
    )

    # Créer un identifiant aléatoire pour cette tentative.
    session_binding = secrets.token_bytes(32)

    # Calculer les empreintes conservées dans PostgreSQL.
    challenge_hash = hashlib.sha256(
        options.challenge
    ).digest()

    session_binding_hash = hashlib.sha256(
        session_binding
    ).digest()

    # Enregistrer le challenge avec une expiration de 60 secondes.
    try:
        enregistrer_challenge_webauthn(
            challenge_hash=challenge_hash,
            session_binding_hash=session_binding_hash,
            operation="registration",
            user_id=user_id,
            duree_secondes=60,
        )
    except (RuntimeError, OSError):
        # Ne conserver aucune tentative après un échec PostgreSQL.
        session.pop("passkey_registration", None)

        # Ne jamais exposer les détails internes au navigateur.
        return app.response_class(
            response="Erreur interne lors de la préparation Passkey.",
            status=500,
            mimetype="text/plain",
        )

    # Conserver les données temporaires pour la vérification.
    session["passkey_registration"] = {
        "challenge": options.challenge.hex(),
        "session_binding": session_binding.hex(),
        "user_id": user_id,
    }

    # Transmettre les options au navigateur.
    return app.response_class(
        response=options_to_json(options),
        status=200,
        mimetype="application/json",
    )


# ============================================================
# PASSKEY - FINALISATION ENREGISTREMENT ADMINISTRATEUR
# ============================================================


@app.post("/admin/passkey/enregistrement/verifier")
def verifier_enregistrement_passkey_admin():
    """Vérifie et enregistre une Passkey administrateur."""

    if (
        session.get("user_id") is None
        or session.get("role") != "admin"
    ):
        return redirect(url_for("connexion_admin"))

    tentative = session.pop("passkey_registration", None)

    if not isinstance(tentative, dict):
        return jsonify({"erreur": "Tentative Passkey absente."}), 400

    if tentative.get("user_id") != session["user_id"]:
        return jsonify({"erreur": "Tentative Passkey invalide."}), 400

    credential = request.get_json(silent=True)

    if not isinstance(credential, dict):
        return jsonify({"erreur": "Réponse WebAuthn invalide."}), 400

    try:
        challenge = bytes.fromhex(tentative["challenge"])
        session_binding = bytes.fromhex(tentative["session_binding"])

        if len(challenge) < 16 or len(session_binding) != 32:
            return jsonify({"erreur": "Tentative Passkey invalide."}), 400

        verification = verifier_enregistrement(
            credential=credential,
            challenge_attendu=challenge,
        )

        resultat = finaliser_enregistrement_webauthn(
            challenge_hash=hashlib.sha256(challenge).digest(),
            session_binding_hash=hashlib.sha256(session_binding).digest(),
            user_id=session["user_id"],
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
        )

    except (ValueError, KeyError, TypeError, WebAuthnException):
        return jsonify({"erreur": "Enregistrement Passkey invalide."}), 400

    except UniqueViolation:
        return jsonify({"erreur": "Passkey déjà enregistrée."}), 409

    if resultat is False:
        return jsonify({"erreur": "Challenge expiré ou déjà utilisé."}), 400

    return jsonify({
        "message": "Passkey administrateur enregistrée.",
        "credential_id": resultat,
    }), 201


# ============================================================
# PASSKEY - AMORCAGE INITIAL ADMINISTRATEUR
# ============================================================


# ============================================================
# PASSKEY - PROTECTION CONTRE LES TENTATIVES EXCESSIVES
# ============================================================


def limiter_tentatives_passkey(fonction):
    """Protège les routes d'amorçage contre les tentatives excessives."""

    @wraps(fonction)
    def fonction_protegee(*args, **kwargs):
        secret = os.getenv("NETATLAS_RATE_LIMIT_SECRET")

        if not secret or len(secret) != 64:
            app.logger.error(
                "Clé HMAC du limiteur Passkey absente ou invalide."
            )
            return jsonify({
                "erreur": "Service temporairement indisponible."
            }), 503

        try:
            cle_secrete = bytes.fromhex(secret)
        except ValueError:
            app.logger.error("Clé HMAC du limiteur Passkey invalide.")
            return jsonify({
                "erreur": "Service temporairement indisponible."
            }), 503

        adresse_ip = request.remote_addr

        if not adresse_ip:
            return jsonify({
                "erreur": "Adresse réseau indisponible."
            }), 503

        cle_ip = hmac.new(
            cle_secrete,
            b"netatlas:passkey:ip:" + adresse_ip.encode("utf-8"),
            hashlib.sha256,
        ).digest()

        cle_globale = hmac.new(
            cle_secrete,
            b"netatlas:passkey:global",
            hashlib.sha256,
        ).digest()

        try:
            autorisee, attente = verifier_limites_combinees_passkey(
                cle_ip=cle_ip,
                cle_globale=cle_globale,
                limite_ip=10,
                limite_globale=100,
                fenetre_secondes=300,
            )
        except Exception:
            app.logger.exception(
                "Échec du contrôle de limitation Passkey."
            )
            return jsonify({
                "erreur": "Service temporairement indisponible."
            }), 503

        if not autorisee:
            reponse = jsonify({
                "erreur": "Trop de tentatives. Réessayez plus tard."
            })
            reponse.status_code = 429
            reponse.headers["Retry-After"] = str(max(1, attente))
            return reponse

        return fonction(*args, **kwargs)

    return fonction_protegee

@app.after_request
def securiser_reponses_passkey(reponse):
    """Empêche la mise en cache des parcours Passkey sensibles."""

    chemins_proteges = (
        "/admin/passkey/amorcage",
        "/admin/passkey/recuperation",
    )

    if any(
        request.path == chemin
        or request.path.startswith(chemin + "/")
        for chemin in chemins_proteges
    ):
        reponse.headers["Cache-Control"] = "no-store"
        reponse.headers["Pragma"] = "no-cache"

    return reponse

@app.get("/admin/passkey/amorcage")
def page_amorcage_passkey_admin():
    """Affiche la page d'initialisation de la première Passkey."""

    reponse = app.make_response(
        render_template("amorcage_passkey_admin.html")
    )

    reponse.headers["Cache-Control"] = "no-store"
    return reponse

@app.post("/admin/passkey/amorcage/options")
@limiter_tentatives_passkey
def options_amorcage_passkey_admin():
    """Prépare la première Passkey administrateur avec un jeton temporaire."""

    session.pop("passkey_bootstrap_registration", None)

    donnees = request.get_json(silent=True)

    if not isinstance(donnees, dict):
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    jeton = donnees.get("token")

    if not isinstance(jeton, str) or len(jeton) != 64:
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    try:
        token_bytes = bytes.fromhex(jeton)
    except ValueError:
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    token_hash = hashlib.sha256(token_bytes).digest()

    user_id = 2

    if not verifier_amorcage_passkey_admin(user_id, token_hash):
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    administrateur = get_admin_passkey_bootstrap(user_id)

    if administrateur is None:
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    options = generer_options_enregistrement(
        user_id=administrateur["user_id"],
        nom=administrateur["nom"],
    )

    session_binding = secrets.token_bytes(32)

    enregistrer_challenge_webauthn(
        challenge_hash=hashlib.sha256(options.challenge).digest(),
        session_binding_hash=hashlib.sha256(session_binding).digest(),
        operation="registration",
        user_id=user_id,
        duree_secondes=60,
    )

    session["passkey_bootstrap_registration"] = {
        "challenge": options.challenge.hex(),
        "session_binding": session_binding.hex(),
        "token_hash": token_hash.hex(),
        "user_id": user_id,
    }

    return app.response_class(
        response=options_to_json(options),
        status=200,
        mimetype="application/json",
    )


@app.post("/admin/passkey/amorcage/verifier")
@limiter_tentatives_passkey
def verifier_amorcage_passkey_admin_web():
    """Finalise la première Passkey administrateur."""

    tentative = session.pop("passkey_bootstrap_registration", None)

    if not isinstance(tentative, dict):
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    if tentative.get("user_id") != 2:
        return jsonify({"erreur": "Autorisation d'amorçage requise."}), 403

    credential = request.get_json(silent=True)

    if not isinstance(credential, dict):
        return jsonify({"erreur": "Réponse WebAuthn invalide."}), 400

    try:
        challenge = bytes.fromhex(tentative["challenge"])
        session_binding = bytes.fromhex(tentative["session_binding"])
        token_hash = bytes.fromhex(tentative["token_hash"])

        if (
            len(challenge) < 16
            or len(session_binding) != 32
            or len(token_hash) != 32
        ):
            return jsonify({"erreur": "Tentative Passkey invalide."}), 400

        verification = verifier_enregistrement(
            credential=credential,
            challenge_attendu=challenge,
        )

        resultat = finaliser_amorcage_passkey_admin(
            user_id=2,
            token_hash=token_hash,
            challenge_hash=hashlib.sha256(challenge).digest(),
            session_binding_hash=hashlib.sha256(session_binding).digest(),
            credential_id=verification.credential_id,
            public_key=verification.credential_public_key,
            sign_count=verification.sign_count,
        )

    except (ValueError, KeyError, TypeError, WebAuthnException):
        return jsonify({"erreur": "Enregistrement Passkey invalide."}), 400

    except UniqueViolation:
        return jsonify({"erreur": "Passkey déjà enregistrée."}), 409

    if resultat is False:
        return jsonify({"erreur": "Autorisation expirée ou déjà utilisée."}), 403

    return jsonify({
        "message": "Première Passkey administrateur enregistrée.",
        "credential_id": resultat,
    }), 201


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
    app.run(host="127.0.0.1", port=5000)
