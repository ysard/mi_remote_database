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
"""Parse data from Xiaomi API"""
# Standard imports
import json
from pathlib import Path
import itertools as it
from collections import defaultdict

# Custom imports
from .crypt_utils import process_xiaomi_shit
from .pattern import Pattern
from .commons import logger

LOGGER = logger()


def load_devices(filename):
    """Get devices from JSON dump

    TODO: what are providers ?

    Example of data returned:

    {
        1: {'name': 'TV'}, 2: {'name': 'Set-top box'}, 3: {'name': 'AC'},
        6: {'name': 'Fan'}, 12: {'name': 'Box'}, 8: {'name': 'A_V receiver'},
        4: {'name': 'DVD'}, 10: {'name': 'Projector'},
        11: {'name': 'Cable _ Satellite box'}, 13: {'name': 'Camera'}
    }

    Other keys are available but not used/returned. See `devices.json` file.

    :return: Dictionary of devices, with numerical ids as keys and dict of
        device description as values.
    :rtype: <dict <int>: <dict>>
    """
    json_filedata = json.loads(Path(filename).read_text(encoding="utf-8"))
    devices = dict()

    for json_device in json_filedata["data"]:
        info = json_device["info"]
        # Get only the english name of the device
        device_name = [item["name"] for item in info if item["country"] == "EN"][0]
        device_id = json_device["deviceid"]
        # Fix further errors with paths...
        devices[device_id] = {
            "name": device_name.replace("/", "_")
        }
    return devices


def load_brand_list(filename):
    r"""Get brands from JSON dump

    Device file data example:

    {
       "status":0,
       "data":[
          {
             "providers":[
                {
                   "id":"1973",
                   "type":"kk"
                }
             ],
             "brandid":1973,
             "deviceid":1,
             "info":[
                {
                   "name":"爱家乐",
                   "country":"CN"
                },
                {
                   "name":"Akira",
                   "country":"EN"
                }
             ],
             "name":"爱家乐",
             "yellow_id":-1,
             "category":"other"
          },
          {
             "brandid":4207,
             "providers":[
                {
                   "id":"4207",
                   "type":"kk"
                }
             ],
             "deviceid":1,
             "info":[
                {
                   "name":"Lloytron",
                   "country":"CN"
                },
                {
                   "name":"Lloytron",
                   "country":"EN"
                }
             ],
             "name":"Lloytron",
             "category":"other",
             "priority":999
          },
          {
             "category":"other",
             "deviceid":1,
             "providers":[
                {
                   "id":"64",
                   "type":"mx"
                },
                {
                   "id":"64",
                   "type":"kk"
                },
                {
                   "id":"64",
                   "type":"mi"
                }
             ],
             "logo":"http:\/\/image.box.xiaomi.com\/mfsv2\/download\/s010\/p01TX25H9u3v\/qjVx5KtQ66bvXj.jpg",
             "brandid":64,
             "name":"东芝",
             "priority":13,
             "info":[
                {
                   "name":"东芝",
                   "country":"CN"
                },
                {
                   "name":"Toshiba",
                   "country":"EN"
                }
             ],
             "yellow_id":14
          },
       ],
       "encoding":"UTF-8",
       "language":"ZH_CN"
    }

    Example of data returned:

    {
        84: {"name":"Canon", "deviceid":13},
        2051: {"name":"Nikon", "deviceid":13}
    }
    Where 84 and 2051 are the brand ids.

    :param filename: JSON file with the definitions of the available brands
    :type filename: <str>
    :return: Dictionary of brand ids as keys, dict of names and device ids as values.
        Used keys from JSON: brandid, deviceid, name
    :rtype: <dict <int>:<dict>>
    """
    json_filedata = json.loads(Path(filename).read_text(encoding="utf-8"))

    brands = dict()
    json_brands = json_filedata["data"]
    for brand in json_brands:
        # Get the occidental name of the brand
        # Assume EN language is always set
        info = brand["info"]
        brand_name = [item["name"] for item in info if item["country"] == "EN"][0]  # TODO some cleaning
        brand_id = brand["brandid"]
        device_id = brand["deviceid"]
        # print(brand_name, brand_id, type(brand_id))
        brands[brand_id] = {
            "name": brand_name.replace("\n", ""),
            "deviceid": device_id,
        }
    return brands


