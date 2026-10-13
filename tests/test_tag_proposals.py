import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg.errors import ForeignKeyViolation

from python.database import (
  analyser_proposition_tag,
  approuver_tag_proposal,
  connexion_db,
  creer_tag,
  creer_tag_proposal,
  get_tag_proposal,
  get_tag_proposals_pending,
  normaliser_nom_tag,
  obtenir_ou_creer_tag,
  rechercher_tag_exact,
  rechercher_tag_proposal_pending,
  rechercher_tags_similaires,
  rejeter_tag_proposal,
)


def test_normaliser_nom_tag():
    resultat = normaliser_nom_tag("   PRODUCTEURS    LOCAUX   ")

    assert resultat == "producteurs locaux"


def test_rechercher_tag_exact():
    resultat = rechercher_tag_exact("   PRODUCTEURS   LOCAUX   ", 1)

    assert resultat is not None
    assert resultat[1] == "Producteurs locaux"

def test_rechercher_tags_similaires():
    resultat = rechercher_tags_similaires("Producteur locaux", 1)

    assert len(resultat) >= 1
    assert resultat[0][1] == "Producteurs locaux"
    assert resultat[0][2] >= 0.50

def test_rechercher_tag_exact_inexistant():
    resultat = rechercher_tag_exact("Tag totalement inexistant", 1)

    assert resultat is None


def test_creer_tag_proposal():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag proposition pytest",
        1,
    )

    connexion = connexion_db()

    try:
        assert isinstance(proposal_id, int)
        assert proposal_id > 0

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT proposed_name, status
                FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )
            proposition = curseur.fetchone()

        assert proposition == ("Tag proposition pytest", "pending")

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                "DELETE FROM tag_proposals WHERE id = %s;",
                (proposal_id,),
            )

        connexion.commit()
        connexion.close()

def test_creer_tag_proposal_place_inexistant():
    with pytest.raises(ForeignKeyViolation):
        creer_tag_proposal(
            999999,
            3,
            "Tag test lieu inexistant",
            1,
        )

def test_creer_tag_proposal_user_inexistant():
    with pytest.raises(ForeignKeyViolation):
        creer_tag_proposal(
            1,
            999999,
            "Tag test utilisateur inexistant",
            1,
        )

def test_creer_tag_proposal_categorie_inexistante():
    with pytest.raises(ForeignKeyViolation):
        creer_tag_proposal(
            1,
            3,
            "Tag test catégorie inexistante",
            999999,
        )

def test_analyser_proposition_tag_existant():
    resultat = analyser_proposition_tag("Producteurs locaux", 1)

    assert resultat["statut"] == "existant"
    assert resultat["tag"] is not None
    assert resultat["tag"][1] == "Producteurs locaux"
    assert resultat["similaires"] == []

def test_analyser_proposition_tag_similaire():
    resultat = analyser_proposition_tag("Producteur locaux", 1)

    assert resultat["statut"] == "similaire"
    assert resultat["tag"] is None
    assert len(resultat["similaires"]) >= 1
    assert resultat["similaires"][0][1] == "Producteurs locaux"

def test_analyser_proposition_tag_nouveau():
    resultat = analyser_proposition_tag("Agriculture volcanique", 1)

    assert resultat["statut"] == "nouveau"
    assert resultat["tag"] is None
    assert resultat["similaires"] == []


def test_rechercher_tag_proposal_pending():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Producteur locaux",
        1,
    )

    connexion = connexion_db()

    try:
        resultat = rechercher_tag_proposal_pending(
            1,
            3,
            " PRODUCTEUR LOCAUX ",
            1,
        )

        assert resultat is not None
        assert resultat[0] == proposal_id
        assert resultat[1] == "Producteur locaux"

    finally:
        try:
            with connexion.cursor() as curseur:
                curseur.execute(
                    "DELETE FROM tag_proposals WHERE id = %s;",
                    (proposal_id,),
                )

            connexion.commit()
        finally:
            connexion.close()

def test_rechercher_tag_proposal_pending_inexistant():
    resultat = rechercher_tag_proposal_pending(
        1,
        3,
        "Proposition totalement inexistante",
        1,
    )

    assert resultat is None

