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
"""Entry point and argument parser"""
# Standard imports
import itertools as it
from pathlib import Path
import argparse

# Custom imports
from src.xiaomi_parser import (
    load_brand_codes_from_dir,
    build_patterns,
    load_ids_from_brands,
    build_all_patterns,
)
from src.xiaomi_query import dump_database, load_devices
from src.writers import *
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


def check_device_path(db_path, deviceid):
    """Check if a database path exists for the given device id

    :param db_path: Database root directory
    :param deviceid: Id of the device queried
    :type db_path: <Path>
    :type deviceid: <int>
    :return: Device directory path
    :rtype: <Path>
    """
    # Expect directory <db_dir>/<int>_<device_name>/
    found_dirs = [p for p in Path(db_path).glob(f"{deviceid}_*") if p.is_dir()]
    device_path = found_dirs[0] if len(found_dirs) == 1 else None

    if not device_path:
        LOGGER.error(
            "Missing device files or wrong directory: %s/%s_*/", db_path, deviceid
        )
        raise SystemExit(1)
    return device_path


def db_export(deviceid=None, format=None, db_path=None, output=None, **kwargs):
    """Export data to various formats"""
    if deviceid == 3:
        raise NotImplementedError(
            "Deciphering AC IR patterns is not currently supported. Any help "
            "is welcome to do this part of reverse engineering!"
        )

    # Load devices ids/names mapping
    device_mapping = {
        k: v["name"] for k, v in load_devices(Path(f"{db_path}/devices.json")).items()
    }

    # Expect directory <db_dir>/<int>_<device_name>/
    device_path = check_device_path(db_path, deviceid)

    if format == "tvkill":
        # Load codes from all brands
        patterns = load_device_codes(device_path)
        tvkill_export(patterns, output, device_mapping[deviceid])
    elif format == "flipper":
        # Prepare filtering on brands
        queried_brands = kwargs.get("brands")
        # Prepare filtering on keys
        keys = frozenset(kwargs.get("keys"))

        # Here we need ALL IR codes, IR codes stored in JSON brand files
        # are NOT enough, we MUST use model files.
        # Load brands data for the given device
        brands_data = load_ids_from_brands(device_path, brands=queried_brands)

        # Get Patterns for all retrieved models
        models_patterns = build_all_patterns(brands_data, device_path / "models", keys=keys)
        flipper_zero_export(models_patterns, output, device_mapping[deviceid])
    else:
        LOGGER.error("To be implemented")
        raise NotImplementedError


def db_stats(deviceid=None, db_path=None, **kwargs):
    """Show stats about what the databse contains"""
    # Load devices ids/names mapping
    device_mapping = {
        k: v["name"] for k, v in load_devices(Path(f"{db_path}/devices.json")).items()
    }

    # Display available devices if asked
    if kwargs.get("list_devices"):
        print("Device ID: Device Name")
        for dev_name, dev_id in device_mapping.items():
            print(f"{dev_name}: {dev_id}")

    if kwargs.get("list_brands"):
        # Expect directory <db_dir>/<int>_<device_name>/
        device_path = check_device_path(db_path, deviceid)
        brands_data = load_ids_from_brands(device_path)
        print(f"Brands for '{device_mapping[deviceid]}' device:")
        print(brands_data.keys())


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

    # Stats
    parser_stats = subparsers.add_parser(
        "db_stats",
        parents=[parent_parser],
        help=db_stats.__doc__,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser_stats.set_defaults(func=db_stats)
    parser_stats.add_argument(
        "-ld",
        "--list_devices",
        help="List available devices in DB",
        action="store_true",
    )
    parser_stats_grp = parser_stats.add_argument_group()
    parser_stats_grp.add_argument(
        "-lb",
        "--list_brands",
        help="List available brands for the given device id",
        action="store_true",
    )
    parser_stats_grp.add_argument(
        "-d",
        "--deviceid",
        help="Device id (1: TV, 10: Projectors, etc.). See devices.json",
        type=int,
        default=1,
    )

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
        "-b",
        "--brands",
        help="Filter on brand names/ids. Items must be space separated. "
        "Ex: <Fujitsu Sony>.",
        nargs="*",
        default=tuple()
    )
    parser_export.add_argument(
        "-k",
        "--keys",
        help="Filter on key names. Items must be space separated. "
        "Ex: <power power_r shutter>.",
        nargs="*",
        default=tuple()
    )
    parser_export.add_argument(
        "-f", "--format", help="Export format (tvkill (only power codes), flipper)", default="tvkill"
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
