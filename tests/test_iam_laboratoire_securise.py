
"""Tests unitaires du registre de récupération IAM."""
import json
import multiprocessing
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import iam_laboratoire_securise as laboratoire
import pytest


@pytest.fixture
def registre_isole(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    """Isole le registre de test du registre réel."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path / "netatlas" / "iam-laboratoires"


def test_creation_et_relecture_operation(registre_isole: Path) -> None:
    """Vérifie la création et la persistance du registre."""

    nom_base = laboratoire.PREFIXE_BASE + "a" * 32

    operation = laboratoire.enregistrer_operation(nom_base)
    identifiant = operation["identifiant"]

    assert operation["etat"] == "preparation"
    assert laboratoire.lire_operation(identifiant) == operation

    chemin = registre_isole / f"{identifiant}.json"

    assert chemin.is_file()
    assert chemin.stat().st_mode & 0o777 == 0o600
    assert registre_isole.stat().st_mode & 0o777 == 0o700


def test_transition_etat_operation(registre_isole: Path) -> None:
    """Vérifie la mise à jour persistante de l'état."""

    nom_base = laboratoire.PREFIXE_BASE + "b" * 32

    operation = laboratoire.enregistrer_operation(nom_base)

    resultat = laboratoire.changer_etat(
        operation["identifiant"],
        "creation_confirmee",
    )

    assert resultat["etat"] == "creation_confirmee"

    assert (
        laboratoire.lire_operation(operation["identifiant"])["etat"]
        == "creation_confirmee"
    )


@pytest.mark.parametrize(
    "nom_base",
    [
        "netatlas",
        "netatlas_test",
        "postgres",
        "",
        laboratoire.PREFIXE_BASE + "invalide",
    ],
)
def test_refus_noms_non_autorises(
    registre_isole: Path,
    nom_base: str,
) -> None:
    """Interdit les noms de bases hors laboratoire."""

    with pytest.raises(ValueError):
        laboratoire.enregistrer_operation(nom_base)

    assert not registre_isole.exists()


@pytest.mark.parametrize(
    "identifiant",
    [
        "",
        "../postgres",
        "a" * 31,
        "z" * 32,
    ],
)
def test_refus_identifiants_invalides(
    registre_isole: Path,
    identifiant: str,
) -> None:
    """Interdit les identifiants non conformes."""

    with pytest.raises(ValueError):
        laboratoire.lire_operation(identifiant)


def test_refus_etat_invalide(registre_isole: Path) -> None:
    """Interdit les états inconnus."""

    nom_base = laboratoire.PREFIXE_BASE + "c" * 32
    operation = laboratoire.enregistrer_operation(nom_base)

    with pytest.raises(ValueError):
        laboratoire.changer_etat(
            operation["identifiant"],
            "suppression_forcee",
        )


def test_refus_identite_incoherente(registre_isole: Path) -> None:
    """Détecte une incohérence dans un fichier enregistré."""

    nom_base = laboratoire.PREFIXE_BASE + "d" * 32
    operation = laboratoire.enregistrer_operation(nom_base)

    chemin = registre_isole / f"{operation['identifiant']}.json"

    donnees = json.loads(chemin.read_text(encoding="utf-8"))
    donnees["identifiant"] = "e" * 32

    chemin.write_text(
        json.dumps(donnees),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="Identité"):
        laboratoire.lire_operation(operation["identifiant"])


def test_refus_registre_symbolique(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse un répertoire de registre symbolique."""

    cible = tmp_path / "cible"
    cible.mkdir()

    racine = tmp_path / "netatlas"
    racine.mkdir(mode=0o700)

    (racine / "iam-laboratoires").symlink_to(
        cible,
        target_is_directory=True,
    )

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    with pytest.raises(RuntimeError, match="symbolique"):
        laboratoire.preparer_registre()


def test_refus_permissions_trop_larges(
    registre_isole: Path,
) -> None:
    """Refuse un registre accessible à d'autres utilisateurs."""

    registre_isole.mkdir(parents=True)
    os.chmod(registre_isole, 0o755)

    with pytest.raises(RuntimeError, match="Permissions"):
        laboratoire.preparer_registre()


def test_refus_creation_operation_existante(
    registre_isole: Path,
) -> None:
    """Refuse explicitement une création déjà enregistrée."""

    nom_base = laboratoire.PREFIXE_BASE + "f" * 32
    operation = laboratoire.enregistrer_operation(nom_base)

    with pytest.raises(FileExistsError):
        laboratoire.sauvegarder_operation(
            operation,
            creation=True,
        )


def test_refus_fichier_operation_symbolique(
    registre_isole: Path,
) -> None:
    """Refuse un fichier de registre remplacé par un lien symbolique."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "1" * 32
    )

    chemin = registre_isole / f"{operation['identifiant']}.json"
    cible = registre_isole / "cible.json"

    chemin.rename(cible)
    chemin.symlink_to(cible)

    with pytest.raises(OSError):
        laboratoire.lire_operation(operation["identifiant"])


def test_refus_permissions_fichier_operation(
    registre_isole: Path,
) -> None:
    """Refuse un fichier accessible à d'autres utilisateurs."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "2" * 32
    )

    chemin = registre_isole / f"{operation['identifiant']}.json"
    os.chmod(chemin, 0o644)

    with pytest.raises(RuntimeError, match="Permissions du fichier"):
        laboratoire.lire_operation(operation["identifiant"])


def test_refus_proprietaire_fichier_invalide(
    registre_isole: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Simule une incohérence de propriétaire."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "3" * 32
    )

    uid_reel = os.getuid()

    monkeypatch.setattr(
        laboratoire.os,
        "getuid",
        lambda: uid_reel + 1,
    )

    with pytest.raises(RuntimeError, match="Propriétaire"):
        laboratoire.lire_operation(operation["identifiant"])


def test_refus_collision_identifiant(
    registre_isole: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse une seconde création avec le même identifiant."""

    identifiant = "4" * 32

    monkeypatch.setattr(
        laboratoire.secrets,
        "token_hex",
        lambda _taille: identifiant,
    )

    nom_base = laboratoire.PREFIXE_BASE + "5" * 32

    laboratoire.enregistrer_operation(nom_base)

    with pytest.raises(FileExistsError):
        laboratoire.enregistrer_operation(nom_base)

def test_mises_a_jour_concurrentes(
    registre_isole: Path,
) -> None:
    """Vérifie qu'une seule transition concurrente est acceptée."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "6" * 32
    )

    identifiant = operation["identifiant"]

    def effectuer_transition(etat: str) -> str:
        try:
            laboratoire.changer_etat(identifiant, etat)
        except ValueError:
            return "refusee"

        return "acceptee"

    with ThreadPoolExecutor(max_workers=3) as executant:
        resultats = list(
            executant.map(
                effectuer_transition,
                ["creation_incertaine"] * 3,
            )
        )

    assert resultats.count("acceptee") == 1
    assert resultats.count("refusee") == 2

    resultat_final = laboratoire.lire_operation(identifiant)

    assert resultat_final["etat"] == "creation_incertaine"


def test_transition_preparation_vers_incertaine(
    registre_isole: Path,
) -> None:
    """Autorise le signalement d'une création incertaine."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "7" * 32
    )

    resultat = laboratoire.changer_etat(
        operation["identifiant"],
        "creation_incertaine",
    )

    assert resultat["etat"] == "creation_incertaine"


def test_refus_transition_inverse(
    registre_isole: Path,
) -> None:
    """Interdit un retour vers un état antérieur."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "8" * 32
    )

    identifiant = operation["identifiant"]

    laboratoire.changer_etat(
        identifiant,
        "creation_confirmee",
    )

    with pytest.raises(ValueError, match="Transition IAM interdite"):
        laboratoire.changer_etat(
            identifiant,
            "preparation",
        )

    assert laboratoire.lire_operation(identifiant)["etat"] == "creation_confirmee"


