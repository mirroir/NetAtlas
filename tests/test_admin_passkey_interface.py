
import sys
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from web.app import app


def test_interface_passkey_administrateur():
    """Vérifie l'interface Passkey avec une session IAM administrateur."""

    jeton = "a" * 64

    with (
        patch(
            "web.app.valider_session_iam",
            return_value={"user_id": 2, "nom": "AdminNetAtlas"},
        ) as valider,
        patch(
            "web.app.get_utilisateur_webauthn",
            return_value={
                "user_id": 2,
                "nom": "AdminNetAtlas",
                "role": "admin",
            },
        ) as identifier,
        app.test_client() as client,
    ):
        client.set_cookie("netatlas_iam", jeton)

        reponse = client.get("/admin")

    assert reponse.status_code == 200

    valider.assert_called_once_with(jeton)
    identifier.assert_called_once_with(2, "admin")

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
