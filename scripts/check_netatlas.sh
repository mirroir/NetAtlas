#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

echo "========================================"
echo "        CONTROLE GLOBAL NETATLAS"
echo "========================================"
echo
echo "[INFO] Projet : $PROJECT_DIR"
echo

echo "[1/2] Controle qualite avec Ruff..."
if ! ruff check .; then
    echo
    echo "[ERREUR] Ruff a detecte un probleme."
    exit 1
fi

echo
echo "[OK] Ruff valide."
echo

echo "[2/2] Tests + couverture..."
if ! python -m pytest -q \
    --cov=python \
    --cov-report=term-missing \
    --cov-fail-under=100; then
    echo
    echo "[ERREUR] Les tests ou la couverture ont echoue."
    exit 1
fi

echo
echo "========================================"
echo "       NETATLAS : ALL CHECKS PASSED"
echo "========================================"
echo
echo "[OK] Qualite du code : validee"
echo "[OK] Tests : valides"
echo "[OK] Couverture minimale : 100 %"
