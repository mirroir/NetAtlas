
"""Registre protégé des laboratoires PostgreSQL IAM temporaires."""

import fcntl
import json
import os
import re
import secrets
import stat
import tempfile
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

PREFIXE_BASE = "netatlas_iam_concurrence_"

ETATS_VALIDES = frozenset(
    {
        "preparation",
        "creation_incertaine",
        "creation_confirmee",
        "nettoyage_requis",
        "nettoyage_confirme",
    }
)

TRANSITIONS_AUTORISEES = {
    "preparation": frozenset(
        {
            "creation_incertaine",
            "creation_confirmee",
            "nettoyage_requis",
        }
    ),
    "creation_incertaine": frozenset(
        {
            "creation_confirmee",
            "nettoyage_requis",
        }
    ),
    "creation_confirmee": frozenset({"nettoyage_requis"}),
    "nettoyage_requis": frozenset({"nettoyage_confirme"}),
    "nettoyage_confirme": frozenset(),
}

def determiner_reconciliation_absence(
    operation: dict,
    *,
    base_absente: bool,
) -> bool:
    """Détermine si une opération peut être réconciliée sans suppression."""

    if not isinstance(operation, dict):
        raise TypeError("Opération IAM invalide.")

    verifier_identifiant(operation["identifiant"])
    verifier_nom_base(operation["base"])

    etat = operation["etat"]

    if etat not in ETATS_VALIDES:
        raise ValueError("État IAM invalide.")

    if type(base_absente) is not bool:
        raise TypeError("Confirmation d'absence IAM invalide.")

    if not base_absente:
        return False

    return etat in {
        "creation_incertaine",
        "creation_confirmee",
        "nettoyage_requis",
    }


def repertoire_registre() -> Path:
    """Détermine le stockage persistant hors du dépôt Git."""

    racine = Path(
        os.environ.get(
            "XDG_STATE_HOME",
            str(Path.home() / ".local" / "state"),
        )
    )

    return racine / "netatlas" / "iam-laboratoires"


def verifier_nom_base(nom_base: str) -> None:
    """Autorise uniquement les bases IAM temporaires."""

    if not isinstance(nom_base, str):
        raise TypeError("Nom de base invalide.")

    if re.fullmatch(
        rf"{PREFIXE_BASE}[0-9a-f]{{32}}",
        nom_base,
    ) is None:
        raise ValueError("Base IAM temporaire non autorisée.")


def verifier_identifiant(identifiant: str) -> None:
    """Valide l'identifiant aléatoire du laboratoire."""

    if not isinstance(identifiant, str):
        raise TypeError("Identifiant de laboratoire invalide.")

    if re.fullmatch(r"[0-9a-f]{32}", identifiant) is None:
        raise ValueError("Identifiant de laboratoire non autorisé.")


def preparer_registre() -> Path:
    """Prépare et contrôle les répertoires privés."""

    repertoire = repertoire_registre()
    parent = repertoire.parent

    for chemin in (parent, repertoire):
        if chemin.is_symlink():
            raise RuntimeError("Registre IAM symbolique interdit.")

        chemin.mkdir(mode=0o700, parents=True, exist_ok=True)

        informations = chemin.lstat()

        if not stat.S_ISDIR(informations.st_mode):
            raise RuntimeError("Chemin du registre IAM invalide.")

        if informations.st_uid != os.getuid():
            raise RuntimeError("Propriétaire du registre IAM invalide.")

        if informations.st_mode & 0o077:
            raise RuntimeError("Permissions du registre IAM insuffisantes.")

    return repertoire


@contextmanager
def verrou_registre() -> Iterator[Path]:
    """Sérialise les opérations entre processus Linux."""

    repertoire = preparer_registre()
    chemin = repertoire / ".registre.lock"

    descripteur = os.open(
        chemin,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )

    try:
        informations = os.fstat(descripteur)

        if not stat.S_ISREG(informations.st_mode):
            raise RuntimeError("Verrou IAM non régulier.")

        if informations.st_uid != os.getuid():
            raise RuntimeError("Propriétaire du verrou IAM invalide.")

        if informations.st_mode & 0o077:
            raise RuntimeError("Permissions du verrou IAM insuffisantes.")

        fcntl.flock(descripteur, fcntl.LOCK_EX)

        try:
            yield repertoire
        finally:
            fcntl.flock(descripteur, fcntl.LOCK_UN)

    finally:
        os.close(descripteur)

