import pathlib
import sys
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "python"))

import menu


def test_supprimer_service_a_lieu_succes():
    with (
        patch("builtins.input", side_effect=["1", "3"]),
        patch("menu.supprimer_service_lieu", return_value=True),
        patch("builtins.print") as mock_print,
    ):
        menu.supprimer_service_a_lieu()

    mock_print.assert_any_call("Service supprimé du lieu avec succès.")


def test_supprimer_service_a_lieu_inexistant():
    with (
        patch("builtins.input", side_effect=["1", "3"]),
        patch("menu.supprimer_service_lieu", return_value=False),
        patch("builtins.print") as mock_print,
    ):
        menu.supprimer_service_a_lieu()

    mock_print.assert_any_call("Association service-lieu inexistante.")


def test_supprimer_service_a_lieu_identifiant_invalide():
    with (
        patch("builtins.input", side_effect=["abc"]),
        patch("builtins.print") as mock_print,
    ):
        menu.supprimer_service_a_lieu()

    mock_print.assert_any_call(
        "Erreur : les identifiants doivent être des nombres."
    )
