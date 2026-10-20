"""Service WebAuthn / Passkey de NetAtlas."""

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
)

RP_ID = "netatlas.home.arpa"
RP_NAME = "NetAtlas"
EXPECTED_ORIGIN = "https://netatlas.home.arpa"
WEBAUTHN_TIMEOUT_MS = 60_000

AUTHENTICATOR_SELECTION = AuthenticatorSelectionCriteria(
    user_verification=UserVerificationRequirement.REQUIRED,
)

def generer_options_enregistrement(user_id: int, nom: str):
    """Génère les options d'enregistrement d'une Passkey."""

    if user_id <= 0:
        raise ValueError("Identifiant utilisateur invalide.")

    if not nom or not nom.strip():
        raise ValueError("Nom utilisateur obligatoire.")

    return generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(user_id).encode("utf-8"),
        user_name=nom.strip(),
        user_display_name=nom.strip(),
        timeout=WEBAUTHN_TIMEOUT_MS,
        authenticator_selection=AUTHENTICATOR_SELECTION,
    )

def verifier_enregistrement(
    credential,
    challenge_attendu: bytes,
):
    """Vérifie cryptographiquement un enregistrement Passkey."""

    if not challenge_attendu or len(challenge_attendu) < 16:
        raise ValueError("Challenge WebAuthn invalide.")

    return verify_registration_response(
        credential=credential,
        expected_challenge=challenge_attendu,
        expected_rp_id=RP_ID,
        expected_origin=EXPECTED_ORIGIN,
        require_user_presence=True,
        require_user_verification=True,
    )

def generer_options_authentification():
    """Génère les options d'authentification Passkey."""

    return generate_authentication_options(
        rp_id=RP_ID,
        timeout=WEBAUTHN_TIMEOUT_MS,
        user_verification=UserVerificationRequirement.REQUIRED,
    )


def verifier_authentification(
    credential,
    challenge_attendu: bytes,
    cle_publique: bytes,
    compteur_actuel: int,
):
    """Vérifie cryptographiquement une authentification Passkey."""

    if not challenge_attendu or len(challenge_attendu) < 16:
        raise ValueError("Challenge WebAuthn invalide.")

    if not cle_publique:
        raise ValueError("Clé publique WebAuthn obligatoire.")

    if compteur_actuel < 0:
        raise ValueError("Compteur WebAuthn invalide.")

    return verify_authentication_response(
        credential=credential,
        expected_challenge=challenge_attendu,
        expected_rp_id=RP_ID,
        expected_origin=EXPECTED_ORIGIN,
        credential_public_key=cle_publique,
        credential_current_sign_count=compteur_actuel,
        require_user_verification=True,
    )


