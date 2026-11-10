
"""Tests de concurrence réelle des sessions IAM NetAtlas."""

import hashlib
import os
import re
import secrets
import subprocess
import threading
import time
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue

import iam_laboratoire_securise as laboratoire
import iam_sessions
import psycopg
import pytest

PREFIXE_BASE_IAM = "netatlas_iam_concurrence_"


def valider_nom_base_temporaire(nom_base: str) -> str:
    """Autorise uniquement un nom de base IAM éphémère."""

    if not isinstance(nom_base, str):
        raise TypeError("Nom de base temporaire invalide.")

    motif = rf"{PREFIXE_BASE_IAM}[0-9a-f]{{32}}"

    if re.fullmatch(motif, nom_base) is None:
        raise ValueError("Nom de base temporaire non autorisé.")

    return nom_base


@pytest.mark.parametrize(
    ("nom_base", "exception_attendue"),
    [
        ("netatlas", ValueError),
        ("netatlas_test", ValueError),
        ("postgres", ValueError),
        ("template0", ValueError),
        ("template1", ValueError),
        ("netatlas_iam_concurrence_", ValueError),
        ("netatlas_iam_concurrence_invalide", ValueError),
        (
            "netatlas_iam_concurrence_"
            + "a" * 32
            + ";DROP DATABASE netatlas",
            ValueError,
        ),
        ("", ValueError),
        (None, TypeError),
    ],
)
def test_refus_noms_bases_non_autorises(
    nom_base,
    exception_attendue,
):
    """Interdit les bases protégées et les noms malformés."""

    with pytest.raises(exception_attendue):
        valider_nom_base_temporaire(nom_base)


def test_acceptation_nom_base_temporaire():
    """Accepte uniquement le format prévu pour le laboratoire IAM."""

    nom_base = PREFIXE_BASE_IAM + "a" * 32

    assert valider_nom_base_temporaire(nom_base) == nom_base


def verifier_environnement_laboratoire(environnement: dict) -> None:
    """Interdit le laboratoire hors environnement de test."""

    if (
        environnement.get("NETATLAS_ENV") != "test"
        or environnement.get("DB_NAME") != "netatlas_test"
    ):
        raise RuntimeError(
            "SECURITE NETATLAS : environnement de test obligatoire."
        )


@pytest.mark.parametrize(
    ("environnement", "autorise"),
    [
        (
            {
                "NETATLAS_ENV": "test",
                "DB_NAME": "netatlas_test",
            },
            True,
        ),
        (
            {
                "NETATLAS_ENV": "production",
                "DB_NAME": "netatlas",
            },
            False,
        ),
        (
            {
                "NETATLAS_ENV": "test",
                "DB_NAME": "netatlas",
            },
            False,
        ),
        (
            {
                "NETATLAS_ENV": "production",
                "DB_NAME": "netatlas_test",
            },
            False,
        ),
        ({}, False),
    ],
)
def test_garde_fou_environnement_laboratoire(
    environnement,
    autorise,
):
    """Le laboratoire est réservé à netatlas_test."""

    if autorise:
        assert verifier_environnement_laboratoire(environnement) is None
    else:
        with pytest.raises(RuntimeError, match="SECURITE NETATLAS"):
            verifier_environnement_laboratoire(environnement)


def test_psql_admin_refuse_sans_autorisation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse toute opération administrative non autorisée."""

    def execution_interdite(*args, **kwargs):
        pytest.fail("Une commande administrative a été exécutée.")

    monkeypatch.setattr(subprocess, "run", execution_interdite)

    with pytest.raises(
        RuntimeError,
        match="Autorisation administrative IAM absente",
    ):
        executer_psql_admin(
            "postgres",
            "SELECT 1;",
        )


def test_psql_admin_refuse_environnement_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bloque les commandes avant leur exécution en production."""

    monkeypatch.setenv("NETATLAS_ENV", "production")
    monkeypatch.setenv("DB_NAME", "netatlas")

    def execution_interdite(*args, **kwargs):
        pytest.fail("Une commande administrative a été exécutée.")

    monkeypatch.setattr(subprocess, "run", execution_interdite)

    with pytest.raises(RuntimeError, match="SECURITE NETATLAS"):
        executer_psql_admin(
            "postgres",
            "SELECT 1;",
            autorisation=True,
        )


