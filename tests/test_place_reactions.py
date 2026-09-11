import os
import sys
from pathlib import Path

import psycopg2
import pytest
from dotenv import load_dotenv

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "python"),
)

load_dotenv(".env.test")

from database import enregistrer_reaction, get_place_reactions, get_user_reaction


def connexion_test():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )


def supprimer_reaction_test():
    connexion = connexion_test()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                DELETE FROM place_reactions
                WHERE place_id = %s
                  AND user_id = %s;
                """,
                (1, 3),
            )

        connexion.commit()

    finally:
        connexion.close()


def lire_reaction_test():
    connexion = connexion_test()

    try:
        with connexion.cursor() as curseur:
            curseur.execute(
                """
                SELECT reaction
                FROM place_reactions
                WHERE place_id = %s
                  AND user_id = %s;
                """,
                (1, 3),
            )

            return curseur.fetchone()

    finally:
        connexion.close()


def test_enregistrer_like():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, 1)

    assert lire_reaction_test() == (1,)

    supprimer_reaction_test()


def test_enregistrer_dislike():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, -1)

    assert lire_reaction_test() == (-1,)

    supprimer_reaction_test()


def test_modifier_reaction():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, 1)
    enregistrer_reaction(1, 3, -1)

    assert lire_reaction_test() == (-1,)

    supprimer_reaction_test()


def test_reaction_invalide():
    supprimer_reaction_test()

    with pytest.raises(
        ValueError,
        match="La réaction doit être -1 ou 1.",
    ):
        enregistrer_reaction(1, 3, 42)

    assert lire_reaction_test() is None


def test_get_place_reactions_aucune_reaction():
    supprimer_reaction_test()

    resultat = get_place_reactions(1)

    assert resultat == (0, 0)


def test_get_place_reactions_avec_like():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, 1)

    resultat = get_place_reactions(1)

    assert resultat == (1, 0)

    supprimer_reaction_test()


def test_get_place_reactions_avec_dislike():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, -1)

    resultat = get_place_reactions(1)

    assert resultat == (0, 1)

    supprimer_reaction_test()


def test_get_user_reaction_aucune_reaction():
    supprimer_reaction_test()

    resultat = get_user_reaction(1, 3)

    assert resultat is None


def test_get_user_reaction_like():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, 1)

    resultat = get_user_reaction(1, 3)

    assert resultat == 1

    supprimer_reaction_test()


def test_get_user_reaction_dislike():
    supprimer_reaction_test()

    enregistrer_reaction(1, 3, -1)

    resultat = get_user_reaction(1, 3)

    assert resultat == -1

    supprimer_reaction_test()




