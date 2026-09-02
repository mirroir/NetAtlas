import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from main import connexion_administrateur


def test_connexion_administrateur_succes(capsys):
    session_attendue = {
        "user_id": 3,
        "nom": "Administrateur",
        "role": "admin",
    }

    with (
        patch("main.afficher_menu_connexion"),
        patch("main.getpass", return_value="2580"),
        patch(
            "main.authentifier_utilisateur",
            return_value=session_attendue,
        ),
    ):
        session = connexion_administrateur()

    sortie = capsys.readouterr().out

    assert session == session_attendue
    assert "Bienvenue Administrateur" in sortie


def test_connexion_administrateur_pin_incorrect(capsys):
    with (
        patch("main.afficher_menu_connexion"),
        patch("main.getpass", return_value="9999"),
        patch(
            "main.authentifier_utilisateur",
            return_value=None,
        ),
    ):
        session = connexion_administrateur()

    sortie = capsys.readouterr().out

    assert session is None
    assert "Accès refusé" in sortie
