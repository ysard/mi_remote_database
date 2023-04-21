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
# Standard imports
import json
from pathlib import Path


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
