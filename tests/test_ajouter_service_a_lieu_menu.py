import pathlib
import sys
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "python"))

import menu


def test_ajouter_service_a_lieu_succes():
    with (
        patch("builtins.input", side_effect=["1", "1"]),
        patch("menu.ajouter_service_lieu", return_value=True),
        patch("builtins.print") as mock_print,
    ):
        menu.ajouter_service_a_lieu()

    mock_print.assert_any_call("Service ajouté au lieu avec succès.")


def test_ajouter_service_a_lieu_deja_existant():
    with (
        patch("builtins.input", side_effect=["1", "1"]),
        patch("menu.ajouter_service_lieu", return_value=False),
        patch("builtins.print") as mock_print,
    ):
        menu.ajouter_service_a_lieu()

    mock_print.assert_any_call("Association service-lieu déjà existante.")


def test_ajouter_service_a_lieu_identifiant_invalide():
    with (
        patch("builtins.input", side_effect=["abc"]),
        patch("builtins.print") as mock_print,
    ):
        menu.ajouter_service_a_lieu()

    mock_print.assert_any_call("Erreur : les identifiants doivent être des nombres.")


