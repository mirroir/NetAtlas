"""Tests du gestionnaire de migrations NetAtlas."""

import hashlib
from dataclasses import replace

import pytest
from migration_manager import (
    Migration,
    calculer_checksum,
    comparer_migrations,
    decouvrir_migrations,
)


def test_calculer_checksum(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    contenu = b"SELECT 1;\n"
    chemin.write_bytes(contenu)

    resultat = calculer_checksum(chemin)

    assert resultat == hashlib.sha256(contenu).hexdigest()


def test_decouvrir_migrations_triees(tmp_path):
    (tmp_path / "002_seconde.sql").write_text("SELECT 2;")
    (tmp_path / "001_premiere.sql").write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)

    assert [migration.numero for migration in migrations] == [1, 2]
    assert migrations[0].nom == "001_premiere.sql"
    assert migrations[0].chemin == tmp_path / "001_premiere.sql"
    assert len(migrations[0].checksum_sha256) == 64
    assert isinstance(migrations[0], Migration)


def test_decouvrir_migrations_ignore_fichiers_non_conformes(tmp_path):
    (tmp_path / "diagnostic.sql").write_text("SELECT 1;")
    (tmp_path / "001_invalide.txt").write_text("SELECT 1;")
    (tmp_path / "001_nom-invalide.sql").write_text("SELECT 1;")

    sous_repertoire = tmp_path / "migrations"
    sous_repertoire.mkdir()
    (sous_repertoire / "001_autre.sql").write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)

    assert migrations == []


def test_decouvrir_migrations_ignore_repertoire_avec_nom_sql(tmp_path):
    (tmp_path / "001_faux.sql").mkdir()

    assert decouvrir_migrations(tmp_path) == []


def test_decouvrir_migrations_repertoire_absent(tmp_path):
    repertoire = tmp_path / "inexistant"

    with pytest.raises(
        ValueError,
        match="Répertoire de migrations introuvable",
    ):
        decouvrir_migrations(repertoire)


def test_decouvrir_migrations_numero_duplique(tmp_path):
    (tmp_path / "001_premiere.sql").write_text("SELECT 1;")
    (tmp_path / "001_seconde.sql").write_text("SELECT 2;")

    with pytest.raises(
        ValueError,
        match="Numéro de migration dupliqué : 001",
    ):
        decouvrir_migrations(tmp_path)


def test_decouvrir_migrations_repertoire_vide(tmp_path):
    assert decouvrir_migrations(tmp_path) == []

def test_decouvrir_migrations_ignore_permissions_test(tmp_path):
    (tmp_path / "002_create_webauthn_challenges.sql").write_text(
        "CREATE TABLE exemple (id INTEGER);"
    )

    (tmp_path / "002_webauthn_challenges_test_grants.sql").write_text(
        "GRANT SELECT ON exemple TO utilisateur_test;"
    )

    migrations = decouvrir_migrations(tmp_path)

    assert len(migrations) == 1
    assert migrations[0].nom == "002_create_webauthn_challenges.sql"

from unittest.mock import MagicMock

from migration_manager import lire_migrations_enregistrees


def test_lire_migrations_enregistrees():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchall.return_value = [
        (
            "022_create_schema_migrations",
            "database/022_create_schema_migrations.sql",
            "a" * 64,
            "executed",
            None,
        )
    ]

    resultat = lire_migrations_enregistrees(connexion)

    assert len(resultat) == 1
    assert resultat[0]["migration_key"] == (
        "022_create_schema_migrations"
    )
    assert resultat[0]["checksum_sha256"] == "a" * 64

    requete = curseur.execute.call_args.args[0]
    assert "FROM public.schema_migrations" in requete
    assert "ORDER BY migration_key" in requete


def test_lire_migrations_enregistrees_registre_vide():
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value

    curseur.fetchall.return_value = []

    assert lire_migrations_enregistrees(connexion) == []

