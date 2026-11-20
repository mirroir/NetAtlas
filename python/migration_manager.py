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
