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
"""Wrapper for IR pulses format"""
# Standard imports
from functools import partial


class Pattern:
    """Wrapper for IR pulses format

    One pulse is the number of cycles of the carrier for which to turn the
    emitter light ON or OFF. Pulses are used for IR transmission based on PWM
    (Pulses Width Modulation) where the carrier frequency acts as a clock.

    Timmings are expressed in microseconds (us),
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

        - :meth:`to_pronto`
        - :meth:`from_pronto`
        - :meth:`from_pulses`
        - :meth:`to_raw`
        - :meth:`to_signed_raw`
        - :meth:`to_pulses`

    Examples:

        >>> pronto = "0000 0071 0000 0002 0000 00AA 0000 0040 0000 0040 0000 0015"
        >>> pattern = Pattern(pronto, None, code_type="pronto")

        >>> ir_code = [9042,4484,579,552,580,567,579,567,544,554]
        >>> pattern = Pattern(ir_code, 37990, code_type="raw")

    Python sets can be made to ensure the uniqueness of Pattern objects.
    """

    def __init__(self, ir_code, frequency=None, code_type="raw", name=None, brand_name=None, model_id=None, vendor_id=None):
        """
        :param ir_code: IR code; Raw timmings by default. If different type,
            set `code_type` argument.
        :key frequency: Optional for Pronto codes only; Mandatory for the others.
        :key code_type: (Optional) `pronto, pulses, raw`. Default: `raw`.
        :type ir_code: <Iterable <int>> or <str>
        :type frequency: <int>
        :type code_type: <str>
        """
        convert_funcs = {
            "pronto": self.from_pronto,
            "pulses": self.from_pulses,
            "raw": lambda code, freq: (tuple(code), freq),
        }

        if code_type in ("raw", "pulses"):
            assert frequency, "Missing frequency argument for the given code_type!"

        self.brand = brand_name
        self.name = name
        self.model_id = model_id
        self.vendor_id = vendor_id
        self.ir_code, self.frequency = convert_funcs[code_type](ir_code, frequency)

    def to_pronto(self):
        """Pronto IR format

        Contains frequency, size of the 2 burst sequences, and burst pairs.

        :return: Hex padded pulses values
            Ex: `0000 006D 0022 0002 0158 00AA 0016 0015`
        :rtype: <str>
        """

        def to_padded_hex(number):
            """Get 4 digits hex padded representation of the given number"""
            return "{0:0{1}X}".format(number, 4)

        # Convert frequency in Hz to pronto internal clock
        freq_number = round(1000000 / (self.frequency * 0.241246))
        frequency = to_padded_hex(freq_number)

        # Convert raw timmings to pulses and pulses to padded hex strings
        ir_code = [to_padded_hex(i) for i in self.to_pulses()]

        # Bursts should be a multiple of 2: Burst pairs (On/Off)
        if len(ir_code) % 2 != 0:
            print("WARNING: Burst pairs are not complete: odd number")

        # Try to detect number and size of sequences
        size_seq_1 = int(len(ir_code) / 2)
        size_seq_2 = 0
        mean_values = sum(self.ir_code) / len(self.ir_code)
        # End of a sequence contains a long time without signal (much longer than the usual timmings)
        # mean * 5 is an arbitrary threshold
        # Remove the first leading burst that could be quite long
        end_burst_indexes = [
            index for index, value in enumerate(self.ir_code)
            if (value > mean_values * 5) and index != 0
        ]
        # print(end_burst_indexes)
        if len(end_burst_indexes) == 2 and end_burst_indexes[0] != 0:
            # There are 2 sequences max
            size_seq_1 = int((end_burst_indexes[0] + 1) / 2)
            size_seq_2 = int((len(self.ir_code) - (end_burst_indexes[0] + 1)) / 2)

        # Leading 0000
        # Frequency
        # Size of the first sequence
        # Size of econd burst (repeat burst), 0 by def
        # Burst pairs
        # ["0000", frequency, to_padded_hex(size_seq_1), to_padded_hex(size_seq_2)] + ir_code
        return "0000 {} {} {} {}".format(
            frequency,
            to_padded_hex(size_seq_1),
            to_padded_hex(size_seq_2),
            " ".join(ir_code),
        )

    def from_pronto(self, ir_code, *args, **kwargs):
        """Convert Pronto hex values to raw timmings

        .. note:: Since Pronto code embeds the carrier frequency, we do not need
            it as an independent argument.

        :param ir_code: Pronto code
        :type ir_code: <str>
        :return: Timmings and frequency.
        :rtype: <<tuple <tuple <int>>, <int>>
        """
        # Convert hex pulse words (4 symbols) to ints
        from_bytes = partial(int.from_bytes, byteorder="big")
        pronto = [from_bytes(bytes.fromhex(i)) for i in ir_code.split()]

        # Test leading null word
        assert pronto[0] == 0

        # Convert pronto internal clock to Hz
        frequency = 1000000 / (pronto[1] * 0.241246)
        # pronto[3]  # nb pairs in first sequence
        # pronto[4]  # nb pairs in second sequence

        # Convert hex pulses to raw timmings
        ir_code = [round((i * 1000000) / frequency) for i in pronto[4:] if i != 0]
        frequency = round(frequency)
        return tuple(ir_code), frequency

    def from_pulses(self, ir_code, frequency=None):
        """Convert raw timmings into pulses according to the given carrier frequency

        :param ir_code: List of pulse values
        :key frequency: (Optional) If not set, the function will try to use the
            current internal frequency attr. Default: None.
        :type ir_code: <list <int>>
        :type frequency: <int>
        :return: Timmings and frequency (not modified).
        :rtype: <<tuple <tuple <int>>, <int>>
        """
        # Convert int pulses to raw timmings
        ir_code = [round((i * 1000000) / frequency) for i in ir_code]
        frequency = frequency if frequency else self.frequency
        return tuple(ir_code), frequency

    def to_raw(self):
        """Raw timmings, not signed

        :return: IR timmings in us
            Ex: `[9042, 4484, 579, 552, 580, ...]`
        :rtype: <tuple <int>>
        """
        return tuple(self.ir_code)

    def to_signed_raw(self):
        """Raw timmings, positive meaning ON negative meaning OFF

        :return: Signed IR timmings in us
            Ex: `['+9042', '-4484', '+579', '-552', '+580', ...]`
        :rtype: <list <str>>
        """
        return [
            ("-" if index % 2 else "+") + str(value)
            for index, value in enumerate(self.ir_code)
        ]

    def to_pulses(self):
        """Pulses (number of cycles of the carrier for which to turn the light ON and OFF)
        Pulses Width Modulation"""
        return [round((i * self.frequency) / 1000000) for i in self.ir_code]

    def __eq__(self, other: "Pattern"):
        return self.ir_code == other.ir_code and self.frequency == other.frequency

    def __hash__(self):
        return hash(self.ir_code) ^ hash(self.frequency)

    def __repr__(self):
        return "<Pattern frequency: {}; ir_code: {}>".format(
            self.frequency, self.ir_code
        )
