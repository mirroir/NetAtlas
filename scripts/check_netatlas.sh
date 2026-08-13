#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

echo "================================"
echo "   CONTROLE NETATLAS"
echo "================================"

echo "[INFO] Projet : $PROJECT_DIR"
echo "[INFO] Demarrage des controles..."

python -m pytest -q --tb=short

CODE_RETOUR=$?

if [ $CODE_RETOUR -eq 0 ]; then
    echo "[OK] Tous les tests NetAtlas sont valides."
    exit 0
else
    echo "[ERREUR] Des tests NetAtlas ont echoue."
    exit 1
fi
