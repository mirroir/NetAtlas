import os
import pytest
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import connexion_db


def test_base_de_test_obligatoire():
    assert os.getenv("DB_NAME") == "netatlas_test"


def test_environnement_test_actif():
    assert os.getenv("NETATLAS_ENV") == "test"


def test_connexion_prod_interdite_en_mode_test(monkeypatch):

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas")

    with pytest.raises(RuntimeError):
        connexion_db()


def test_connexion_test_autorisee(monkeypatch):

    monkeypatch.setenv("NETATLAS_ENV", "test")
    monkeypatch.setenv("DB_NAME", "netatlas_test")

    connexion = connexion_db()

    assert connexion is not None

    connexion.close()


