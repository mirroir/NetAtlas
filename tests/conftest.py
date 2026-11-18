import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
PYTHON_DIR = ROOT_DIR / "python"

sys.path.insert(0, str(PYTHON_DIR))

ENV_TEST = ROOT_DIR / ".env.test"

load_dotenv(ENV_TEST, override=True)

os.environ["NETATLAS_ENV"] = "test"

os.environ["FLASK_SECRET_KEY"] = (
    "netatlas-cle-reservee-exclusivement-aux-tests-automatises"
)

import re

import pytest


@pytest.fixture
def csrf_data():
    def obtenir_jeton(client):
        reponse = client.get("/connexion/utilisateur")

        assert reponse.status_code == 200

        correspondance = re.search(
            rb'(?:name="csrf_token"|id="passkey-csrf-token")\s+value="([^"]+)"',
            reponse.data,
        )

        assert correspondance is not None, (
            "Jeton CSRF introuvable dans le formulaire"
        )

        return {
            "csrf_token": correspondance.group(1).decode()
        }

    return obtenir_jeton


@pytest.fixture
def administrateur_iam(monkeypatch):
    """Simule une identité IAM administrateur autorisée."""

    jeton = "a" * 64

    def valider(jeton_recu):
        if jeton_recu != jeton:
            return None

        return {
            "user_id": 2,
            "nom": "AdminNetAtlas",
        }

    def identifier(user_id, role):
        if user_id != 2 or role != "admin":
            return None

        return {
            "user_id": 2,
            "nom": "AdminNetAtlas",
            "role": "admin",
        }

    monkeypatch.setattr(
        "web.app.valider_session_iam",
        valider,
    )
    monkeypatch.setattr(
        "web.app.get_utilisateur_webauthn",
        identifier,
    )

    return jeton
