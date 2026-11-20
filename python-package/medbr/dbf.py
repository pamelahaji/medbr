"""Minimal dBase (.dbf) reader: DATASUS files are plain dBase III with text fields."""
import struct

import pandas as pd


def read_dbf(data, encoding="latin-1"):
    """Parse the bytes of a .dbf file into a DataFrame of stripped strings."""
    n_records, header_len, record_len = struct.unpack("<IHH", data[4:12])
    fields, pos = [], 32
    while data[pos] != 0x0D:
        name = data[pos:pos + 11].split(b"\0")[0].decode("ascii")
        fields.append((name, data[pos + 16]))
        pos += 32
    rows = []
    for i in range(n_records):
        record = data[header_len + i * record_len: header_len + (i + 1) * record_len]
        if record[:1] == b"*":  # deleted record
            continue
        offset, row = 1, []
        for _, length in fields:
            row.append(record[offset:offset + length].decode(encoding).strip())
            offset += length
        rows.append(row)
    return pd.DataFrame(rows, columns=[name for name, _ in fields])
