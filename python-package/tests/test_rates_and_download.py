"""Population/rates, bundle download and bundle building (pandas only)."""
import io
import zipfile

import pandas as pd
import pytest

from medbr import download, population as pop_mod
from medbr.bundle import build_bundle, collect_files
from medbr.population import add_rate, parse_sidra, to_rate
from medbr.utils import data_dir, ensure_data

HEADER = {"NC": "Nível Territorial (Código)", "V": "Valor", "D1C": "Unidade da Federação (Código)"}


def test_parse_sidra_uf_and_city():
    uf = parse_sidra([HEADER, {"D1C": "35", "V": "44420459"}, {"D1C": "33", "V": "16055174"}], "uf")
    assert uf.to_dict() == {"SP": 44420459, "RJ": 16055174}
    city = parse_sidra([HEADER, {"D1C": "3550308", "V": "11451999"}, {"D1C": "1100015", "V": "21494"}], "city")
    assert city["355030"] == 11451999 and city["110001"] == 21494


def test_parse_sidra_skips_missing_values_and_empty_raises():
    s = parse_sidra([HEADER, {"D1C": "35", "V": "-"}, {"D1C": "33", "V": "10"}], "uf")
    assert s.to_dict() == {"RJ": 10}
    with pytest.raises(ValueError):
        parse_sidra([HEADER], "uf")


def test_to_rate():
    counts = pd.Series({"SP": 50, "RJ": 10, "XX": 5})
    pop = pd.Series({"SP": 100, "RJ": 200})
    assert to_rate(counts, pop, 1000).to_dict() == {"SP": 500.0, "RJ": 50.0}  # XX has no population
    with pytest.raises(ValueError):
        to_rate(pd.Series({"XX": 1}), pop, 1000)


def test_add_rate_by_city():
    df = pd.DataFrame({"city_code": [1, 2, 3], "n": [10, 20, 30]})
    out = add_rate(df, pd.Series({"1": 1000, "2": 4000}), "n", 100_000)
    assert out["n"].tolist() == [1000.0, 500.0]  # city 3 dropped (unknown population)


def test_population_fetches_once_then_uses_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    calls = []

    class Resp:
        def raise_for_status(self): pass
        def json(self): return [HEADER, {"D1C": "35", "V": "100"}]

    monkeypatch.setattr(pop_mod.requests, "get", lambda url, **kw: calls.append(url) or Resp())
    assert pop_mod.population("uf")["SP"] == 100
    assert pop_mod.population("uf")["SP"] == 100  # second call reads the cache
    assert len(calls) == 1 and "/n3/" in calls[0]
    with pytest.raises(ValueError):
        pop_mod.population("region")


def _zip_bytes(files):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


def test_ensure_data_downloads_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MEDBR_NO_DOWNLOAD", "0")
    payload = _zip_bytes({"beds/transformed/beds.csv": "uf;beds_count\nSP;1\n"})

    class Resp:
        raw = io.BytesIO(payload)
        def raise_for_status(self): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass

    monkeypatch.setattr(download.requests, "get", lambda url, **kw: Resp())
    path = ensure_data("beds", "transformed", "beds.csv")
    assert path.read_text().startswith("uf;beds_count")


def test_ensure_data_reports_download_failure(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MEDBR_NO_DOWNLOAD", "0")

    def boom(url, **kw):
        raise download.requests.ConnectionError("offline")

    monkeypatch.setattr(download.requests, "get", boom)
    with pytest.raises(FileNotFoundError, match="download failed"):
        ensure_data("beds", "transformed", "beds.csv")


def test_ensure_data_download_disabled_message(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="MEDBR_NO_DOWNLOAD"):
        ensure_data("beds", "transformed", "beds.csv")


def test_safe_extract_blocks_path_traversal(tmp_path):
    z = tmp_path / "evil.zip"
    z.write_bytes(_zip_bytes({"../evil.txt": "x"}))
    with pytest.raises(ValueError, match="Unsafe"):
        download.safe_extract(z, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_data_dir_falls_back_to_user_cache(monkeypatch, tmp_path):
    monkeypatch.delenv("MEDBR_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path))
    assert data_dir() == tmp_path / "medbr"


def test_build_bundle_roundtrip(tmp_path):
    root = tmp_path / "data"
    for rel in ["beds/transformed/beds.csv", "population/transformed/population_uf.csv", "cities/raw/br_states.json"]:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    (root / "beds" / "raw").mkdir()
    (root / "beds" / "raw" / "huge.csv").write_text("not shipped")
    out = build_bundle(tmp_path / "b.zip", root=root)
    names = set(zipfile.ZipFile(out).namelist())
    assert names == {"beds/transformed/beds.csv", "population/transformed/population_uf.csv", "cities/raw/br_states.json"}
    assert len(collect_files(root)) == 3
    with pytest.raises(FileNotFoundError):
        build_bundle(tmp_path / "c.zip", root=tmp_path / "empty")
