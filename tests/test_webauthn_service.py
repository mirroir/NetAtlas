import sys
from pathlib import Path

import pytest
from webauthn.helpers.structs import UserVerificationRequirement

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))

from unittest.mock import patch

from webauthn_service import (
    EXPECTED_ORIGIN,
    RP_ID,
    WEBAUTHN_TIMEOUT_MS,
    generer_options_authentification,
    generer_options_enregistrement,
    verifier_authentification,
    verifier_enregistrement,
)


def test_options_enregistrement_webauthn():
    options = generer_options_enregistrement(
        user_id=1,
        nom="Utilisateur NetAtlas",
    )

    assert options.rp.id == RP_ID
    assert options.rp.name == "NetAtlas"
    assert options.user.id == b"1"
    assert options.user.name == "Utilisateur NetAtlas"
    assert options.timeout == WEBAUTHN_TIMEOUT_MS
    assert len(options.challenge) >= 16

    assert (
        options.authenticator_selection.user_verification
        == UserVerificationRequirement.REQUIRED
    )


def test_challenges_enregistrement_distincts():
    premier = generer_options_enregistrement(1, "Utilisateur")
    second = generer_options_enregistrement(1, "Utilisateur")

    assert premier.challenge != second.challenge


@pytest.mark.parametrize("user_id", [0, -1])
def test_enregistrement_user_id_invalide(user_id):
    with pytest.raises(ValueError, match="Identifiant utilisateur invalide"):
        generer_options_enregistrement(user_id, "Utilisateur")


@pytest.mark.parametrize("nom", ["", "   ", None])
def test_enregistrement_nom_invalide(nom):
    with pytest.raises(ValueError, match="Nom utilisateur obligatoire"):
        generer_options_enregistrement(1, nom)


def test_enregistrement_nom_normalise():
    options = generer_options_enregistrement(
        1,
        "  Utilisateur NetAtlas  ",
    )

    assert options.user.name == "Utilisateur NetAtlas"
    assert options.user.display_name == "Utilisateur NetAtlas"


def test_origine_webauthn_https():
    assert EXPECTED_ORIGIN == f"https://{RP_ID}"

def test_verifier_enregistrement_parametres_securises():
    with patch(
        "webauthn_service.verify_registration_response"
    ) as verification:
        resultat = verifier_enregistrement(
            credential={"id": "credential-test"},
            challenge_attendu=b"challenge-test-securise-123",
        )

    assert resultat is verification.return_value
    verification.assert_called_once_with(
        credential={"id": "credential-test"},
        expected_challenge=b"challenge-test-securise-123",
        expected_rp_id=RP_ID,
        expected_origin=EXPECTED_ORIGIN,
        require_user_presence=True,
        require_user_verification=True,
    )


@pytest.mark.parametrize(
    "challenge",
    [b"", b"court", None],
)
def test_verifier_enregistrement_challenge_invalide(challenge):
    with patch(
        "webauthn_service.verify_registration_response"
    ) as verification, pytest.raises(ValueError, match="Challenge WebAuthn invalide"):
        verifier_enregistrement(
            credential={"id": "credential-test"},
            challenge_attendu=challenge,
        )

    verification.assert_not_called()

def test_options_authentification_webauthn():
    options = generer_options_authentification()

    assert options.rp_id == RP_ID
    assert options.timeout == WEBAUTHN_TIMEOUT_MS
    assert len(options.challenge) >= 16
    assert options.user_verification == UserVerificationRequirement.REQUIRED


def test_challenges_authentification_distincts():
    premier = generer_options_authentification()
    second = generer_options_authentification()

    assert premier.challenge != second.challenge


def test_verifier_authentification_parametres_securises():
    with patch(
        "webauthn_service.verify_authentication_response"
    ) as verification:
        resultat = verifier_authentification(
            credential={"id": "credential-test"},
            challenge_attendu=b"challenge-authentification-123",
            cle_publique=b"cle-publique-test",
            compteur_actuel=5,
        )

    assert resultat is verification.return_value
    verification.assert_called_once_with(
        credential={"id": "credential-test"},
        expected_challenge=b"challenge-authentification-123",
        expected_rp_id=RP_ID,
        expected_origin=EXPECTED_ORIGIN,
        credential_public_key=b"cle-publique-test",
        credential_current_sign_count=5,
        require_user_verification=True,
    )


@pytest.mark.parametrize("challenge", [b"", b"court", None])
def test_authentification_challenge_invalide(challenge):
    with patch(
        "webauthn_service.verify_authentication_response"
    ) as verification, pytest.raises(ValueError, match="Challenge WebAuthn invalide"):
        verifier_authentification(
            credential={},
            challenge_attendu=challenge,
            cle_publique=b"cle-publique",
            compteur_actuel=0,
        )

    verification.assert_not_called()


def test_authentification_cle_publique_absente():
    with (
        patch("webauthn_service.verify_authentication_response") as verification,
        pytest.raises(ValueError, match="Clé publique WebAuthn obligatoire"),
    ):
            verifier_authentification(
                credential={},
                challenge_attendu=b"challenge-authentification-123",
                cle_publique=b"",
                compteur_actuel=0,
            )

    verification.assert_not_called()


def test_authentification_compteur_negatif():
    with patch(
        "webauthn_service.verify_authentication_response"
    ) as verification, pytest.raises(ValueError, match="Compteur WebAuthn invalide"):
        verifier_authentification(
            credential={},
            challenge_attendu=b"challenge-authentification-123",
            cle_publique=b"cle-publique",
            compteur_actuel=-1,
        )

    verification.assert_not_called()


