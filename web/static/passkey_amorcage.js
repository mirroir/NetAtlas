"use strict";

// Conversion Base64URL vers Uint8Array.
function decoderBase64URL(valeur) {
    const base64 = valeur.replace(/-/g, "+").replace(/_/g, "/");
    const texte = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
    return Uint8Array.from(texte, caractere => caractere.charCodeAt(0));
}

// Conversion ArrayBuffer vers Base64URL.
function encoderBase64URL(valeur) {
    const octets = new Uint8Array(valeur);
    let texte = "";

    for (const octet of octets) {
        texte += String.fromCharCode(octet);
    }

    return btoa(texte)
        .replace(/\+/g, "-")
        .replace(/\//g, "_")
        .replace(/=+$/, "");
}

async function amorcerPasskeyAdministrateur(evenement) {
    evenement.preventDefault();

    const bouton = document.getElementById("bouton-amorcage");
    const message = document.getElementById("message-amorcage");
    const champJeton = document.getElementById("jeton-amorcage");
    const csrf = document.getElementById("passkey-amorcage-csrf").value;

    const jeton = champJeton.value.trim();

    bouton.disabled = true;
    message.textContent = "Préparation de la Passkey...";

    try {
        if (!window.isSecureContext || !window.PublicKeyCredential) {
            throw new Error(
                "WebAuthn nécessite Firefox compatible et une connexion HTTPS."
            );
        }

        if (!/^[0-9a-fA-F]{64}$/.test(jeton)) {
            throw new Error("Le jeton doit contenir exactement 64 caractères hexadécimaux.");
        }

        const reponseOptions = await fetch(
            "/admin/passkey/amorcage/options",
            {
                method: "POST",
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf
                },
                body: JSON.stringify({token: jeton})
            }
        );

        // Ne pas conserver inutilement le jeton dans le formulaire.
        champJeton.value = "";

        if (!reponseOptions.ok) {
            throw new Error("Jeton refusé, expiré ou administrateur déjà initialisé.");
        }

        const options = await reponseOptions.json();

        options.challenge = decoderBase64URL(options.challenge);
        options.user.id = decoderBase64URL(options.user.id);

        if (Array.isArray(options.excludeCredentials)) {
            options.excludeCredentials = options.excludeCredentials.map(
                element => ({
                    ...element,
                    id: decoderBase64URL(element.id)
                })
            );
        }

        message.textContent = "Veuillez confirmer la création de votre Passkey dans Firefox...";

        const credential = await navigator.credentials.create({
            publicKey: options
        });

        if (!credential) {
            throw new Error("Aucune Passkey n'a été créée.");
        }

        const donnees = {
            id: credential.id,
            rawId: encoderBase64URL(credential.rawId),
            type: credential.type,
            response: {
                clientDataJSON: encoderBase64URL(
                    credential.response.clientDataJSON
                ),
                attestationObject: encoderBase64URL(
                    credential.response.attestationObject
                )
            },
            clientExtensionResults: credential.getClientExtensionResults()
        };

        const reponseVerification = await fetch(
            "/admin/passkey/amorcage/verifier",
            {
                method: "POST",
                credentials: "same-origin",
                cache: "no-store",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf
                },
                body: JSON.stringify(donnees)
            }
        );

        const resultat = await reponseVerification.json();

        if (!reponseVerification.ok) {
            throw new Error(
                resultat.erreur || "La vérification de la Passkey a échoué."
            );
        }

        message.textContent =
            resultat.message || "Passkey administrateur enregistrée avec succès.";

    } catch (erreur) {
        if (erreur.name === "NotAllowedError") {
            message.textContent = "Création annulée ou refusée par Firefox.";
        } else {
            message.textContent = erreur.message;
        }
    } finally {
        champJeton.value = "";
        bouton.disabled = false;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const formulaire = document.getElementById("formulaire-amorcage");

    if (formulaire) {
        formulaire.addEventListener(
            "submit",
            amorcerPasskeyAdministrateur
        );
    }
});