@contextmanager
def verrou_cycle_iam() -> Iterator[None]:
    """Coordonne les opérations du cycle de vie IAM entre processus."""

    repertoire = preparer_registre()
    chemin = repertoire / ".cycle.lock"

    descripteur = os.open(
        chemin,
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW,
        0o600,
    )

    try:
        informations = os.fstat(descripteur)

        if not stat.S_ISREG(informations.st_mode):
            raise RuntimeError("Verrou de cycle IAM non régulier.")

        if informations.st_uid != os.getuid():
            raise RuntimeError(
                "Propriétaire du verrou de cycle IAM invalide."
            )

        if informations.st_mode & 0o077:
            raise RuntimeError(
                "Permissions du verrou de cycle IAM insuffisantes."
            )

        fcntl.flock(descripteur, fcntl.LOCK_EX)

        try:
            yield
        finally:
            fcntl.flock(descripteur, fcntl.LOCK_UN)

    finally:
        os.close(descripteur)


def synchroniser_repertoire(repertoire: Path) -> None:
    """Synchronise les modifications du répertoire."""

    descripteur = os.open(
        repertoire,
        os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
    )

    try:
        os.fsync(descripteur)
    finally:
        os.close(descripteur)


def chemin_operation(repertoire: Path, identifiant: str) -> Path:
    """Construit un chemin après validation stricte."""

    verifier_identifiant(identifiant)
    return repertoire / f"{identifiant}.json"


def lire_operation_verrouillee(
    repertoire: Path,
    identifiant: str,
) -> dict:
    """Relit une opération sous verrou."""

    chemin = chemin_operation(repertoire, identifiant)

    descripteur = os.open(
        chemin,
        os.O_RDONLY | os.O_NOFOLLOW,
    )

    try:
        informations = os.fstat(descripteur)

        if not stat.S_ISREG(informations.st_mode):
            raise RuntimeError("Fichier IAM non régulier.")

        if informations.st_uid != os.getuid():
            raise RuntimeError("Propriétaire du fichier IAM invalide.")

        if informations.st_mode & 0o077:
            raise RuntimeError("Permissions du fichier IAM insuffisantes.")

        with os.fdopen(descripteur, "r", encoding="utf-8") as fichier:
            descripteur = -1
            operation = json.load(fichier)

    finally:
        if descripteur >= 0:
            os.close(descripteur)

    if not isinstance(operation, dict):
        raise TypeError("Format du registre IAM invalide.")


    if operation.get("identifiant") != identifiant:
        raise RuntimeError("Identité du registre IAM incohérente.")

    verifier_nom_base(operation["base"])

    if operation["etat"] not in ETATS_VALIDES:
        raise RuntimeError("État du registre IAM incohérent.")

    return operation


def sauvegarder_operation_verrouillee(
    repertoire: Path,
    operation: dict,
    *,
    creation: bool = False,
) -> None:
    """Enregistre une opération sous verrou interprocessus."""

    identifiant = operation["identifiant"]
    verifier_identifiant(identifiant)
    verifier_nom_base(operation["base"])

    if operation["etat"] not in ETATS_VALIDES:
        raise ValueError("État de laboratoire IAM invalide.")

    destination = chemin_operation(repertoire, identifiant)

    descripteur, temporaire = tempfile.mkstemp(
        prefix=".iam-",
        suffix=".tmp",
        dir=repertoire,
    )

    try:
        with os.fdopen(descripteur, "w", encoding="utf-8") as fichier:
            json.dump(operation, fichier, sort_keys=True)
            fichier.flush()
            os.fsync(fichier.fileno())

        if creation:
            os.link(
                temporaire,
                destination,
                follow_symlinks=False,
            )
            os.unlink(temporaire)
        else:
            lire_operation_verrouillee(repertoire, identifiant)
            os.replace(temporaire, destination)

        synchroniser_repertoire(repertoire)

    finally:
        if os.path.exists(temporaire):
            os.unlink(temporaire)


