import json
import os
from pathlib import Path


def flipper_export(brands, export_filename):
    directory = Path(export_filename.replace(" ", "_"))
    if not directory.exists():
        directory.mkdir()
    for brand_per_patterns in brands:
        content = "Filetype: IR signals file\nVersion: 1"
        for pattern in brand_per_patterns['ir_codes']:
            content += "\n#"
            content += "\nname: " + pattern.id
            content += "\ntype: raw"
            content += "\nfrequency: " + str(pattern.frequency)
            content += "\nduty_cycle: 0.330000"
            content += "\ndata: " + ' '.join([str(timing) for timing in pattern.to_raw()])
        path = Path(str(directory) + "/" + brand_per_patterns['brand'] + ".ir")
        if path.exists():
            os.remove(path)
        path.write_text(content)


def tvkill_export(patterns, export_filename):
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
    Path(export_filename.replace(" ", "_") + ".json").write_text(json_data)
