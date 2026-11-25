import hashlib
import os
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from migration_manager import (
    ManifesteMigrations,
    Migration,
    _lire_fichier_depuis_repertoire,
    calculer_checksum,
    capturer_manifeste_migrations,
    comparer_migrations,
    decouvrir_migrations,
    lire_fichier_securise,
    lire_manifeste_migrations,
    lire_migrations_enregistrees,
    ouvrir_repertoire_securise,
    revalider_inventaire_migrations,
    revalider_manifeste_migrations,
    valider_manifeste_migrations,
    valider_perimetre_baseline,
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

def test_lire_manifeste_migrations_valide(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_premiere.sql\n"
        f"{'b' * 64}  database/002_seconde.sql\n",
        encoding="ascii",
    )

    resultat = lire_manifeste_migrations(chemin)

    assert resultat == {
        "001_premiere.sql": "a" * 64,
        "002_seconde.sql": "b" * 64,
    }


def test_lire_manifeste_migrations_fichier_absent(tmp_path):
    chemin = tmp_path / "inexistant.txt"

    with pytest.raises(
        ValueError,
        match="Manifeste de migrations introuvable",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_repertoire(tmp_path):
    with pytest.raises(
        ValueError,
        match="Manifeste de migrations introuvable",
    ):
        lire_manifeste_migrations(tmp_path)


def test_lire_manifeste_migrations_vide(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text("", encoding="ascii")

    with pytest.raises(
        ValueError,
        match="Manifeste de migrations vide",
    ):
        lire_manifeste_migrations(chemin)


@pytest.mark.parametrize(
    "ligne",
    [
        f"{'a' * 63}  database/001_exemple.sql",
        f"{'a' * 65}  database/001_exemple.sql",
        f"{'A' * 64}  database/001_exemple.sql",
        f"{'g' * 64}  database/001_exemple.sql",
        f"{'a' * 64} database/001_exemple.sql",
        f"{'a' * 64}   database/001_exemple.sql",
        f"{'a' * 64}\tdatabase/001_exemple.sql",
        f"{'a' * 64}  migrations/001_exemple.sql",
        f"{'a' * 64}  /database/001_exemple.sql",
        f"{'a' * 64}  database/../001_exemple.sql",
        f"{'a' * 64}  database/001_exemple.txt",
        f"{'a' * 64}  database/01_exemple.sql",
        f"{'a' * 64}  database/001_nom-invalide.sql",
        f"{'a' * 64}  database/001_exemple.sql ",
        "",
    ],
)
def test_lire_manifeste_migrations_ligne_invalide(
    tmp_path,
    ligne,
):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(f"{ligne}\n", encoding="ascii")

    with pytest.raises(
        ValueError,
        match="Ligne de manifeste invalide : 1",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_ligne_vide(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_exemple.sql\n\n",
        encoding="ascii",
    )

    with pytest.raises(
        ValueError,
        match="Ligne de manifeste invalide : 2",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_auxiliaire_interdite(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(
        f"{'a' * 64}  database/002_exemple_test_grants.sql\n",
        encoding="ascii",
    )

    with pytest.raises(
        ValueError,
        match="Migration auxiliaire interdite",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_doublon(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_exemple.sql\n"
        f"{'a' * 64}  database/001_exemple.sql\n",
        encoding="ascii",
    )

    with pytest.raises(
        ValueError,
        match="Migration dupliquée dans le manifeste",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_numero_duplique(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_premiere.sql\n"
        f"{'b' * 64}  database/001_seconde.sql\n",
        encoding="ascii",
    )

    with pytest.raises(
        ValueError,
        match="Numéro dupliqué dans le manifeste : 001",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_encodage_invalide(tmp_path):
    chemin = tmp_path / "manifeste.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_épreuve.sql\n",
        encoding="utf-8",
    )

    with pytest.raises(UnicodeDecodeError):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_reel():
    racine = Path(__file__).resolve().parents[1]
    chemin = racine / "docs/audit/migrations_sha256.txt"

    manifeste = lire_manifeste_migrations(chemin)

    assert len(manifeste) == 22
    assert next(iter(manifeste)) == (
        "001_create_webauthn_credentials.sql"
    )
    assert next(reversed(manifeste)) == (
        "022_create_schema_migrations.sql"
    )
    assert [int(nom[:3]) for nom in manifeste] == list(
        range(1, 23)
    )

def test_valider_manifeste_migrations_conforme(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {
        chemin.name: calculer_checksum(chemin),
    }

    assert valider_manifeste_migrations(
        migrations,
        manifeste,
    ) is None


def test_valider_manifeste_migrations_manifeste_vide():
    with pytest.raises(
        ValueError,
        match="Manifeste de migrations vide",
    ):
        valider_manifeste_migrations([], {})


def test_valider_manifeste_migrations_inventaire_vide():
    manifeste = {"001_exemple.sql": "a" * 64}

    with pytest.raises(
        ValueError,
        match="Inventaire de migrations vide",
    ):
        valider_manifeste_migrations([], manifeste)


@pytest.mark.parametrize(
    "nom",
    [
        None,
        123,
        True,
        "",
        "exemple.sql",
        "01_exemple.sql",
        "001_exemple.txt",
        "001_nom-invalide.sql",
        "../001_exemple.sql",
        "database/001_exemple.sql",
    ],
)
def test_valider_manifeste_migrations_nom_invalide(
    tmp_path,
    nom,
):
    (tmp_path / "001_exemple.sql").write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {nom: "a" * 64}

    with pytest.raises(
        ValueError,
        match="Nom de migration invalide dans le manifeste",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_auxiliaire_interdite(
    tmp_path,
):
    (tmp_path / "001_exemple.sql").write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {
        "002_exemple_test_grants.sql": "a" * 64,
    }

    with pytest.raises(
        ValueError,
        match="Migration auxiliaire interdite",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_checksum_invalide(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {chemin.name: "invalide"}

    with pytest.raises(
        ValueError,
        match="Empreinte SHA-256 invalide",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_fichier_modifie(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    manifeste = {
        chemin.name: calculer_checksum(chemin),
    }

    chemin.write_text("SELECT 2;")
    migrations = decouvrir_migrations(tmp_path)

    with pytest.raises(
        ValueError,
        match=r"001_exemple \(integrite_invalide\)",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_fichier_manquant(
    tmp_path,
):
    chemin = tmp_path / "001_premiere.sql"
    chemin.write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {
        chemin.name: calculer_checksum(chemin),
        "002_seconde.sql": "b" * 64,
    }

    with pytest.raises(
        ValueError,
        match=r"002_seconde \(inconnue\)",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_fichier_supplementaire(
    tmp_path,
):
    chemin = tmp_path / "001_premiere.sql"
    chemin.write_text("SELECT 1;")

    manifeste = {
        chemin.name: calculer_checksum(chemin),
    }

    (tmp_path / "002_seconde.sql").write_text("SELECT 2;")
    migrations = decouvrir_migrations(tmp_path)

    with pytest.raises(
        ValueError,
        match=r"002_seconde \(non_enregistree\)",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_inventaire_duplique(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {
        chemin.name: calculer_checksum(chemin),
    }

    migrations.append(migrations[0])

    with pytest.raises(
        ValueError,
        match="Migration présente en double",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_numero_incoherent(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_text("SELECT 1;")

    migrations = decouvrir_migrations(tmp_path)
    manifeste = {
        chemin.name: calculer_checksum(chemin),
    }

    migrations[0] = replace(migrations[0], numero=2)

    with pytest.raises(
        ValueError,
        match="Numéro de migration incohérent",
    ):
        valider_manifeste_migrations(
            migrations,
            manifeste,
        )


def test_valider_manifeste_migrations_reel():
    racine = Path(__file__).resolve().parents[1]

    migrations = decouvrir_migrations(
        racine / "database",
    )

    manifeste = lire_manifeste_migrations(
        racine / "docs/audit/migrations_sha256.txt",
    )

    assert len(migrations) == len(manifeste) == 22

    assert valider_manifeste_migrations(
        migrations,
        manifeste,
    ) is None

def construire_perimetre_baseline(tmp_path, numeros):
    """Construit un inventaire et un manifeste SQL de test."""

    for numero in numeros:
        chemin = tmp_path / f"{numero:03d}_exemple.sql"
        chemin.write_text(
            f"SELECT {numero};",
            encoding="ascii",
        )

    migrations = decouvrir_migrations(tmp_path)

    manifeste = {
        migration.nom: migration.checksum_sha256
        for migration in migrations
    }

    return migrations, manifeste


def test_valider_perimetre_baseline_conforme(tmp_path):
    migrations, manifeste = construire_perimetre_baseline(
        tmp_path,
        range(1, 23),
    )

    assert valider_perimetre_baseline(
        migrations,
        manifeste,
    ) is None


@pytest.mark.parametrize(
    "numero_manquant",
    [1, 10, 22],
)
def test_valider_perimetre_baseline_migration_manquante(
    tmp_path,
    numero_manquant,
):
    numeros = [
        numero
        for numero in range(1, 23)
        if numero != numero_manquant
    ]

    migrations, manifeste = construire_perimetre_baseline(
        tmp_path,
        numeros,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Migrations historiques manquantes : "
            f"{numero_manquant:03d}"
        ),
    ):
        valider_perimetre_baseline(
            migrations,
            manifeste,
        )


def test_valider_perimetre_baseline_plusieurs_manquantes(
    tmp_path,
):
    numeros = [
        numero
        for numero in range(1, 23)
        if numero not in {1, 10, 22}
    ]

    migrations, manifeste = construire_perimetre_baseline(
        tmp_path,
        numeros,
    )

    with pytest.raises(
        ValueError,
        match="Migrations historiques manquantes : 001, 010, 022",
    ):
        valider_perimetre_baseline(
            migrations,
            manifeste,
        )


@pytest.mark.parametrize(
    "numero_supplementaire",
    [0, 23, 999],
)
def test_valider_perimetre_baseline_hors_perimetre(
    tmp_path,
    numero_supplementaire,
):
    numeros = [
        *range(1, 23),
        numero_supplementaire,
    ]

    migrations, manifeste = construire_perimetre_baseline(
        tmp_path,
        numeros,
    )

    with pytest.raises(
        ValueError,
        match=(
            "Migrations hors périmètre historique : "
            f"{numero_supplementaire:03d}"
        ),
    ):
        valider_perimetre_baseline(
            migrations,
            manifeste,
        )


def test_valider_perimetre_baseline_plusieurs_supplementaires(
    tmp_path,
):
    migrations, manifeste = construire_perimetre_baseline(
        tmp_path,
        [0, *range(1, 23), 23],
    )

    with pytest.raises(
        ValueError,
        match="Migrations hors périmètre historique : 000, 023",
    ):
        valider_perimetre_baseline(
            migrations,
            manifeste,
        )


def test_valider_perimetre_baseline_integrite_invalide(
    tmp_path,
):
    migrations, manifeste = construire_perimetre_baseline(
        tmp_path,
        range(1, 23),
    )

    manifeste["010_exemple.sql"] = "0" * 64

    with pytest.raises(
        ValueError,
        match=r"010_exemple \(integrite_invalide\)",
    ):
        valider_perimetre_baseline(
            migrations,
            manifeste,
        )


def test_valider_perimetre_baseline_reel():
    racine = Path(__file__).resolve().parents[1]

    migrations = decouvrir_migrations(
        racine / "database",
    )

    manifeste = lire_manifeste_migrations(
        racine / "docs/audit/migrations_sha256.txt",
    )

    assert valider_perimetre_baseline(
        migrations,
        manifeste,
    ) is None

def test_calculer_checksum_lien_symbolique(tmp_path):
    cible = tmp_path / "cible.sql"
    cible.write_text("SELECT 1;", encoding="ascii")

    lien = tmp_path / "001_exemple.sql"
    lien.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Lien symbolique interdit",
    ):
        calculer_checksum(lien)


def test_calculer_checksum_lien_symbolique_casse(tmp_path):
    cible = tmp_path / "absent.sql"

    lien = tmp_path / "001_exemple.sql"
    lien.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Lien symbolique interdit",
    ):
        calculer_checksum(lien)


def test_decouvrir_migrations_repertoire_symbolique(tmp_path):
    cible = tmp_path / "migrations"
    cible.mkdir()

    (cible / "001_exemple.sql").write_text(
        "SELECT 1;",
        encoding="ascii",
    )

    lien = tmp_path / "database"
    lien.symlink_to(cible, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="Répertoire symbolique interdit",
    ):
        decouvrir_migrations(lien)


def test_decouvrir_migrations_fichier_symbolique(tmp_path):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    cible = tmp_path / "externe.sql"
    cible.write_text("SELECT 1;", encoding="ascii")

    lien = repertoire / "001_exemple.sql"
    lien.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Lien symbolique interdit",
    ):
        decouvrir_migrations(repertoire)


def test_decouvrir_migrations_lien_symbolique_casse(tmp_path):
    cible = tmp_path / "absent.sql"

    lien = tmp_path / "001_exemple.sql"
    lien.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Lien symbolique interdit",
    ):
        decouvrir_migrations(tmp_path)


def test_decouvrir_migrations_lien_symbolique_repertoire(
    tmp_path,
):
    cible = tmp_path / "repertoire"
    cible.mkdir()

    lien = tmp_path / "001_exemple.sql"
    lien.symlink_to(cible, target_is_directory=True)

    with pytest.raises(
        ValueError,
        match="Lien symbolique interdit",
    ):
        decouvrir_migrations(tmp_path)


def test_lire_manifeste_migrations_lien_symbolique(tmp_path):
    cible = tmp_path / "manifeste_original.txt"
    cible.write_text(
        f"{'a' * 64}  database/001_exemple.sql\n",
        encoding="ascii",
    )

    lien = tmp_path / "migrations_sha256.txt"
    lien.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Manifeste symbolique interdit",
    ):
        lire_manifeste_migrations(lien)


def test_lire_manifeste_migrations_lien_symbolique_casse(
    tmp_path,
):
    cible = tmp_path / "manifeste_absent.txt"

    lien = tmp_path / "migrations_sha256.txt"
    lien.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Manifeste symbolique interdit",
    ):
        lire_manifeste_migrations(lien)


def test_decouvrir_migrations_lien_symbolique_auxiliaire(
    tmp_path,
):
    migration = tmp_path / "001_exemple.sql"
    migration.write_text("SELECT 1;", encoding="ascii")

    lien = tmp_path / "002_exemple_test_grants.sql"
    lien.symlink_to(migration)

    migrations = decouvrir_migrations(tmp_path)

    assert len(migrations) == 1
    assert migrations[0].nom == migration.name


def test_decouvrir_migrations_lien_symbolique_non_conforme(
    tmp_path,
):
    migration = tmp_path / "001_exemple.sql"
    migration.write_text("SELECT 1;", encoding="ascii")

    lien = tmp_path / "exemple.sql"
    lien.symlink_to(migration)

    migrations = decouvrir_migrations(tmp_path)

    assert len(migrations) == 1
    assert migrations[0].nom == migration.name

@pytest.mark.parametrize(
    "contenu",
    [
        b"",
        b"SELECT 1;",
        b"\x00\x01\xff\xfe",
        b"A" * 65536,
        b"B" * 65537,
        b"C" * 200000,
    ],
)
def test_lire_fichier_securise_contenu(
    tmp_path,
    contenu,
):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(contenu)

    assert lire_fichier_securise(chemin) == contenu


def test_lire_fichier_securise_chemin_relatif(
    tmp_path,
    monkeypatch,
):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    monkeypatch.chdir(tmp_path)

    assert lire_fichier_securise(
        Path("exemple.sql"),
    ) == b"SELECT 1;"


def test_lire_fichier_securise_repertoires_imbriques(
    tmp_path,
):
    repertoire = tmp_path / "niveau1" / "niveau2"
    repertoire.mkdir(parents=True)

    chemin = repertoire / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    assert lire_fichier_securise(
        chemin,
    ) == b"SELECT 1;"

def test_lire_fichier_securise_remontee_interdite(
    tmp_path,
):
    repertoire = tmp_path / "niveau1"
    repertoire.mkdir()

    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    chemin_invalide = repertoire / ".." / chemin.name

    with pytest.raises(
        ValueError,
        match="Chemin contenant une remontée interdite",
    ):
        lire_fichier_securise(chemin_invalide)


def test_lire_fichier_securise_racine_interdite():
    with pytest.raises(
        ValueError,
        match="Chemin de fichier invalide",
    ):
        lire_fichier_securise(Path("/"))


def test_lire_fichier_securise_fichier_absent(tmp_path):
    chemin = tmp_path / "absent.sql"

    with pytest.raises(FileNotFoundError):
        lire_fichier_securise(chemin)


def test_lire_fichier_securise_parent_absent(tmp_path):
    chemin = tmp_path / "absent" / "exemple.sql"

    with pytest.raises(FileNotFoundError):
        lire_fichier_securise(chemin)


def test_lire_fichier_securise_parent_non_repertoire(
    tmp_path,
):
    parent = tmp_path / "parent"
    parent.write_bytes(b"SELECT 1;")

    with pytest.raises(NotADirectoryError):
        lire_fichier_securise(
            parent / "exemple.sql",
        )

@pytest.mark.parametrize(
    "cible_existante",
    [True, False],
)
def test_lire_fichier_securise_lien_symbolique(
    tmp_path,
    cible_existante,
):
    cible = tmp_path / "cible.sql"

    if cible_existante:
        cible.write_bytes(b"SELECT 1;")

    lien = tmp_path / "exemple.sql"
    lien.symlink_to(cible)

    with pytest.raises(OSError):
        lire_fichier_securise(lien)


def test_lire_fichier_securise_parent_symbolique(
    tmp_path,
):
    cible = tmp_path / "repertoire"
    cible.mkdir()

    chemin = cible / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lien = tmp_path / "lien"
    lien.symlink_to(
        cible,
        target_is_directory=True,
    )

    with pytest.raises(OSError):
        lire_fichier_securise(
            lien / chemin.name,
        )


def test_lire_fichier_securise_lien_physique(tmp_path):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lien = tmp_path / "copie.sql"
    os.link(chemin, lien)

    with pytest.raises(
        ValueError,
        match="Nombre de liens physiques invalide",
    ):
        lire_fichier_securise(chemin)


def test_lire_fichier_securise_repertoire(tmp_path):
    chemin = tmp_path / "exemple.sql"
    chemin.mkdir()

    with pytest.raises(
        ValueError,
        match="Fichier non régulier interdit",
    ):
        lire_fichier_securise(chemin)


def test_lire_fichier_securise_fifo(tmp_path):
    chemin = tmp_path / "exemple.sql"
    os.mkfifo(chemin)

    with pytest.raises(
        ValueError,
        match="Fichier non régulier interdit",
    ):
        lire_fichier_securise(chemin)

def test_lire_fichier_securise_modification_concurrente(
    tmp_path,
    monkeypatch,
):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lecture_originale = os.read

    def lire_et_modifier(descripteur, taille):
        contenu = lecture_originale(
            descripteur,
            taille,
        )

        if contenu:
            chemin.write_bytes(b"")

        return contenu

    monkeypatch.setattr(
        os,
        "read",
        lire_et_modifier,
    )

    with pytest.raises(
        ValueError,
        match="Fichier modifié pendant la lecture",
    ):
        lire_fichier_securise(chemin)


def test_lire_fichier_securise_erreur_lecture(
    tmp_path,
    monkeypatch,
):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    descripteurs = []

    def lecture_en_erreur(descripteur, taille):
        descripteurs.append(descripteur)
        raise OSError("Erreur de lecture simulée")

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "read",
            lecture_en_erreur,
        )

        with pytest.raises(
            OSError,
            match="Erreur de lecture simulée",
        ):
            lire_fichier_securise(chemin)

    assert len(descripteurs) == 1

    with pytest.raises(OSError):
        os.fstat(descripteurs[0])


def test_lire_fichier_securise_fermeture_descripteurs(
    tmp_path,
):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    repertoire_fd = Path("/proc/self/fd")
    avant = len(list(repertoire_fd.iterdir()))

    for _ in range(10):
        assert lire_fichier_securise(
            chemin,
        ) == b"SELECT 1;"

        with pytest.raises(FileNotFoundError):
            lire_fichier_securise(
                tmp_path / "absent.sql",
            )

    apres = len(list(repertoire_fd.iterdir()))

    assert apres == avant

def test_calculer_checksum_parent_symbolique(tmp_path):
    cible = tmp_path / "repertoire"
    cible.mkdir()

    chemin = cible / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lien = tmp_path / "lien"
    lien.symlink_to(
        cible,
        target_is_directory=True,
    )

    with pytest.raises(OSError):
        calculer_checksum(lien / chemin.name)


def test_calculer_checksum_lien_physique(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    os.link(
        chemin,
        tmp_path / "copie.sql",
    )

    with pytest.raises(
        ValueError,
        match="Nombre de liens physiques invalide",
    ):
        calculer_checksum(chemin)


def test_calculer_checksum_modification_concurrente(
    tmp_path,
    monkeypatch,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lecture_originale = os.read

    def lire_et_modifier(descripteur, taille):
        contenu = lecture_originale(
            descripteur,
            taille,
        )

        if contenu:
            chemin.write_bytes(b"")

        return contenu

    monkeypatch.setattr(
        os,
        "read",
        lire_et_modifier,
    )

    with pytest.raises(
        ValueError,
        match="Fichier modifié pendant la lecture",
    ):
        calculer_checksum(chemin)

def test_lire_manifeste_migrations_parent_symbolique(
    tmp_path,
):
    cible = tmp_path / "audit"
    cible.mkdir()

    chemin = cible / "migrations_sha256.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_exemple.sql\n",
        encoding="ascii",
    )

    lien = tmp_path / "lien"
    lien.symlink_to(
        cible,
        target_is_directory=True,
    )

    with pytest.raises(OSError):
        lire_manifeste_migrations(
            lien / chemin.name,
        )


def test_lire_manifeste_migrations_lien_physique(
    tmp_path,
):
    chemin = tmp_path / "migrations_sha256.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_exemple.sql\n",
        encoding="ascii",
    )

    os.link(
        chemin,
        tmp_path / "copie.txt",
    )

    with pytest.raises(
        ValueError,
        match="Nombre de liens physiques invalide",
    ):
        lire_manifeste_migrations(chemin)


def test_lire_manifeste_migrations_modification_concurrente(
    tmp_path,
    monkeypatch,
):
    chemin = tmp_path / "migrations_sha256.txt"
    chemin.write_text(
        f"{'a' * 64}  database/001_exemple.sql\n",
        encoding="ascii",
    )

    lecture_originale = os.read

    def lire_et_modifier(descripteur, taille):
        contenu = lecture_originale(
            descripteur,
            taille,
        )

        if contenu:
            chemin.write_bytes(b"")

        return contenu

    monkeypatch.setattr(
        os,
        "read",
        lire_et_modifier,
    )

    with pytest.raises(
        ValueError,
        match="Fichier modifié pendant la lecture",
    ):
        lire_manifeste_migrations(chemin)

def test_decouvrir_migrations_lien_physique(tmp_path):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    os.link(
        chemin,
        tmp_path / "copie.sql",
    )

    with pytest.raises(
        ValueError,
        match="Nombre de liens physiques invalide",
    ):
        decouvrir_migrations(tmp_path)


def test_decouvrir_migrations_parent_symbolique(
    tmp_path,
):
    cible = tmp_path / "projet"
    cible.mkdir()

    repertoire = cible / "database"
    repertoire.mkdir()

    chemin = repertoire / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lien = tmp_path / "lien"
    lien.symlink_to(
        cible,
        target_is_directory=True,
    )

    with pytest.raises(OSError):
        decouvrir_migrations(
            lien / "database",
        )

def test_ouvrir_repertoire_securise_conforme(tmp_path):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    descripteur = ouvrir_repertoire_securise(repertoire)

    try:
        informations = os.fstat(descripteur)
        attendu = repertoire.stat()

        assert informations.st_ino == attendu.st_ino
        assert informations.st_dev == attendu.st_dev
        assert os.listdir(descripteur) == []
        assert not os.get_inheritable(descripteur)

    finally:
        os.close(descripteur)


def test_ouvrir_repertoire_securise_racine():
    descripteur = ouvrir_repertoire_securise(Path("/"))

    try:
        assert os.fstat(descripteur).st_ino == Path("/").stat().st_ino

    finally:
        os.close(descripteur)


def test_ouvrir_repertoire_securise_relatif(
    tmp_path,
    monkeypatch,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    monkeypatch.chdir(tmp_path)

    descripteur = ouvrir_repertoire_securise(
        Path("database"),
    )

    try:
        assert os.listdir(descripteur) == []

    finally:
        os.close(descripteur)


def test_ouvrir_repertoire_securise_remontee_interdite(
    tmp_path,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    with pytest.raises(
        ValueError,
        match="Chemin contenant une remontée interdite",
    ):
        ouvrir_repertoire_securise(
            repertoire / "..",
        )


def test_ouvrir_repertoire_securise_absent(tmp_path):
    with pytest.raises(FileNotFoundError):
        ouvrir_repertoire_securise(
            tmp_path / "absent",
        )


def test_ouvrir_repertoire_securise_fichier(tmp_path):
    chemin = tmp_path / "exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    with pytest.raises(NotADirectoryError):
        ouvrir_repertoire_securise(chemin)


@pytest.mark.parametrize(
    "cible_existante",
    [True, False],
)
def test_ouvrir_repertoire_securise_lien_symbolique(
    tmp_path,
    cible_existante,
):
    cible = tmp_path / "database"

    if cible_existante:
        cible.mkdir()

    lien = tmp_path / "lien"
    lien.symlink_to(
        cible,
        target_is_directory=True,
    )

    with pytest.raises(OSError):
        ouvrir_repertoire_securise(lien)


def test_decouvrir_migrations_parent_symbolique_vide(
    tmp_path,
):
    cible = tmp_path / "projet"
    cible.mkdir()

    repertoire = cible / "database"
    repertoire.mkdir()

    lien = tmp_path / "lien"
    lien.symlink_to(
        cible,
        target_is_directory=True,
    )

    assert decouvrir_migrations(repertoire) == []

    with pytest.raises(OSError):
        decouvrir_migrations(
            lien / "database",
        )


def test_decouvrir_migrations_remontee_interdite(
    tmp_path,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    with pytest.raises(
        ValueError,
        match="Chemin contenant une remontée interdite",
    ):
        decouvrir_migrations(
            repertoire / ".." / "database",
        )

def test_decouvrir_migrations_erreur_enumeration(
    tmp_path,
    monkeypatch,
):
    descripteurs = []

    def enumeration_en_erreur(descripteur):
        descripteurs.append(descripteur)
        raise OSError("Erreur enumeration simulee")

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "listdir",
            enumeration_en_erreur,
        )

        with pytest.raises(
            OSError,
            match="Erreur enumeration simulee",
        ):
            decouvrir_migrations(tmp_path)

    assert len(descripteurs) == 1

    with pytest.raises(OSError):
        os.fstat(descripteurs[0])


def test_ouvrir_repertoire_securise_fermeture_sur_erreur(
    tmp_path,
):
    repertoire_fd = Path("/proc/self/fd")
    avant = len(list(repertoire_fd.iterdir()))

    for _ in range(10):
        with pytest.raises(FileNotFoundError):
            ouvrir_repertoire_securise(
                tmp_path / "absent",
            )

    apres = len(list(repertoire_fd.iterdir()))

    assert apres == avant


def test_decouvrir_migrations_fermeture_descripteurs(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    repertoire_fd = Path("/proc/self/fd")
    avant = len(list(repertoire_fd.iterdir()))

    for _ in range(10):
        migrations = decouvrir_migrations(tmp_path)

        assert len(migrations) == 1
        assert migrations[0].nom == chemin.name

    apres = len(list(repertoire_fd.iterdir()))

    assert apres == avant

@pytest.mark.parametrize(
    "nom",
    [
        "",
        ".",
        "..",
        "../exemple.sql",
        "/exemple.sql",
        "sous_repertoire/exemple.sql",
    ],
)
def test_lire_fichier_depuis_repertoire_nom_invalide(
    tmp_path,
    nom,
):
    descripteur = ouvrir_repertoire_securise(tmp_path)

    try:
        with pytest.raises(
            ValueError,
            match="Nom de fichier invalide",
        ):
            _lire_fichier_depuis_repertoire(
                descripteur,
                nom,
                tmp_path / nom,
            )

        assert os.listdir(descripteur) == []

    finally:
        os.close(descripteur)

@pytest.mark.parametrize(
    "operation",
    ["substitution", "modification"],
)
def test_decouvrir_migrations_modification_avant_lecture(
    tmp_path,
    monkeypatch,
    operation,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    remplacement = tmp_path / "remplacement.tmp"
    remplacement.write_bytes(b"SELECT 999;")

    ouverture_originale = os.open
    descripteurs = []

    def ouvrir_et_modifier(
        nom,
        options,
        *args,
        **kwargs,
    ):
        if (
            nom == chemin.name
            and kwargs.get("dir_fd") is not None
        ):
            if operation == "substitution":
                remplacement.replace(chemin)
            else:
                chemin.write_bytes(b"SELECT 123456;")

            descripteur = ouverture_originale(
                nom,
                options,
                *args,
                **kwargs,
            )

            descripteurs.append(descripteur)

            return descripteur

        return ouverture_originale(
            nom,
            options,
            *args,
            **kwargs,
        )

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "open",
            ouvrir_et_modifier,
        )

        with pytest.raises(
            ValueError,
            match="Fichier modifié avant la lecture",
        ):
            decouvrir_migrations(tmp_path)

    assert len(descripteurs) == 1

    with pytest.raises(OSError):
        os.fstat(descripteurs[0])


def test_decouvrir_migrations_ancrage_physique(
    tmp_path,
    monkeypatch,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    archive = tmp_path / "database_initial"

    nom = "001_exemple.sql"
    contenu_initial = b"SELECT 1;"
    contenu_substitue = b"SELECT 999;"

    (repertoire / nom).write_bytes(contenu_initial)

    enumeration_originale = os.listdir
    lecture_originale = os.read

    contenus_lus = []

    def enumerer_et_substituer(descripteur):
        noms = enumeration_originale(descripteur)

        repertoire.rename(archive)
        repertoire.mkdir()

        (repertoire / nom).write_bytes(
            contenu_substitue,
        )

        return noms

    def lire_et_enregistrer(descripteur, taille):
        contenu = lecture_originale(
            descripteur,
            taille,
        )

        contenus_lus.append(contenu)

        return contenu

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "listdir",
            enumerer_et_substituer,
        )

        contexte.setattr(
            os,
            "read",
            lire_et_enregistrer,
        )

        with pytest.raises(
            ValueError,
            match="Répertoire modifié pendant l'inventaire",
        ):
            decouvrir_migrations(repertoire)

    assert b"".join(contenus_lus) == contenu_initial
    assert (archive / nom).read_bytes() == contenu_initial
    assert (repertoire / nom).read_bytes() == contenu_substitue


def test_decouvrir_migrations_modification_pendant_lecture(
    tmp_path,
    monkeypatch,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    lecture_originale = os.read

    def lire_et_modifier(descripteur, taille):
        contenu = lecture_originale(
            descripteur,
            taille,
        )

        if contenu:
            chemin.write_bytes(b"")

        return contenu

    monkeypatch.setattr(
        os,
        "read",
        lire_et_modifier,
    )

    with pytest.raises(
        ValueError,
        match="Fichier modifié pendant la lecture",
    ):
        decouvrir_migrations(tmp_path)

@pytest.mark.parametrize(
    "nombre",
    [1, 3, 22],
)
def test_decouvrir_migrations_nombre_ouvertures_repertoire(
    tmp_path,
    monkeypatch,
    nombre,
):
    import migration_manager

    for numero in range(1, nombre + 1):
        chemin = tmp_path / f"{numero:03d}_exemple.sql"
        chemin.write_bytes(
            f"SELECT {numero};".encode("ascii"),
        )

    ouverture_originale = (
        migration_manager.ouvrir_repertoire_securise
    )

    ouvertures = []

    def ouvrir_et_compter(repertoire):
        ouvertures.append(repertoire)

        return ouverture_originale(repertoire)

    monkeypatch.setattr(
        migration_manager,
        "ouvrir_repertoire_securise",
        ouvrir_et_compter,
    )

    migrations = decouvrir_migrations(tmp_path)

    assert len(migrations) == nombre
    assert ouvertures == [tmp_path, tmp_path]

@pytest.mark.parametrize(
    "nombre",
    [1, 3],
)
def test_revalider_inventaire_migrations_conforme(
    tmp_path,
    nombre,
):
    for numero in range(1, nombre + 1):
        chemin = tmp_path / f"{numero:03d}_exemple.sql"
        chemin.write_bytes(
            f"SELECT {numero};".encode("ascii"),
        )

    initial = decouvrir_migrations(tmp_path)

    actuel = revalider_inventaire_migrations(
        tmp_path,
        initial,
    )

    assert actuel == initial
    assert actuel is not initial
    assert len(actuel) == nombre

    for ancienne, nouvelle in zip(
        initial,
        actuel,
        strict=True,
    ):
        assert ancienne is not nouvelle


def test_revalider_inventaire_migrations_ordre(
    tmp_path,
):
    for numero in range(1, 4):
        chemin = tmp_path / f"{numero:03d}_exemple.sql"
        chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)
    inverse = list(reversed(initial))

    actuel = revalider_inventaire_migrations(
        tmp_path,
        inverse,
    )

    assert actuel == initial
    assert inverse == list(reversed(initial))


def test_revalider_inventaire_migrations_chemin_absolu(
    tmp_path,
    monkeypatch,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    chemin = repertoire / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    monkeypatch.chdir(tmp_path)

    initial = decouvrir_migrations(repertoire)

    actuel = revalider_inventaire_migrations(
        Path("database"),
        initial,
    )

    assert len(actuel) == 1
    assert actuel[0].chemin == Path(
        "database/001_exemple.sql",
    )
    assert actuel[0].chemin.absolute() == chemin
    assert (
        actuel[0].checksum_sha256
        == initial[0].checksum_sha256
    )

def test_revalider_inventaire_migrations_vide(
    tmp_path,
):
    with pytest.raises(
        ValueError,
        match="Inventaire de migrations vide",
    ):
        revalider_inventaire_migrations(
            tmp_path,
            [],
        )


def test_revalider_inventaire_migrations_doublon(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    with pytest.raises(
        ValueError,
        match="Migration présente en double",
    ):
        revalider_inventaire_migrations(
            tmp_path,
            initial + initial,
        )


@pytest.mark.parametrize(
    ("champ", "valeur", "message"),
    [
        (
            "numero",
            2,
            "Numéro de migration incohérent",
        ),
        (
            "numero",
            True,
            "Numéro de migration incohérent",
        ),
        (
            "nom",
            "exemple.sql",
            "Nom de migration invalide",
        ),
        (
            "checksum_sha256",
            "invalide",
            "Empreinte SHA-256 de migration invalide",
        ),
    ],
)
def test_revalider_inventaire_migrations_structure(
    tmp_path,
    champ,
    valeur,
    message,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    migration = replace(
        initial[0],
        **{champ: valeur},
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        revalider_inventaire_migrations(
            tmp_path,
            [migration],
        )

@pytest.mark.parametrize(
    "scenario",
    [
        "autre_repertoire",
        "autre_fichier",
        "type_invalide",
    ],
)
def test_revalider_inventaire_migrations_chemin_incoherent(
    tmp_path,
    scenario,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    if scenario == "autre_repertoire":
        chemin_invalide = (
            tmp_path / "autre" / chemin.name
        )
    elif scenario == "autre_fichier":
        chemin_invalide = (
            tmp_path / "002_exemple.sql"
        )
    else:
        chemin_invalide = str(chemin)

    migration = replace(
        initial[0],
        chemin=chemin_invalide,
    )

    with pytest.raises(
        ValueError,
        match="Chemin de migration incohérent",
    ):
        revalider_inventaire_migrations(
            tmp_path,
            [migration],
        )

@pytest.mark.parametrize(
    ("operation", "message"),
    [
        (
            "suppression",
            "Migrations disparues depuis l'inventaire",
        ),
        (
            "ajout",
            "Migrations ajoutées depuis l'inventaire",
        ),
        (
            "renommage",
            "Migrations disparues depuis l'inventaire",
        ),
        (
            "modification",
            "Migration modifiée depuis l'inventaire",
        ),
        (
            "troncature",
            "Migration modifiée depuis l'inventaire",
        ),
    ],
)
def test_revalider_inventaire_migrations_divergence(
    tmp_path,
    operation,
    message,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    if operation == "suppression":
        chemin.unlink()
    elif operation == "ajout":
        nouveau = tmp_path / "002_exemple.sql"
        nouveau.write_bytes(b"SELECT 2;")
    elif operation == "renommage":
        chemin.rename(
            tmp_path / "001_renommee.sql",
        )
    elif operation == "modification":
        chemin.write_bytes(b"SELECT 2;")
    else:
        chemin.write_bytes(b"")

    with pytest.raises(
        ValueError,
        match=message,
    ):
        revalider_inventaire_migrations(
            tmp_path,
            initial,
        )

@pytest.mark.parametrize(
    "cible_existante",
    [True, False],
)
def test_revalider_inventaire_migrations_lien_symbolique(
    tmp_path,
    cible_existante,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    cible = tmp_path / "cible.tmp"

    if cible_existante:
        cible.write_bytes(b"SELECT 1;")

    chemin.unlink()
    chemin.symlink_to(cible)

    with pytest.raises(
        ValueError,
        match="Lien symbolique interdit",
    ):
        revalider_inventaire_migrations(
            tmp_path,
            initial,
        )


def test_revalider_inventaire_migrations_lien_physique(
    tmp_path,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    os.link(
        chemin,
        tmp_path / "copie.tmp",
    )

    with pytest.raises(
        ValueError,
        match="Nombre de liens physiques invalide",
    ):
        revalider_inventaire_migrations(
            tmp_path,
            initial,
        )


@pytest.mark.parametrize(
    "type_objet",
    ["repertoire", "fifo"],
)
def test_revalider_inventaire_migrations_non_reguliere(
    tmp_path,
    type_objet,
):
    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    initial = decouvrir_migrations(tmp_path)

    chemin.unlink()

    if type_objet == "repertoire":
        chemin.mkdir()
    else:
        os.mkfifo(chemin)

    with pytest.raises(
        ValueError,
        match="Migrations disparues depuis l'inventaire",
    ):
        revalider_inventaire_migrations(
            tmp_path,
            initial,
        )

def test_revalider_inventaire_migrations_repertoire_substitue(
    tmp_path,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    nom = "001_exemple.sql"

    (repertoire / nom).write_bytes(
        b"SELECT 1;",
    )

    initial = decouvrir_migrations(repertoire)

    repertoire.rename(
        tmp_path / "database_initial",
    )

    repertoire.mkdir()

    (repertoire / nom).write_bytes(
        b"SELECT 2;",
    )

    with pytest.raises(
        ValueError,
        match="Migration modifiée depuis l'inventaire",
    ):
        revalider_inventaire_migrations(
            repertoire,
            initial,
        )


def test_revalider_inventaire_migrations_reel():
    racine = Path(__file__).resolve().parents[1]
    repertoire = racine / "database"

    initial = decouvrir_migrations(repertoire)

    actuel = revalider_inventaire_migrations(
        repertoire,
        initial,
    )

    manifeste = lire_manifeste_migrations(
        racine / "docs/audit/migrations_sha256.txt",
    )

    valider_perimetre_baseline(
        actuel,
        manifeste,
    )

    assert len(actuel) == 22
    assert actuel == initial
    assert actuel is not initial

@pytest.mark.parametrize(
    "operation",
    ["ajout", "suppression", "renommage"],
)
def test_decouvrir_migrations_identite_entrees(
    tmp_path,
    monkeypatch,
    operation,
):
    migration = tmp_path / "001_exemple.sql"
    migration.write_bytes(b"SELECT 1;")

    auxiliaire = tmp_path / "auxiliaire.tmp"
    auxiliaire.write_bytes(b"Initial")

    enumeration_originale = os.listdir

    def enumerer_et_modifier(descripteur):
        noms = enumeration_originale(descripteur)

        if operation == "ajout":
            nouveau = tmp_path / "nouveau.tmp"
            nouveau.write_bytes(b"Nouveau")
        elif operation == "suppression":
            auxiliaire.unlink()
        else:
            auxiliaire.rename(
                tmp_path / "renomme.tmp",
            )

        return noms

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "listdir",
            enumerer_et_modifier,
        )

        with pytest.raises(
            ValueError,
            match="Répertoire modifié pendant l'inventaire",
        ):
            decouvrir_migrations(tmp_path)

def test_decouvrir_migrations_identite_permissions(
    tmp_path,
    monkeypatch,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir(mode=0o700)

    chemin = repertoire / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    enumeration_originale = os.listdir

    def enumerer_et_modifier(descripteur):
        noms = enumeration_originale(descripteur)

        repertoire.chmod(0o750)

        return noms

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "listdir",
            enumerer_et_modifier,
        )

        with pytest.raises(
            ValueError,
            match="Répertoire modifié pendant l'inventaire",
        ):
            decouvrir_migrations(repertoire)

@pytest.mark.parametrize(
    "substitution",
    ["symbolique", "contenu_identique"],
)
def test_decouvrir_migrations_identite_substitution(
    tmp_path,
    monkeypatch,
    substitution,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    archive = tmp_path / "database_initial"

    nom = "001_exemple.sql"
    contenu = b"SELECT 1;"

    (repertoire / nom).write_bytes(contenu)

    enumeration_originale = os.listdir

    def enumerer_et_substituer(descripteur):
        noms = enumeration_originale(descripteur)

        repertoire.rename(archive)

        if substitution == "symbolique":
            repertoire.symlink_to(
                archive,
                target_is_directory=True,
            )
        else:
            repertoire.mkdir()

            (repertoire / nom).write_bytes(
                contenu,
            )

        return noms

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "listdir",
            enumerer_et_substituer,
        )

        if substitution == "symbolique":
            with pytest.raises(OSError):
                decouvrir_migrations(repertoire)
        else:
            with pytest.raises(
                ValueError,
                match="Répertoire modifié pendant l'inventaire",
            ):
                decouvrir_migrations(repertoire)

def test_revalider_inventaire_migrations_identite_concurrente(
    tmp_path,
    monkeypatch,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    archive = tmp_path / "database_initial"

    nom = "001_exemple.sql"
    contenu = b"SELECT 1;"

    (repertoire / nom).write_bytes(contenu)

    initial = decouvrir_migrations(repertoire)

    enumeration_originale = os.listdir

    def enumerer_et_substituer(descripteur):
        noms = enumeration_originale(descripteur)

        repertoire.rename(archive)
        repertoire.mkdir()

        (repertoire / nom).write_bytes(contenu)

        return noms

    with monkeypatch.context() as contexte:
        contexte.setattr(
            os,
            "listdir",
            enumerer_et_substituer,
        )

        with pytest.raises(
            ValueError,
            match="Répertoire modifié pendant l'inventaire",
        ):
            revalider_inventaire_migrations(
                repertoire,
                initial,
            )

@pytest.mark.parametrize(
    "scenario",
    [
        "ouverture_finale",
        "fstat_final",
        "fstat_initial",
    ],
)
def test_decouvrir_migrations_identite_erreur_systeme(
    tmp_path,
    monkeypatch,
    scenario,
):
    import migration_manager

    chemin = tmp_path / "001_exemple.sql"
    chemin.write_bytes(b"SELECT 1;")

    ouverture_originale = (
        migration_manager.ouvrir_repertoire_securise
    )

    fstat_original = os.fstat

    descripteurs = []
    appels = []

    def ouvrir_et_enregistrer(repertoire):
        appels.append(repertoire)

        if (
            len(appels) == 2
            and scenario == "ouverture_finale"
        ):
            raise OSError(
                "Erreur identite simulee",
            )

        descripteur = ouverture_originale(
            repertoire,
        )

        descripteurs.append(descripteur)

        return descripteur

    def fstat_et_controler(descripteur):
        if len(descripteurs) == 2:
            if (
                scenario == "fstat_final"
                and descripteur == descripteurs[1]
            ):
                raise OSError(
                    "Erreur identite simulee",
                )

            if (
                scenario == "fstat_initial"
                and descripteur == descripteurs[0]
            ):
                raise OSError(
                    "Erreur identite simulee",
                )

        return fstat_original(descripteur)

    repertoire_fd = Path("/proc/self/fd")
    avant = len(list(repertoire_fd.iterdir()))

    with monkeypatch.context() as contexte:
        contexte.setattr(
            migration_manager,
            "ouvrir_repertoire_securise",
            ouvrir_et_enregistrer,
        )

        contexte.setattr(
            os,
            "fstat",
            fstat_et_controler,
        )

        with pytest.raises(
            OSError,
            match="Erreur identite simulee",
        ):
            decouvrir_migrations(tmp_path)

    assert len(appels) == 2

    if scenario == "ouverture_finale":
        assert len(descripteurs) == 1
    else:
        assert len(descripteurs) == 2

    for descripteur in descripteurs:
        with pytest.raises(OSError):
            os.fstat(descripteur)

    apres = len(list(repertoire_fd.iterdir()))

    assert apres == avant

def test_revalider_inventaire_migrations_identite_intermediaire(
    tmp_path,
):
    repertoire = tmp_path / "database"
    repertoire.mkdir()

    archive = tmp_path / "database_initial"

    nom = "001_exemple.sql"
    contenu = b"SELECT 1;"

    (repertoire / nom).write_bytes(contenu)

    initial = decouvrir_migrations(repertoire)

    inode_initial = repertoire.stat().st_ino

    repertoire.rename(archive)
    repertoire.mkdir()

    (repertoire / nom).write_bytes(contenu)

    inode_actuel = repertoire.stat().st_ino

    actuel = revalider_inventaire_migrations(
        repertoire,
        initial,
    )

    assert inode_actuel != inode_initial
    assert actuel == initial
    assert actuel is not initial

def test_capturer_manifeste_migrations_structure(
    tmp_path,
):
    chemin = tmp_path / "manifeste.txt"

    checksum = hashlib.sha256(
        b"SELECT 1;",
    ).hexdigest()

    nom = "001_exemple.sql"

    contenu = (
        f"{checksum}  database/{nom}\n"
    ).encode("ascii")

    chemin.write_bytes(contenu)

    reference = capturer_manifeste_migrations(
        chemin,
    )

    assert isinstance(
        reference,
        ManifesteMigrations,
    )

    assert reference.chemin == chemin.absolute()

    assert reference.checksum_sha256 == (
        hashlib.sha256(contenu).hexdigest()
    )

    assert reference.entrees == (
        (nom, checksum),
    )

    assert isinstance(reference.entrees, tuple)
    assert isinstance(reference.entrees[0], tuple)

@pytest.mark.parametrize(
    "attribut",
    ["chemin", "checksum_sha256", "entrees"],
)
def test_capturer_manifeste_migrations_immutabilite(
    tmp_path,
    attribut,
):
    chemin = tmp_path / "manifeste.txt"

    chemin.write_bytes(
        f"{'a' * 64}  database/001_exemple.sql\n"
        .encode("ascii"),
    )

    reference = capturer_manifeste_migrations(
        chemin,
    )

    with pytest.raises(FrozenInstanceError):
        setattr(
            reference,
            attribut,
            None,
        )

@pytest.mark.parametrize(
    "operation",
    ["capture", "lecture", "revalidation"],
)
def test_manifeste_migrations_lecture_unique(
    tmp_path,
    monkeypatch,
    operation,
):
    import migration_manager

    chemin = tmp_path / "manifeste.txt"

    chemin.write_bytes(
        f"{'a' * 64}  database/001_exemple.sql\n"
        .encode("ascii"),
    )

    reference = capturer_manifeste_migrations(
        chemin,
    )

    lecture_originale = (
        migration_manager.lire_fichier_securise
    )

    lectures = []

    def lire_et_compter(chemin_lu):
        lectures.append(chemin_lu)

        return lecture_originale(
            chemin_lu,
        )

    monkeypatch.setattr(
        migration_manager,
        "lire_fichier_securise",
        lire_et_compter,
    )

    if operation == "capture":
        capturer_manifeste_migrations(chemin)

    elif operation == "lecture":
        lire_manifeste_migrations(chemin)

    else:
        revalider_manifeste_migrations(
            chemin,
            reference,
        )

    assert lectures == [chemin.absolute()]

@pytest.mark.parametrize(
    "relatif",
    [True, False],
)
def test_revalider_manifeste_migrations_conforme(
    tmp_path,
    monkeypatch,
    relatif,
):
    chemin = tmp_path / "manifeste.txt"

    chemin.write_bytes(
        f"{'a' * 64}  database/001_exemple.sql\n"
        .encode("ascii"),
    )

    reference = capturer_manifeste_migrations(
        chemin,
    )

    if relatif:
        monkeypatch.chdir(tmp_path)
        chemin = Path("manifeste.txt")

    actuel = revalider_manifeste_migrations(
        chemin,
        reference,
    )

    assert actuel == reference
    assert actuel is not reference
    assert actuel.chemin.is_absolute()

    assert lire_manifeste_migrations(
        chemin,
    ) == dict(reference.entrees)

@pytest.mark.parametrize(
    ("scenario", "exception", "message"),
    [
        (
            "type",
            TypeError,
            "Référence de manifeste invalide",
        ),
        (
            "chemin_type",
            ValueError,
            "Chemin de manifeste incohérent",
        ),
        (
            "chemin_different",
            ValueError,
            "Chemin de manifeste incohérent",
        ),
        (
            "checksum",
            ValueError,
            "Manifeste modifié depuis sa capture",
        ),
        (
            "entrees",
            ValueError,
            "Entrées du manifeste incohérentes",
        ),
    ],
)
def test_revalider_manifeste_migrations_reference_invalide(
    tmp_path,
    scenario,
    exception,
    message,
):
    chemin = tmp_path / "manifeste.txt"

    chemin.write_bytes(
        f"{'a' * 64}  database/001_exemple.sql\n"
        .encode("ascii"),
    )

    reference = capturer_manifeste_migrations(
        chemin,
    )

    if scenario == "type":
        reference = {}

    elif scenario == "chemin_type":
        reference = replace(
            reference,
            chemin=str(chemin),
        )

    elif scenario == "chemin_different":
        reference = replace(
            reference,
            chemin=tmp_path / "autre.txt",
        )

    elif scenario == "checksum":
        reference = replace(
            reference,
            checksum_sha256="0" * 64,
        )

    else:
        reference = replace(
            reference,
            entrees=(),
        )

    with pytest.raises(
        exception,
        match=message,
    ):
        revalider_manifeste_migrations(
            chemin,
            reference,
        )

@pytest.mark.parametrize(
    "operation",
    [
        "checksum",
        "ajout",
        "suppression",
        "ordre",
        "sans_lf_final",
        "crlf",
    ],
)
def test_revalider_manifeste_migrations_divergence_binaire(
    tmp_path,
    operation,
):
    chemin = tmp_path / "manifeste.txt"

    premiere = (
        f"{'a' * 64}  database/001_exemple.sql\n"
    ).encode("ascii")

    seconde = (
        f"{'b' * 64}  database/002_exemple.sql\n"
    ).encode("ascii")

    contenu = premiere + seconde

    chemin.write_bytes(contenu)

    reference = capturer_manifeste_migrations(
        chemin,
    )

    if operation == "checksum":
        nouveau = (
            b"c" * 64
            + premiere[64:]
            + seconde
        )

    elif operation == "ajout":
        nouveau = contenu + (
            f"{'d' * 64}  database/003_exemple.sql\n"
        ).encode("ascii")

    elif operation == "suppression":
        nouveau = premiere

    elif operation == "ordre":
        nouveau = seconde + premiere

    elif operation == "sans_lf_final":
        nouveau = contenu.removesuffix(b"\n")

    else:
        nouveau = contenu.replace(
            b"\n",
            b"\r\n",
        )

    chemin.write_bytes(nouveau)

    if operation == "sans_lf_final":
        message = "Manifeste sans LF final"

    elif operation == "crlf":
        message = "Ligne de manifeste invalide : 1"

    else:
        message = "Manifeste modifié depuis sa capture"

    if operation == "ordre":
        assert lire_manifeste_migrations(
            chemin,
        ) == dict(reference.entrees)

    if operation in {"sans_lf_final", "crlf"}:
        with pytest.raises(
            ValueError,
            match=message,
        ):
            lire_manifeste_migrations(chemin)

    with pytest.raises(
        ValueError,
        match=message,
    ):
        revalider_manifeste_migrations(
            chemin,
            reference,
        )


@pytest.mark.parametrize(
    "scenario",
    [
        "suppression",
        "symbolique",
        "physique",
        "contenu_modifie",
        "contenu_identique",
    ],
)
def test_revalider_manifeste_migrations_substitution(
    tmp_path,
    scenario,
):
    chemin = tmp_path / "manifeste.txt"
    archive = tmp_path / "manifeste_initial.txt"

    contenu = (
        f"{'a' * 64}  database/001_exemple.sql\n"
    ).encode("ascii")

    chemin.write_bytes(contenu)

    reference = capturer_manifeste_migrations(
        chemin,
    )

    inode_initial = chemin.stat().st_ino

    chemin.rename(archive)

    if scenario == "suppression":
        with pytest.raises(
            ValueError,
            match="Manifeste de migrations introuvable",
        ):
            revalider_manifeste_migrations(
                chemin,
                reference,
            )

    elif scenario == "symbolique":
        chemin.symlink_to(archive)

        with pytest.raises(
            ValueError,
            match="Manifeste symbolique interdit",
        ):
            revalider_manifeste_migrations(
                chemin,
                reference,
            )

    elif scenario == "physique":
        os.link(archive, chemin)

        with pytest.raises(
            ValueError,
            match="Nombre de liens physiques invalide",
        ):
            revalider_manifeste_migrations(
                chemin,
                reference,
            )

    elif scenario == "contenu_modifie":
        chemin.write_bytes(
            b"b" * 64 + contenu[64:],
        )

        with pytest.raises(
            ValueError,
            match="Manifeste modifié depuis sa capture",
        ):
            revalider_manifeste_migrations(
                chemin,
                reference,
            )

    else:
        chemin.write_bytes(contenu)

        assert chemin.stat().st_ino != inode_initial

        actuel = revalider_manifeste_migrations(
            chemin,
            reference,
        )

        assert actuel == reference
        assert actuel is not reference

def test_revalider_manifeste_migrations_reel():
    racine = Path(__file__).resolve().parents[1]

    repertoire = racine / "database"

    chemin = (
        racine
        / "docs"
        / "audit"
        / "migrations_sha256.txt"
    )

    inventaire = decouvrir_migrations(
        repertoire,
    )

    reference = capturer_manifeste_migrations(
        chemin,
    )

    migrations = revalider_inventaire_migrations(
        repertoire,
        inventaire,
    )

    actuel = revalider_manifeste_migrations(
        chemin,
        reference,
    )

    valider_perimetre_baseline(
        migrations,
        dict(actuel.entrees),
    )

    assert len(migrations) == 22
    assert len(actuel.entrees) == 22
    assert actuel == reference
    assert actuel is not reference

@pytest.mark.parametrize(
    "separateur",
    [
        b"\r\n",
        b"\r",
        b"\x0b",
        b"\x0c",
        b"\x1c",
        b"\x1d",
        b"\x1e",
    ],
)
def test_capturer_manifeste_migrations_separateur_interdit(
    tmp_path,
    separateur,
):
    chemin = tmp_path / "manifeste.txt"

    premiere = (
        f"{'a' * 64}  database/001_exemple.sql"
    ).encode("ascii")

    seconde = (
        f"{'b' * 64}  database/002_exemple.sql"
    ).encode("ascii")

    chemin.write_bytes(
        premiere + separateur + seconde + b"\n",
    )

    with pytest.raises(
        ValueError,
        match="Ligne de manifeste invalide : 1",
    ):
        capturer_manifeste_migrations(chemin)

@pytest.mark.parametrize(
    "octet",
    [
        valeur
        for valeur in range(32)
        if valeur != 10
    ] + [127],
)
def test_capturer_manifeste_migrations_controle_ascii(
    tmp_path,
    octet,
):
    chemin = tmp_path / "manifeste.txt"

    contenu = (
        f"{'a' * 64}  database/001_exemple.sql\n"
    ).encode("ascii")

    contenu = (
        contenu[:32]
        + bytes([octet])
        + contenu[32:]
    )

    chemin.write_bytes(contenu)

    with pytest.raises(
        ValueError,
        match="Ligne de manifeste invalide : 1",
    ):
        capturer_manifeste_migrations(chemin)

@pytest.mark.parametrize(
    ("suffixe", "message"),
    [
        (
            b"",
            "Manifeste sans LF final",
        ),
        (
            b"\r",
            "Manifeste sans LF final",
        ),
        (
            b"\r\n",
            "Ligne de manifeste invalide : 1",
        ),
        (
            b"\n\n",
            "Ligne de manifeste invalide : 2",
        ),
        (
            b"\n\n\n",
            "Ligne de manifeste invalide : 2",
        ),
    ],
)
def test_capturer_manifeste_migrations_terminaison(
    tmp_path,
    suffixe,
    message,
):
    chemin = tmp_path / "manifeste.txt"

    ligne = (
        f"{'a' * 64}  database/001_exemple.sql"
    ).encode("ascii")

    chemin.write_bytes(
        ligne + suffixe,
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        capturer_manifeste_migrations(chemin)

@pytest.mark.parametrize(
    "encodage",
    [
        "utf-8-sig",
        "utf-16",
        "utf-32",
        "utf-16-be",
    ],
)
def test_capturer_manifeste_migrations_encodage_interdit(
    tmp_path,
    encodage,
):
    chemin = tmp_path / "manifeste.txt"

    texte = (
        f"{'a' * 64}  database/001_exemple.sql\n"
    )

    chemin.write_bytes(
        texte.encode(encodage),
    )

    with pytest.raises(
        ValueError,
    ):
        capturer_manifeste_migrations(chemin)

def test_capturer_manifeste_migrations_format_historique():
    racine = Path(__file__).resolve().parents[1]

    chemin = (
        racine
        / "docs"
        / "audit"
        / "migrations_sha256.txt"
    )

    contenu = lire_fichier_securise(chemin)

    reference = capturer_manifeste_migrations(
        chemin,
    )

    assert contenu.isascii()
    assert contenu.endswith(b"\n")
    assert contenu.count(b"\n") == 22

    assert all(
        octet == 10 or 32 <= octet <= 126
        for octet in contenu
    )

    assert len(reference.entrees) == 22

    assert reference.checksum_sha256 == (
        hashlib.sha256(contenu).hexdigest()
    )

    assert [
        int(nom[:3])
        for nom, _ in reference.entrees
    ] == list(range(1, 23))