def enregistrer_operation(nom_base: str) -> dict:
    """Enregistre une opération avant création PostgreSQL."""

    verifier_nom_base(nom_base)

    operation = {
        "identifiant": secrets.token_hex(16),
        "base": nom_base,
        "etat": "preparation",
        "cree_le": datetime.now(UTC).isoformat(),
    }

    sauvegarder_operation(operation, creation=True)
    return operation


def sauvegarder_operation(
    operation: dict,
    *,
    creation: bool = False,
) -> None:
    """Autorise uniquement la création initiale du registre."""

    if not creation:
        raise PermissionError(
            "Modification directe du registre IAM interdite."
        )

    if operation.get("etat") != "preparation":
        raise ValueError(
            "Une opération IAM doit commencer en préparation."
        )

    with verrou_registre() as repertoire:
        sauvegarder_operation_verrouillee(
            repertoire,
            operation,
            creation=True,
        )

def lire_operation(identifiant: str) -> dict:
    """Relit une opération protégée."""

    verifier_identifiant(identifiant)

    with verrou_registre() as repertoire:
        return lire_operation_verrouillee(
            repertoire,
            identifiant,
        )

def changer_etat(identifiant: str, etat: str) -> dict:
    """Effectue une transition autorisée sous verrou interprocessus."""

    if etat not in ETATS_VALIDES:
        raise ValueError("État de laboratoire IAM invalide.")

    verifier_identifiant(identifiant)

    with verrou_registre() as repertoire:
        operation = lire_operation_verrouillee(
            repertoire,
            identifiant,
        )

        etat_actuel = operation["etat"]

        if etat not in TRANSITIONS_AUTORISEES[etat_actuel]:
            raise ValueError(
                "Transition IAM interdite : "
                f"{etat_actuel} -> {etat}."
            )

        operation["etat"] = etat

        sauvegarder_operation_verrouillee(
            repertoire,
            operation,
        )

        return operation

def reconcilier_operation_absente(
    identifiant: str,
    verifier_absence: Callable[[str], bool],
) -> dict:
    """Réconcilie une opération dont la base est confirmée absente."""

    verifier_identifiant(identifiant)

    with verrou_cycle_iam():
        operation = lire_operation(identifiant)

        etat_initial = operation["etat"]
        nom_base = operation["base"]

        if etat_initial == "nettoyage_confirme":
            return operation

        if etat_initial not in {
            "creation_incertaine",
            "creation_confirmee",
            "nettoyage_requis",
        }:
            raise ValueError(
                "Sécurité IAM : état non éligible à la réconciliation."
            )

        absence = verifier_absence(nom_base)

        if type(absence) is not bool:
            raise TypeError(
                "Sécurité IAM : réponse de vérification ambiguë."
            )

        if not determiner_reconciliation_absence(
            operation,
            base_absente=absence,
        ):
            raise RuntimeError(
                "Sécurité IAM : base présente, réconciliation refusée."
            )

        with verrou_registre() as repertoire:
            operation_actuelle = lire_operation_verrouillee(
                repertoire,
                identifiant,
            )

            if operation_actuelle != operation:
                raise RuntimeError(
                    "Sécurité IAM : opération modifiée pendant "
                    "la réconciliation."
                )


            if (
                etat_initial != "nettoyage_requis"
                and "nettoyage_requis"
                not in TRANSITIONS_AUTORISEES[etat_initial]
            ):
                raise RuntimeError(
                    "Sécurité IAM : transition intermédiaire interdite."
                )

            if (
                "nettoyage_confirme"
                not in TRANSITIONS_AUTORISEES["nettoyage_requis"]
            ):
                raise RuntimeError(
                    "Sécurité IAM : transition finale interdite."
                )

            operation_actuelle.update(
                {
                    "etat": "nettoyage_confirme",
                    "mode_cloture": "reconciliation_absence",
                    "etat_avant_reconciliation": etat_initial,
                    "reconcilie_le": datetime.now(UTC).isoformat(),
                }
            )

            sauvegarder_operation_verrouillee(
                repertoire,
                operation_actuelle,
            )

            return operation_actuelle