def test_psql_admin_signale_echec_commande(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signale un échec PostgreSQL sans divulguer le diagnostic."""

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas_test")
    monkeypatch.delenv("NETATLAS_SQL_TEST_MODE", raising=False)

    def simuler_echec(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="Erreur PostgreSQL simulée.",
        )

    monkeypatch.setattr(subprocess, "run", simuler_echec)

    with pytest.raises(
        RuntimeError,
        match=r"Échec d'une opération PostgreSQL IAM \(code 1\)",
    ):
        executer_psql_admin(
            "postgres",
            "SELECT 1;",
            autorisation=True,
        )


def test_psql_admin_signale_authentification_sudo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explique un refus sudo sans exposer d'informations sensibles."""

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas_test")
    monkeypatch.delenv("NETATLAS_SQL_TEST_MODE", raising=False)

    def simuler_refus_sudo(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=1,
            stdout="",
            stderr="sudo: interactive authentication is required",
        )

    monkeypatch.setattr(subprocess, "run", simuler_refus_sudo)

    with pytest.raises(
        RuntimeError,
        match="Authentification sudo requise",
    ):
        executer_psql_admin(
            "postgres",
            "SELECT 1;",
            autorisation=True,
        )


def test_psql_admin_signale_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Signale un dépassement de délai PostgreSQL."""

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas_test")
    monkeypatch.delenv("NETATLAS_SQL_TEST_MODE", raising=False)

    def simuler_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(
            cmd=args[0],
            timeout=20,
        )

    monkeypatch.setattr(subprocess, "run", simuler_timeout)

    with pytest.raises(
        RuntimeError,
        match="Délai dépassé",
    ):
        executer_psql_admin(
            "postgres",
            "SELECT 1;",
            autorisation=True,
        )


def test_psql_admin_retourne_sortie(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vérifie la récupération d'un résultat SQL administratif."""

    class ResultatSimule:
        returncode = 0
        stdout = "  marqueur_iam_valide\n"
        stderr = ""

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas_test")
    monkeypatch.delenv("NETATLAS_SQL_TEST_MODE", raising=False)

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: ResultatSimule(),
    )

    resultat = executer_psql_admin(
        "postgres",
        "SELECT 'marqueur_iam_valide';",
        autorisation=True,
        retourner_sortie=True,
    )

    assert resultat == "marqueur_iam_valide"


