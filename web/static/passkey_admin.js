
"use strict";

// Convertir une chaîne Base64URL en tableau d'octets.
function decoderBase64URL(valeur) {
    const base64 = valeur.replace(/-/g, "+").replace(/_/g, "/");
    const texte = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
    return Uint8Array.from(texte, caractere => caractere.charCodeAt(0));
}

// Convertir des octets en chaîne Base64URL.
function encoderBase64URL(valeur) {
    const octets = new Uint8Array(valeur);
    let texte = "";

    for (const octet of octets) {
        texte += String.fromCharCode(octet);
    }

    return btoa(texte).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

async function enregistrerPasskey() {
    const bouton = document.getElementById("enregistrer-passkey");
    const message = document.getElementById("passkey-message");
    const csrf = document.getElementById("passkey-csrf-token").value;

    bouton.disabled = true;
    message.textContent = "Préparation de la Passkey...";

    try {
        if (!window.isSecureContext || !window.PublicKeyCredential) {
            throw new Error("WebAuthn nécessite un navigateur compatible et une connexion sécurisée.");
        }

        const reponseOptions = await fetch(
            "/admin/passkey/enregistrement/options",
            {
                method: "POST",
                credentials: "same-origin",
                headers: {"X-CSRFToken": csrf}
            }
        );

        if (!reponseOptions.ok) {
            throw new Error("Impossible de préparer l'enregistrement.");
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

        message.textContent = "Validation de la Passkey en cours...";

        const credential = await navigator.credentials.create({
            publicKey: options
        });

        if (!credential) {
            throw new Error("Aucune Passkey créée.");
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
            "/admin/passkey/enregistrement/verifier",
            {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": csrf
                },
                body: JSON.stringify(donnees)
            }
        );

        const resultat = await reponseVerification.json();

        if (!reponseVerification.ok) {
            throw new Error(resultat.erreur || "Enregistrement refusé.");
        }

        message.textContent = resultat.message;

    } catch (erreur) {
        if (erreur.name === "NotAllowedError") {
            message.textContent = "Enregistrement annulé ou non autorisé.";
        } else {
            message.textContent = erreur.message;
        }
    } finally {
        bouton.disabled = false;
    }
}

// Initialiser uniquement lorsque les éléments sont présents.
document.addEventListener("DOMContentLoaded", () => {
    const bouton = document.getElementById("enregistrer-passkey");

    if (bouton) {
        bouton.addEventListener("click", enregistrerPasskey);
    }
});