def load_stp_brand_list(filename):
    """Get brands from JSON dump of set-top box devices

    Here, the `sp` key is assimilated to the `brandid` usually adopted
    everywhere else in the API.

    Device file data example:

    {"status":0,"data":{
        "count":52,"data":[
            {
                "type":0,"matchs":[],"sp":"in112","s_tpbrand":94,
                "name":"ACT Digital", "_id":"in_lu_112"
            },
            {
                "type":0,"matchs":[],"sp":"in100","s_tpbrand":93,
                "name":"Airtel","_id":"in_lu_100"
            }
            ...
        ]
    }}

    :param filename: JSON file with the definitions of the available brands
    :type filename: <str>
    :return: Dictionary of sp ids as keys, dict of names and device ids as values.
        Used keys from JSON: brandid, deviceid, name
    :rtype: <dict <str>:<dict>>
    """
    json_filedata = json.loads(Path(filename).read_text(encoding="utf-8"))

    brands = dict()
    json_brands = json_filedata["data"]["data"]
    for brand in json_brands:
        # print(brand["name"], brand["sp"], type(brand["sp"]))
        brands[brand["sp"]] = {
            "name": brand["name"].replace("\n", ""),  # TODO: cleaning
            "deviceid": 2,
        }
    return brands


def load_brand_codes(filename):
    r"""Extract IR encrypted codes for each model from a given JSON dump of a brand

    {
       "status":0,
       "data":{
          "tree":{
             "hasPower":1,
             "root_index":0,
             "spid":null,
             "seceret_key":null,
             "brand":64,
             "entrys":28,
             "nodes":[
                {
                   "children_index":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32],
                   "frequency":0,
                   "level":0,
                   "parent_index":-1,
                   "index":0
                },
                {
                   "ir_zip_key":"QJPmll3+SCgpSE73bTO9hni9upbSpKrS73cugR4FZSMT2VGtMTkEIsegm1kjFy3bCLQJsJZKAXxjDF7hGaYIolNzR+qo5f2H3C\/PqsSK2Q8kaQaJAycytxhqhVgnwnOUZ6gj0xXscdkPK3MBzr6HH5yEOGDtocCXKP8qEXZdvctnCmFZaZwubXf1Cscf\/rlVkAz53JacxfUkCiDqw8M27g==",
                   "keysetids":["xm_1_199", "xm_1_2425"],
                   "children_index":[7, 8],
                   "frequency":37990,
                   "level":1,
                   "parent_index":0,
                   "index":6,
                   "keyid":"power"
                },
                {
                   "ir_zip_key_r":"xxx",
                   "ir_zip_key":"xxx",
                   "keysetids":["xm_1_4410"],
                   "children_index":[],
                   "frequency":37000,
                   "level":1,
                   "parent_index":0,
                   "index":2,
                   "keyid":"power"
                },
                "status":true,
             "device":1,
             "version":1,
             "country":"IN"
          },
          "others":[
             {
                "_id":"kk_1_64_3445",
                "key":{
                   "vol+":"xxx",
                   "power":"xxx"
                },
                "frequency":38000,
                "seceret_key":null,
                "source":"kk",
                "kk_id":"3445",
                "brand":"64",
                "match_counts":{"ID":260, "UZ":1, "IN":27470, ...},
                "locales":{"MY":10, "ID":10, "IN":10},
                "order":10,
                "device":1
             },
             {
                "_id":"kk_1_64_6857",
                "key":{
                   "power_r":"xxx",
                   "vol+":"xxx",
                   "tv_av":"xxx",
                   "power":"xxx"
                },
                "frequency":36960,
                "seceret_key":null,
                "source":"kk",
                "kk_id":"6857",
                "brand":"64",
                "match_counts":{"SA":4, "ID":1687, "IN":2994, ...},
                "locales":{"MY":12, "ID":12, "IN":12},
                "order":12,
                "device":1
             }
          ]
       },
       "encoding":"UTF-8",
       "language":"ZH_CN"
    }

    TODO:
        filter on other keys than power/power_r for "other" field.
        If a device hasn't such keys, it will be skipped.

        TL;DR: Quickly, there is a filtering in this function which should not
        be done at this level.

        If we really wanted to retrieve all models, we would only use keysetids
        and _id/source fields.

    :param filename: JSON file with the definitions of the models available for 1 brand.
        1 model can have multiple codes including reverse codes.
        We asked power codes so, each code corresponds to this type.
    :type filename: <str>
    :return: List of dictionnaries corresponding to the definitions of the codes for each model.
        1 dict per model.
        Used keys from JSON: ir_zip_key, frequency, ir_zip_key_r, keysetids
        (internal model id linked to the codes in database), _id, source, power, power_r.
    :rtype: <list <dict>>
    """

    def parse_others_section(section):
        """Temp function to handle 'others' key of a brand JSON description"""
        # TODO: filter on other keys than power/power_r/shutter

        for json_model in section:
            power_code = json_model["key"].get("power")
            # TODO: Exception for Cameras... See workaround above...
            shutter_code = json_model["key"].get("shutter")
            if not power_code and not shutter_code:
                LOGGER.warning(
                    "Key power/shutter NOT FOUND in 'others', path: <%s>; "
                    "model id <%s>; keys: %s",
                    filename, json_model["_id"], json_model["key"].keys(),
                )
                continue

            model = {
                # TODO: Ugly workaround: assign shutter if no power (for cameras)
                "ir_zip_key": power_code if power_code else shutter_code,
                "frequency": json_model["frequency"],
                "_id": json_model["_id"],
                "source": json_model["source"],
            }

            # Optional reverse code
            reverse_code = json_model["key"].get("power_r")
            if reverse_code:
                model["ir_zip_key_r"] = reverse_code

            yield model

    json_filedata = json.loads(Path(filename).read_text(encoding="utf-8"))
    models = list()

    if "others" in json_filedata["data"]:
        models += [
            model for model in parse_others_section(json_filedata["data"]["others"])
        ]

    ############################################################################
    # Usual data from "mi" vendor
    tree = json_filedata["data"]["tree"]
    if not tree:
        # Empty tree
        return models

    json_models = tree["nodes"]
    for json_model in json_models[1:]:  # Skip the first element: "children_index"
        model = {
            "ir_zip_key": json_model["ir_zip_key"],
            "frequency": json_model["frequency"],
            "keysetids": json_model["keysetids"],  # Get list of compatible models
        }
        # Optional reverse code
        reverse_code = json_model.get("ir_zip_key_r")
        if reverse_code:
            model["ir_zip_key_r"] = reverse_code

        models.append(model)
    return models