def test_psql_admin_sans_retour(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Préserve le comportement des appels administratifs existants."""

    class ResultatSimule:
        returncode = 0
        stdout = "valeur_ignoree"
        stderr = ""

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas_test")
    monkeypatch.delenv("NETATLAS_SQL_TEST_MODE", raising=False)

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *_args, **_kwargs: ResultatSimule(),
    )

    resultat = executer_psql_admin(
        "postgres",
        "SELECT 1;",
        autorisation=True,
    )

    assert resultat is None


def executer_psql_admin(
    base: str,
    sql: str,
    *,
    autorisation: bool = False,
    retourner_sortie: bool = False,
) -> str | None:
    """Exécute du SQL administratif dans le laboratoire IAM."""

    if not autorisation:
        raise RuntimeError("Autorisation administrative IAM absente.")

    verifier_environnement_laboratoire(os.environ)

    if base != "postgres":
        valider_nom_base_temporaire(base)

    environnement = os.environ.copy()
    environnement.pop("PGPASSWORD", None)

    if environnement.get("NETATLAS_SQL_TEST_MODE") == "ci":
        if environnement.get("GITHUB_ACTIONS") != "true":
            raise RuntimeError("Mode CI IAM non autorisé hors GitHub Actions.")

        mot_de_passe = environnement.get("NETATLAS_SQL_ADMIN_PASSWORD")

        if not mot_de_passe:
            raise RuntimeError("Mot de passe PostgreSQL CI absent.")

        environnement["PGPASSWORD"] = mot_de_passe

        commande = [
            "psql",
            "-A",
            "-t",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-h",
            "localhost",
            "-p",
            "5432",
            "-U",
            "postgres",
            "-d",
            base,
        ]
    else:
        commande = [
            "sudo",
            "-n",
            "-u",
            "postgres",
            "psql",
            "-A",
            "-t",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-d",
            base,
        ]

    try:
        resultat = subprocess.run(
            commande,
            input=sql,
            text=True,
            capture_output=True,
            check=False,
            timeout=20,
            env=environnement,
        )
    except subprocess.TimeoutExpired as erreur:
        raise RuntimeError(
            "Délai dépassé lors d'une opération PostgreSQL IAM."
        ) from erreur


    if resultat.returncode != 0:
        diagnostic = resultat.stderr.strip()

        if "interactive authentication is required" in diagnostic:
            raise RuntimeError(
                "Authentification sudo requise : exécuter sudo -v."
            )

        raise RuntimeError(
            "Échec d'une opération PostgreSQL IAM "
            f"(code {resultat.returncode}) : "
            f"{diagnostic[:1000]}"
        )

    if retourner_sortie:
        return resultat.stdout.strip()

    return None

@pytest.mark.parametrize(
    ("marqueur_obtenu", "attendu"),
    [
        ("netatlas-iam-laboratoire:" + "a" * 32, True),
        ("netatlas-iam-laboratoire:" + "b" * 32, False),
        ("", False),
    ],
)
def test_verifier_marqueur_base_iam(
    monkeypatch: pytest.MonkeyPatch,
    marqueur_obtenu: str,
    attendu: bool,
) -> None:
    """Vérifie l'acceptation exclusive du marqueur attendu."""

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        lambda *_args, **_kwargs: marqueur_obtenu,
    )

    resultat = verifier_marqueur_base_iam(
        PREFIXE_BASE_IAM + "c" * 32,
        "a" * 32,
    )

    assert resultat is attendu


