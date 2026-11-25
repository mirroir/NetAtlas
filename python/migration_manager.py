"""Inventaire et contrôle d'intégrité des migrations NetAtlas."""

import hashlib
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path

MIGRATION_PATTERN = re.compile(r"^([0-9]{3})_[a-zA-Z0-9_]+\.sql$")

BASELINE_PREMIERE_MIGRATION = 1
BASELINE_DERNIERE_MIGRATION = 22


@dataclass(frozen=True)
class Migration:
    """Description d'une migration SQL versionnée."""

    numero: int
    nom: str
    chemin: Path
    checksum_sha256: str


@dataclass(frozen=True)
class ManifesteMigrations:
    """Description immuable d'un manifeste de migrations."""

    chemin: Path
    checksum_sha256: str
    entrees: tuple[tuple[str, str], ...]


def ouvrir_repertoire_securise(repertoire: Path) -> int:
    """Ouvre un répertoire sans suivre de liens symboliques."""

    repertoire = Path(repertoire).absolute()

    if ".." in repertoire.parts:
        raise ValueError(
            f"Chemin contenant une remontée interdite : {repertoire}"
        )

    options = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
    )

    descripteur = os.open(
        repertoire.anchor,
        options,
    )

    try:
        for composant in repertoire.parts[1:]:
            suivant = os.open(
                composant,
                options,
                dir_fd=descripteur,
            )

            os.close(descripteur)
            descripteur = suivant

        return descripteur

    except BaseException:
        os.close(descripteur)
        raise


def _identite_fichier(informations: os.stat_result) -> tuple:
    """Retourne les caractéristiques physiques contrôlées."""

    return (
        informations.st_dev,
        informations.st_ino,
        informations.st_mode,
        informations.st_nlink,
        informations.st_size,
        informations.st_mtime_ns,
        informations.st_ctime_ns,
    )


def _verifier_identite_repertoire(
    repertoire: Path,
    descripteur_initial: int,
    informations_initiales: os.stat_result,
) -> None:
    """Vérifie la stabilité physique du répertoire inventorié."""

    descripteur_final = ouvrir_repertoire_securise(
        repertoire,
    )

    try:
        informations_finales = os.fstat(
            descripteur_final,
        )

        informations_actuelles = os.fstat(
            descripteur_initial,
        )

        if (
            _identite_fichier(informations_initiales)
            != _identite_fichier(informations_actuelles)
            or _identite_fichier(informations_actuelles)
            != _identite_fichier(informations_finales)
        ):
            raise ValueError(
                f"Répertoire modifié pendant l'inventaire : "
                f"{repertoire}"
            )

    finally:
        os.close(descripteur_final)


def _lire_fichier_depuis_repertoire(
    descripteur_repertoire: int,
    nom: str,
    chemin: Path,
    informations_attendues: os.stat_result | None = None,
) -> bytes:
    """Lit un fichier depuis un répertoire physique déjà ouvert."""

    if not nom or nom in {".", ".."} or "/" in nom:
        raise ValueError(
            f"Nom de fichier invalide : {nom}"
        )

    options_fichier = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        | os.O_CLOEXEC
        | os.O_NONBLOCK
    )

    descripteur_fichier = os.open(
        nom,
        options_fichier,
        dir_fd=descripteur_repertoire,
    )

    try:
        avant = os.fstat(descripteur_fichier)

        if not stat.S_ISREG(avant.st_mode):
            raise ValueError(
                f"Fichier non régulier interdit : {chemin}"
            )

        if avant.st_nlink != 1:
            raise ValueError(
                f"Nombre de liens physiques invalide : {chemin}"
            )

        if (
            informations_attendues is not None
            and _identite_fichier(informations_attendues)
            != _identite_fichier(avant)
        ):
            raise ValueError(
                f"Fichier modifié avant la lecture : {chemin}"
            )

        blocs = []

        while True:
            bloc = os.read(
                descripteur_fichier,
                65536,
            )

            if not bloc:
                break

            blocs.append(bloc)

        contenu = b"".join(blocs)

        apres = os.fstat(descripteur_fichier)

        if (
            _identite_fichier(avant)
            != _identite_fichier(apres)
            or len(contenu) != apres.st_size
        ):
            raise ValueError(
                f"Fichier modifié pendant la lecture : {chemin}"
            )

        return contenu

    finally:
        os.close(descripteur_fichier)

def lire_fichier_securise(chemin: Path) -> bytes:
    """Lit un fichier régulier sans suivre de liens symboliques."""

    chemin = Path(chemin).absolute()

    if ".." in chemin.parts:
        raise ValueError(
            f"Chemin contenant une remontée interdite : {chemin}"
        )

    if not chemin.name:
        raise ValueError(
            f"Chemin de fichier invalide : {chemin}"
        )

    descripteur_repertoire = ouvrir_repertoire_securise(
        chemin.parent,
    )

    try:
        return _lire_fichier_depuis_repertoire(
            descripteur_repertoire,
            chemin.name,
            chemin,
        )

    finally:
        os.close(descripteur_repertoire)



