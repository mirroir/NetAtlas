#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR" || exit 1

MODE="${1:-all}"

case "$MODE" in
    all|ruff|tests|ci)
        ;;
    *)
        echo "[ERREUR] Mode inconnu : $MODE"
        exit 1
        ;;
esac

echo "========================================"
echo "        CONTROLE GLOBAL NETATLAS"
echo "========================================"
echo
echo "[INFO] Projet : $PROJECT_DIR"
echo

if [ "$MODE" = "all" ] || [ "$MODE" = "ruff" ]; then
    echo "[1/2] Controle qualite avec Ruff..."

    if ! ruff check .; then
        echo
        echo "[ERREUR] Ruff a detecte un probleme."
        exit 1
    fi

    echo
    echo "[OK] Ruff valide."
    echo
fi

if [ "$MODE" = "all" ] || [ "$MODE" = "tests" ] || [ "$MODE" = "ci" ]; then
    echo "[2/2] Tests + couverture..."

    if [ "$MODE" = "ci" ]; then
        echo "[INFO] Mode CI : tests SQL privilegies exclus."

        if ! python -m pytest -q \
            --ignore=tests/test_admin_passkey_recovery_integration.py \
            --cov=python \
            --cov-report=term-missing \
            --cov-fail-under=100; then
            echo
            echo "[ERREUR] Les tests CI ou la couverture ont echoue."
            exit 1
        fi
    else
        if ! python -m pytest -q \
            --cov=python \
            --cov-report=term-missing \
            --cov-fail-under=100; then
            echo
            echo "[ERREUR] Les tests ou la couverture ont echoue."
            exit 1
        fi
    fi
fi

echo
echo "========================================"

case "$MODE" in
    all)
        echo "     NETATLAS : ALL CHECKS PASSED"
        echo "========================================"
        echo
        echo "[OK] Qualite du code : validee"
        echo "[OK] Tests : valides"
        echo "[OK] Couverture minimale : 100 %"
        ;;
    ruff)
        echo "     NETATLAS : RUFF CHECK PASSED"
        echo "========================================"
        echo
        echo "[OK] Qualite du code : validee"
        ;;
    tests)
        echo "     NETATLAS : TESTS PASSED"
        echo "========================================"
        echo
        echo "[OK] Tests : valides"
        echo "[OK] Couverture minimale : 100 %"
        ;;
    ci)
        echo "     NETATLAS : CI TESTS PASSED"
        echo "========================================"
        echo
        echo "[OK] Tests applicatifs : valides"
        echo "[OK] Couverture minimale : 100 %"
        ;;
esac
