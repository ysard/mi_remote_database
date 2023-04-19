"""Test crypt_utils module"""
import pytest
from unittest.mock import patch
from src.crypt_utils import get_opaque_http_param, build_url, process_xiaomi_shit

TOKEN = "0f9dfa001cba164d7bda671649c50abf"
KEY = "581582928c881b42eedce96331bff5d3"


@pytest.mark.parametrize(
    "url_path, expected_opaque",
    [
        # Standard devices
        ("/controller/match/tree/1?version=6034&country=FR&ts=1615406520766&nonce=-745784427&devid=1&miyk=1&brandid=64&power=1", "ca532688afb979158cc1fc511e36af666dba061b"),
        ("/controller/code/1?version=6034&country=FR&ts=1615406532233&nonce=-1591647351&matchid=xm_1_199&vendor=mi", "b2138842dc4a2b05f1e45d4822dfbdc2fe25a407"),
        ("/controller/device/1?version=6034&country=FR&ts=1615406505554&nonce=1126639370", "f422f7bdc77403414fdd674758af0b39435bb46e"),
        # Set-top box devices
        # brandid replaced by spid
        ("/controller/match/tree/1?version=6329&country=IN&ts=1667318152151&nonce=-20782770&devid=2&miyk=1&spid=in100&power=1", "5a31c79439f2314a2ff935fd852eb5172c9316ed"),
        ("/controller/stb/lineup/match/1?version=6329&country=IN&ts=1667318148341&nonce=871222104", "c9f3ffc28ac586207772e11bcd909ead2b339f3a"),
    ],
    ids=[
        "url_brand_tree", "url_model_code", "url_devices",
        "url_lineup_tree", "url_stb_lineup",
    ]
)
def test_get_opaque_http_param(url_path, expected_opaque):
    """Test opaque parameter for the given url path"""
    found_opaque = get_opaque_http_param(url_path, TOKEN, KEY)
    assert expected_opaque == found_opaque


# Mock builtin random functions for test reproducibility
@patch("src.crypt_utils.randint")
@patch("time.time")
def test_build_url(mock_time, mock_randint):

    # Fix return of random functions
    mock_time.return_value = 1615956113.224
    mock_randint.return_value = -234287591

    # Toshiba TV
    url = build_url(
        "/controller/match/tree/1",
        [("devid", 1), ("miyk", 1), ("brandid", 64), ("power", 1)],
        no_execute=True,
    )
    print(url)
    expected = "https://sg-urc.io.mi.com/controller/match/tree/1?country=FR&version=6034&ts=1615956113224&nonce=-234287591&devid=1&miyk=1&brandid=64&power=1&opaque=668e370bc4c023481caadddde251b63dca1f8eda"
    assert expected == url

    mock_time.return_value = 1615956113.225
    mock_randint.return_value = 244751999

    # Sony camera
    url = build_url(
        "/controller/code/1",
        [("matchid", "kk_13_141_12147"), ("vendor", "kk")],
        no_execute=True,
    )
    print(url)
    expected = "https://sg-urc.io.mi.com/controller/code/1?country=FR&version=6034&ts=1615956113225&nonce=244751999&matchid=kk_13_141_12147&vendor=kk&opaque=3805cd984845631c0ee0ab8c5c7663053eefcb9d"
    assert expected == url


def test_process_xiaomi_shit():
    """Test full decode/decrypt/uncompress/cast of ir code"""
    xiaomi_code = "QJPmll3+SCgpSE73bTO9hni9upbSpKrS73cugR4FZSMT2VGtMTkEIsegm1kjFy3bCLQJsJZKAXxjDF7hGaYIolNzR+qo5f2H3C/PqsSK2Q8kaQaJAycytxhqhVgnwnOUZ6gj0xXscdkPK3MBzr6HH5yEOGDtocCXKP8qEXZdvctnCmFZaZwubXf1Cscf/rlVkAz53JacxfUkCiDqw8M27g=="
    ir_code = process_xiaomi_shit(xiaomi_code)

    expected = [
        9042, 4484, 579, 552, 580, 567, 579, 567, 544, 554, 579, 568, 579, 567,
        579, 1639, 605, 556, 544, 1673, 579, 1686, 553, 1680, 580, 1671, 579, 1686,
        544, 1689, 544, 554, 579, 1671, 579, 567, 579, 1671, 579, 551, 544, 570, 579,
        1639, 605, 572, 581, 550, 544, 570, 580, 1639, 545, 619, 579, 1638, 605,
        1660, 605, 557, 545, 1687, 544, 1658, 579, 1671, 579, 40318, 9018, 2250,
        579, 96733
    ]
    print(ir_code)
    assert expected == ir_code
