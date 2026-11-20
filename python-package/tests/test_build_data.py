"""build_data: parsing of the ANS files (pandas) and of the IBGE mesh (geopandas, if present)."""
import io
import zipfile

import pandas as pd
import pytest

from medbr import download
from medbr.build_data import build_beneficiaries, summarize_beneficiaries, summarize_plans
from medbr.utils import ensure_data


def test_summarize_beneficiaries_sums_by_uf_and_drops_unknown():
    csv = io.StringIO("ID_CMPT;SG_UF;NR_BENEF_T\n2026-06;SP;10\n2026-06;SP;5\n2026-06;RJ;7\n2026-06;XX;99\n")
    out = summarize_beneficiaries(csv)
    assert out.set_index("uf")["beneficiaries_count"].to_dict() == {"RJ": 7, "SP": 15}


def test_build_beneficiaries_uses_only_latest_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path / "data"))
    z = tmp_path / "b.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("tb_br_2512.csv", "SG_UF;NR_BENEF_T\nSP;100\n")
        zf.writestr("tb_br_2606.csv", "SG_UF;NR_BENEF_T\nSP;7\n")
    path, latest = build_beneficiaries(z)
    assert latest == "tb_br_2606.csv"
    assert pd.read_csv(path, sep=";")["beneficiaries_count"].tolist() == [7]


def test_summarize_plans_counts_across_chunks_and_cleans_operator():
    csv = io.StringIO(
        "ID_PLANO;CD_PLANO;CD_OPERADORA;CD_MUNICIPIO\n"
        '1;"a";"\t5711";"270010"\n2;"b";"5711";"270010"\n3;"c";"5711";"270020"\n4;"d";"9";"270010"\n'
    )
    out = summarize_plans(csv, chunksize=2)
    got = {(r.city_code, r.operator): r.count for r in out.itertuples()}
    assert got == {("270010", 5711): 2, ("270020", 5711): 1, ("270010", 9): 1}


def test_bundle_is_downloaded_only_once(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MEDBR_NO_DOWNLOAD", "0")
    calls = []

    def fake_update(url=None):
        calls.append(1)
        download.bundle_marker().touch()

    monkeypatch.setattr(download, "update_data", fake_update)
    for _ in range(2):
        with pytest.raises(FileNotFoundError):
            ensure_data("beds", "transformed", "beds.csv")
    assert len(calls) == 1


def test_build_cities_from_ibge_like_zip(tmp_path, monkeypatch):
    gpd = pytest.importorskip("geopandas")
    from shapely.geometry import box
    from medbr.build_data import build_cities
    from medbr.utils import get_cities
    import json

    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path / "data"))
    mesh = gpd.GeoDataFrame(
        {"CD_MUN": ["3550308", "3304557"], "NM_MUN": ["A", "B"], "SIGLA_UF": ["SP", "RJ"]},
        geometry=[box(-47, -24, -46, -23), box(-44, -23, -43, -22)], crs="EPSG:4674",
    )
    src = tmp_path / "src"; src.mkdir()
    mesh.to_file(src / "BR_Municipios_2022.shp")
    z = tmp_path / "mesh.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for f in src.iterdir():
            zf.write(f, f.name)
    build_cities(z)
    cities = get_cities()
    assert sorted(cities["city_code"]) == ["330455", "355030"] and set(cities["uf"]) == {"SP", "RJ"}
    states = json.loads((tmp_path / "data" / "cities" / "raw" / "br_states.json").read_text())
    assert sorted(f["id"] for f in states["features"]) == ["RJ", "SP"]