def test_refus_transition_identique(
    registre_isole: Path,
) -> None:
    """Interdit une transition redondante."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "9" * 32
    )

    with pytest.raises(ValueError, match="Transition IAM interdite"):
        laboratoire.changer_etat(
            operation["identifiant"],
            "preparation",
        )


def test_etat_final_irreversible(
    registre_isole: Path,
) -> None:
    """Empêche toute réouverture d'une opération clôturée."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "a" * 32
    )

    identifiant = operation["identifiant"]

    laboratoire.changer_etat(identifiant, "creation_confirmee")
    laboratoire.changer_etat(identifiant, "nettoyage_requis")
    laboratoire.changer_etat(identifiant, "nettoyage_confirme")

    with pytest.raises(ValueError, match="Transition IAM interdite"):
        laboratoire.changer_etat(
            identifiant,
            "creation_confirmee",
        )

    assert laboratoire.lire_operation(identifiant)["etat"] == "nettoyage_confirme"


def test_transition_incertaine_vers_nettoyage(
    registre_isole: Path,
) -> None:
    """Autorise le suivi d'un nettoyage après création incertaine."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "b" * 32
    )

    identifiant = operation["identifiant"]

    laboratoire.changer_etat(identifiant, "creation_incertaine")

    resultat = laboratoire.changer_etat(
        identifiant,
        "nettoyage_requis",
    )

    assert resultat["etat"] == "nettoyage_requis"

def test_refus_modification_directe(
    registre_isole: Path,
) -> None:
    """Interdit de contourner les transitions d'état."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "c" * 32
    )

    operation["etat"] = "nettoyage_confirme"

    with pytest.raises(PermissionError, match="Modification directe"):
        laboratoire.sauvegarder_operation(operation)

    assert (
        laboratoire.lire_operation(operation["identifiant"])["etat"]
        == "preparation"
    )


