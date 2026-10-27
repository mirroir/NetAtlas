"""Tests PostgreSQL du limiteur de tentatives Passkey."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

import psycopg
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "python"))

from unittest.mock import patch

from database import verifier_limite_tentatives_passkey


@pytest.fixture
def cle_limitation():
    """Fournit une clé unique pour isoler chaque test."""

    return uuid4().bytes + uuid4().bytes


@pytest.fixture
def connexion_test():
    """Ouvre exclusivement une connexion à netatlas_test."""

    if os.getenv("NETATLAS_ENV") != "test":
        pytest.fail("NETATLAS_ENV=test obligatoire.")

    if os.getenv("DB_NAME") != "netatlas_test":
        pytest.fail("Base netatlas_test obligatoire.")

    connexion = psycopg.connect(
        dbname="netatlas_test",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

    yield connexion

    connexion.close()


def test_premiere_tentative_autorisee(cle_limitation):
    """La première requête doit être acceptée."""

    autorisee, attente = verifier_limite_tentatives_passkey(
        cle_limitation,
        limite=3,
    )

    assert autorisee is True
    assert attente == 0


def test_depassement_limite(cle_limitation):
    """La quatrième tentative doit être refusée."""

    resultats = [
        verifier_limite_tentatives_passkey(
            cle_limitation,
            limite=3,
        )
        for _ in range(4)
    ]

    assert [resultat[0] for resultat in resultats] == [
        True,
        True,
        True,
        False,
    ]

    assert resultats[-1][1] > 0


def test_reinitialisation_fenetre(cle_limitation, connexion_test):
    """Une fenêtre expirée doit réinitialiser le compteur."""

    verifier_limite_tentatives_passkey(
        cle_limitation,
        limite=1,
    )

    with connexion_test.cursor() as curseur:
        curseur.execute(
            """
            UPDATE public.passkey_rate_limits
            SET window_started_at =
                CURRENT_TIMESTAMP - INTERVAL '10 minutes'
            WHERE key_hash = %s
            """,
            (cle_limitation,),
        )

    connexion_test.commit()

    autorisee, attente = verifier_limite_tentatives_passkey(
        cle_limitation,
        limite=1,
    )

    assert autorisee is True
    assert attente == 0


@pytest.mark.parametrize(
    ("cle", "limite", "fenetre"),
    [
        (b"incorrect", 3, 300),
        (b"x" * 32, 0, 300),
        (b"x" * 32, True, 300),
        (b"x" * 32, 3, 0),
        (b"x" * 32, 3, 3601),
    ],
)
def test_parametres_invalides(cle, limite, fenetre):
    """Les paramètres invalides doivent être rejetés."""

    with pytest.raises(ValueError):
        verifier_limite_tentatives_passkey(
            cle,
            limite,
            fenetre,
        )


def test_tentatives_concurrentes(cle_limitation, connexion_test):
    """Les requêtes simultanées ne doivent pas contourner le seuil."""

    with ThreadPoolExecutor(max_workers=5) as executant:
        resultats = list(
            executant.map(
                lambda _: verifier_limite_tentatives_passkey(
                    cle_limitation,
                    limite=3,
                ),
                range(5),
            )
        )

    assert sum(autorisee for autorisee, _ in resultats) == 3

    with connexion_test.cursor() as curseur:
        curseur.execute(
            """
            SELECT attempts
            FROM public.passkey_rate_limits
            WHERE key_hash = %s
            """,
            (cle_limitation,),
        )

        compteur = curseur.fetchone()[0]

    assert compteur == 5

def test_erreur_sql_limiteur_individuel(cle_limitation):
    """Une erreur SQL provoque un rollback et remonte l'exception."""

    class ConnexionErreur:
        def __init__(self):
            self.rollback_effectue = False
            self.fermeture_effectuee = False

        def cursor(self):
            raise RuntimeError("Erreur PostgreSQL simulée")

        def rollback(self):
            self.rollback_effectue = True

        def close(self):
            self.fermeture_effectuee = True

    connexion = ConnexionErreur()

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(RuntimeError, match="Erreur PostgreSQL simulée"),
    ):
        verifier_limite_tentatives_passkey(
            cle_limitation,
            limite=3,
        )

    assert connexion.rollback_effectue is True
    assert connexion.fermeture_effectuee is True
