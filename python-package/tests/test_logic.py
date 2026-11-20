"""Tests that need only pandas (no folium/geopandas)."""
import pandas as pd
import pytest

from medbr.utils import (as_code_list, as_list, filter_dates, group_by_date,
                         read_data, uri_creator, remove_nil)
from medbr.plancoverage import plancoverage_data
from medbr.beds import beds_data
from medbr.beneficiaries import beneficiaries_data


def test_as_list_and_codes():
    assert as_list(None) is None
    assert as_list("SP") == ["SP"]
    assert as_list(["SP", "RJ"]) == ["SP", "RJ"]
    assert as_code_list(355030) == ["355030"]
    assert as_code_list([1, "2"]) == ["1", "2"]


def test_remove_nil_and_uri():
    assert remove_nil({"a": 1, "b": None}) == {"a": 1}
    assert uri_creator("http://x", {"a": 1, "b": 2}) == "http://x?a=1&b=2"


def test_filter_dates_bounds_are_optional():
    df = pd.DataFrame({"d": ["2021-01-01", "2021-06-01", "2022-01-01"]})
    assert len(filter_dates(df, "d")) == 3
    assert len(filter_dates(df, "d", start_at="2021-02-01")) == 2
    assert len(filter_dates(df, "d", end_at="2021-06-01")) == 2
    assert len(filter_dates(df, "d", "2021-01-01", "2021-12-31")) == 2


def test_filter_dates_empty_raises():
    df = pd.DataFrame({"d": ["2021-01-01"]})
    with pytest.raises(ValueError):
        filter_dates(df, "d", start_at="2030-01-01")


def test_group_by_date_orders_and_skips_unknown_cities():
    df = pd.DataFrame({
        "city_code": [1, 2, 1, 9],
        "date": ["2021-01-02", "2021-01-01", "2021-01-01", "2021-01-01"],
        "n": [5, 3, 4, 7],
    })
    points = {"1": (-23.0, -46.0), "2": (-22.0, -45.0)}
    index, frames = group_by_date(df, "date", "n", points)
    assert index == ["2021-01-01", "2021-01-02"]
    assert frames[0] == [[-22.0, -45.0, 3], [-23.0, -46.0, 4]]  # city 9 has no geometry
    assert frames[1] == [[-23.0, -46.0, 5]]


def test_plancoverage_filters_by_operator():
    df = pd.DataFrame({
        "city_code": [1, 1, 2], "operator": [10, 20, 10], "count": [5, 7, 3],
    })
    assert plancoverage_data(df).to_dict() == {"1": 12, "2": 3}
    assert plancoverage_data(df, operators=10).to_dict() == {"1": 5, "2": 3}
    with pytest.raises(ValueError):
        plancoverage_data(df, operators=[99])


def test_beds_and_beneficiaries_filter_by_uf():
    beds = pd.DataFrame({"uf": ["SP", "RJ"], "beds_count": [10, 5]})
    assert beds_data(beds).to_dict() == {"SP": 10, "RJ": 5}
    assert beds_data(beds, ufs="SP").to_dict() == {"SP": 10}
    ben = pd.DataFrame({"uf": ["SP", "RJ"], "beneficiaries_count": [100, 50]})
    assert beneficiaries_data(ben, ufs=["RJ"]).to_dict() == {"RJ": 50}
    with pytest.raises(ValueError):
        beds_data(beds, ufs=["XX"])


def test_read_data_missing_file_has_clear_message(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="Preparing the data"):
        read_data("beds", "transformed", "beds.csv")


def test_read_data_uses_env_dir(tmp_path, monkeypatch):
    (tmp_path / "beds" / "transformed").mkdir(parents=True)
    (tmp_path / "beds" / "transformed" / "beds.csv").write_text("uf;beds_count\nSP;10\n")
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path))
    assert read_data("beds", "transformed", "beds.csv")["beds_count"].iloc[0] == 10
