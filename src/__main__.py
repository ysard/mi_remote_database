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
# Standard imports
import itertools as it
import json
from pathlib import Path
import argparse

# Custom imports
from src.xiaomi_parser import load_brand_codes_from_dir, build_patterns
from src.xiaomi_query import dump_database, load_devices
import src.commons as cm

LOGGER = cm.logger()


def load_device_codes(device_directory):
    """Load IR codes from the brands stored in the given device directory

    Brand files are located in `<database_dump>/<device>/*.json`.
    They contain (theoretically) only power codes.

    .. warning:: Returned Patterns ARE NOT unique. Make a set if you want this.

    :param device_directory: Directory of a device (brands files are stored in it).
    :type device_directory: <str> or <Path>
    :return: List of Pattern objects (wrappers for decrypted IR codes).
    :rtype: <list <Pattern>>
    """
    # Extract encrypted codes from all the models these brands
    models_per_brand = load_brand_codes_from_dir(device_directory)
    models = list(it.chain(*models_per_brand.values()))
    # Get Patterns from clear IR codes
    patterns = build_patterns(models)

    print("Nb brands:", len(models_per_brand))
    print("Nb models:", len(models))
    print("Nb Patterns:", len(patterns))
    print("Nb unique patterns:", len(set(patterns)))
    return patterns


def db_export(deviceid=None, format=None, list_devices=False, db_path=None, output=None):
    """Export data to (various ?) formats"""
    # Load devices ids/names mapping
    device_mapping = {
        k: v["name"] for k, v in
        load_devices(Path(f"{db_path}/devices.json")).items()
    }

    # Display available devices if asked
    if list_devices:
        print("Device ID: Device Name")
        for dev_name, dev_id in device_mapping.items():
            print(f"{dev_name}: {dev_id}")
        raise SystemExit(0)

    # Expect directory <db_dir>/<int>_<device_name>/
    found_dirs = [p for p in Path(db_path).glob(f"{deviceid}_*") if p.is_dir()]
    device_path = found_dirs[0] if len(found_dirs) == 1 else None

    if not device_path:
        LOGGER.error(
            "Missing device files or wrong directory: %s/%s_*/", db_path, deviceid
        )
        raise SystemExit(1)

    # Build export filename based on device name
    export_filename = f"{format} Xiaomi_" + device_mapping[deviceid]

    if format == "tvkill":
        # Load codes from directory
        patterns = load_device_codes(device_path)
        tvkill_export(patterns, output, export_filename)
    else:
        LOGGER.error("To be implemented")
        raise NotImplementedError


def tvkill_export(patterns, output, export_filename):
    """Export Pattern objects to JSON data for TV Kill app

    .. note:: Unique patterns are used to reduce overhead.
    """
    code_list = [
        {
            "comment": "{} {}".format(code.vendor_id, code.model_id),
            "frequency": code.frequency,
            "pattern": code.to_pulses(),
        }
        for code in set(patterns)
    ]
    tvkill_patterns = {
        "designation": export_filename,
        "patterns": code_list,
    }
    json_data = json.dumps([tvkill_patterns])  # , indent=2)
    Path(output, export_filename.replace(" ", "_") + ".json").write_text(
        json_data
    )


def args_to_param(args):
    """Return argparse namespace as a dict {variable name: value}"""
    return {k: v for k, v in vars(args).items() if k not in ("func", "verbose")}


def dir_path(path):
    """Test existence of the given directory"""
    if Path(path).is_dir():
        return path.rstrip("/")
    raise argparse.ArgumentTypeError(f"{path} is not a valid directory.")


def main():
    """Entry point and argument parser"""
    parser = argparse.ArgumentParser()
    # Default log level: info
    parser.add_argument("-vv", "--verbose", nargs="?", default="info")

    # Parent subparser: All subparsers will inherit of this argument
    parent_parser = argparse.ArgumentParser(add_help=False)
    parent_parser.add_argument(
        "-p",
        "--db_path",
        help="Path of database dump",
        default="./database_dump",
        type=dir_path,
    )
    # Subparsers
    subparsers = parser.add_subparsers(title="subcommands")

    # Database dump
    parser_db_dump = subparsers.add_parser(
        "db_dump",
        parents=[parent_parser],
        help=dump_database.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_db_dump.set_defaults(func=dump_database)

    # Export
    parser_export = subparsers.add_parser(
        "db_export",
        parents=[parent_parser],
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
        "-o",
        "--output",
        help="Output directory",
        default=".",
        type=dir_path,
    )

    # Get program args and launch associated command
    args = parser.parse_args()

    # Set log level
    cm.log_level(vars(args)["verbose"])

    if "func" not in dir(args):
        # Nor argument
        parser.print_usage()
        raise SystemExit(1)

    args.func(**args_to_param(args))


if __name__ == "__main__":
    main()