def test_refus_creation_etat_non_initial(
    registre_isole: Path,
) -> None:
    """Impose l'état initial lors de la création du registre."""

    operation = {
        "identifiant": "d" * 32,
        "base": laboratoire.PREFIXE_BASE + "e" * 32,
        "etat": "nettoyage_confirme",
        "cree_le": "2026-11-10T00:00:00+00:00",
    }

    with pytest.raises(ValueError, match="commencer en préparation"):
        laboratoire.sauvegarder_operation(
            operation,
            creation=True,
        )

def test_verrou_cycle_iam_acquisition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vérifie la création du verrou privé de cycle IAM."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    with laboratoire.verrou_cycle_iam():
        chemin = laboratoire.repertoire_registre() / ".cycle.lock"

        assert chemin.is_file()
        assert chemin.stat().st_mode & 0o077 == 0


def test_verrou_cycle_iam_lien_symbolique_refuse(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse un verrou de cycle pointant vers un lien symbolique."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    repertoire = laboratoire.preparer_registre()
    cible = tmp_path / "cible.lock"
    cible.touch()

    (repertoire / ".cycle.lock").symlink_to(cible)

    with pytest.raises(OSError), laboratoire.verrou_cycle_iam():
            pytest.fail("Le verrou symbolique ne doit pas être acquis.")

def travailleur_verrou_cycle_iam(
    repertoire: str,
    connexion: object,
) -> None:
    """Tente d'acquérir le verrou depuis un autre processus."""

    os.environ["XDG_STATE_HOME"] = repertoire

    connexion.send("demarrage")

    with laboratoire.verrou_cycle_iam():
        connexion.send("acquis")

    connexion.close()


def test_verrou_cycle_iam_interprocessus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Vérifie l'exclusion mutuelle entre deux processus Linux."""

    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    contexte = multiprocessing.get_context("spawn")
    parent, enfant = contexte.Pipe(duplex=False)

    processus = contexte.Process(
        target=travailleur_verrou_cycle_iam,
        args=(str(tmp_path), enfant),
    )

    try:
        with laboratoire.verrou_cycle_iam():
            processus.start()
            enfant.close()

            assert parent.poll(5)
            assert parent.recv() == "demarrage"

            # Le processus enfant doit attendre la libération du verrou.
            assert not parent.poll(0.5)

        # Après libération, l'enfant doit acquérir le verrou.
        assert parent.poll(5)
        assert parent.recv() == "acquis"

    finally:
        if processus.pid is not None:
            processus.join(timeout=5)

            if processus.is_alive():
                processus.terminate()
                processus.join(timeout=5)

        parent.close()
        enfant.close()

    assert processus.exitcode == 0

@pytest.mark.parametrize(
    ("etat", "attendu"),
    [
        ("preparation", False),
        ("creation_incertaine", True),
        ("creation_confirmee", True),
        ("nettoyage_requis", True),
        ("nettoyage_confirme", False),
    ],
)
def test_decision_reconciliation_base_absente(
    registre_isole: Path,
    etat: str,
    attendu: bool,
) -> None:
    """Vérifie les états éligibles à une réconciliation."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "a" * 32
    )

    operation["etat"] = etat

    assert (
        laboratoire.determiner_reconciliation_absence(
            operation,
            base_absente=True,
        )
        is attendu
    )


@pytest.mark.parametrize(
    "etat",
    [
        "creation_incertaine",
        "creation_confirmee",
        "nettoyage_requis",
    ],
)
def test_refus_reconciliation_base_presente(
    registre_isole: Path,
    etat: str,
) -> None:
    """Refuse la réconciliation lorsque la base est présente."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "b" * 32
    )

    operation["etat"] = etat

    assert (
        laboratoire.determiner_reconciliation_absence(
            operation,
            base_absente=False,
        )
        is False
    )

