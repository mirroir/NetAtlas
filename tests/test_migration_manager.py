"""Tests du gestionnaire de migrations NetAtlas."""

import hashlib

import pytest
from migration_manager import (
    Migration,
    calculer_checksum,
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
