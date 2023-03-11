import json
import os
from itertools import chain
from pathlib import Path

from src.xiaomi_parser import build_patterns


def flipper_export(db_directory, models, export_filename):
    directory = Path(export_filename.replace(" ", "_"))
    if not directory.exists():
        directory.mkdir()
    for model_index in range(len(models)):
        model = models[model_index]
        content = "Filetype: IR signals file\nVersion: 1\n"
        patterns = model['ir_codes']

        if model['keysetids'] is not None:
            patterns += chain(*[load_keyset_codes(db_directory, keyset) for keyset in model['keysetids']])

        for pattern in patterns:
            content += "\n#\n"
            content += pattern.to_flipper()

        path = Path(str(directory) + "/" + model['brand'] + "_" + str(model_index) + ".ir")
        if path.exists():
            os.remove(path)
        path.write_text(content)


def load_keyset_codes(directory, keyset):
    json_filedata = json.loads(Path(str(directory) + '/models/' + keyset + '.json').read_text())
    json_model = json_filedata["data"]
    if 'key' not in json_model:
        return []
    ir_codes = [
        {
            "id": name,
            "ir_zip_key": ircode,
            "frequency": json_model["frequency"]
        }
        for name, ircode in json_model["key"].items()
    ]
    return build_patterns(ir_codes)


def tvkill_export(models, export_filename):
    """Export Pattern objects to JSON data for TV Kill app

    .. note:: Unique patterns are used to reduce overhead.
    """
    patterns = filter(
        lambda pattern: pattern.id == 'power' or pattern.id == 'shutter',
        chain(*[model['ir_codes'] for model in models]))
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