@pytest.mark.parametrize(
    ("operation", "absence", "exception"),
    [
        (None, True, TypeError),
        ({}, True, KeyError),
        (
            {
                "identifiant": "invalide",
                "base": "netatlas",
                "etat": "creation_confirmee",
            },
            True,
            ValueError,
        ),
        (
            {
                "identifiant": "a" * 32,
                "base": "netatlas",
                "etat": "creation_confirmee",
            },
            True,
            ValueError,
        ),
        (
            {
                "identifiant": "a" * 32,
                "base": "netatlas_iam_concurrence_" + "a" * 32,
                "etat": "etat_inconnu",
            },
            True,
            ValueError,
        ),
        (
            {
                "identifiant": "a" * 32,
                "base": "netatlas_iam_concurrence_" + "a" * 32,
                "etat": "creation_confirmee",
            },
            "oui",
            TypeError,
        ),
    ],
)
def test_refus_reconciliation_donnees_invalides(
    operation: object,
    absence: object,
    exception: type[Exception],
) -> None:
    """Refuse les données incorrectes ou ambiguës."""

    with pytest.raises(exception):
        laboratoire.determiner_reconciliation_absence(
            operation,
            base_absente=absence,
        )

@pytest.mark.parametrize(
    "etat_initial",
    [
        "creation_incertaine",
        "creation_confirmee",
        "nettoyage_requis",
    ],
)
def test_reconciliation_operation_absente(
    registre_isole: Path,
    etat_initial: str,
) -> None:
    """Réconcilie une opération absente avec traçabilité."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "c" * 32
    )
    identifiant = operation["identifiant"]

    if etat_initial != "preparation":
        laboratoire.changer_etat(
            identifiant,
            etat_initial,
        )

    appels = []

    def verifier_absence(nom_base: str) -> bool:
        appels.append(nom_base)
        return True

    resultat = laboratoire.reconcilier_operation_absente(
        identifiant,
        verifier_absence,
    )

    assert appels == [operation["base"]]
    assert resultat["etat"] == "nettoyage_confirme"
    assert resultat["mode_cloture"] == "reconciliation_absence"
    assert resultat["etat_avant_reconciliation"] == etat_initial
    assert resultat["reconcilie_le"]

    assert laboratoire.lire_operation(identifiant) == resultat


def test_refus_reconciliation_base_presente_registre_inchange(
    registre_isole: Path,
) -> None:
    """Ne modifie pas le registre si la base est présente."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "d" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(
        identifiant,
        "creation_confirmee",
    )

    avant = laboratoire.lire_operation(identifiant)

    def verifier_absence(nom_base: str) -> bool:
        assert nom_base == operation["base"]
        return False

    with pytest.raises(RuntimeError, match="base présente"):
        laboratoire.reconcilier_operation_absente(
            identifiant,
            verifier_absence,
        )

    assert laboratoire.lire_operation(identifiant) == avant


