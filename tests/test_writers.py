"""Test writers module"""
# Standard imports
from collections import Counter
# Custom imports
from .test_pattern import ir_code
from src.pattern import Pattern
from src.writers import flipper_zero_export


def test_flipper(tmp_path, ir_code):
    params = {
        "code_type": "raw",
        "brand_name": "Fake Brand",
        "vendor_id": "Fake vendor id",
    }

    pattern_1 = Pattern(ir_code, 37990, model_id="kk_1", **params)
    pattern_2 = Pattern(ir_code, 38000, model_id="mi_1", **params)

    fake_data = {
        'kk_1': [pattern_1, pattern_2],
        'mi_1': [pattern_1, pattern_2],
    }

    # Create file to test unlink function if file exists
    (tmp_path / "Fake_Brand_kk_1.ir").write_text("hello")

    flipper_zero_export(fake_data, tmp_path, "Fake Device")

    # Test replacement of whitespace chars by "_"
    # We expect 1 file per model_id
    expected_files = ["Fake_Brand_kk_1.ir", "Fake_Brand_mi_1.ir"]
    for expected_file in expected_files:
        assert (tmp_path / expected_file).exists()

    # Test content
    found_content = (tmp_path / "Fake_Brand_kk_1.ir").read_text()
    print(found_content)

    # Test header + 1st pattern in 1st file
    expected_content = """Filetype: IR signals file
Version: 1
# Device: Fake Device; Brand: Fake Brand; Model: mi_1; from Mi Remote DB <https://github.com/ysard/mi_remote_database>
# AGPL-3.0 license, Copyright (C) 2021-2023 Ysard
#
name: None
type: raw
frequency: 37990
duty_cycle: 0.330000
data: """ + " ".join(map(str, ir_code))

    assert expected_content in found_content

    # Test that this file has 2 patterns
    words_count = Counter(found_content.replace("\n", " ").split(" "))

    assert words_count["name:"] == 2
    assert words_count["type:"] == 2
    assert words_count["raw"] == 2
    assert words_count["frequency:"] == 2
    assert words_count["37990"] == 1
    assert words_count["38000"] == 1