def test_marquer_base_iam_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vérifie la construction du marquage PostgreSQL."""

    commandes = []

    def simuler_psql(
        base: str,
        sql: str,
        *,
        autorisation: bool = False,
        retourner_sortie: bool = False,
    ) -> None:
        commandes.append((base, sql, autorisation))

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        simuler_psql,
    )

    nom_base = PREFIXE_BASE_IAM + "a" * 32
    identifiant = "b" * 32

    marquer_base_iam(nom_base, identifiant)

    assert commandes == [
        (
            "postgres",
            f'COMMENT ON DATABASE "{nom_base}" '
            + f"IS 'netatlas-iam-laboratoire:{identifiant}';",
            True,
        )
    ]


def test_verifier_registre_base_iam_valide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accepte un registre correspondant à la base."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    nom_base = PREFIXE_BASE_IAM + "c" * 32
    operation = laboratoire.enregistrer_operation(nom_base)

    laboratoire.changer_etat(
        operation["identifiant"],
        "creation_confirmee",
    )

    assert verifier_registre_base_iam(
        nom_base,
        operation["identifiant"],
    )


def test_verifier_registre_base_iam_nom_different(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse un nom de base différent du registre."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    operation = laboratoire.enregistrer_operation(
        PREFIXE_BASE_IAM + "d" * 32
    )

    laboratoire.changer_etat(
        operation["identifiant"],
        "creation_confirmee",
    )

    assert not verifier_registre_base_iam(
        PREFIXE_BASE_IAM + "e" * 32,
        operation["identifiant"],
    )


def test_verifier_registre_base_iam_etat_non_autorise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse une opération encore en préparation."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    nom_base = PREFIXE_BASE_IAM + "f" * 32
    operation = laboratoire.enregistrer_operation(nom_base)

    assert not verifier_registre_base_iam(
        nom_base,
        operation["identifiant"],
    )


def marquer_base_iam(
    nom_base: str,
    identifiant: str,
) -> None:
    """Associe une base temporaire à son registre IAM."""

    valider_nom_base_temporaire(nom_base)
    laboratoire.verifier_identifiant(identifiant)

    marqueur = f"netatlas-iam-laboratoire:{identifiant}"

    executer_psql_admin(
        "postgres",
        f'COMMENT ON DATABASE "{nom_base}" IS \'{marqueur}\';',
        autorisation=True,
    )

def verifier_marqueur_base_iam(
    nom_base: str,
    identifiant: str,
) -> bool:
    """Vérifie la correspondance exacte du marqueur PostgreSQL IAM."""

    valider_nom_base_temporaire(nom_base)
    laboratoire.verifier_identifiant(identifiant)

    marqueur_attendu = f"netatlas-iam-laboratoire:{identifiant}"

    sql = f"""
        SELECT COALESCE(
            shobj_description(oid, 'pg_database'),
            ''
        )
        FROM pg_database
        WHERE datname = '{nom_base}';
    """

    resultat = executer_psql_admin(
        "postgres",
        sql,
        autorisation=True,
        retourner_sortie=True,
    )

    return resultat == marqueur_attendu


def verifier_registre_base_iam(
    nom_base: str,
    identifiant: str,
) -> bool:
    """Vérifie la correspondance avec le registre local IAM."""

    valider_nom_base_temporaire(nom_base)
    laboratoire.verifier_identifiant(identifiant)

    operation = laboratoire.lire_operation(identifiant)

    return (
        operation["base"] == nom_base
        and operation["identifiant"] == identifiant
        and operation["etat"]
        in {
            "creation_confirmee",
            "nettoyage_requis",
        }
    )


@pytest.mark.parametrize(
    ("reponse_sql", "diagnostic_attendu"),
    [
        ("0", "base_absente"),
        ("1", "base_presente"),
    ],
)
def test_diagnostiquer_operation_iam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reponse_sql: str,
    diagnostic_attendu: str,
) -> None:
    """Distingue une base absente d'une base présente."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    nom_base = PREFIXE_BASE_IAM + "a" * 32
    operation = laboratoire.enregistrer_operation(nom_base)

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        lambda *_args, **_kwargs: reponse_sql,
    )

    resultat = diagnostiquer_operation_iam(
        operation["identifiant"],
    )

    assert resultat == diagnostic_attendu


def test_diagnostiquer_operation_iam_reponse_invalide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse une réponse PostgreSQL ambiguë."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    operation = laboratoire.enregistrer_operation(
        PREFIXE_BASE_IAM + "b" * 32
    )

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        lambda *_args, **_kwargs: "",
    )

    with pytest.raises(
        RuntimeError,
        match="réponse PostgreSQL inattendue",
    ):
        diagnostiquer_operation_iam(
            operation["identifiant"],
        )


def test_diagnostiquer_operation_iam_erreur_sql(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propage une erreur PostgreSQL sans clôturer le registre."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    operation = laboratoire.enregistrer_operation(
        PREFIXE_BASE_IAM + "c" * 32
    )

    def simuler_erreur(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("PostgreSQL indisponible.")

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        simuler_erreur,
    )

    with pytest.raises(RuntimeError, match="PostgreSQL indisponible"):
        diagnostiquer_operation_iam(
            operation["identifiant"],
        )

    assert (
        laboratoire.lire_operation(operation["identifiant"])["etat"]
        == "preparation"
    )

def diagnostiquer_operation_iam(
    identifiant: str,
) -> str:
    """Diagnostique une opération IAM sans modifier le registre."""

    laboratoire.verifier_identifiant(identifiant)

    operation = laboratoire.lire_operation(identifiant)
    nom_base = operation["base"]

    valider_nom_base_temporaire(nom_base)

    if operation["identifiant"] != identifiant:
        raise RuntimeError(
            "Sécurité IAM : identifiant du registre incohérent."
        )

    resultat = executer_psql_admin(
        "postgres",
        (
            "SELECT count(*) FROM pg_database "
            f"WHERE datname = '{nom_base}';"
        ),
        autorisation=True,
        retourner_sortie=True,
    )

    if resultat == "0":
        return "base_absente"

    if resultat == "1":
        return "base_presente"

    raise RuntimeError(
        "Sécurité IAM : réponse PostgreSQL inattendue."
    )

