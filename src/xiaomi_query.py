#!/usr/bin/env python3
# mi_remote_database a database retriever for IR codes
# Copyright (C) 2021  Ysard
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

# Custom imports
from .crypt_utils import build_url
from .xiaomi_parser import load_devices, load_brand_list, load_brand_codes_from_dir, build_patterns


def get_json_devices():
    """Get all available devices

    `/controller/device/1?version=6034&country=FR&ts=1234&nonce=-1234&opaque=XXX`
    """
    return build_url("https://sg-urc.io.mi.com", "/controller/device/1", [])


def get_json_brands(device_id):
    """Get all brands available for the given device id

    `/controller/brand/list/1?version=6034&country=FR&ts=1234&nonce=1234&devid=1&opaque=XXX`
    """
    return build_url(
        "https://sg-urc.io.mi.com", "/controller/brand/list/1", [("devid", device_id)]
    )


def get_json_brand(brand_id, device_id):
    """Query the API for a brand and return the text result (JSON data)

    URL: `https://urc.io.mi.com/`

    Path:
    `/controller/match/tree/1?version=6034&country=FR&ts=1234&
    nonce=-1234&devid=1&miyk=1&brandid=64&power=1&opaque=XXX`

    :param brand_id: The id of the brand to be queried.
    :param device_id: The id of the device type in the DB;
        TV = 1, Projector = 10
    :type brand_id: <int>
    :type device_id: <int>
    :return: JSON data
    :rtype: <str>
    """
    return build_url(
        "https://sg-urc.io.mi.com",
        "/controller/match/tree/1",
        [("devid", device_id), ("miyk", 1), ("brandid", brand_id), ("power", 1)],
    )


def get_json_model(matchid, vendorid="mi"):
    """Query the API for a model and return the text result (JSON data)

    URL: https://urc.io.mi.com/

    Path:
    `/controller/code/1?version=6034&country=FR&ts=1234&
    nonce=-1234&matchid=xm_1_199&vendor=mi&opaque=XXX`

    `matchid=1_8582&vendor=kk`

    :param matchid: The id of the model to be queried.
    :key vendorid: (Optional) Id of the vendor for which the models are queried.
        Possible ids (known until now): `mi (default), kk, mx, yk`.
    :type matchid: <str>
    :type vendorid: <str>
    :return: JSON data
    :rtype: <str>
    """
    return build_url(
        "https://sg-urc.io.mi.com",
        "/controller/code/1",
        [("matchid", matchid), ("vendor", vendorid)],
    )


################################################################################


