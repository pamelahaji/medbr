"""DBF reader and SI-PNI coverage parsing (pandas only)."""
import io
import struct

import pandas as pd
import pytest

from medbr.build_data import VACCINES, fetch_ftp, summarize_coverage
from medbr.dbf import read_dbf


def make_dbf(fields, rows):
    """Tiny dBase III writer for the tests: all fields are text."""
    header_len = 32 + 32 * len(fields) + 1
    record_len = 1 + sum(length for _, length in fields)
    out = bytearray(b"\x03\x77\x05\x14") + struct.pack("<IHH", len(rows), header_len, record_len) + bytes(20)
    for name, length in fields:
        out += name.encode().ljust(11, b"\0") + b"C" + bytes(4) + bytes([length]) + bytes(15)
    out += b"\x0d"
    for row in rows:
        out += b" " + b"".join(str(v).encode("latin-1").ljust(length) for v, (_, length) in zip(row, fields))
    return bytes(out)


FIELDS = [("ANO", 4), ("UF", 2), ("MUNIC", 6), ("IMUNO", 3), ("QT_DOSE", 8), ("POP", 8), ("COBERT", 8)]


def test_read_dbf_roundtrip_and_deleted_rows():
    data = make_dbf(FIELDS, [("2018", "35", "354990", "072", "950", "1000", "95"),
                             ("2018", "35", "354990", "080", "5", "1000", ",50")])
    df = read_dbf(data)
    assert list(df.columns) == [n for n, _ in FIELDS]
    assert df.loc[1, "COBERT"] == ",50" and df.loc[0, "MUNIC"] == "354990"
    deleted = bytearray(data)
    first_record = int.from_bytes(data[8:10], "little")
    deleted[first_record] = ord("*")
    assert len(read_dbf(bytes(deleted))) == 1


def test_summarize_coverage_parses_comma_decimals_and_filters_vaccines():
    df = read_dbf(make_dbf(FIELDS, [
        ("2018", "35", "354990", "072", "950", "1000", "95"),
        ("2018", "35", "354990", "080", "5", "1000", ",50"),
        ("2018", "35", "354990", "012", "1100", "1000", "110,5"),
        ("2018", "35", "354990", "999", "1", "1000", "0,1"),   # not in VACCINES
        ("2018", "35", "354991", "074", "800", "1000", ""),    # missing coverage
    ]))
    out = summarize_coverage(df).set_index(["city_code", "vaccine"])
    assert set(out.index.get_level_values("vaccine")) == {"bcg", "penta", "pneumococcal", "polio"}
    assert out.loc[("354990", "bcg"), "coverage"] == 95.0
    assert out.loc[("354990", "penta"), "coverage"] == 0.5
    assert out.loc[("354990", "pneumococcal"), "coverage"] == 110.5
    assert pd.isna(out.loc[("354991", "polio"), "coverage"])


def test_vaccine_keys_are_unique():
    keys = [k for k, _ in VACCINES.values()]
    assert len(keys) == len(set(keys))


def test_fetch_ftp_tries_the_next_name(monkeypatch):
    import ftplib

    class Fake:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def login(self): pass
        def cwd(self, d): pass
        def retrbinary(self, cmd, cb):
            if cmd.endswith(".DBF"):
                raise ftplib.error_perm("550 no such file")
            cb(b"abc")

    monkeypatch.setattr(ftplib, "FTP", Fake)
    assert fetch_ftp("h", "/d", ["X.DBF", "X.dbf"]) == b"abc"
    with pytest.raises(FileNotFoundError):
        fetch_ftp("h", "/d", ["X.DBF"])


def test_build_data_runs_as_a_module():
    """Regression: importing medbr must not import build_data, or `python -m` registers twice."""
    import subprocess
    import sys

    out = subprocess.run([sys.executable, "-m", "medbr.build_data", "--help"], capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    assert "vaccination" in out.stdout