def test_marqueur_postgresql_reel(
    base_iam_temporaire: str,
) -> None:
    """Vérifie le marqueur réel sans modifier la base temporaire."""

    repertoire = laboratoire.preparer_registre()

    operations = [
        laboratoire.lire_operation(chemin.stem)
        for chemin in repertoire.glob("*.json")
    ]

    operations_base = [
        operation
        for operation in operations
        if operation["base"] == base_iam_temporaire
    ]

    assert len(operations_base) == 1

    identifiant = operations_base[0]["identifiant"]

    assert verifier_marqueur_base_iam(
        base_iam_temporaire,
        identifiant,
    )

def verifier_absence_base_iam(nom_base: str) -> bool:
    """Confirme l'absence d'une base IAM temporaire dans PostgreSQL."""

    valider_nom_base_temporaire(nom_base)

    resultat = executer_psql_admin(
        "postgres",
        (
            "SELECT count(*) FROM pg_database "
            f"WHERE datname = '{nom_base}';"
        ),
        autorisation=True,
        retourner_sortie=True,
    )

    if resultat == "0":
        return True

    if resultat == "1":
        return False

    raise RuntimeError(
        "Sécurité IAM : réponse PostgreSQL ambiguë "
        "lors de la vérification d'absence."
    )

@pytest.mark.parametrize(
    ("reponse", "absence_attendue"),
    [
        ("0", True),
        ("1", False),
    ],
)
def test_verifier_absence_base_iam(
    monkeypatch: pytest.MonkeyPatch,
    reponse: str,
    absence_attendue: bool,
) -> None:
    """Vérifie les réponses PostgreSQL sans accès réel à la base."""

    def simuler_psql(
        base: str,
        sql: str,
        *,
        autorisation: bool = False,
        retourner_sortie: bool = False,
    ) -> str:
        assert base == "postgres"
        assert autorisation is True
        assert retourner_sortie is True
        assert "pg_database" in sql
        return reponse

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        simuler_psql,
    )

    nom_base = PREFIXE_BASE_IAM + "a" * 32

    assert verifier_absence_base_iam(nom_base) is absence_attendue


def test_verifier_absence_base_iam_reponse_ambigue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse une réponse PostgreSQL impossible à interpréter."""

    def simuler_psql(
        base: str,
        sql: str,
        *,
        autorisation: bool = False,
        retourner_sortie: bool = False,
    ) -> str:
        return "inconnue"

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        simuler_psql,
    )

    with pytest.raises(RuntimeError, match="réponse PostgreSQL ambiguë"):
        verifier_absence_base_iam(PREFIXE_BASE_IAM + "a" * 32)


def test_verifier_absence_base_iam_erreur_postgresql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Propage une erreur PostgreSQL sans confirmer l'absence."""

    def simuler_psql(
        base: str,
        sql: str,
        *,
        autorisation: bool = False,
        retourner_sortie: bool = False,
    ) -> str:
        raise RuntimeError("PostgreSQL indisponible")

    monkeypatch.setattr(
        "test_iam_sessions_concurrence.executer_psql_admin",
        simuler_psql,
    )

    with pytest.raises(RuntimeError, match="PostgreSQL indisponible"):
        verifier_absence_base_iam(PREFIXE_BASE_IAM + "a" * 32)

