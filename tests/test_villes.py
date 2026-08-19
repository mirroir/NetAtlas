import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import get_villes


def test_get_villes_retourne_des_donnees():
    villes = get_villes()

    assert villes is not None
    assert isinstance(villes, list)
    assert len(villes) > 0