@pytest.mark.parametrize(
    "reponse",
    [None, "oui", 1],
)
def test_refus_reconciliation_reponse_ambigue(
    registre_isole: Path,
    reponse: object,
) -> None:
    """Refuse une réponse non booléenne du vérificateur."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "e" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(
        identifiant,
        "creation_incertaine",
    )

    avant = laboratoire.lire_operation(identifiant)

    def verifier_absence(nom_base: str) -> object:
        return reponse

    with pytest.raises(TypeError, match="réponse de vérification ambiguë"):
        laboratoire.reconcilier_operation_absente(
            identifiant,
            verifier_absence,
        )

    assert laboratoire.lire_operation(identifiant) == avant

def test_reconciliation_verificateur_indisponible(
    registre_isole: Path,
) -> None:
    """Préserve le registre lorsque PostgreSQL est indisponible."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "f" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(identifiant, "creation_incertaine")
    avant = laboratoire.lire_operation(identifiant)

    def verifier_absence(nom_base: str) -> bool:
        assert nom_base == operation["base"]
        raise RuntimeError("PostgreSQL indisponible")

    with pytest.raises(RuntimeError, match="PostgreSQL indisponible"):
        laboratoire.reconcilier_operation_absente(
            identifiant,
            verifier_absence,
        )

    assert laboratoire.lire_operation(identifiant) == avant


