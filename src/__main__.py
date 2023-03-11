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
"""Entry point and argument parser"""
import argparse
from itertools import chain
# Standard imports
from pathlib import Path

import src.commons as cm
from .exports import flipper_export, tvkill_export
# Custom imports
from .xiaomi_parser import load_brand_codes_from_dir, build_patterns
from .xiaomi_query import dump_database, load_devices

LOGGER = cm.logger()


def load_device_codes(device_directory):
    """Load IR codes from the brands stored in the given device directory

    Brand files are located in `<database_dump>/<device>/*.json`.
    They contain (theoretically) only power codes.

    .. warning:: Returned Patterns ARE NOT unique. Make a set if you want this.

    :param device_directory: Directory of a device (brands files are stored in it).
    :type device_directory: <str> or <Path>
    :return: List of model objects
    :rtype: <list <Pattern>>
    """
    # Extract encrypted codes from all the models these brands
    models_per_brand = load_brand_codes_from_dir(device_directory)
    models = list()
    for brand, models_dict in models_per_brand.items():
        for model in models_dict:
            models.append({
                "brand": brand,
                "ir_codes": build_patterns(model["buttons"]),
                "source": model.get("source", None),
                "keysetids": model.get("keysetids", None)
            })
    ir_codes = list(chain(*[model['ir_codes'] for model in models]))

    print("Nb brands:", len(models_per_brand))
    print("Nb models:", len(models))
    print("Nb Patterns:", len(ir_codes))
    print("Nb unique patterns:", len(set(ir_codes)))
    return models


def db_export(deviceid=None, format=None, list_devices=False, db_path=None):
    """Export data to (various ?) formats"""
    # Load devices ids/names mapping
    device_mapping = {
        k: v["name"] for k, v in
        load_devices(Path(f"{db_path}/devices.json")).items()
    }

    # Display available devices if asked
    if list_devices:
        print("Device Name: Device ID")
        [print(f"{v}: {k}") for k, v in device_mapping.items()]
        exit(0)

    # Expect directory <db_dir>/<int>_<device_name>/
    directory = [p for p in Path(db_path).glob(f"{deviceid}_*") if p.is_dir()]
    if len(directory) != 1:
        LOGGER.error("Missing or Wrong directory %s", directory)

    output_path = Path('output')
    if not output_path.exists():
        output_path.mkdir()

    # Build export filename based on device name
    export_filename = str(output_path) + "/" + device_mapping[deviceid]

    # Load codes from directory
    models = load_device_codes(directory[0])

    if format == "tvkill":
        tvkill_export(models, export_filename)
    elif format == "flipper":
        flipper_export(directory[0], models, export_filename)
    else:
        LOGGER.error("To be implemented")
        raise NotImplementedError


def args_to_param(args):
    """Return argparse namespace as a dict {variable name: value}"""
    return {k: v for k, v in vars(args).items() if k not in ("func", "verbose")}


def main():
    """Entry point and argument parser"""
    parser = argparse.ArgumentParser()
    # Default log level: info
    parser.add_argument("-vv", "--verbose", nargs="?", default="info")

    # Subparsers
    subparsers = parser.add_subparsers(title="subcommands")

    # Database dump
    parser_db_dump = subparsers.add_parser(
        "db_dump",
        help=dump_database.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_db_dump.set_defaults(func=dump_database)
    parser_db_dump.add_argument(
        "-o",
        "--output",
        help="Output directory",
        default="./database_dump",
    )

    # Export
    parser_export = subparsers.add_parser(
        "db_export",
        help=db_export.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_export.set_defaults(func=db_export)
    parser_export.add_argument(
        "-d",
        "--deviceid",
        help="Device id (1: TV, 10: Projectors, etc.). See devices.json",
        type=int,
        default=1,
    )
    parser_export.add_argument(
        "-f", "--format", help="Export format (tvkill for now)", default="tvkill"
    )
    parser_export.add_argument(
        "-l", "--list_devices", help="List available devices in DB",
        action="store_true"
    )
    parser_export.add_argument(
        "-p",
        "--db_path",
        help="Path of database dump",
        default="./database_dump",
    )

    # Get program args and launch associated command
    args = parser.parse_args()

    # Set log level
    cm.log_level(vars(args)["verbose"])

    if "func" not in dir(args):
        # Nor argument
        parser.print_usage()
        exit(1)

    args.func(**args_to_param(args))


if "__main__" == __name__:
    main()
