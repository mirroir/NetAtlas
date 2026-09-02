import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "python"))

from database import hash_pin, verifier_pin


def test_hash_pin_ne_contient_pas_pin_clair():
    pin = "2580"

    pin_hash = hash_pin(pin)

    assert pin not in pin_hash


def test_hash_pin_differe_pour_meme_pin():
    pin = "2580"

    hash_1 = hash_pin(pin)
    hash_2 = hash_pin(pin)

    assert hash_1 != hash_2


def test_verifier_pin_correct():
    pin = "2580"
    pin_hash = hash_pin(pin)

    assert verifier_pin(pin, pin_hash) is True


def test_verifier_pin_incorrect():
    pin_hash = hash_pin("2580")

    assert verifier_pin("9999", pin_hash) is False



def test_valider_pin_4_chiffres():
    from database import valider_pin

    assert valider_pin("2580") is True


def test_valider_pin_6_chiffres():
    from database import valider_pin

    assert valider_pin("258036") is True


def test_valider_pin_trop_court():
    from database import valider_pin

    assert valider_pin("123") is False


def test_valider_pin_trop_long():
    from database import valider_pin

    assert valider_pin("1234567") is False


def test_valider_pin_non_numerique():
    from database import valider_pin

    assert valider_pin("12ab") is False