def test_reconciliation_echec_ecriture(
    registre_isole: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Refuse la clôture si la sauvegarde échoue avant écriture."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "a" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(identifiant, "creation_confirmee")
    avant = laboratoire.lire_operation(identifiant)

    def refuser_ecriture(
        repertoire: Path,
        operation: dict,
        *,
        creation: bool = False,
    ) -> None:
        raise OSError("Écriture IAM simulée impossible")

    monkeypatch.setattr(
        laboratoire,
        "sauvegarder_operation_verrouillee",
        refuser_ecriture,
    )

    with pytest.raises(OSError, match="Écriture IAM simulée impossible"):
        laboratoire.reconcilier_operation_absente(
            identifiant,
            lambda nom_base: True,
        )

    assert laboratoire.lire_operation(identifiant) == avant

def test_reconciliation_deja_confirmee_idempotente(
    registre_isole: Path,
) -> None:
    """Ne modifie pas une opération déjà clôturée."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "a" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(identifiant, "creation_confirmee")
    laboratoire.changer_etat(identifiant, "nettoyage_requis")
    laboratoire.changer_etat(identifiant, "nettoyage_confirme")

    avant = laboratoire.lire_operation(identifiant)

    def verifier_absence(nom_base: str) -> bool:
        raise AssertionError(
            "Le vérificateur ne doit pas être appelé."
        )

    resultat = laboratoire.reconcilier_operation_absente(
        identifiant,
        verifier_absence,
    )

    assert resultat == avant
    assert laboratoire.lire_operation(identifiant) == avant


def test_reconciliation_modification_concurrente_refusee(
    registre_isole: Path,
) -> None:
    """Refuse une opération modifiée pendant la vérification."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "b" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(identifiant, "creation_incertaine")

    def verifier_absence(nom_base: str) -> bool:
        assert nom_base == operation["base"]

        laboratoire.changer_etat(
            identifiant,
            "nettoyage_requis",
        )

        return True

    with pytest.raises(
        RuntimeError,
        match="opération modifiée pendant",
    ):
        laboratoire.reconcilier_operation_absente(
            identifiant,
            verifier_absence,
        )

    resultat = laboratoire.lire_operation(identifiant)

    assert resultat["etat"] == "nettoyage_requis"
    assert "mode_cloture" not in resultat

def test_reconciliation_echec_synchronisation_apres_remplacement(
    registre_isole: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Relit le registre après un échec suivant os.replace."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "9" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(
        identifiant,
        "creation_confirmee",
    )

    avant = laboratoire.lire_operation(identifiant)

    synchroniser_original = laboratoire.synchroniser_repertoire
    appels = []

    def synchronisation_simulee(repertoire: Path) -> None:
        appels.append(repertoire)
        raise OSError("Échec fsync répertoire simulé")

    with monkeypatch.context() as modification:
        modification.setattr(
            laboratoire,
            "synchroniser_repertoire",
            synchronisation_simulee,
        )

        with pytest.raises(
            OSError,
            match="Échec fsync répertoire simulé",
        ):
            laboratoire.reconcilier_operation_absente(
                identifiant,
                lambda nom_base: True,
            )

    assert len(appels) == 1

    apres = laboratoire.lire_operation(identifiant)

    assert apres["etat"] == "nettoyage_confirme"
    assert apres["mode_cloture"] == "reconciliation_absence"
    assert (
        apres["etat_avant_reconciliation"]
        == "creation_confirmee"
    )
    assert apres["reconcilie_le"]
    assert apres != avant

    assert laboratoire.synchroniser_repertoire is synchroniser_original

def test_reconciliation_reprise_apres_echec_synchronisation(
    registre_isole: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Préserve une clôture déjà visible après une erreur fsync."""

    operation = laboratoire.enregistrer_operation(
        laboratoire.PREFIXE_BASE + "8" * 32
    )
    identifiant = operation["identifiant"]

    laboratoire.changer_etat(
        identifiant,
        "creation_confirmee",
    )

    def refuser_synchronisation(repertoire: Path) -> None:
        raise OSError("Synchronisation interrompue")

    with monkeypatch.context() as modification:
        modification.setattr(
            laboratoire,
            "synchroniser_repertoire",
            refuser_synchronisation,
        )

        with pytest.raises(
            OSError,
            match="Synchronisation interrompue",
        ):
            laboratoire.reconcilier_operation_absente(
                identifiant,
                lambda nom_base: True,
            )

    apres_incident = laboratoire.lire_operation(identifiant)

    assert apres_incident["etat"] == "nettoyage_confirme"
    assert apres_incident["mode_cloture"] == "reconciliation_absence"

    def verifier_absence_interdit(nom_base: str) -> bool:
        raise AssertionError(
            "Une opération déjà clôturée ne doit pas être revérifiée."
        )

    resultat = laboratoire.reconcilier_operation_absente(
        identifiant,
        verifier_absence_interdit,
    )

    assert resultat == apres_incident
    assert laboratoire.lire_operation(identifiant) == apres_incident

def test_verrou_cycle_iam_libere_apres_exception(
    registre_isole: Path,
) -> None:
    """Libère le verrou de cycle après une exception."""

    with (
        pytest.raises(
            RuntimeError,
            match="Incident IAM simulé",
        ),
        laboratoire.verrou_cycle_iam(),
    ):
        raise RuntimeError("Incident IAM simulé")

    contexte = multiprocessing.get_context("spawn")
    parent, enfant = contexte.Pipe(duplex=False)

    processus = contexte.Process(
        target=travailleur_verrou_cycle_iam,
        args=(str(registre_isole.parent.parent), enfant),
    )

    try:
        processus.start()
        enfant.close()

        assert parent.poll(5), (
            "Le processus secondaire n'a pas démarré."
        )
        assert parent.recv() == "demarrage"

        assert parent.poll(5), (
            "Le verrou IAM n'a pas été libéré après l'exception."
        )
        assert parent.recv() == "acquis"

    finally:
        if processus.pid is not None:
            processus.join(timeout=5)

            if processus.is_alive():
                processus.terminate()
                processus.join(timeout=5)

        parent.close()
        enfant.close()

    assert processus.exitcode == 0
