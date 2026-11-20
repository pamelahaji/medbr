"""Resident population (IBGE Census 2022, SIDRA table 9514) used to compute rates."""
import pandas as pd
import requests

from medbr.utils import data_path, REQUEST_TIMEOUT

SIDRA_URL = (
    "https://apisidra.ibge.gov.br/values/t/9514/{level}/all/v/93/p/2022"
    "/c2/6794/c287/100362/c286/113635?formato=json"
)
_LEVELS = {"uf": "n3", "city": "n6"}

UF_CODES = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL", 28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}


def parse_sidra(records, level):
    """Turn the SIDRA JSON (first item is a header) into a population Series.

    Index: UF abbreviation (``level='uf'``) or 6-digit city code as ``str``
    (``level='city'``; IBGE's 7th digit is a check digit, dropped like in the
    municipal mesh).
    """
    values = {}
    for row in records[1:]:
        code, value = row["D1C"], row["V"]
        if value in ("-", "...", "X", ""):
            continue
        key = UF_CODES[int(code)] if level == "uf" else str(code)[:6]
        values[key] = int(value)
    if not values:
        raise ValueError("No population data found.")
    return pd.Series(values, name="population")


def population(level="uf"):
    """Population by state (``'uf'``) or municipality (``'city'``), Census 2022.

    The result is cached in the data folder, so the IBGE API is called once.
    """
    if level not in _LEVELS:
        raise ValueError("level must be 'uf' or 'city'")
    path = data_path("population", "transformed", f"population_{level}.csv")
    if path.exists():
        df = pd.read_csv(path, sep=";", dtype={"code": str})
        return df.set_index("code")["population"]

    response = requests.get(SIDRA_URL.format(level=_LEVELS[level]), timeout=REQUEST_TIMEOUT * 4)
    response.raise_for_status()
    series = parse_sidra(response.json(), level)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        series.rename_axis("code").reset_index().to_csv(path, sep=";", index=False)
    except OSError:
        pass  # read-only data folder: just skip the cache
    return series


def to_rate(counts, pop, per):
    """``counts / population * per`` for the keys present in both (``per``: e.g. 1000)."""
    pop = pop.reindex(counts.index)
    ok = pop.notna() & (pop > 0)
    if not ok.any():
        raise ValueError("No population found for these places.")
    return counts[ok] / pop[ok] * per


def add_rate(data, pop, count_col, per):
    """Replace ``count_col`` by the rate per ``per`` inhabitants (rows by ``city_code``)."""
    data = data.copy()
    data["city_code"] = data["city_code"].astype(str)
    p = data["city_code"].map(pop)
    keep = p.notna() & (p > 0)
    if not keep.any():
        raise ValueError("No population found for these places.")
    data = data[keep]
    data[count_col] = data[count_col] / p[keep] * per
    return data
