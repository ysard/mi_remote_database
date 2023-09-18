"""Test Pattern class"""
import math
from functools import partial
import pytest
from src.pattern import Pattern


@pytest.fixture()
def ir_code():
    """Get raw IR timmings in microseconds"""
    return [
        9042, 4484, 579, 552, 580, 567, 579, 567, 544, 554, 579, 568, 579, 567,
        579, 1639, 605, 556, 544, 1673, 579, 1686, 553, 1680, 580, 1671, 579, 1686,
        544, 1689, 544, 554, 579, 1671, 579, 567, 579, 1671, 579, 551, 544, 570, 579,
        1639, 605, 572, 581, 550, 544, 570, 580, 1639, 545, 619, 579, 1638, 605,
        1660, 605, 557, 545, 1687, 544, 1658, 579, 1671, 579, 40318, 9018, 2250,
        579, 96733
    ]


@pytest.fixture()
def pronto_code():
    """Get IR pulses in Pronto format"""
    return "0000 006D 0022 0002 0158 00AA 0016 0015 0016 0016 0016 0016 0015 0015 0016 0016 0016 0016 0016 003E 0017 0015 0015 0040 0016 0040 0015 0040 0016 003F 0016 0040 0015 0040 0015 0015 0016 003F 0016 0016 0016 003F 0016 0015 0015 0016 0016 003E 0017 0016 0016 0015 0015 0016 0016 003E 0015 0018 0016 003E 0017 003F 0017 0015 0015 0040 0015 003F 0016 003F 0016 05FC 0157 0055 0016 0E5B"


@pytest.fixture()
def pulse_code():
    """Get IR pulses
    Pulses (number of cycles of the carrier for which to turn the light ON and OFF)
    """
    return [
        344, 170, 22, 21, 22, 22, 22, 22, 21, 21, 22, 22, 22, 22, 22, 62, 23, 21,
        21, 64, 22, 64, 21, 64, 22, 63, 22, 64, 21, 64, 21, 21, 22, 63, 22, 22,
        22, 63, 22, 21, 21, 22, 22, 62, 23, 22, 22, 21, 21, 22, 22, 62, 21, 24,
        22, 62, 23, 63, 23, 21, 21, 64, 21, 63, 22, 63, 22, 1532, 343, 85, 22, 3675
    ]


def test_to_pulses(ir_code, pulse_code):
    """Convert raw pulses to pulses"""
    pattern = Pattern(ir_code, 37990, code_type="raw")
    print(pattern)
    found = pattern.to_pulses()

    print(found)
    assert pulse_code == found

    # Missing frequency
    with pytest.raises(
            AssertionError, match="Missing frequency argument for the given code_type!"
    ):
        _ = Pattern(ir_code, code_type="raw")


def test_to_pronto(ir_code, pronto_code, capsys):
    """Test conversion and ability to detect 2 sequences in IR pulses"""
    pattern = Pattern(ir_code, 37990, code_type="raw")
    print(pattern)
    found = pattern.to_pronto()

    print(found)
    assert pronto_code == found

    # Test Odd number of burst values
    ir_code.pop()
    pattern = Pattern(ir_code, 37990, code_type="raw")
    found = pattern.to_pronto()
    captured = capsys.readouterr()
    print(found)
    assert "Burst pairs are not complete" in captured.out


def test_to_signed_raw(ir_code):
    pattern = Pattern(ir_code, 37990, code_type="raw")
    print(pattern)
    found = " ".join(pattern.to_signed_raw())

    expected = "+9042 -4484 +579 -552 +580 -567 +579 -567 +544 -554 +579 -568 +579 -567 +579 -1639 +605 -556 +544 -1673 +579 -1686 +553 -1680 +580 -1671 +579 -1686 +544 -1689 +544 -554 +579 -1671 +579 -567 +579 -1671 +579 -551 +544 -570 +579 -1639 +605 -572 +581 -550 +544 -570 +580 -1639 +545 -619 +579 -1638 +605 -1660 +605 -557 +545 -1687 +544 -1658 +579 -1671 +579 -40318 +9018 -2250 +579 -96733"
    print(found)
    assert expected == found


def test_from_pronto(ir_code, pronto_code):
    pattern = Pattern(pronto_code, 37990, code_type="pronto")
    print(pattern)
    found = pattern.to_raw()

    print(found)
    # Allow 5% relative difference (10% in the IR standard)
    isclose = partial(math.isclose, abs_tol=0.0, rel_tol=0.05)
    diff_result = list(map(isclose, ir_code, found))

    # All values must be True (no significative diff)
    print(diff_result, all(diff_result))
    assert all(diff_result)


def test_from_pulses(ir_code, pulse_code):
    """Convert pulses to raw pulses"""
    pattern = Pattern(pulse_code, 37990, code_type="pulses")
    print(pattern)
    found = pattern.to_raw()

    print(found)

    # Allow 5% relative difference (10% in the IR standard)
    isclose = partial(math.isclose, abs_tol=0.0, rel_tol=0.05)
    diff_result = list(map(isclose, ir_code, found))

    # All values must be True (no significative diff)
    print(diff_result, all(diff_result))
    assert all(diff_result)


def test_magic_functions(ir_code):
    """Test uniqueness & hash capacities of Pattern objects"""
    pattern_1 = Pattern(ir_code, 37990, code_type="raw")
    pattern_2 = Pattern(ir_code, 37990)
    pattern_3 = Pattern(ir_code, 38000, code_type="raw")

    assert pattern_1 == pattern_2
    assert pattern_1 != pattern_3

    uniq_patterns = {pattern_1, pattern_2, pattern_3}

    assert len(uniq_patterns) == 2
