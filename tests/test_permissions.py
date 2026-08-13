import sys
import pytest
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))



from database import connexion_db


@pytest.mark.parametrize(
    "permission, resultat_attendu",
    [
        ("SELECT", True),
        ("INSERT", True),
        ("UPDATE", True),
        ("DELETE", False),
        ("TRUNCATE", False),
        ("TRIGGER", False),
        ("REFERENCES", False),
    ],
)
def test_permissions_villes(permission, resultat_attendu):
    connexion = connexion_db()

    try:
        curseur = connexion.cursor()

        curseur.execute(
            """
            SELECT has_table_privilege(
                current_user,
                'villes',
                %s
            );
            """,
            (permission,),
        )

        autorise = curseur.fetchone()[0]

        assert autorise is resultat_attendu

    finally:
        connexion.close()