def test_creer_tag_proposal_evite_doublon_pending():
    premier_id = creer_tag_proposal(
        1,
        3,
        "Tag anti doublon pytest",
        1,
    )

    second_id = creer_tag_proposal(
        1,
        3,
        "  TAG   ANTI   DOUBLON   PYTEST  ",
        1,
    )

    assert premier_id == second_id

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT COUNT(*)
                FROM tag_proposals
                WHERE place_id = %s
                  AND user_id = %s
                  AND category_id = %s
                  AND status = 'pending'
                  AND lower(
                      regexp_replace(trim(proposed_name), '\\s+', ' ', 'g')
                  ) = %s;
                """,
                (1, 3, 1, "tag anti doublon pytest"),
            )

            assert curseur.fetchone()[0] == 1

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (premier_id,),
            )
        connexion.commit()
        connexion.close()

def test_get_tag_proposals_pending():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag pending liste pytest",
        1,
    )

    connexion = connexion_db()

    try:
        propositions = get_tag_proposals_pending()

        ids = [proposition[0] for proposition in propositions]

        assert proposal_id in ids

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )
        connexion.commit()
        connexion.close()

def test_rejeter_tag_proposal():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag rejet pytest",
        1,
    )

    resultat = rejeter_tag_proposal(
        proposal_id,
        3,
    )

    assert resultat is True

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT status, moderated_by, moderated_at
                FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )

            proposition = curseur.fetchone()

            assert proposition[0] == "rejected"
            assert proposition[1] == 3
            assert proposition[2] is not None

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )
        connexion.commit()
        connexion.close()


def test_rejeter_tag_proposal_deja_rejetee():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag double rejet pytest",
        1,
    )

    premier_resultat = rejeter_tag_proposal(
        proposal_id,
        3,
    )

    second_resultat = rejeter_tag_proposal(
        proposal_id,
        3,
    )

    assert premier_resultat is True
    assert second_resultat is False

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )
        connexion.commit()
    finally:
        connexion.close()


def test_approuver_tag_proposal():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag approbation pytest",
        1,
    )

    resultat = approuver_tag_proposal(
        proposal_id,
        3,
    )

    assert resultat is True

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT status, moderated_by, moderated_at
                FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )

            proposition = curseur.fetchone()

            assert proposition[0] == "approved"
            assert proposition[1] == 3
            assert proposition[2] is not None

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )

            curseur.execute(
                """
                DELETE FROM place_tags
                WHERE tag_id IN (
                    SELECT id
                    FROM tags
                    WHERE name = %s
                      AND category_id = %s
                );
                """,
                ("Tag approbation pytest", 1),
            )

            curseur.execute(
                """
                DELETE FROM tags
                WHERE name = %s
                  AND category_id = %s;
                """,
                ("Tag approbation pytest", 1),
            )

        connexion.commit()
        connexion.close()


def test_approuver_tag_proposal_deja_approuvee():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag double approbation pytest",
        1,
    )

    premier_resultat = approuver_tag_proposal(
        proposal_id,
        3,
    )

    second_resultat = approuver_tag_proposal(
        proposal_id,
        3,
    )

    assert premier_resultat is True
    assert second_resultat is False

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )
        connexion.commit()

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )

            curseur.execute(
                """
                DELETE FROM place_tags
                WHERE tag_id IN (
                    SELECT id
                    FROM tags
                    WHERE name = %s
                      AND category_id = %s
                );
                """,
                ("Tag double approbation pytest", 1),
            )

            curseur.execute(
                """
                DELETE FROM tags
                WHERE name = %s
                  AND category_id = %s;
                """,
                ("Tag double approbation pytest", 1),
            )

        connexion.commit()
        connexion.close()


def test_creer_tag():
    tag_id = creer_tag(
        "Tag creation pytest",
        1,
    )

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT name, category_id
                FROM tags
                WHERE id = %s;
                """,
                (tag_id,),
            )

            tag = curseur.fetchone()

            assert tag is not None
            assert tag[0] == "Tag creation pytest"
            assert tag[1] == 1

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tags
                WHERE id = %s;
                """,
                (tag_id,),
            )
        connexion.commit()
        connexion.close()


def test_get_tag_proposal():
    proposal_id = creer_tag_proposal(
        1,
        3,
        "Tag lecture proposition pytest",
        1,
    )

    proposition = get_tag_proposal(proposal_id)

    assert proposition is not None
    assert proposition[0] == proposal_id
    assert proposition[1] == 1
    assert proposition[2] == 3
    assert proposition[3] == "Tag lecture proposition pytest"
    assert proposition[4] == 1
    assert proposition[5] == "pending"

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )
        connexion.commit()
    finally:
        connexion.close()


def test_obtenir_ou_creer_tag_existant():
    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT COUNT(*)
                FROM tags
                WHERE lower(name) = lower(%s)
                  AND category_id = %s;
                """,
                ("Producteurs locaux", 1),
            )

            nombre_avant = curseur.fetchone()[0]

        tag_id = obtenir_ou_creer_tag(
            "  PRODUCTEURS   LOCAUX  ",
            1,
        )

        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT COUNT(*)
                FROM tags
                WHERE lower(name) = lower(%s)
                  AND category_id = %s;
                """,
                ("Producteurs locaux", 1),
            )

            nombre_apres = curseur.fetchone()[0]

        assert tag_id == 2
        assert nombre_avant == 1
        assert nombre_apres == 1

    finally:
        connexion.close()

def test_obtenir_ou_creer_tag_nouveau():
    tag_id = obtenir_ou_creer_tag(
        "Tag nouveau obtenir pytest",
        1,
    )

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT name, category_id
                FROM tags
                WHERE id = %s;
                """,
                (tag_id,),
            )

            tag = curseur.fetchone()

            assert tag is not None
            assert tag[0] == "Tag nouveau obtenir pytest"
            assert tag[1] == 1

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tags
                WHERE id = %s;
                """,
                (tag_id,),
            )
        connexion.commit()
        connexion.close()

def test_approuver_tag_proposal_cree_et_associe_tag():
    nom_tag = "Tag approbation complete pytest"

    proposal_id = creer_tag_proposal(
        1,
        3,
        nom_tag,
        1,
    )

    resultat = approuver_tag_proposal(
        proposal_id,
        3,
    )

    assert resultat is True

    connexion = connexion_db()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT id
                FROM tags
                WHERE name = %s
                  AND category_id = %s;
                """,
                (nom_tag, 1),
            )

            tag = curseur.fetchone()

            assert tag is not None

            tag_id = tag[0]

            curseur.execute(
                """
                SELECT 1
                FROM place_tags
                WHERE place_id = %s
                  AND tag_id = %s;
                """,
                (1, tag_id),
            )

            assert curseur.fetchone() is not None

    finally:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM tag_proposals
                WHERE id = %s;
                """,
                (proposal_id,),
            )

            curseur.execute(
                """
                DELETE FROM place_tags
                WHERE place_id = %s
                  AND tag_id = %s;
                """,
                (1, tag_id),
            )

            curseur.execute(
                """
                DELETE FROM tags
                WHERE id = %s;
                """,
                (tag_id,),
            )

        connexion.commit()
        connexion.close()

def test_approuver_tag_proposal_inexistante():
    resultat = approuver_tag_proposal(
        999999,
        3,
    )

    assert resultat is False


