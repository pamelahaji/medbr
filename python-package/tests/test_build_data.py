"""build_data: parsing of the ANS files (pandas) and of the IBGE mesh (geopandas, if present)."""
import io
import zipfile

import pandas as pd
import pytest

from medbr import download
from medbr.build_data import build_beneficiaries, summarize_beneficiaries, summarize_plans
from medbr.utils import ensure_data


def test_summarize_beneficiaries_sums_by_uf_and_drops_unknown():
    csv = io.StringIO(
        "SG_UF;NR_BENEF_T;NR_BENEF_M;NR_BENEF_O\n"
        "SP;10;6;4\nSP;5;5;0\nRJ;7;7;0\nXX;99;99;0\n"
    )
    out = summarize_beneficiaries(csv).set_index("uf")
    assert out["beneficiaries_count"].to_dict() == {"RJ": 7, "SP": 15}
    assert out["medical_count"].to_dict() == {"RJ": 7, "SP": 11}
    assert out["dental_count"].to_dict() == {"RJ": 0, "SP": 4}


def test_build_beneficiaries_uses_only_latest_snapshot(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path / "data"))
    z = tmp_path / "b.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("tb_br_2512.csv", "SG_UF;NR_BENEF_T;NR_BENEF_M;NR_BENEF_O\nSP;100;100;0\n")
        zf.writestr("tb_br_2606.csv", "SG_UF;NR_BENEF_T;NR_BENEF_M;NR_BENEF_O\nSP;7;7;0\n")
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


def test_summarize_deaths_excludes_fetal_and_converts_dates():
    from medbr.build_data import summarize_deaths

    csv = io.StringIO(
        "TIPOBITO;DTOBITO;CODMUNOCOR\n"
        "2;05012021;355030\n2;05012021;355030\n1;05012021;355030\n2;06012021;330455\n2;;330455\n2;07012021;\n"
    )
    out = summarize_deaths(csv)
    got = {(r.city_code, r.death_date): r.death_count for r in out.itertuples()}
    assert got == {("355030", "2021-01-05"): 2, ("330455", "2021-01-06"): 1}


def test_summarize_births_counts_rows_across_chunks():
    from medbr.build_data import summarize_births

    csv = io.StringIO("CODMUNNASC;DTNASC;HORANASC\n355030;01022021;1200\n355030;01022021;\n355030;02022021;0100\n")
    out = summarize_births(csv)
    got = {(r.city_code, r.birth_date): r.birth_count for r in out.itertuples()}
    assert got == {("355030", "2021-02-01"): 2, ("355030", "2021-02-02"): 1}  # empty HORANASC still counts


def test_combine_daily_adds_same_day_from_two_files():
    from medbr.build_data import combine_daily

    a = pd.DataFrame({"city_code": ["1"], "death_date": ["2021-12-31"], "death_count": [2]})
    b = pd.DataFrame({"city_code": ["1", "1"], "death_date": ["2021-12-31", "2022-01-01"], "death_count": [3, 1]})
    out = combine_daily([a, b], "death_date", "death_count").set_index("death_date")["death_count"]
    assert out.to_dict() == {"2021-12-31": 5, "2022-01-01": 1}


def test_summarize_beds_uses_latest_month_only():
    from medbr.build_data import summarize_beds

    csv = io.StringIO(
        "COMP,UF,LEITOS_EXISTENTES\n"
        "202301,SP,100\n202301,RJ,50\n202312,SP,110\n202312,SP,10\n202312,RJ,55\n202312,XX,9\n"
    )
    out, month = summarize_beds(csv)
    assert month == "202312"
    assert out.set_index("uf")["beds_count"].to_dict() == {"RJ": 55, "SP": 120}
