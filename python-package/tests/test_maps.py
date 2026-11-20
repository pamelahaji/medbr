"""End-to-end map tests on tiny synthetic data (need folium + geopandas)."""
import json

import pandas as pd
import pytest

pytest.importorskip("folium")
gpd = pytest.importorskip("geopandas")
from shapely.geometry import box, mapping  # noqa: E402

import medbr  # noqa: E402


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    cities = gpd.GeoDataFrame(
        {"city_code": [111111, 222222], "city_name": ["A", "B"], "uf": ["SP", "RJ"]},
        geometry=[box(-47, -24, -46, -23), box(-44, -23, -43, -22)], crs="EPSG:4326",
    )
    (tmp_path / "cities" / "transformed").mkdir(parents=True)
    (tmp_path / "cities" / "raw").mkdir(parents=True)
    cities.to_file(tmp_path / "cities" / "transformed" / "cities.shp")
    states = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "id": "SP", "properties": {}, "geometry": mapping(box(-47, -24, -46, -23))},
        {"type": "Feature", "id": "RJ", "properties": {}, "geometry": mapping(box(-44, -23, -43, -22))},
    ]}
    (tmp_path / "cities" / "raw" / "br_states.json").write_text(json.dumps(states))

    def put(name, df):
        (tmp_path / name / "transformed").mkdir(parents=True)
        df.to_csv(tmp_path / name / "transformed" / f"{name}.csv", sep=";", index=False)

    put("beds", pd.DataFrame({"uf": ["SP", "RJ"], "beds_count": [10, 5]}))
    put("beneficiaries", pd.DataFrame({"uf": ["SP", "RJ"], "beneficiaries_count": [100, 50]}))
    put("plancoverage", pd.DataFrame({"city_code": [111111, 222222], "operator": [1, 2], "count": [4, 6]}))
    pop_dir = tmp_path / "population" / "transformed"
    pop_dir.mkdir(parents=True)
    pd.DataFrame({"code": ["SP", "RJ"], "population": [1000, 500]}).to_csv(pop_dir / "population_uf.csv", sep=";", index=False)
    pd.DataFrame({"code": ["111111", "222222"], "population": [1000, 2000]}).to_csv(pop_dir / "population_city.csv", sep=";", index=False)
    put("birth", pd.DataFrame({"city_code": [111111, 222222, 111111],
                               "birth_date": ["2021-01-01", "2021-01-01", "2021-01-02"],
                               "birth_count": [3, 4, 5]}))
    put("mortality", pd.DataFrame({"city_code": [111111], "death_date": ["2021-01-01"], "death_count": [2]}))


@pytest.mark.parametrize("call", [
    lambda: medbr.beds(),
    lambda: medbr.beds(ufs=["SP"]),
    lambda: medbr.beds(rate=True),
    lambda: medbr.beneficiaries(rate=True),
    lambda: medbr.plancoverage(rate=True),
    lambda: medbr.birth(rate=True),
    lambda: medbr.mortality(rate=True),
    lambda: medbr.beneficiaries(),
    lambda: medbr.plancoverage(),
    lambda: medbr.plancoverage(ufs=["SP"], operators=[1]),
    lambda: medbr.birth(),
    lambda: medbr.birth(cities_code=[111111], start_at="2021-01-01", end_at="2021-12-31"),
    lambda: medbr.mortality(start_at="2021-01-01", end_at="2022-01-01"),
])
def test_maps_render(data_dir, call):
    m = call()
    assert "<html" in m.get_root().render().lower()


def test_birth_without_data_in_range_raises(data_dir):
    with pytest.raises(ValueError):
        medbr.birth(start_at="2030-01-01")