def crawl_brands(output_directory, brands):
    """Query the API for all the given brands and dump the result to the given directory

    Brand files are located in `<database_dump>/<device>/*.json`.

    At this step we have (theoretically) only power IR codes for multiple
    models in each brand file.

    .. seealso:: :meth:`get_json_brand`

    :param output_directory: Directory where JSON data will be dumped
    :param brands: Dictionary of brand ids as keys, dict of names and device ids as values.
        .. seealso:: :meth:`load_brand_list`, `full_process_device`
    :type output_directory: <str> or <Path>
    :type brands: <dict <int>:<dict>>
    """
    total = len(brands)

    for index, (brand_id, brand) in enumerate(brands.items()):
        brand_name = brand["name"]
        device_id = brand["deviceid"]
        filepath = Path(f"./{output_directory}/{brand_name}_{brand_id}.json")
        if filepath.exists():
            continue

        # Query the API for the given brand id
        print(f"Begin {index}/{total}: {brand_name} {brand_id}")
        json_data = get_json_brand(brand_id, device_id)

        # Dump the result
        filepath.write_text(json_data)

        print("Done:", brand_id)
        # Do not be too harsh with the server...
        time.sleep(0.4)


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
        Possible ids (known until now): `mi (default), kk, mx, yk`.
    :type output_directory: <str> or <Path>
    :type model_ids: <set <str>>
    :type vendorid: <str>
    """
    total = len(model_ids)

    for index, model_id in enumerate(model_ids):
        filepath = Path(f"./{output_directory}/{model_id}.json")
        if filepath.exists():
            continue
        # Query the API for the given brand id
        print(f"Begin {index}/{total}: {model_id}")
        json_data = get_json_model(model_id, vendorid=vendorid)

        # Dump the result
        filepath.write_text(json_data)

        print("Done:", model_id)
        # Do not be too harsh with the server...
        time.sleep(0.4)
        # input("pause")


def guess_models(output_directory, ids_range):
    """Bruteforce TV ids (deviceid = 1) of xiaomi models and retrieve their data"""
    model_ids = [f"xm_1_{model_id}" for model_id in range(*ids_range)]
    # in place shuffleing
    shuffle(model_ids)
    crawl_models(output_directory, model_ids)


def full_process_device(output_directory, json_device_brands_path):
    """Crawl the API according to brands in the given json, and dump data

    :param output_directory: Device path `<database_dump>/<device>/`
    :param json_device_brands_path: File that lists brands to be queried in
        a specific device.
    :type output_directory: <Path>
    :type json_device_brands_path: <Path>
    """
    # Load list of brands
    brands = load_brand_list(json_device_brands_path)
    # Query data for all brands if dir is empty
    output_directory.mkdir(exist_ok=True)
    # Download brands
    crawl_brands(output_directory, brands)


def dump_database(db_path="./database_dump", *args, **kwargs):
    """Dump all the database into the given directory

    - get all devices: mapping deviceid/device type
    - get all brands per deviceid
    - get models per brand for each deviceid
    """
    # Get all devices
    json_devices_path = Path(f"{db_path}/devices.json")
    if not json_devices_path.is_file():
        Path(json_devices_path).write_text(get_json_devices())

    # TODO: 2: {'name': 'Set-top box'} doesn't use the standard URL
    devices = {k: v for k, v in load_devices(json_devices_path).items() if k != 2}

    # devices = {1: {'name': 'TV'}, 10: {'name': 'Projector'}}
    # devices = {1: {'name': 'TV'}, 3: {'name': 'AC'},
    #  6: {'name': 'Fan'}, 12: {'name': 'Box'}, 8: {'name': 'A_V receiver'},
    #  4: {'name': 'DVD'}, 10: {'name': 'Projector'},
    #  11: {'name': 'Cable _ Satellite box'}, 13: {'name': 'Camera'}}

    # Get brands
    for device_id, device in devices.items():
        device_name = device["name"]
        json_device_brands_path = Path(f"{db_path}/{device_id}_{device_name}.json")

        # Get available brands per deviceid
        if not json_device_brands_path.is_file():
            Path(json_device_brands_path).write_text(get_json_brands(device_id))

        device_brands_path = Path(f"{db_path}/{device_id}_{device_name}")
        device_brands_path.mkdir(exist_ok=True)

        # Get all brands definitions (with power IR code) per deviceid
        # TODO: separate the function
        full_process_device(device_brands_path, json_device_brands_path)

    # Get models per device
    # models_path = Path(f"{db_path}/models/")
    # models_path.mkdir(exist_ok=True)
    for device_id, device in devices.items():
        device_name = device["name"]
        device_brands_path = Path(f"{db_path}/{device_id}_{device_name}")
        models_path = device_brands_path / "models/"
        models_path.mkdir(exist_ok=True)

        device_name = device["name"]
        device_brands_path = Path(f"{db_path}/{device_id}_{device_name}")

        # Only xiaomi models
        models = list(it.chain(*load_brand_codes_from_dir(device_brands_path).values()))
        mi_models = set(
            it.chain(*[model["keysetids"] for model in models if "keysetids" in model])
        )
        crawl_models(models_path, mi_models)

        # Create sets of model ids for each "others" vendor
        other_models = ("kk", "mx", "yk")
        model_id_sets = [
            {model["_id"] for model in models if model.get("source") == vendor}
            for vendor in other_models
        ]

        for vendor, model_ids in zip(other_models, model_id_sets):
            print(model_ids)
            crawl_models(models_path, model_ids, vendorid=vendor)


if __name__ == "__main__":
    dump_database()

    # guess_models("./dump_models/", (6171, 6652))
