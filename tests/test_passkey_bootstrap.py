from unittest.mock import MagicMock, patch

import pytest

from database import (
    creer_amorcage_passkey_admin,
    finaliser_amorcage_passkey_admin,
    get_admin_passkey_bootstrap,
    verifier_amorcage_passkey_admin,
)


@pytest.mark.parametrize("user_id", [0, -1, None, "2", True])
def test_creation_refuse_identifiant_invalide(user_id):
    with pytest.raises(ValueError, match="Identifiant administrateur"):
        creer_amorcage_passkey_admin(user_id, b"a" * 32)


@pytest.mark.parametrize("token_hash", [None, b"", b"a" * 31, "jeton"])
def test_creation_refuse_empreinte_invalide(token_hash):
    with pytest.raises(ValueError, match="Empreinte du jeton"):
        creer_amorcage_passkey_admin(2, token_hash)


@pytest.mark.parametrize("duree", [0, -1, 301, "300"])
def test_creation_refuse_duree_invalide(duree):
    with pytest.raises(ValueError, match="Durée d'amorçage"):
        creer_amorcage_passkey_admin(2, b"a" * 32, duree)


def preparer_connexion(resultats):
    connexion = MagicMock()
    curseur = connexion.cursor.return_value.__enter__.return_value
    curseur.fetchone.side_effect = resultats
    return connexion, curseur

# ============================================================
# PASSKEY - IDENTIFICATION ADMINISTRATEUR POUR AMORCAGE
# ============================================================


@pytest.mark.parametrize("user_id", [0, -1, None, "2", True])
def test_get_admin_bootstrap_refuse_identifiant_invalide(user_id):
    with patch("database.connexion_db") as connexion:
        resultat = get_admin_passkey_bootstrap(user_id)

    assert resultat is None
    connexion.assert_not_called()


def test_get_admin_bootstrap_compte_eligible():
    connexion, curseur = preparer_connexion([(2, "AdminNetAtlas")])

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_admin_passkey_bootstrap(2)

    assert resultat == {
        "user_id": 2,
        "nom": "AdminNetAtlas",
    }
    curseur.execute.assert_called_once()
    connexion.close.assert_called_once()


def test_get_admin_bootstrap_compte_non_eligible():
    connexion, curseur = preparer_connexion([None])

    with patch("database.connexion_db", return_value=connexion):
        resultat = get_admin_passkey_bootstrap(2)

    assert resultat is None
    curseur.execute.assert_called_once()
    connexion.close.assert_called_once()


def test_creation_amorcage_reussie():
    connexion, curseur = preparer_connexion(
        [(2,), (1,), None, (42,)]
    )

    with patch("database.connexion_db", return_value=connexion):
        resultat = creer_amorcage_passkey_admin(2, b"a" * 32)

    assert resultat == 42
    assert curseur.execute.call_count == 5
    connexion.commit.assert_called_once()
    connexion.close.assert_called_once()


def test_creation_refuse_compte_inexistant():
    connexion, _ = preparer_connexion([None])

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(ValueError, match="introuvable"),
        ):
            creer_amorcage_passkey_admin(2, b"a" * 32)

    connexion.rollback.assert_called_once()
    connexion.close.assert_called_once()


def test_creation_refuse_compte_non_admin():
    connexion, _ = preparer_connexion([(2,), None])

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(ValueError, match="non administrateur"),
        ):
            creer_amorcage_passkey_admin(2, b"a" * 32)

    connexion.rollback.assert_called_once()


def test_creation_refuse_passkey_existante():
    connexion, _ = preparer_connexion([(2,), (1,), (1,)])

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(ValueError, match="Passkey existe déjà"),
        ):
            creer_amorcage_passkey_admin(2, b"a" * 32)

    connexion.rollback.assert_called_once()


@pytest.mark.parametrize(
    "user_id,token_hash",
    [
        (0, b"a" * 32),
        (True, b"a" * 32),
        (2, b"a" * 31),
        (2, None),
    ],
)
def test_verification_refuse_parametres_invalides(user_id, token_hash):
    assert verifier_amorcage_passkey_admin(user_id, token_hash) is False


@pytest.mark.parametrize(
    "resultat,attendu",
    [
        ((1,), True),
        (None, False),
    ],
)
def test_verification_amorcage(resultat, attendu):
    connexion, _ = preparer_connexion([resultat])

    with patch("database.connexion_db", return_value=connexion):
        assert verifier_amorcage_passkey_admin(2, b"a" * 32) is attendu

    connexion.close.assert_called_once()

# ============================================================
# PASSKEY - TESTS DE FINALISATION ATOMIQUE
# ============================================================


def finaliser_passkey_test():
    return finaliser_amorcage_passkey_admin(
        user_id=2,
        token_hash=b"t" * 32,
        challenge_hash=b"c" * 32,
        session_binding_hash=b"s" * 32,
        credential_id=b"credential-test",
        public_key=b"public-key-test",
    )


@pytest.mark.parametrize(
    "resultats",
    [
        [None],
        [(2,), None],
        [(2,), (1,), (1,)],
        [(2,), (1,), None, None],
        [(2,), (1,), None, (10,), None],
    ],
)
def test_finalisation_refuse_conditions_invalides(resultats):
    connexion, _ = preparer_connexion(resultats)

    with patch("database.connexion_db", return_value=connexion):
        assert finaliser_passkey_test() is False

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()


def test_finalisation_amorcage_reussie():
    connexion, curseur = preparer_connexion(
        [(2,), (1,), None, (10,), (20,), (30,)]
    )

    with patch("database.connexion_db", return_value=connexion):
        resultat = finaliser_passkey_test()

    assert resultat == 30
    assert curseur.execute.call_count == 6
    connexion.commit.assert_called_once()
    connexion.rollback.assert_not_called()
    connexion.close.assert_called_once()


def test_finalisation_annule_transaction_sur_erreur():
    connexion, curseur = preparer_connexion(
        [(2,), (1,), None, (10,), (20,)]
    )
    curseur.execute.side_effect = [
        None, None, None, None, None, RuntimeError("Erreur SQL")
    ]

    with (
        patch("database.connexion_db", return_value=connexion),
        pytest.raises(RuntimeError, match="Erreur SQL"),
    ):
        finaliser_passkey_test()

    connexion.rollback.assert_called_once()
    connexion.commit.assert_not_called()
    connexion.close.assert_called_once()


@pytest.mark.parametrize(
    "parametre,valeur",
    [
        ("user_id", 0),
        ("user_id", True),
        ("token_hash", b"x"),
        ("challenge_hash", b"x"),
        ("session_binding_hash", b"x"),
        ("credential_id", b""),
        ("public_key", b""),
        ("sign_count", -1),
        ("sign_count", True),
    ],
)
def test_finalisation_refuse_parametres_invalides(parametre, valeur):
    arguments = {
        "user_id": 2,
        "token_hash": b"t" * 32,
        "challenge_hash": b"c" * 32,
        "session_binding_hash": b"s" * 32,
        "credential_id": b"credential-test",
        "public_key": b"public-key-test",
        "sign_count": 0,
    }
    arguments[parametre] = valeur

    with pytest.raises(ValueError):
        finaliser_amorcage_passkey_admin(**arguments)
