"""Registry, bundle discovery and the map factories (pandas only)."""
import zipfile

import pandas as pd
import pytest

from medbr import registry
from medbr.build_data import build_all
from medbr.bundle import build_bundle, collect_files
from medbr.factories import city_series, uf_choropleth, uf_series


def test_builtin_datasets_are_registered_in_build_order():
    import medbr.build_data  # noqa: F401

    names = list(registry.REGISTRY)
    assert names[:2] == ["cities", "population"]
    assert {"beds", "beneficiaries", "birth", "mortality", "plancoverage"} <= set(names)


def test_a_new_dataset_is_picked_up_by_build_and_bundle(tmp_path, monkeypatch):
    monkeypatch.setenv("MEDBR_DATA_DIR", str(tmp_path / "data"))
    calls = []

    @registry.dataset("dengue_test", "fake data set")
    def build_fake(tmp, simplify):
        calls.append(simplify)
        out = tmp_path / "data" / "dengue_test" / "transformed"
        out.mkdir(parents=True)
        (out / "dengue_test.csv").write_text("uf;cases\nSP;1\n")

    try:
        out = tmp_path / "b.zip"
        build_all(only=["dengue_test"], bundle=str(out))
        assert calls == [0.005]
        assert "dengue_test/transformed/dengue_test.csv" in zipfile.ZipFile(out).namelist()
        with pytest.raises(ValueError, match="already registered"):
            registry.dataset("dengue_test", "again")(lambda tmp, s: None)
    finally:
        registry.REGISTRY.pop("dengue_test")


def test_build_all_rejects_unknown_dataset():
    with pytest.raises(ValueError, match="Unknown"):
        build_all(only=["nope"])


def test_collect_files_ships_transformed_only(tmp_path):
    for rel in ["a/transformed/a.csv", "a/raw/big.csv", "b/transformed/b.parquet", "cities/raw/br_states.json"]:
        f = tmp_path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("x")
    names = {p.relative_to(tmp_path).as_posix() for p in collect_files(tmp_path)}
    assert names == {"a/transformed/a.csv", "b/transformed/b.parquet", "cities/raw/br_states.json"}


def test_uf_and_city_series():
    df = pd.DataFrame({"uf": ["SP", "RJ"], "cases": [3, 4]})
    assert uf_series(df, "cases").to_dict() == {"SP": 3, "RJ": 4}
    assert uf_series(df, "cases", "RJ").to_dict() == {"RJ": 4}
    with pytest.raises(ValueError, match="rebuild"):
        uf_series(df, "missing")
    c = pd.DataFrame({"city_code": [1, 1, 2], "n": [1, 2, 5]})
    assert city_series(c, "n").to_dict() == {"1": 3, "2": 5}


def test_factory_builds_a_documented_function():
    f = uf_choropleth("dengue", "cases", "Dengue cases", per=100_000)
    assert f.__name__ == "dengue" and "Dengue cases" in f.__doc__
