
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from web.app import app


def test_interface_passkey_administrateur():
    """Vérifie les éléments Passkey dans l'espace administrateur."""
    with app.test_client() as client:
        with client.session_transaction() as session:
            session["user_id"] = 2
            session["nom"] = "AdminNetAtlas"
            session["role"] = "admin"

        reponse = client.get("/admin")

    assert reponse.status_code == 200

    contenu = reponse.get_data(as_text=True)

    assert 'id="enregistrer-passkey"' in contenu
    assert 'id="passkey-csrf-token"' in contenu
    assert 'id="passkey-message"' in contenu
    assert "passkey_admin.js" in contenu


def test_script_passkey_accessible():
    """Vérifie que Flask distribue le fichier JavaScript."""
    with app.test_client() as client:
        reponse = client.get("/static/passkey_admin.js")

    assert reponse.status_code == 200
    assert b"enregistrerPasskey" in reponse.data


def test_script_passkey_web_authn():
    """Vérifie la présence des appels WebAuthn attendus."""
    chemin = ROOT_DIR / "web/static/passkey_admin.js"
    contenu = chemin.read_text(encoding="utf-8")

    assert "navigator.credentials.create" in contenu
    assert "/admin/passkey/enregistrement/options" in contenu
    assert "/admin/passkey/enregistrement/verifier" in contenu
    assert "X-CSRFToken" in contenu


def test_script_passkey_conversion_base64url():
    """Vérifie la présence des conversions binaires WebAuthn."""
    chemin = ROOT_DIR / "web/static/passkey_admin.js"
    contenu = chemin.read_text(encoding="utf-8")

    assert "decoderBase64URL" in contenu
    assert "encoderBase64URL" in contenu


def test_script_passkey_gestion_erreurs():
    """Vérifie les protections élémentaires côté navigateur."""
    chemin = ROOT_DIR / "web/static/passkey_admin.js"
    contenu = chemin.read_text(encoding="utf-8")

    assert "isSecureContext" in contenu
    assert "NotAllowedError" in contenu
    assert "bouton.disabled = true" in contenu
    assert "bouton.disabled = false" in contenu