@pytest.fixture(scope="module")
def base_iam_temporaire() -> Iterator[str]:
    """Crée une base IAM isolée avec coordination interprocessus."""

    verifier_environnement_laboratoire(os.environ)

    with laboratoire.verrou_cycle_iam():
        nom_base = valider_nom_base_temporaire(
            PREFIXE_BASE_IAM + secrets.token_hex(16)
        )

        operation = laboratoire.enregistrer_operation(nom_base)
        identifiant = operation["identifiant"]

        creation_confirmee = False

        try:
            laboratoire.changer_etat(
                identifiant,
                "creation_incertaine",
            )

            executer_psql_admin(
                "postgres",
                f'CREATE DATABASE "{nom_base}" TEMPLATE template0;',
                autorisation=True,
            )

            marquer_base_iam(
                nom_base,
                identifiant,
            )

            if not verifier_marqueur_base_iam(nom_base, identifiant):
                raise RuntimeError(
                    "Sécurité IAM : marqueur PostgreSQL non confirmé."
                )

            laboratoire.changer_etat(
                identifiant,
                "creation_confirmee",
            )

            creation_confirmee = True

            executer_psql_admin(
                nom_base,
                """
                CREATE TABLE public.users (
                    id INTEGER PRIMARY KEY,
                    nom VARCHAR(100)
                );

                INSERT INTO public.users (id, nom)
                VALUES (1, 'Utilisateur IAM laboratoire');
                """,
                autorisation=True,
            )

            executer_psql_admin(
                nom_base,
                charger_migration_iam(),
                autorisation=True,
            )

            configurer_permissions_iam(
                nom_base,
                os.environ["DB_USER"],
            )

            yield nom_base

        finally:
            if creation_confirmee:
                if not verifier_registre_base_iam(
                    nom_base,
                    identifiant,
                ):
                    raise RuntimeError(
                        "Sécurité IAM : registre non conforme, "
                        "suppression refusée."
                    )

                if not verifier_marqueur_base_iam(
                    nom_base,
                    identifiant,
                ):
                    raise RuntimeError(
                        "Sécurité IAM : marqueur non conforme, "
                        "suppression refusée."
                    )

                laboratoire.changer_etat(
                    identifiant,
                    "nettoyage_requis",
                )

                executer_psql_admin(
                    "postgres",
                    f'DROP DATABASE "{nom_base}";',
                    autorisation=True,
                )

                if not verifier_absence_base_iam(nom_base):
                    raise RuntimeError(
                        "Sécurité IAM : base temporaire encore présente "
                        "après DROP DATABASE ; nettoyage non confirmé."
                    )

                laboratoire.changer_etat(
                    identifiant,
                    "nettoyage_confirme",
                )

def charger_migration_iam() -> str:
    """Charge la migration IAM officielle du dépôt NetAtlas."""

    racine_projet = Path(__file__).resolve().parents[1]
    chemin_migration = racine_projet / "database" / "019_create_iam_sessions.sql"

    return chemin_migration.read_text(encoding="utf-8")



def configurer_permissions_iam(
    nom_base: str,
    utilisateur: str,
) -> None:
    """Configure les droits IAM dans la base temporaire uniquement."""

    valider_nom_base_temporaire(nom_base)

    if utilisateur not in {"netatlas_test_user", "netatlas_ci_user"}:
        raise ValueError("Compte applicatif IAM non autorisé.")

    executer_psql_admin(
        nom_base,
        f"""
        GRANT USAGE ON SCHEMA public TO {utilisateur};

        GRANT SELECT ON public.users TO {utilisateur};

        GRANT SELECT, INSERT, UPDATE
            ON public.iam_sessions TO {utilisateur};
        """,
        autorisation=True,
    )


def test_laboratoire_postgresql_isole(base_iam_temporaire: str) -> None:
    """Vérifie que le laboratoire dispose de sa propre base."""

    assert base_iam_temporaire.startswith(PREFIXE_BASE_IAM)
    assert base_iam_temporaire not in {
        "netatlas",
        "netatlas_test",
        "postgres",
        "template0",
        "template1",
    }



