You will find on this repository a proof of concept aiming to reproduce and query the infrared
code database used by the Xiaomi *Mi Remote* application.

The codes are decrypted and can be converted into a number of formats.

This will hopefully allow the creation or improvement of free and gratis alternatives
(and not just gratis with behavioral tracking).

You will find a write-up about this project on the following site:
[reversing Xiaomi Mi Remote (in French)](https://pro-domo.ddns.net/blog/retro-ingenierie-dune-application-android-xiaomi-mi-remote-partie-1.html)

Full database and [TVKILL](https://github.com/42SK/TVKILL/) exports are available in the assets of the GitHub release page.


# Data overview

Data from the DB could be localized (not really studied at the moment);
however, codes are currently queried for France and by extension for Europe (I guess...).

Please note that the following numbers are for *power codes* (ON/OFF codes) **only**.
The number of patterns for other commands **is much more important**.

    TV codes:
    Nb brands: 1060
    Nb models: 2634
    Nb Patterns: 2998
    Nb unique patterns: 1290

    Air conditioners:
    Nb brands: 280
    Nb models: 67
    Nb Patterns: 67
    Nb unique patterns: 50
    (much more in fact, but patterns are crypted and not reversed for now)

    DVD players:
    Nb brands: 247
    Nb models: 579
    Nb Patterns: 608
    Nb unique patterns: 577

    Fans:
    Nb brands: 133
    Nb models: 417
    Nb Patterns: 434
    Nb unique patterns: 191

    Audio/video:
    Nb brands: 202
    Nb models: 432
    Nb Patterns: 505
    Nb unique patterns: 446

    Projectors:
    Nb brands: 118
    Nb models: 364
    Nb Patterns: 385
    Nb unique patterns: 274

    Internet Box:
    Nb brands: 136
    Nb models: 213
    Nb Patterns: 214
    Nb unique patterns: 140

    Camera:
    Nb brands: 12
    Nb models: 17
    Nb Patterns: 17
    Nb unique patterns: 16


# Installation

The project is written for Python 3.6+:

    $ pip install -r requirements.txt


# Usage

Get some help:

    $ python -m src --help

Dump the database (If you don't want to use the one that is available in the GitHub assets, or if you want to update it).

    $ python -m src db_dump
    # or just:
    $ make db_dump

Have coffee in the meantime... Files are in the directory `./database_dump` by default.

If you just want to make an update, delete the *.json files in `./database_dump` but **keep files** in `models`
directories.

List the known devices types in the dump:

    $ python -m src db_export -l
    Device Name: Device ID
    TV: 1
    Set-top box: 2  <= Not supported for now (help wanted to reverse this part)
    AC: 3
    Fan: 6
    Box: 12
    A_V receiver: 8
    DVD: 4
    Projector: 10
    Cable _ Satellite box: 11
    Camera: 13

With **this ids mapping you will be able to export codes for a specific device**,
like shown in the next example.


Export IR codes for one device type to the format of [TVKILL](https://github.com/42SK/TVKILL/) Android app.
Other format can be easily implemented by someone who needs it.
The number `1` in the command is the internal device id in the database (see above).

    $ python -m src db_export -d 1 -f tvkill

A JSON file (`Xiaomi_TV.json`) will be exported with the following structure as example:

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

# Developers

Functions are fully documented in the source code according to Python documentation standards;
moreover, some examples are available in unit tests.

## Data structure

    .
    ├── database_dump
    │   ├── 10_Projector.json # "Device" file: List of brands for this type of device (HP, Epson, Philips, etc.)
    │   ├── 10_Projector      # "Brands" directory: 1 file per brand
    │   │   ├── 3M_1.json     # "Brand" file: each file contains multiple models references with (most of the time) their *power* code
    │   │   ├── ...
    │   │   ├── models        # "Models" directory: 1 file per model
    │   │   │   ├── 1_8582.json # "Model" file: Definitions of all IR codes known for one model
    │   │   │   ├── ...

## Online API description & flowchart

```{mermaid}

    flowchart TD
        A[Get devices] --> |/controller/device/1| B{Is Set-top box device?}
        B --> |No| C[Get all brands] --> |/controller/brand/list/1| D[Get brand]
        B --> |Yes| E[Get all set-topbox brands] --> |/controller/stb/lineup/match/1| D
        D --> |/controller/match/tree/1| G[Get models]
        G --> |/controller/code/1| H[done]
```

## Pattern object

Pattern is a wrapper for IR pulses format.

One pulse is the number of cycles of the carrier for which to turn the
emitter light ON or OFF. Pulses are used for IR transmission based on PWM
(Pulses Width Modulation) where the carrier frequency acts as a clock.

Timmings are expressed in microseconds (us or µs),
Burst/pulse values are expressed in number of cycles of the carrier for which
to turn the light on and off.

Supported formats:

- raw: Timmings in microseconds (us)
- signed raw: Same as raw but positive values are for ON time,
    and negative ones for OFF time.
- pronto: Hex values embedding the carrier frequency, metadata about
    the length of the 2 embedded sequences, and the burst/pulse pairs.
- pulses: Numerical values of the pulse pairs.

Conversion methods available (See in-code documentation):

    to_pronto
    from_pronto
    from_pulses
    to_raw
    to_signed_raw
    to_pulses


Examples:

    >>> pronto = "0000 0071 0000 0002 0000 00AA 0000 0040 0000 0040 0000 0015"
    >>> pattern = Pattern(pronto, None, code_type="pronto")

    >>> ir_code = [9042,4484,579,552,580,567,579,567,544,554]
    >>> pattern = Pattern(ir_code, 37990, code_type="raw")


Python sets can be made to ensure the uniqueness of Pattern objects.


## Cast crypted IR code from database to raw timmings (µs)

    >>> mi = "QJPmll3+SCgpSE73bTO9hni9upbSpKrS73cugR4FZSMT2VGtMTkEIsegm1kjFy3bCLQJsJZKAXxjDF7hGaYIolNzR+qo5f2H3C/PqsSK2Q8kaQaJAycytxhqhVgnwnOUZ6gj0xXscdkPK3MBzr6HH5yEOGDtocCXKP8qEXZdvctnCmFZaZwubXf1Cscf/rlVkAz53JacxfUkCiDqw8M27g=="
    >>> ir_code = process_xiaomi_shit(mi)


## Load codes from a directory

    >>> codes = load_device_codes("./database_dump/1_TV/")

Some brands have an additional section named "others" in the JSON response.
Currently this section *is used* to retrieve codes.
This influences the number of codes collected.

For exemple, for TV codes:

    Without others section:
    Nb brands: 1060
    Nb models: 2302
    Nb Patterns: 2625

    With others section:
    Nb brands: 1060
    Nb models: 2634
    Nb Patterns: 2998
    Nb unique patterns: 1290
    1236 unique IR codes (without frequency param)

# Contributing

Feedback in issues is important and pull-requests are welcome,
but time could be missing to implement large functionality requests ;)
