import sys
from pathlib import Path
from unittest.mock import patch

sys.path.append(str(Path(__file__).parent.parent / "python"))

from menu import afficher_place

PLACE = (
    1,
    "Marché de Saint-Pierre",
    "Marché local",
    "Centre-ville",
    -21.34,
    55.47,
    "0262000000",
    "contact@test.local",
    "https://example.test",
    True,
    "Saint-Pierre",
    "Agriculture",
)


def test_afficher_place_avec_avis(capsys):
    with (
        patch("menu.get_place_tags", return_value=["Marché forain"]),
        patch("menu.get_place_services", return_value=["Parking"]),
        patch(
            "menu.get_avis_by_place",
            return_value=[
                (1, "Très bon marché", "Utilisateur Test"),
            ],
        ),
    ):
        afficher_place(PLACE)

    sortie = capsys.readouterr().out

    assert "=== COMMENTAIRES UTILISATEURS ===" in sortie
    assert "Utilisateur Test" in sortie
    assert "Très bon marché" in sortie


def test_afficher_place_sans_avis(capsys):
    with (
        patch("menu.get_place_tags", return_value=[]),
        patch("menu.get_place_services", return_value=[]),
        patch("menu.get_avis_by_place", return_value=[]),
    ):
        afficher_place(PLACE)

    sortie = capsys.readouterr().out

    assert "=== COMMENTAIRES UTILISATEURS ===" in sortie
    assert "Aucun commentaire." in sortie



