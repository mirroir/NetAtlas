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
            rb'name="csrf_token"\s+value="([^"]+)"',
            reponse.data,
        )

        assert correspondance is not None, (
            "Jeton CSRF introuvable dans le formulaire"
        )

        return {
            "csrf_token": correspondance.group(1).decode()
        }

    return obtenir_jeton

