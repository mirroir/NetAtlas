import sys

from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_categories


def test_get_categories_retourne_des_donnees():
    categories = get_categories()

    assert categories is not None
    assert len(categories) > 0
