#!/usr/bin/env python3
# mi_remote_database a database retriever for IR codes
# Copyright (C) 2021-2023  Ysard
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""Interpretation of obfuscated IR codes and formatting of urls"""
# Standard imports
import time
import json
import base64
import gzip
from random import randint

# Custom imports
# pycryptodome==3.5.1
from Crypto.Cipher import AES
from Crypto.Hash import HMAC, SHA1
from requests import Request, Session


PATTERN_SECRET_KEY = "fd7e915003168929c1a9b0ec32a60788"  # 16bytes length multiple
URL_TOKEN = "0f9dfa001cba164d7bda671649c50abf"
URL_SECRET_KEY = "581582928c881b42eedce96331bff5d3"


def decrypt_pattern(encoded_pattern):
    """Decrypt base64 string with AES ECB mode and a known "secret key"

    :param encoded_pattern: Encrypted text
    :type encoded_pattern: <str>
    :return: Decrypted bytes
    :rtype: <bytes>
    """
    # Base64 decode
    encoded_pattern = base64.b64decode(encoded_pattern)
    cipher = AES.new(PATTERN_SECRET_KEY.encode(), AES.MODE_ECB)
    # Remove trailing padding spaces
    return cipher.decrypt(encoded_pattern).rstrip()


def process_xiaomi_shit(encoded_pattern):
    """Process encoded IR pattern from the API of Xiaomi

    Operations:
        - Decode base64 string
        - Decrypt pattern (AES ECB mode) with a known "secret key"
        - Uncompress GZIP data to recover the plain text as a JSON array
        - Convert JSON array to Python list

    :param encoded_pattern: Base64 encoded, AES ECB crypted, GZip compressed pattern.
        .. seealso:: :meth:`decrypt_pattern`
    :return: List of raw timmings corresponding to the IR code.
        Each value is the time during the transmitter should be stay ON or OFF
        (It's not based on the number of pulses regarding to the frequency used).
    """
    decrypted_pattern = decrypt_pattern(encoded_pattern)
    plain_text = gzip.decompress(decrypted_pattern)
    return json.loads(plain_text)


################################################################################


def get_opaque_http_param(url, token, secret_key):
    """Get the opaque parameter based on the url, an internal token and a
    secret key for the hash algorithm

    :return: "opaque" parameter to be inserted at the end of the url path
    :rtype: <str>
    """
    plain_text = url + "&token=" + token
    # Get signature of this concatenation
    return get_signature(plain_text, secret_key)


def get_signature(plain_text, secret_key):
    """Get signature/hash of the given plain_text with the secret_key

    Use HMAC (Hash-based Message Authentication Code) with SHA1 hash algorithm.

    :param plain_text: Clear text to be signed
    :param secret_key: Secret key
    :type plain_text: <str>
    :type secret_key: <str>
    :return: Hex digest of the signature
    :rtype: <str>
    """
    cipher = HMAC.new(secret_key.encode(), digestmod=SHA1)
    return cipher.update(plain_text.encode()).hexdigest()


def build_url(url_prefix, params, server="https://sg-urc.io.mi.com", country="FR", no_execute=False):
    """Build and execute an URL for the API

    The built is based on the implementation of an anti-replay attack protection.
    .. seealso:: :meth:`get_opaque_http_param`, `get_signature`.

    Add version=6034, country=FR, ts, nonce and opaque signature HTTP parameters.

    Headers of queries:
        `accept-encoding: gzip`
        `user-agent: okhttp/3.8.0`

    :param url_prefix: Fixed part of the url (without server name)
    :param params: List of http parameters
    :param country: 2 letters country code. Some IR codes may be localized like CN ones.
    :key server: Server url
    :key no_execute: (Optional) Don't execute the query, just return the URL string.
        Default: False.
    :type url_prefix: <str>
    :type params: <list <tuples>>
    :type server: <str>
    :type country: <str>
    :type no_execute: <boolean>
    :return:
    """
    fixed_parameters = [
        ("country", country),
        ("version", 6034),
        ("ts", int(time.time() * 1000)),
        ("nonce", randint(-500_000_000, 500_000_000)),
    ]
    fixed_parameters += params

    headers = {
        "accept-encoding": "gzip",
        "user-agent": "okhttp/3.8.0",
    }

    session = Session()

    # Use Request object to format parameters for us
    query = Request(
        "GET", server + url_prefix, params=fixed_parameters, headers=headers
    ).prepare()
    # print(query.url, query.path_url)
    # The path part is accessible via path_url attr
    opaque = get_opaque_http_param(query.path_url, URL_TOKEN, URL_SECRET_KEY)

    # Update url by adding the opaque parameter
    query.prepare_url(query.url, {"opaque": opaque})

    if no_execute:
        return query.url
    return session.send(query).text
