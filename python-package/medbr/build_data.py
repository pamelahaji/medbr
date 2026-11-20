"""Build the medbr data sets straight from the official sources.

    python -m medbr.build_data                     # all available data sets
    python -m medbr.build_data --only cities population
    python -m medbr.build_data --bundle medbr-data.zip

Sources (downloaded to a temporary folder, only the result is kept):

* cities      IBGE municipal mesh 2022 (~200 MB zip), simplified; also builds the states file
* population  IBGE SIDRA, Census 2022
* beneficiaries  ANS open data, latest quarterly snapshot (``benef_regiao_geog.zip``)
* plancoverage   ANS open data, plans by municipality (``pda_area_comer_plano_ntrp.csv``, ~1 GB)

Not automated yet (no verified direct link): births (SINASC), deaths (SIM) and hospital beds;
use their ``*_aggregator.py`` scripts.
"""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import requests

from medbr.utils import data_dir, data_path

IBGE_MESH_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/"
    "malhas_municipais/municipio_2022/Brasil/BR/BR_Municipios_2022.zip"
)
ANS_PDA = "https://dadosabertos.ans.gov.br/FTP/PDA"
ANS_BENEFICIARIES_URL = f"{ANS_PDA}/dados_de_beneficiarios_por_regiao_geografica/benef_regiao_geog.zip"
ANS_PLANS_URL = f"{ANS_PDA}/area_comercializacao_planos_ntrp/pda_area_comer_plano_ntrp.csv"

CITY_SIMPLIFY = 0.005   # degrees (~500 m): keeps the maps light
STATE_SIMPLIFY = 0.01
DATASETS = ["cities", "population", "beneficiaries", "plancoverage"]


def download(url, dest, timeout=600):
    """Stream ``url`` to the file ``dest``."""
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()
        with open(dest, "wb") as f:
            shutil.copyfileobj(response.raw, f, length=1024 * 1024)
    return Path(dest)


def _write_csv(df, *parts):
    path = data_path(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, sep=";", index=False)
    return path


# ---------------------------------------------------------------- cities + states
def build_cities(mesh_zip, simplify=CITY_SIMPLIFY, state_simplify=STATE_SIMPLIFY):
    """IBGE mesh zip -> ``cities.shp`` (``city_code``, ``city_name``, ``uf``) and ``br_states.json``."""
    import geopandas as gpd

    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(mesh_zip) as zf:
            shp = next(n for n in zf.namelist() if n.lower().endswith(".shp"))
            zf.extractall(tmp)
        gdf = gpd.read_file(Path(tmp) / shp)

    gdf["city_code"] = gdf["CD_MUN"].str[:-1].astype("int64")  # drop the check digit
    gdf = gdf.rename(columns={"NM_MUN": "city_name", "SIGLA_UF": "uf"})
    gdf = gdf[["city_code", "city_name", "uf", "geometry"]]

    states = gdf[["uf", "geometry"]].dissolve(by="uf")
    states["geometry"] = states.geometry.simplify(state_simplify, preserve_topology=True)
    states_path = data_path("cities", "raw", "br_states.json")
    states_path.parent.mkdir(parents=True, exist_ok=True)
    states_path.write_text(states.to_json(), encoding="utf-8")  # feature id = UF

    gdf["geometry"] = gdf.geometry.simplify(simplify, preserve_topology=True)
    cities_path = data_path("cities", "transformed", "cities.shp")
    cities_path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(cities_path, driver="ESRI Shapefile")
    return cities_path


# ---------------------------------------------------------------- ANS
def summarize_beneficiaries(csv_file):
    """ANS ``tb_br_*.csv`` -> beneficiaries by UF: all, medical and dental plans."""
    from medbr.population import UF_CODES

    df = pd.read_csv(csv_file, sep=";", usecols=["SG_UF", "NR_BENEF_T", "NR_BENEF_M", "NR_BENEF_O"])
    df = df[df["SG_UF"].isin(UF_CODES.values())]
    df = df.groupby("SG_UF", as_index=False)[["NR_BENEF_T", "NR_BENEF_M", "NR_BENEF_O"]].sum()
    # T = M + O: a person with a medical and a dental plan is counted in both
    return df.rename(columns={
        "SG_UF": "uf", "NR_BENEF_T": "beneficiaries_count",
        "NR_BENEF_M": "medical_count", "NR_BENEF_O": "dental_count",
    })