def calculer_checksum(chemin: Path) -> str:
    """Calcule l'empreinte SHA-256 du contenu exact d'un fichier."""

    chemin = Path(chemin)

    if chemin.is_symlink():
        raise ValueError(
            f"Lien symbolique interdit : {chemin}"
        )

    contenu = lire_fichier_securise(chemin)

    return hashlib.sha256(contenu).hexdigest()


def decouvrir_migrations(repertoire: Path) -> list[Migration]:
    """Découvre les migrations SQL officielles sans les exécuter."""

    repertoire = Path(repertoire)

    if repertoire.is_symlink():
        raise ValueError(
            f"Répertoire symbolique interdit : {repertoire}"
        )

    if not repertoire.is_dir():
        raise ValueError(
            f"Répertoire de migrations introuvable : {repertoire}"
        )

    migrations = []
    numeros_vus = set()

    descripteur = ouvrir_repertoire_securise(repertoire)

    try:
        informations_initiales = os.fstat(descripteur)

        for nom in sorted(os.listdir(descripteur)):
            correspondance = MIGRATION_PATTERN.fullmatch(nom)

            if correspondance is None:
                continue

            if nom.endswith("_test_grants.sql"):
                continue

            chemin = repertoire / nom

            informations = os.stat(
                nom,
                dir_fd=descripteur,
                follow_symlinks=False,
            )

            if stat.S_ISLNK(informations.st_mode):
                raise ValueError(
                    f"Lien symbolique interdit : {chemin}"
                )

            if not stat.S_ISREG(informations.st_mode):
                continue

            numero = int(correspondance.group(1))

            if numero in numeros_vus:
                raise ValueError(
                    f"Numéro de migration dupliqué : {numero:03d}"
                )

            numeros_vus.add(numero)

            contenu = _lire_fichier_depuis_repertoire(
                descripteur,
                nom,
                chemin,
                informations_attendues=informations,
            )

            migrations.append(
                Migration(
                    numero=numero,
                    nom=nom,
                    chemin=chemin,
                    checksum_sha256=hashlib.sha256(
                        contenu,
                    ).hexdigest(),
                )
            )

        _verifier_identite_repertoire(
            repertoire,
            descripteur,
            informations_initiales,
        )

    finally:
        os.close(descripteur)

    return sorted(
        migrations,
        key=lambda migration: migration.numero,
    )


def _analyser_manifeste_migrations(
    contenu: bytes,
) -> dict[str, str]:
    """Analyse les octets d'un manifeste au format ASCII LF strict."""

    texte = contenu.decode("ascii")

    if not texte:
        raise ValueError("Manifeste de migrations vide")

    if not texte.endswith("\n"):
        raise ValueError(
            "Manifeste sans LF final"
        )

    manifeste = {}
    numeros_vus = set()

    for numero_ligne, ligne in enumerate(
        texte.removesuffix("\n").split("\n"),
        start=1,
    ):
        correspondance = re.fullmatch(
            r"([0-9a-f]{64})  database/([0-9]{3}_[a-zA-Z0-9_]+\.sql)",
            ligne,
        )

        if correspondance is None:
            raise ValueError(
                f"Ligne de manifeste invalide : {numero_ligne}"
            )

        checksum, nom = correspondance.groups()
        numero = int(nom[:3])

        if nom.endswith("_test_grants.sql"):
            raise ValueError(
                f"Migration auxiliaire interdite : {nom}"
            )

        if nom in manifeste:
            raise ValueError(
                f"Migration dupliquée dans le manifeste : {nom}"
            )

        if numero in numeros_vus:
            raise ValueError(
                f"Numéro dupliqué dans le manifeste : {numero:03d}"
            )

        numeros_vus.add(numero)
        manifeste[nom] = checksum

    return manifeste


def capturer_manifeste_migrations(
    chemin: Path,
) -> ManifesteMigrations:
    """Capture une référence immuable du manifeste historique."""

    chemin = Path(chemin).absolute()

    if chemin.is_symlink():
        raise ValueError(
            f"Manifeste symbolique interdit : {chemin}"
        )

    if not chemin.is_file():
        raise ValueError(
            f"Manifeste de migrations introuvable : {chemin}"
        )

    contenu = lire_fichier_securise(chemin)

    manifeste = _analyser_manifeste_migrations(
        contenu,
    )

    return ManifesteMigrations(
        chemin=chemin,
        checksum_sha256=hashlib.sha256(
            contenu,
        ).hexdigest(),
        entrees=tuple(manifeste.items()),
    )


def lire_manifeste_migrations(
    chemin: Path,
) -> dict[str, str]:
    """Lit et valide le manifeste SHA-256 des migrations historiques."""

    manifeste = capturer_manifeste_migrations(
        chemin,
    )

    return dict(manifeste.entrees)


