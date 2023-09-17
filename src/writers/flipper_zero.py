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
"""Functions to export data formatted for the Flipper Zero device"""
# Standard imports
from string import whitespace
import re
from pathlib import Path


def flipper_zero_export(models, output, device_name):
    """Export Pattern objects to ir files required by Flipper Zero device

    File example:

        Filetype: IR signals file
        Version: 1
        # Comments
        #
        name: down
        type: raw
        frequency: 38000
        duty_cycle: 0.330000
        data: ...

    :param models: Dictionary of model ids as keys and list of Pattern objects as values.

        Example:

        {
            'kk_*': [Pattern, ...],
            'mi_*': [Pattern, ...],
        }

    :param output: Directory where files will be exported
    :param device_name: Device name (TV, AC, etc.). Used to identify the origin
        of the codes in the ir files.
    :type models: <dict <str>: <list <Pattern>>>
    :type output: <str>
    :type device_name: <str>
    """
    header_template = """Filetype: IR signals file
Version: 1
# Device: {}; Brand: {}; Model: {}; from Mi Remote DB <https://github.com/ysard/mi_remote_database>
# AGPL-3.0 license, Copyright (C) 2021-2023 Ysard"""

    template = "\n#\nname: {}\ntype: raw\nfrequency: {}\nduty_cycle: 0.330000\ndata: {}"
    for model_id, patterns in models.items():

        content = ""
        for pattern in patterns:
            data = [
                pattern.name,
                pattern.frequency,
                " ".join(map(str, pattern.to_raw())),
            ]
            content += template.format(*data)

        # Prepend header
        content = (
            header_template.format(device_name, pattern.brand, pattern.model_id)
            + content
        )

        # Name processing workaround
        brand = re.sub(rf"[{whitespace}]", "_", pattern.brand)

        # Dump
        path = Path(output) / f"{brand}_{model_id}.ir"
        path.write_text(content, encoding="utf-8")
