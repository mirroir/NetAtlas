"""Inventaire et contrôle d'intégrité des migrations NetAtlas."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

MIGRATION_PATTERN = re.compile(r"^([0-9]{3})_[a-zA-Z0-9_]+\.sql$")


@dataclass(frozen=True)
class Migration:
    """Description d'une migration SQL versionnée."""

    numero: int
    nom: str
    chemin: Path
    checksum_sha256: str


def calculer_checksum(chemin: Path) -> str:
    """Calcule l'empreinte SHA-256 du contenu exact d'un fichier."""

    contenu = chemin.read_bytes()
    return hashlib.sha256(contenu).hexdigest()


def decouvrir_migrations(repertoire: Path) -> list[Migration]:
    """Découvre les migrations SQL officielles sans les exécuter."""

    repertoire = Path(repertoire)

    if not repertoire.is_dir():
        raise ValueError(
            f"Répertoire de migrations introuvable : {repertoire}"
        )

    migrations = []
    numeros_vus = set()

    for chemin in sorted(repertoire.iterdir()):
        correspondance = MIGRATION_PATTERN.fullmatch(chemin.name)

        if not chemin.is_file() or correspondance is None:
            continue

        if chemin.name.endswith("_test_grants.sql"):
            continue

        numero = int(correspondance.group(1))

        if numero in numeros_vus:
            raise ValueError(
                f"Numéro de migration dupliqué : {numero:03d}"
            )

        numeros_vus.add(numero)

        migrations.append(
            Migration(
                numero=numero,
                nom=chemin.name,
                chemin=chemin,
                checksum_sha256=calculer_checksum(chemin),
            )
        )

    return sorted(
        migrations,
        key=lambda migration: migration.numero,
    )

def lire_migrations_enregistrees(connexion):
    """Lit le registre des migrations sans le modifier."""

    with connexion.cursor() as curseur:
        curseur.execute(
            """
            SELECT
                migration_key,
                file_path,
                checksum_sha256,
                application_mode,
                applied_at
            FROM public.schema_migrations
            ORDER BY migration_key
            """
        )

        lignes = curseur.fetchall()

    return [
        {
            "migration_key": ligne[0],
            "file_path": ligne[1],
            "checksum_sha256": ligne[2],
            "application_mode": ligne[3],
            "applied_at": ligne[4],
        }
        for ligne in lignes
    ]


def comparer_migrations(migrations, enregistrements):
    """Compare les migrations SQL avec leur historique enregistré."""

    fichiers = {}
    numeros_vus = set()

    for migration in migrations:
        correspondance = (
            MIGRATION_PATTERN.fullmatch(migration.nom)
            if isinstance(migration.nom, str)
            else None
        )

        if correspondance is None:
            raise ValueError(
                f"Nom de migration invalide : {migration.nom}"
            )

        numero_attendu = int(correspondance.group(1))

        if (
            type(migration.numero) is not int
            or migration.numero != numero_attendu
        ):
            raise ValueError(
                f"Numéro de migration incohérent : {migration.nom}"
            )

        checksum = migration.checksum_sha256

        if not isinstance(checksum, str) or not re.fullmatch(
            r"[0-9a-f]{64}", checksum
        ):
            raise ValueError(
                f"Empreinte SHA-256 de migration invalide : {migration.nom}"
            )

        cle = migration.nom.removesuffix(".sql")

        if cle in fichiers:
            raise ValueError(
                f"Migration présente en double : {cle}"
            )

        if migration.numero in numeros_vus:
            raise ValueError(
                f"Numéro de migration dupliqué : {migration.numero:03d}"
            )

        numeros_vus.add(migration.numero)
        fichiers[cle] = migration

    historiques = {}

    for ligne in enregistrements:
        cle = ligne.get("migration_key")
        chemin = ligne.get("file_path")
        mode = ligne.get("application_mode")

        if not isinstance(cle, str) or not MIGRATION_PATTERN.fullmatch(
            f"{cle}.sql"
        ):
            raise ValueError(
                f"Identifiant de migration invalide : {cle}"
            )

        chemin_attendu = f"database/{cle}.sql"

        if chemin != chemin_attendu:
            raise ValueError(
                f"Chemin de migration invalide : {cle}"
            )

        if not isinstance(mode, str) or mode not in {
            "executed",
            "baseline",
        }:
            raise ValueError(
                f"Mode de migration invalide : {cle}"
            )

        checksum = ligne.get("checksum_sha256")

        if not isinstance(checksum, str) or not re.fullmatch(
            r"[0-9a-f]{64}", checksum
        ):
            raise ValueError(
                f"Empreinte SHA-256 invalide : {cle}"
            )

        if cle in historiques:
            raise ValueError(
                f"Migration enregistrée en double : {cle}"
            )

        historiques[cle] = ligne

    resultats = []

    for cle, migration in fichiers.items():
        historique = historiques.get(cle)

        if historique is None:
            statut = "non_enregistree"
        elif historique["checksum_sha256"] != migration.checksum_sha256:
            statut = "integrite_invalide"
        else:
            statut = "conforme"

        resultats.append(
            {
                "migration_key": cle,
                "statut": statut,
            }
        )

    for cle in historiques.keys() - fichiers.keys():
        resultats.append(
            {
                "migration_key": cle,
                "statut": "inconnue",
            }
        )

    return sorted(
        resultats,
        key=lambda resultat: resultat["migration_key"],
    )