def build_patterns(models):
    """Generate Pattern objects (clear IR codes) for the given models.

    IR codes are decrypted according to :meth:`process_xiaomi_shit`.

    :param models: Models returned by :meth:`load_brand_codes`.
    :return: List of Pattern objects: wrappers for one IR code.
    :rtype: <list <Pattern>>
    """
    patterns = list()

    for model in models:
        frequency = model["frequency"]

        if not frequency:
            # Some codes have a 0 frequency...
            LOGGER.error("Invalid frequency for the model:\n%s", model)
            continue

        # Decrypt IR code
        ir_code = process_xiaomi_shit(model["ir_zip_key"])
        pattern = Pattern(
            ir_code,
            frequency,
            model_id=model.get("_id", model.get("keysetids")),
            vendor_id=model.get("source", "mi"),
        )
        patterns.append(pattern)

        # Optional reverse code = separated Pattern
        if "ir_zip_key_r" in model:
            # Decrypt IR code
            ir_code = process_xiaomi_shit(model["ir_zip_key_r"])
            pattern = Pattern(
                ir_code,
                frequency,
                model_id=model.get("_id", model.get("keysetids")),
                vendor_id=model.get("source", "mi"),
            )
            patterns.append(pattern)

    return patterns


def build_all_patterns(brands_data, models_path, keys=tuple()):
    """Generate 1 Pattern object (clear IR codes) for each IR code found in the
    model files corresponding to the given model ids.

    IR codes are decrypted according to :meth:`process_xiaomi_shit`.

    Example of input data:

        {
            'Fujitsu_70': {
                'kk': {'kk_*'},
                'mi': {'xm_*'},
                ...
            },
            ...
        }

    Example of returned data:

        {
            'kk_*': [Pattern, ...],
            'mi_*': [Pattern, ...],
        }

    :param brands_data: Model ids per vendor per brand.
        See :meth:`load_ids_from_brands`.
    :param models_path: Directory path storing all JSON files for models of
        a type of device.
    :key keys: Iterable of key names to retrieve. Non-matching names will
        be dropped. Default: No filtering.
    :type brands_data: <dict <dict <str>: <set>>>
    :type models_path: <Path>
    :type keys: <tuple> or <set>
    :return: Dictionary of model ids as keys and list of Pattern objects as values.
        .. note:: Empty models ARE NOT returned.
    :rtype: <dict <str>: <list <Pattern>>>
    """
    models = (
        (brand, vendor_id, model_ids)
        for brand, vendors in brands_data.items()
        for vendor_id, model_ids in vendors.items()
    )
    # Index to speed up process in case of duplicates
    patterns = dict()
    # Final result: model_id as keys, patterns as values
    models_patterns = defaultdict(list)
    total_models = 0
    for brand, vendor_id, model_ids in models:
        total_models += len(model_ids)

        for model_id in model_ids:
            filepath = models_path / (model_id + ".json")
            if not filepath.exists():
                continue
            json_filedata = json.loads(filepath.read_text(encoding="utf-8"))

            data = json_filedata["data"]
            if not data:
                continue
            frequency = data["frequency"]
            if not frequency:
                LOGGER.error("Bad frequency: %s: %d", filepath, frequency)
                continue

            # Create 1 pattern object for each key
            for key_name, ir_cipher in data["key"].items():
                # Filter keys
                if keys and key_name not in keys:
                    continue
                # Is pattern already built ?
                pattern_key = (ir_cipher, frequency)
                pattern = patterns.get(pattern_key)
                if pattern:
                    models_patterns[model_id].append(pattern)
                    continue

                # Decrypt IR code
                ir_code = process_xiaomi_shit(ir_cipher)
                pattern = Pattern(
                    ir_code,
                    frequency,
                    name=key_name,
                    model_id=model_id,
                    brand_name=brand,
                    vendor_id=vendor_id,
                )
                patterns[pattern_key] = pattern
                models_patterns[model_id].append(pattern)

    LOGGER.info("Nb brands: %d", len(brands_data))
    LOGGER.info("Nb models: %d", total_models)
    LOGGER.info("Unique patterns: %d", len(patterns))
    return dict(models_patterns)