def test_permissions_applicatives_iam(base_iam_temporaire: str) -> None:
    """Vérifie les permissions réelles du compte applicatif IAM."""

    with psycopg.connect(
        dbname=base_iam_temporaire,
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        connect_timeout=5,
    ) as connexion, connexion.cursor() as curseur:
        curseur.execute(
            """
                SELECT
                    current_user,
                    has_table_privilege(
                        current_user,
                        'public.users',
                        'SELECT'
                    ),
                    has_table_privilege(
                        current_user,
                        'public.iam_sessions',
                        'SELECT'
                    ),
                    has_table_privilege(
                        current_user,
                        'public.iam_sessions',
                        'INSERT'
                    ),
                    has_table_privilege(
                        current_user,
                        'public.iam_sessions',
                        'UPDATE'
                    ),
                    has_table_privilege(
                        current_user,
                        'public.iam_sessions',
                        'DELETE'
                    )
                """
        )

        resultat = curseur.fetchone()

    assert resultat is not None

    (
        utilisateur,
        lecture_utilisateurs,
        lecture_sessions,
        creation_sessions,
        modification_sessions,
        suppression_sessions,
    ) = resultat

    assert utilisateur == os.environ["DB_USER"]
    assert lecture_utilisateurs is True
    assert lecture_sessions is True
    assert creation_sessions is True
    assert modification_sessions is True
    assert suppression_sessions is False



@pytest.mark.parametrize(
    ("confirmer_revocation", "session_valide"),
    [
        (True, False),
        (False, True),
    ],
    ids=["revocation_commit", "revocation_rollback"],
)
def test_concurrence_validation_revocation_iam(
    base_iam_temporaire: str,
    monkeypatch: pytest.MonkeyPatch,
    confirmer_revocation: bool,
    session_valide: bool,
) -> None:
    """Teste une validation bloquée par une révocation concurrente."""

    verifier_environnement_laboratoire(os.environ)

    pids_validations: Queue[int] = Queue()

    def ouvrir_connexion():
        connexion = psycopg.connect(
            dbname=base_iam_temporaire,
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            host=os.environ["DB_HOST"],
            port=os.environ["DB_PORT"],
            connect_timeout=5,
            options="-c statement_timeout=5000 -c lock_timeout=4000",
        )

        if threading.current_thread() is not threading.main_thread():
            pids_validations.put(connexion.info.backend_pid)

        return connexion

    monkeypatch.setattr(
        iam_sessions,
        "connexion_db",
        ouvrir_connexion,
    )

    # Le service IAM crée lui-même un jeton cryptographique aléatoire.
    jeton = iam_sessions.creer_session_iam(user_id=1)
    empreinte = hashlib.sha256(bytes.fromhex(jeton)).digest()

    connexion_revocation = ouvrir_connexion()

    try:
        with connexion_revocation.cursor() as curseur:
            curseur.execute(
                """
                UPDATE public.iam_sessions
                SET
                    revoked_at = statement_timestamp(),
                    revocation_reason = 'test_concurrence'
                WHERE token_hash = %s
                  AND revoked_at IS NULL
                RETURNING id
                """,
                (empreinte,),
            )
            assert curseur.fetchone() is not None

        # La révocation reste non validée : son verrou est conservé.
        with ThreadPoolExecutor(max_workers=1) as executant:
            validation = executant.submit(
                iam_sessions.valider_session_iam,
                jeton,
            )

            pid_validation = pids_validations.get(timeout=5)
            pid_revocation = connexion_revocation.info.backend_pid



            # Vérification réelle du blocage dans PostgreSQL.
            verrou_confirme = False
            limite = time.monotonic() + 2.5

            with (
                ouvrir_connexion() as observation,
                observation.cursor() as curseur,
            ):
                while time.monotonic() < limite:
                    curseur.execute(
                        """
                        SELECT %s = ANY(
                            pg_blocking_pids(%s)
                        )
                        """,
                        (pid_revocation, pid_validation),
                    )

                    verrou_confirme = curseur.fetchone()[0]

                    if verrou_confirme:
                        break

                    time.sleep(0.05)


            assert verrou_confirme, (
                "La validation IAM n'a pas attendu "
                "le verrou PostgreSQL de révocation."
            )

            if confirmer_revocation:
                connexion_revocation.commit()
            else:
                connexion_revocation.rollback()

            resultat = validation.result(timeout=6)

        if session_valide:
            assert resultat == {
                "user_id": 1,
                "nom": "Utilisateur IAM laboratoire",
            }
        else:
            assert resultat is None

    finally:
        connexion_revocation.rollback()
        connexion_revocation.close()
