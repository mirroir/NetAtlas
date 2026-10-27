"""Tests PostgreSQL des limites Passkey combinées."""

import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "python"))

from unittest.mock import patch

from database import verifier_limites_combinees_passkey


@pytest.fixture(autouse=True)
def verifier_environnement_test():
    """Interdit toute exécution hors de netatlas_test."""

    if (
        os.getenv("NETATLAS_ENV") != "test"
        or os.getenv("DB_NAME") != "netatlas_test"
    ):
        pytest.fail("Ces tests nécessitent netatlas_test.")


@pytest.fixture
def cles():
    """Génère deux empreintes indépendantes pour chaque test."""

    return os.urandom(32), os.urandom(32)


def test_premiere_tentative_autorisee(cles):
    """La première tentative est autorisée."""

    assert verifier_limites_combinees_passkey(
        *cles,
        limite_ip=3,
        limite_globale=5,
    ) == (True, 0)


def test_depassement_limite_ip(cles):
    """La quatrième tentative dépasse la limite IP."""

    resultats = [
        verifier_limites_combinees_passkey(
            *cles,
            limite_ip=3,
            limite_globale=10,
        )
        for _ in range(4)
    ]

    assert [autorisee for autorisee, _ in resultats] == [
        True,
        True,
        True,
        False,
    ]

    assert resultats[-1][1] > 0


def test_depassement_limite_globale(cles):
    """La quatrième tentative dépasse la limite globale."""

    resultats = [
        verifier_limites_combinees_passkey(
            *cles,
            limite_ip=10,
            limite_globale=3,
        )
        for _ in range(4)
    ]

    assert [autorisee for autorisee, _ in resultats] == [
        True,
        True,
        True,
        False,
    ]

    assert resultats[-1][1] > 0


def test_plusieurs_ip_meme_limite_globale(cles):
    """Plusieurs IP partagent le même compteur global."""

    _, cle_globale = cles

    resultats = [
        verifier_limites_combinees_passkey(
            os.urandom(32),
            cle_globale,
            limite_ip=2,
            limite_globale=3,
        )
        for _ in range(4)
    ]

    assert [autorisee for autorisee, _ in resultats] == [
        True,
        True,
        True,
        False,
    ]


def test_reinitialisation_fenetre(cles):
    """Les compteurs expirés repartent à une tentative."""

    cle_ip, cle_globale = cles

    verifier_limites_combinees_passkey(
        *cles,
        limite_ip=1,
        limite_globale=1,
    )

    connexion = psycopg.connect(
        dbname="netatlas_test",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.passkey_rate_limits
                SET window_started_at =
                    CURRENT_TIMESTAMP - INTERVAL '10 minutes'
                WHERE key_hash IN (%s, %s)
                """,
                (cle_ip, cle_globale),
            )

        connexion.commit()

    finally:
        connexion.close()

    assert verifier_limites_combinees_passkey(
        *cles,
        limite_ip=1,
        limite_globale=1,
    ) == (True, 0)


def test_requetes_concurrentes(cles):
    """La concurrence ne doit pas dépasser les seuils."""

    with ThreadPoolExecutor(max_workers=5) as executant:
        resultats = list(
            executant.map(
                lambda _: verifier_limites_combinees_passkey(
                    *cles,
                    limite_ip=3,
                    limite_globale=10,
                ),
                range(5),
            )
        )

    assert sum(autorisee for autorisee, _ in resultats) == 3

    connexion = psycopg.connect(
        dbname="netatlas_test",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
    )

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT key_hash, attempts
                FROM public.passkey_rate_limits
                WHERE key_hash IN (%s, %s)
                """,
                cles,
            )

            compteurs = dict(curseur.fetchall())

        assert compteurs[cles[0]] == 5
        assert compteurs[cles[1]] == 5

    finally:
        connexion.close()

@pytest.mark.parametrize(
    ("cle_ip", "cle_globale"),
    [
        (b"invalide", b"g" * 32),
        (b"i" * 32, b"invalide"),
        (b"i" * 32, b"i" * 32),
    ],
)
def test_cles_invalides(cle_ip, cle_globale):
    """Les empreintes incorrectes sont refusées."""

    with pytest.raises(ValueError, match="Clés de limitation invalides"):
        verifier_limites_combinees_passkey(cle_ip, cle_globale)


@pytest.mark.parametrize(
    ("limite_ip", "limite_globale"),
    [
        (0, 100),
        (10, 0),
        (True, 100),
        (10, False),
    ],
)
def test_limites_invalides(cles, limite_ip, limite_globale):
    """Les seuils incorrects sont refusés."""

    with pytest.raises(ValueError, match="Limites de tentatives invalides"):
        verifier_limites_combinees_passkey(
            *cles,
            limite_ip=limite_ip,
            limite_globale=limite_globale,
        )


@pytest.mark.parametrize(
    "fenetre",
    [0, 3601, True, "300"],
)
def test_fenetre_invalide(cles, fenetre):
    """Une fenêtre temporelle incorrecte est refusée."""

    with pytest.raises(ValueError, match="Fenêtre temporelle invalide"):
        verifier_limites_combinees_passkey(
            *cles,
            fenetre_secondes=fenetre,
        )


def test_erreur_sql_limiteur_combine(cles):
    """Une erreur SQL entraîne un rollback et une fermeture."""

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
        verifier_limites_combinees_passkey(*cles)

    assert connexion.rollback_effectue is True
    assert connexion.fermeture_effectuee is True
