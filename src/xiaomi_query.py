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
"""Interrogation of the Xiaomi API"""
# Standard imports
import time
import itertools as it
from pathlib import Path
from random import shuffle
from collections import defaultdict

# Custom imports
from .crypt_utils import build_url
from .xiaomi_parser import (
    load_devices,
    load_brand_list,
    load_stp_brand_list,
    load_ids_from_brands,
)
from .commons import logger

LOGGER = logger()


def get_json_devices():
    """Get all available devices

    Example of url used:
    `/controller/device/1?version=6034&country=FR&ts=1234&nonce=-1234&opaque=XXX`
    """
    return build_url("/controller/device/1", [])


def get_json_brands(device_id):
    """Get all brands available for the given device id

    Example of url used:
    `/controller/brand/list/1?version=6034&country=FR&ts=1234&nonce=1234&devid=1&opaque=XXX`
    """
    return build_url("/controller/brand/list/1", [("devid", device_id)])


def get_json_stb_brands():
    """Get all brands of Set-top box devices

    .. note:: Languages available: CN, IN, EN, TW.
        IN is the only one with some brands returned.
    """
    return build_url("/controller/stb/lineup/match/1", [], country="IN")


def get_json_brand(brand_id, device_id, stb=False):
    """Query the API for a brand and return the text result (JSON data)

    Example of url used:
    `/controller/match/tree/1?version=6034&country=FR&ts=1234&
    nonce=-1234&devid=1&miyk=1&brandid=64&power=1&opaque=XXX`

    :param brand_id: The id of the brand to be queried.
    :param device_id: The id of the device type in the DB;
        TV = 1, Projector = 10
    :key stb: Switch to Set-top box devices if True.
    :type brand_id: <int>
    :type device_id: <int>
    :type stb: <boolean>
    :return: JSON data
    :rtype: <str>
    """
    if stb:
        return build_url(
            "/controller/match/tree/1",
            [("devid", device_id), ("miyk", 1), ("spid", brand_id), ("power", 1)],
        )

    return build_url(
        "/controller/match/tree/1",
        [("devid", device_id), ("miyk", 1), ("brandid", brand_id), ("power", 1)],
    )


def get_json_model(matchid, vendorid="mi"):
    """Query the API for a model and return the text result (JSON data)

    Example of url used:
    `/controller/code/1?version=6034&country=FR&ts=1234&
    nonce=-1234&matchid=xm_1_199&vendor=mi&opaque=XXX`
    or:
    `...matchid=1_8582&vendor=kk...`

    :param matchid: The id of the model to be queried.
    :key vendorid: (Optional) Id of the vendor for which the models are queried.
        Possible ids (known until now): `mi (default), kk, mx, yk`.
    :type matchid: <str>
    :type vendorid: <str>
    :return: JSON data
    :rtype: <str>
    """
    return build_url(
        "/controller/code/1",
        [("matchid", matchid), ("vendor", vendorid)],
    )


################################################################################


def crawl_brands(output_directory, brands, stb=False):
    """Query the API for all the given brands and dump the result to the given directory

    Brand files are located in `<database_dump>/<device>/*.json`.

    At this step we have (theoretically) only power IR codes for multiple
    models in each brand file.

    Example of files created: Fujitsu_70.json, Sony_141.json, etc.

    .. seealso:: :meth:`get_json_brand`

    :param output_directory: Directory where JSON data will be dumped
    :param brands: Dictionary of brand ids as keys, dict of names and device ids as values.
        .. seealso:: :meth:`load_brand_list`, `full_process_device`
    :key stb: Switch to Set-top box devices if True.
    :type output_directory: <str> or <Path>
    :type brands: <dict <int>:<dict>>
    :type stb: <boolean>
    """
    total = len(brands)

    for index, (brand_id, brand) in enumerate(brands.items()):
        brand_name = brand["name"]
        device_id = brand["deviceid"]
        filepath = Path(f"./{output_directory}/{brand_name}_{brand_id}.json")
        if filepath.exists():
            continue

        # Query the API for the given brand id
        LOGGER.info("Begin %d/%d: %s %s", index, total, brand_name, brand_id)
        json_data = get_json_brand(brand_id, device_id, stb=stb)

        # Dump the result
        filepath.write_text(json_data, encoding="utf-8")

        LOGGER.debug("Done: %s", brand_id)
        # Do not be too harsh with the server...
        time.sleep(0.2)