def test_comparer_migrations_conforme(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]

    enregistrements = [
        {
            "migration_key": "001_exemple",
            "file_path": "database/001_exemple.sql",
            "checksum_sha256": migration.checksum_sha256,
            "application_mode": "executed",
        }
    ]

    resultat = comparer_migrations([migration], enregistrements)

    assert resultat == [
        {
            "migration_key": "001_exemple",
            "statut": "conforme",
        }
    ]


def test_comparer_migrations_non_enregistree(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]

    resultat = comparer_migrations([migration], [])

    assert resultat[0]["statut"] == "non_enregistree"




def test_comparer_migrations_inconnue():
    enregistrements = [
        {
            "migration_key": "999_inconnue",
            "file_path": "database/999_inconnue.sql",
            "checksum_sha256": "a" * 64,
            "application_mode": "executed",
        }
    ]

    resultat = comparer_migrations([], enregistrements)

    assert resultat == [
        {
            "migration_key": "999_inconnue",
            "statut": "inconnue",
        }
    ]

def test_comparer_migrations_refuse_doublons():
    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": "a" * 64,
        "application_mode": "executed",
    }

    with pytest.raises(
        ValueError,
        match="Migration enregistrée en double : 001_exemple",
    ):
        comparer_migrations(
            [],
            [enregistrement, enregistrement.copy()],
        )

def test_comparer_migrations_integrite_invalide(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]

    enregistrements = [
        {
            "migration_key": "001_exemple",
            "file_path": "database/001_exemple.sql",
            "checksum_sha256": "b" * 64,
            "application_mode": "executed",
        }
    ]

    resultat = comparer_migrations([migration], enregistrements)

    assert resultat[0]["statut"] == "integrite_invalide"


@pytest.mark.parametrize(
    "cle",
    [
        "../001_exemple",
        "001_exemple.sql",
        "migration_invalide",
        "",
        None,
    ],
)
def test_comparer_migrations_refuse_identifiant_invalide(cle):
    enregistrement = {
        "migration_key": cle,
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": "a" * 64,
        "application_mode": "executed",
    }

    with pytest.raises(
        ValueError,
        match="Identifiant de migration invalide",
    ):
        comparer_migrations([], [enregistrement])


@pytest.mark.parametrize(
    "chemin",
    [
        "../001_exemple.sql",
        "/tmp/001_exemple.sql",
        "database/../001_exemple.sql",
        "database/autre_migration.sql",
        "",
        None,
    ],
)
def test_comparer_migrations_refuse_chemin_invalide(chemin):
    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": chemin,
        "checksum_sha256": "a" * 64,
        "application_mode": "executed",
    }

    with pytest.raises(
        ValueError,
        match="Chemin de migration invalide : 001_exemple",
    ):
        comparer_migrations([], [enregistrement])

@pytest.mark.parametrize(
    "mode",
    ["inconnu", "", None],
)
def test_comparer_migrations_refuse_mode_invalide(mode):
    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": "a" * 64,
        "application_mode": mode,
    }

    with pytest.raises(
        ValueError,
        match="Mode de migration invalide : 001_exemple",
    ):
        comparer_migrations([], [enregistrement])

@pytest.mark.parametrize(
    "checksum",
    [
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "A" * 64,
        "",
        None,
        123,
        "a" * 64 + "\n",
    ],
)
def test_comparer_migrations_refuse_checksum_invalide(checksum):
    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": checksum,
        "application_mode": "executed",
    }

    with pytest.raises(
        ValueError,
        match="Empreinte SHA-256 invalide : 001_exemple",
    ):
        comparer_migrations([], [enregistrement])

def test_comparer_migrations_refuse_doublons_inventaire(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]

    with pytest.raises(
        ValueError,
        match="Migration présente en double : 001_exemple",
    ):
        comparer_migrations([migration, migration], [])