def get_vendors_model_ids(brand_filepath):
    """Get model ids per vendor, for the given brand file

    Example of returned data:

        {
            'kk': {'kk_*'},
            'mi': {'xm_*'},
            ...
        }

    :param brand_filepath: Filepath of a brand JSON file.
    :type brand_filepath: <Path>
    :return: Dictionary of vendors as keys and model ids as values.
        Expected optional keys: ("mi", "kk", "mx", "xm", "yk").
        'mi' vendor should be set most of the time but not guaranteed.
    :rtype: <dict <str>: <set>>
    """
    json_filedata = json.loads(Path(brand_filepath).read_text(encoding="utf-8"))

    data = json_filedata["data"]
    model_ids = defaultdict(set)

    # Extra data from other vendors
    if "others" in data:
        for model in data["others"]:
            model_ids[model["source"]].add(model["_id"])

    # Usual data from "mi" vendor
    tree = data["tree"]
    if not tree:
        return dict(model_ids)

    # Skip the first element of nodes: "children_index"
    model_ids["mi"].update(
        it.chain(*[model["keysetids"] for model in tree["nodes"][1:]])
    )
    return dict(model_ids)


def load_ids_from_brands(device_path, brands=tuple(), vendors=tuple()):
    """Get model ids per vendor per brand, for the given device path

    Example of returned data:

        {
            'Fujitsu_70': {
                'kk': {'kk_*'},
                'mi': {'xm_*'},
                ...
            },
            ...
        }

    :param device_path: Directory path storing all JSON files for brands of
        a type of device.
    :key: brands: Iterable of brand names to retrieve. Non-matching names will
        be dropped. Default: No filtering.
    :key: vendors: Iterable of vendors to retrieve. Non-matching names will
        be dropped. Default: No filtering.
    :type brands: <tuple>
    :type vendors: <tuple>
    :type device_path: <Path>
    :return: Dictionary of brands as keys and dict of vendors as values.
        Each vendor has model ids as values.
        Expected optional vendor keys: ("mi", "kk", "mx", "xm", "yk").
        'mi' vendor should be set most of the time but not guaranteed.
    :rtype: <dict <dict <str>: <set>>>
    """
    total = 0
    brands_data = dict()
    for brand_filepath in device_path.glob("*.json"):

        # Skip if filter is enabled and name not compatible with the current file
        if brands:
            found_name = [True for name in brands if name in str(brand_filepath)]
            if not found_name:
                continue

        # Load model ids per vendor, from models in this brand file
        vendors_data = get_vendors_model_ids(brand_filepath)
        if vendors:
            # Filter on vendor names
            vendors_data = {
                vendor: data
                for vendor, data in vendors_data.items()
                if vendor in vendors
            }

        brand_name = brand_filepath.stem  # TODO: str(brand_filepath.stem).split("_")[0]
        brands_data[brand_name] = vendors_data

        nb_model_ids = sum(len(ids) for ids in vendors_data.values())
        LOGGER.info("%s... %d", brand_filepath, nb_model_ids)
        total += nb_model_ids

    LOGGER.info("TOTAL models from brands loaded: %d", total)
    return brands_data


def load_brand_codes_from_dir(device_path):
    """Extract IR encrypted codes for models from all brands in the given directory

    .. seealso:: :meth:`load_brand_codes`

    :return: Dict with filenames as keys and list of dictionnaries corresponding
        to the definitions of the codes as values.
    :rtype: <dict <str>:<list <dict>>>
    """
    total = 0
    models = dict()
    for brand_filepath in Path(device_path).glob("*.json"):
        # Load codes from models in this brand file
        temp_models = load_brand_codes(brand_filepath)
        models[brand_filepath.stem] = temp_models
        total += len(temp_models)
        LOGGER.info("%s... %d", brand_filepath, len(temp_models))

    LOGGER.info("TOTAL models from brands loaded: %d", total)
    return models
