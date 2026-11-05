
"use strict";

(() => {
    function decoderBase64URL(valeur) {
        const base64 = valeur.replace(/-/g, "+").replace(/_/g, "/");
        const texte = atob(base64.padEnd(Math.ceil(base64.length / 4) * 4, "="));
        return Uint8Array.from(texte, caractere => caractere.charCodeAt(0));
    }

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

    async function authentifierPasskey() {
        const bouton = document.getElementById("authentifier-passkey");
        const message = document.getElementById("passkey-message");
        const csrf = document.getElementById("passkey-csrf-token");
        const role = bouton.dataset.role;

        bouton.disabled = true;
        message.textContent = "Préparation de l'authentification...";

        try {
            if (!window.isSecureContext || !window.PublicKeyCredential) {
                throw new Error(
                    "WebAuthn nécessite un navigateur compatible et une connexion sécurisée."
                );
            }

            if (!["admin", "utilisateur"].includes(role)) {
                throw new Error("Rôle de connexion invalide.");
            }

            if (!csrf || !csrf.value) {
                throw new Error("Protection CSRF indisponible.");
            }

            const reponseOptions = await fetch(
                "/passkey/authentification/options",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "X-CSRFToken": csrf.value
                    }
                }
            );

            if (!reponseOptions.ok) {
                throw new Error("Impossible de préparer l'authentification.");
            }

            const options = await reponseOptions.json();
            options.challenge = decoderBase64URL(options.challenge);

            if (Array.isArray(options.allowCredentials)) {
                options.allowCredentials = options.allowCredentials.map(
                    element => ({
                        ...element,
                        id: decoderBase64URL(element.id)
                    })
                );
            }

            message.textContent = "Vérification de la Passkey...";

            const credential = await navigator.credentials.get({
                publicKey: options
            });

            if (!credential) {
                throw new Error("Aucune Passkey sélectionnée.");
            }

            const donnees = {
                role: role,
                credential: {
                    id: credential.id,
                    rawId: encoderBase64URL(credential.rawId),
                    type: credential.type,
                    response: {
                        clientDataJSON: encoderBase64URL(
                            credential.response.clientDataJSON
                        ),
                        authenticatorData: encoderBase64URL(
                            credential.response.authenticatorData
                        ),
                        signature: encoderBase64URL(
                            credential.response.signature
                        ),
                        userHandle: credential.response.userHandle
                            ? encoderBase64URL(credential.response.userHandle)
                            : null
                    },
                    clientExtensionResults: credential.getClientExtensionResults()
                }
            };

            const reponseVerification = await fetch(
                "/passkey/authentification/verifier",
                {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf.value
                    },
                    body: JSON.stringify(donnees)
                }
            );

            const resultat = await reponseVerification.json();

            if (!reponseVerification.ok) {
                throw new Error(
                    resultat.erreur || "Authentification Passkey refusée."
                );
            }

            if (
                typeof resultat.redirect !== "string" ||
                !resultat.redirect.startsWith("/") ||
                resultat.redirect.startsWith("//")
            ) {
                throw new Error("Destination de connexion invalide.");
            }

            message.textContent = "Authentification réussie.";
            window.location.assign(resultat.redirect);

        } catch (erreur) {
            if (erreur.name === "NotAllowedError") {
                message.textContent =
                    "Authentification annulée ou non autorisée.";
            } else {
                message.textContent =
                    erreur.message || "Erreur d'authentification.";
            }
        } finally {
            bouton.disabled = false;
        }
    }

    document.addEventListener("DOMContentLoaded", () => {
        const bouton = document.getElementById("authentifier-passkey");

        if (bouton) {
            bouton.addEventListener("click", authentifierPasskey);
        }
    });
})();
