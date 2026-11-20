"""Build the medbr data sets straight from the official sources.

    python -m medbr.build_data                     # all available data sets
    python -m medbr.build_data --only cities population
    python -m medbr.build_data --bundle medbr-data.zip

Sources (downloaded to a temporary folder, only the result is kept):

* cities      IBGE municipal mesh 2022 (~200 MB zip), simplified; also builds the states file
* population  IBGE SIDRA, Census 2022
* beneficiaries  ANS open data, latest quarterly snapshot (``benef_regiao_geog.zip``)
* plancoverage   ANS open data, plans by municipality (``pda_area_comer_plano_ntrp.csv``, ~1 GB)

* mortality   SIM "Mortalidade Geral" 2021-2022 (OpenDataSUS, ~110 MB zip per year); deaths by
              municipality of occurrence and day, fetal deaths excluded
* birth       SINASC 2021-2022 (OpenDataSUS, ~110 MB zip per year); births by municipality of
              occurrence and day
* beds        CNES "Leitos 2023" (OpenDataSUS); existing beds by state in the latest month of the file
"""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import pandas as pd
import requests

from medbr.registry import REGISTRY, dataset
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
S3 = "https://s3.sa-east-1.amazonaws.com/ckan.saude.gov.br"
SIM_URL = S3 + "/SIM/csv/Mortalidade_Geral_{year}_csv.zip"
SINASC_URL = S3 + "/SINASC/csv/SINASC_{year}_csv.zip"
BEDS_URL = S3 + "/Leitos_SUS/Leitos_{year}.csv"
YEARS = (2021, 2022)
BEDS_YEAR = 2023


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


# ---------------------------------------------------------------- SIM, SINASC, CNES beds
def _count_by_day(csv_file, city_col, date_col, count_name, only=None, chunksize=1_000_000):
    """Rows per (municipality, day) of a DATASUS csv (dates are ``ddmmyyyy``).

    ``only=(column, value)`` keeps just the rows where ``column == value``.
    """
    usecols = [city_col, date_col] + ([only[0]] if only else [])
    total = None
    reader = pd.read_csv(csv_file, sep=";", usecols=usecols, dtype=str, encoding="latin-1", chunksize=chunksize)
    for chunk in reader:
        if only:
            chunk = chunk[chunk[only[0]] == only[1]]
        chunk = chunk.assign(**{date_col: pd.to_datetime(chunk[date_col], format="%d%m%Y", errors="coerce")})
        chunk = chunk.dropna(subset=[city_col, date_col])
        part = chunk.groupby([city_col, date_col]).size()
        total = part if total is None else total.add(part, fill_value=0)
    if total is None or len(total) == 0:
        raise ValueError("No records found.")
    df = total.astype("int64").rename(count_name).reset_index()
    df[date_col] = df[date_col].dt.strftime("%Y-%m-%d")
    return df.rename(columns={city_col: "city_code", date_col: count_name.replace("_count", "_date")})


def summarize_deaths(csv_file):
    """SIM csv -> ``city_code``, ``death_date``, ``death_count`` (non-fetal deaths, by occurrence)."""
    return _count_by_day(csv_file, "CODMUNOCOR", "DTOBITO", "death_count", only=("TIPOBITO", "2"))


def summarize_births(csv_file):
    """SINASC csv -> ``city_code``, ``birth_date``, ``birth_count`` (by municipality of occurrence)."""
    return _count_by_day(csv_file, "CODMUNNASC", "DTNASC", "birth_count")


def combine_daily(frames, date_col, count_col):
    """Add up the same (city, day) coming from several yearly files."""
    return pd.concat(frames).groupby(["city_code", date_col], as_index=False)[count_col].sum()


def summarize_beds(csv_file):
    """CNES "Leitos" csv (one row per establishment and month) -> existing beds by UF.

    Only the latest month (``COMP``) is used: summing all months would count the same beds 12 times.
    """
    from medbr.population import UF_CODES

    df = pd.read_csv(csv_file, usecols=["COMP", "UF", "LEITOS_EXISTENTES"], dtype={"COMP": str}, encoding="latin-1")
    latest = df["COMP"].max()
    df = df[(df["COMP"] == latest) & df["UF"].isin(UF_CODES.values())]
    out = df.groupby("UF", as_index=False)["LEITOS_EXISTENTES"].sum()
    return out.rename(columns={"UF": "uf", "LEITOS_EXISTENTES": "beds_count"}), latest