def revalider_manifeste_migrations(
    chemin: Path,
    reference: ManifesteMigrations,
) -> ManifesteMigrations:
    """Revalide le contenu exact d'un manifeste historique."""

    chemin = Path(chemin).absolute()

    if not isinstance(reference, ManifesteMigrations):
        raise TypeError(
            "Référence de manifeste invalide"
        )

    if (
        not isinstance(reference.chemin, Path)
        or reference.chemin != chemin
    ):
        raise ValueError(
            f"Chemin de manifeste incohérent : {chemin}"
        )

    actuel = capturer_manifeste_migrations(
        chemin,
    )

    if (
        actuel.checksum_sha256
        != reference.checksum_sha256
    ):
        raise ValueError(
            f"Manifeste modifié depuis sa capture : {chemin}"
        )

    if actuel.entrees != reference.entrees:
        raise ValueError(
            f"Entrées du manifeste incohérentes : {chemin}"
        )

    return actuel


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


def revalider_inventaire_migrations(
    repertoire: Path,
    migrations: list[Migration],
) -> list[Migration]:
    """Revalide physiquement un inventaire de migrations SQL."""

    repertoire = Path(repertoire)

    if not migrations:
        raise ValueError("Inventaire de migrations vide")

    comparer_migrations(migrations, [])

    inventaire_initial = {}

    for migration in migrations:
        chemin_attendu = repertoire / migration.nom

        if (
            not isinstance(migration.chemin, Path)
            or migration.chemin.absolute()
            != chemin_attendu.absolute()
        ):
            raise ValueError(
                f"Chemin de migration incohérent : {migration.nom}"
            )

        inventaire_initial[migration.nom] = migration

    migrations_actuelles = decouvrir_migrations(repertoire)

    inventaire_actuel = {
        migration.nom: migration
        for migration in migrations_actuelles
    }

    migrations_manquantes = sorted(
        inventaire_initial.keys() - inventaire_actuel.keys()
    )

    migrations_supplementaires = sorted(
        inventaire_actuel.keys() - inventaire_initial.keys()
    )

    if migrations_manquantes:
        raise ValueError(
            "Migrations disparues depuis l'inventaire : "
            + ", ".join(migrations_manquantes)
        )

    if migrations_supplementaires:
        raise ValueError(
            "Migrations ajoutées depuis l'inventaire : "
            + ", ".join(migrations_supplementaires)
        )

    for nom, migration_initiale in inventaire_initial.items():
        migration_actuelle = inventaire_actuel[nom]

        if (
            migration_initiale.checksum_sha256
            != migration_actuelle.checksum_sha256
        ):
            raise ValueError(
                f"Migration modifiée depuis l'inventaire : {nom}"
            )

    return migrations_actuelles


def valider_manifeste_migrations(
    migrations: list[Migration],
    manifeste: dict[str, str],
) -> None:
    """Vérifie la conformité de l'inventaire au manifeste historique."""

    if not manifeste:
        raise ValueError("Manifeste de migrations vide")

    if not migrations:
        raise ValueError("Inventaire de migrations vide")

    enregistrements = []

    for nom, checksum in manifeste.items():
        if not isinstance(nom, str) or not MIGRATION_PATTERN.fullmatch(
            nom
        ):
            raise ValueError(
                f"Nom de migration invalide dans le manifeste : {nom}"
            )

        if nom.endswith("_test_grants.sql"):
            raise ValueError(
                f"Migration auxiliaire interdite : {nom}"
            )

        cle = nom.removesuffix(".sql")

        enregistrements.append(
            {
                "migration_key": cle,
                "file_path": f"database/{nom}",
                "checksum_sha256": checksum,
                "application_mode": "baseline",
            }
        )

    resultats = comparer_migrations(
        migrations,
        enregistrements,
    )

    for resultat in resultats:
        cle = resultat["migration_key"]
        statut = resultat["statut"]

        if statut != "conforme":
            raise ValueError(
                f"Manifeste non conforme : {cle} ({statut})"
            )

def valider_perimetre_baseline(
    migrations: list[Migration],
    manifeste: dict[str, str],
) -> None:
    """Vérifie le périmètre de la baseline historique initiale."""

    valider_manifeste_migrations(
        migrations,
        manifeste,
    )

    numeros_attendus = set(
        range(
            BASELINE_PREMIERE_MIGRATION,
            BASELINE_DERNIERE_MIGRATION + 1,
        )
    )

    numeros_presents = {
        migration.numero
        for migration in migrations
    }

    numeros_manquants = sorted(
        numeros_attendus - numeros_presents
    )

    numeros_supplementaires = sorted(
        numeros_presents - numeros_attendus
    )

    if numeros_manquants:
        raise ValueError(
            "Migrations historiques manquantes : "
            + ", ".join(
                f"{numero:03d}"
                for numero in numeros_manquants
            )
        )

    if numeros_supplementaires:
        raise ValueError(
            "Migrations hors périmètre historique : "
            + ", ".join(
                f"{numero:03d}"
                for numero in numeros_supplementaires
            )
        )