def build_beneficiaries(zip_path):
    """Use only the latest quarterly snapshot: summing snapshots counts people more than once."""
    with zipfile.ZipFile(zip_path) as zf:
        latest = sorted(n for n in zf.namelist() if Path(n).name.startswith("tb_br_"))[-1]
        with zf.open(latest) as f:
            df = summarize_beneficiaries(f)
    return _write_csv(df, "beneficiaries", "transformed", "beneficiaries.csv"), latest


def summarize_plans(csv_file, chunksize=2_000_000):
    """ANS plan-by-municipality file -> rows per (``city_code``, ``operator``) as ``count``."""
    total = None
    reader = pd.read_csv(
        csv_file, sep=";", usecols=["ID_PLANO", "CD_OPERADORA", "CD_MUNICIPIO"],
        dtype=str, encoding="latin-1", chunksize=chunksize,
    )
    for chunk in reader:
        chunk["CD_OPERADORA"] = chunk["CD_OPERADORA"].str.strip()  # some codes carry a tab
        part = chunk.groupby(["CD_MUNICIPIO", "CD_OPERADORA"])["ID_PLANO"].count()
        total = part if total is None else total.add(part, fill_value=0)
    if total is None:
        raise ValueError("Empty plans file.")
    df = total.astype("int64").rename("count").reset_index()
    df = df.rename(columns={"CD_MUNICIPIO": "city_code", "CD_OPERADORA": "operator"})
    df["operator"] = pd.to_numeric(df["operator"], errors="coerce")
    return df.dropna(subset=["operator"]).astype({"operator": "int64"})


def build_plancoverage(csv_path):
    return _write_csv(summarize_plans(csv_path), "plancoverage", "transformed", "plancoverage.csv")


# ---------------------------------------------------------------- driver
def build_all(only=None, bundle=None, simplify=CITY_SIMPLIFY):
    from medbr.population import population
    from medbr.bundle import build_bundle

    wanted = only or DATASETS
    unknown = set(wanted) - set(DATASETS)
    if unknown:
        raise ValueError(f"Unknown data set(s): {sorted(unknown)}; choose from {DATASETS}")
    data_dir().mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        if "cities" in wanted:
            print("cities: downloading IBGE mesh ...", flush=True)
            print("  ->", build_cities(download(IBGE_MESH_URL, tmp / "mesh.zip"), simplify))
        if "population" in wanted:
            print("population: IBGE SIDRA ...", flush=True)
            for level in ("uf", "city"):
                path = data_path("population", "transformed", f"population_{level}.csv")
                if path.exists():
                    path.unlink()  # refresh
                print(f"  -> {level}: {len(population(level))} rows")
        if "beneficiaries" in wanted:
            print("beneficiaries: ANS ...", flush=True)
            path, snapshot = build_beneficiaries(download(ANS_BENEFICIARIES_URL, tmp / "benef.zip"))
            print("  ->", path, f"(snapshot {snapshot})")
        if "plancoverage" in wanted:
            print("plancoverage: ANS (large file) ...", flush=True)
            print("  ->", build_plancoverage(download(ANS_PLANS_URL, tmp / "plans.csv", timeout=1800)))
    if bundle:
        print("bundle ->", build_bundle(bundle))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", choices=DATASETS)
    parser.add_argument("--bundle", help="also write the zip that medbr downloads (e.g. medbr-data.zip)")
    parser.add_argument("--simplify", type=float, default=CITY_SIMPLIFY)
    args = parser.parse_args()
    build_all(args.only, args.bundle, args.simplify)


if __name__ == "__main__":
    main()
