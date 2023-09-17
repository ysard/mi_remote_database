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
"""Functions to export data formatted for the Android App TV Kill"""
# Standard imports
import json
from pathlib import Path


def tvkill_export(patterns, output, device_name):
    """Export Pattern objects to JSON data for TV Kill app

    File example:

        [
            {
                "designation": "Xiaomi Projector",
                "patterns": [
                {
                    "comment": "kk 111_6667",
                    "frequency": 37960,
                    "pattern": [
                        341,171,20,22,20,...
                    ]
                }
            }
        ]

    .. note:: Unique patterns are used to reduce overhead.

    :param output: Directory where files will be exported
    :param device_name: Device name (TV, AC, etc.). Used to name the exported file.
    :type output: <str>
    :type device_name: <str>
    """
    json_patterns = [
        {
            "comment": "{} {}".format(pattern.vendor_id, pattern.model_id),
            "frequency": pattern.frequency,
            "pattern": pattern.to_pulses(),
        }
        for pattern in set(patterns)
    ]
    tvkill_patterns = {
        "designation": "Xiaomi '"
        + device_name
        + "' from Mi Remote DB <https://github.com/ysard/mi_remote_database>",
        "patterns": json_patterns,
    }
    json_data = json.dumps([tvkill_patterns])  # , indent=2)

    # Build export filename based on device name
    export_filename = "TVKill_Xiaomi_" + device_name
    Path(output, export_filename.replace(" ", "_") + ".json").write_text(json_data, encoding="utf-8")