def crawl_models(output_directory, model_ids, vendorid="mi"):
    """Query the API for all the given models and dump the result to the given directory

    Model files are located in `<database_dump>/<device>/models/*.json`.

    At this step we have ALL IR codes known for every models.

    .. seealso:: :meth:`get_json_model`

    :param output_directory: Directory where JSON data will be dumped
    :param model_ids: Iterable of ids of models known to belong to the given
        vendorid. Ids are extracted from brand files for a specific device.
        .. seealso:: :meth:`load_brand_codes_from_dir`
    :key vendorid: (Optional) Id of the vendor for which the models are queried.
        Possible ids (known until now): `mi (default), kk, mx, xm, yk`.
    :type output_directory: <str> or <Path>
    :type model_ids: <set <str>>
    :type vendorid: <str>
    """
    total = len(model_ids)

    # Sort before iterating: better output for progression if files are akready downloaded
    for index, model_id in enumerate(sorted(model_ids)):
        filepath = Path(f"./{output_directory}/{model_id}.json")
        if filepath.exists():
            continue
        # Query the API for the given brand id
        LOGGER.info("Begin %d/%d: %s", index, total, model_id)
        json_data = get_json_model(model_id, vendorid=vendorid)

        # Dump the result
        filepath.write_text(json_data, encoding="utf-8")

        LOGGER.debug("Done: %s", model_id)
        # Do not be too harsh with the server...
        time.sleep(0.2)


def guess_models(output_directory, ids_range):
    """Bruteforce TV ids (deviceid = 1) of xiaomi models and retrieve their data"""
    model_ids = [f"xm_1_{model_id}" for model_id in range(*ids_range)]
    # in place shuffleing
    shuffle(model_ids)
    crawl_models(output_directory, model_ids)


def full_process_device(output_directory, json_device_brands_path, stb=False):
    """Crawl the API according to brands in the given json, and dump data

    :param output_directory: Device path `<database_dump>/<device>/`
    :param json_device_brands_path: File that lists brands to be queried in
        a specific device.
    :key stb: Switch to Set-top box devices if True.
    :type output_directory: <Path>
    :type json_device_brands_path: <Path>
    :type stb: <boolean>
    """
    # Load list of brands that should be queried
    func = load_stp_brand_list if stb else load_brand_list
    brands = func(json_device_brands_path)
    output_directory.mkdir(exist_ok=True)
    # Download brands
    crawl_brands(output_directory, brands, stb=stb)


def dump_database(*_args, db_path="./database_dump", **_kwargs):
    """Dump all the database into the given directory

    - get all devices: mapping deviceid/device type;
        Example of files created: 1_TV.json, 2_Set-top box.json, etc.
    - get all brands per deviceid;
        Example of files created: Fujitsu_70.json, Sony_141.json, etc.
    - get models per brand for each deviceid.
    """
    # Get all devices
    json_devices_path = Path(f"{db_path}/devices.json")
    if not json_devices_path.is_file():
        Path(json_devices_path).write_text(get_json_devices(), encoding="utf-8")

    # Data ex: {1: {'name': 'TV'}, ...}
    devices = load_devices(json_devices_path)

    # Get brands
    for device_id, device in devices.items():
        device_name = device["name"]
        json_device_brands_path = Path(f"{db_path}/{device_id}_{device_name}.json")
        stb_device = device_id == 2

        # Get available brands per deviceid
        if not json_device_brands_path.is_file():
            if stb_device:
                # Handle set-top box devices
                json_data = get_json_stb_brands()
            else:
                json_data = get_json_brands(device_id)
            Path(json_device_brands_path).write_text(json_data, encoding="utf-8")

        device_brands_path = Path(f"{db_path}/{device_id}_{device_name}")
        device_brands_path.mkdir(exist_ok=True)

        # Download all brands definitions (with power IR code) per deviceid
        LOGGER.info("Downloading device: %s", device_name)
        full_process_device(device_brands_path, json_device_brands_path, stb=stb_device)

    # Get models per device
    for device_id, device in devices.items():
        device_name = device["name"]
        device_brands_path = Path(f"{db_path}/{device_id}_{device_name}")
        models_path = device_brands_path / "models/"
        models_path.mkdir(exist_ok=True)

        # Get model ids per vendor per brand
        brands_data = load_ids_from_brands(device_brands_path)

        # Merge all vendors and their model_ids for the current device
        # - Could iterate over brands and download instead merging,
        # but global progression will be impossible.
        # - Also avoid multiple downloads for a model
        model_ids_per_vendors = defaultdict(set)
        g = it.chain(*[vendor.items() for vendor in brands_data.values()])
        for vendor_id, model_ids in g:
            model_ids_per_vendors[vendor_id].update(model_ids)

        for vendor_id, model_ids in model_ids_per_vendors.items():
            LOGGER.info("Downloading models for vendor %s, device: %s", vendor_id, device_name)
            # Download models
            crawl_models(models_path, model_ids, vendorid=vendor_id)


if __name__ == "__main__":
    dump_database()

    # guess_models("./dump_models/", (6171, 6652))