def _from_yearly_zips(url_template, summarize, date_col, count_col, tmp):
    frames = []
    for year in YEARS:
        zip_path = download(url_template.format(year=year), Path(tmp) / f"{count_col}_{year}.zip", timeout=1800)
        with zipfile.ZipFile(zip_path) as zf:
            name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
            with zf.open(name) as f:
                frames.append(summarize(f))
        zip_path.unlink()
    return combine_daily(frames, date_col, count_col)


# ---------------------------------------------------------------- builders (registered)
@dataset("cities", "IBGE municipal mesh 2022 (simplified) and the states file")
def build_cities_dataset(tmp, simplify):
    print("cities: downloading IBGE mesh ...", flush=True)
    print("  ->", build_cities(download(IBGE_MESH_URL, tmp / "mesh.zip"), simplify))


@dataset("population", "Resident population, Census 2022 (IBGE SIDRA)")
def build_population_dataset(tmp, simplify):
    from medbr.population import population

    print("population: IBGE SIDRA ...", flush=True)
    for level in ("uf", "city"):
        path = data_path("population", "transformed", f"population_{level}.csv")
        if path.exists():
            path.unlink()  # refresh
        print(f"  -> {level}: {len(population(level))} rows")


@dataset("beneficiaries", "Supplementary health beneficiaries by state, latest quarter (ANS)")
def build_beneficiaries_dataset(tmp, simplify):
    print("beneficiaries: ANS ...", flush=True)
    path, snapshot = build_beneficiaries(download(ANS_BENEFICIARIES_URL, tmp / "benef.zip"))
    print("  ->", path, f"(snapshot {snapshot})")


@dataset("plancoverage", "Health plans sold by municipality (ANS, ~1 GB download)")
def build_plancoverage_dataset(tmp, simplify):
    print("plancoverage: ANS (large file) ...", flush=True)
    print("  ->", build_plancoverage(download(ANS_PLANS_URL, tmp / "plans.csv", timeout=1800)))


@dataset("mortality", "Non-fetal deaths by municipality and day, 2021-2022 (SIM)")
def build_mortality_dataset(tmp, simplify):
    print("mortality: SIM (large files) ...", flush=True)
    df = _from_yearly_zips(SIM_URL, summarize_deaths, "death_date", "death_count", tmp)
    print("  ->", _write_csv(df, "mortality", "transformed", "mortality.csv"), f"({int(df.death_count.sum())} deaths)")


@dataset("birth", "Births by municipality and day, 2021-2022 (SINASC)")
def build_birth_dataset(tmp, simplify):
    print("birth: SINASC (large files) ...", flush=True)
    df = _from_yearly_zips(SINASC_URL, summarize_births, "birth_date", "birth_count", tmp)
    print("  ->", _write_csv(df, "birth", "transformed", "birth.csv"), f"({int(df.birth_count.sum())} births)")


@dataset("beds", "Existing hospital beds by state, latest month of 2023 (CNES)")
def build_beds_dataset(tmp, simplify):
    print("beds: CNES ...", flush=True)
    df, month = summarize_beds(download(BEDS_URL.format(year=BEDS_YEAR), tmp / "beds.csv"))
    print("  ->", _write_csv(df, "beds", "transformed", "beds.csv"), f"(month {month}, {int(df.beds_count.sum())} beds)")


# ---------------------------------------------------------------- driver
def build_all(only=None, bundle=None, simplify=CITY_SIMPLIFY):
    from medbr.bundle import build_bundle

    wanted = list(only) if only else list(REGISTRY)
    unknown = set(wanted) - set(REGISTRY)
    if unknown:
        raise ValueError(f"Unknown data set(s): {sorted(unknown)}; choose from {list(REGISTRY)}")
    data_dir().mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name in wanted:  # registration order: cities and population come first
            REGISTRY[name][0](Path(tmp), simplify)
    if bundle:
        print("bundle ->", build_bundle(bundle))


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="data sets: " + "; ".join(f"{k} ({v[1]})" for k, v in REGISTRY.items()),
    )
    parser.add_argument("--only", nargs="+", choices=list(REGISTRY))
    parser.add_argument("--bundle", help="also write the zip that medbr downloads (e.g. medbr-data.zip)")
    parser.add_argument("--simplify", type=float, default=CITY_SIMPLIFY)
    args = parser.parse_args()
    build_all(args.only, args.bundle, args.simplify)


if __name__ == "__main__":
    main()