def test_comparer_migrations_refuse_numeros_dupliques(tmp_path):
    repertoire_a = tmp_path / "a"
    repertoire_b = tmp_path / "b"

    repertoire_a.mkdir()
    repertoire_b.mkdir()

    (repertoire_a / "001_exemple.sql").write_text("SELECT 1;")
    (repertoire_b / "001_autre.sql").write_text("SELECT 2;")

    migrations = (
        decouvrir_migrations(repertoire_a)
        + decouvrir_migrations(repertoire_b)
    )

    with pytest.raises(
        ValueError,
        match="Numéro de migration dupliqué : 001",
    ):
        comparer_migrations(migrations, [])

@pytest.mark.parametrize(
    "nom",
    [
        "../001_exemple.sql",
        "001_exemple.txt",
        "migration_invalide.sql",
        "",
    ],
)
def test_comparer_migrations_refuse_nom_invalide(tmp_path, nom):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]
    migration = replace(migration, nom=nom)

    with pytest.raises(
        ValueError,
        match="Nom de migration invalide",
    ):
        comparer_migrations([migration], [])


def test_comparer_migrations_refuse_numero_incoherent(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]
    migration = replace(migration, numero=2)

    with pytest.raises(
        ValueError,
        match="Numéro de migration incohérent : 001_exemple.sql",
    ):
        comparer_migrations([migration], [])

@pytest.mark.parametrize(
    "checksum",
    [
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "A" * 64,
        "",
        None,
        123,
        "a" * 64 + "\n",
    ],
)
def test_comparer_migrations_refuse_checksum_inventaire_invalide(
    tmp_path,
    checksum,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]
    migration = replace(migration, checksum_sha256=checksum)

    with pytest.raises(
        ValueError,
        match="Empreinte SHA-256 de migration invalide",
    ):
        comparer_migrations([migration], [])

@pytest.mark.parametrize("nom", [None, 123, [], True])
def test_comparer_migrations_refuse_type_nom_invalide(tmp_path, nom):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]
    migration = replace(migration, nom=nom)

    with pytest.raises(
        ValueError,
        match="Nom de migration invalide",
    ):
        comparer_migrations([migration], [])


@pytest.mark.parametrize("numero", [True, 1.0, "1", None])
def test_comparer_migrations_refuse_type_numero_invalide(
    tmp_path,
    numero,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]
    migration = replace(migration, numero=numero)

    with pytest.raises(
        ValueError,
        match="Numéro de migration incohérent",
    ):
        comparer_migrations([migration], [])


@pytest.mark.parametrize("mode", [[], {}, 123, True])
def test_comparer_migrations_refuse_type_mode_invalide(mode):
    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": "a" * 64,
        "application_mode": mode,
    }

    with pytest.raises(
        ValueError,
        match="Mode de migration invalide : 001_exemple",
    ):
        comparer_migrations([], [enregistrement])


@pytest.mark.parametrize(
    ("champ", "message"),
    [
        ("migration_key", "Identifiant de migration invalide"),
        ("file_path", "Chemin de migration invalide"),
        ("checksum_sha256", "Empreinte SHA-256 invalide"),
        ("application_mode", "Mode de migration invalide"),
    ],
)
def test_comparer_migrations_refuse_champ_absent(champ, message):
    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": "a" * 64,
        "application_mode": "executed",
    }

    del enregistrement[champ]

    with pytest.raises(ValueError, match=message):
        comparer_migrations([], [enregistrement])


def test_comparer_migrations_accepte_baseline(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migration = decouvrir_migrations(tmp_path)[0]

    enregistrement = {
        "migration_key": "001_exemple",
        "file_path": "database/001_exemple.sql",
        "checksum_sha256": migration.checksum_sha256,
        "application_mode": "baseline",
    }

    resultat = comparer_migrations(
        [migration],
        [enregistrement],
    )

    assert resultat == [
        {
            "migration_key": "001_exemple",
            "statut": "conforme",
        }
    ]
