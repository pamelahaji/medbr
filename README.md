# medbr: Geographic Health Data Sets of Brazil

<img align="right" src="https://github.com/pamgcosta/medbr/assets/66846949/2cbfe684-a173-42dd-8bfc-c579438ceab3" alt="logo" width="320"> 
<p align="justify">medbr is a computational package for visualizing public health data in Brazil in geospatial format. The package includes a geospatial data functions available with variable parameters to obtain a geospatial visualization of the data. </p> 

The package is currently available in Python. It is under development and **not yet published on PyPI**.

## Installation Python

```bash
pip install "git+https://github.com/pamelahaji/medbr.git#subdirectory=python-package"
```

For development:

```bash
git clone https://github.com/pamelahaji/medbr.git
cd medbr/python-package
pip install -e ".[test]"
pytest
```

*Windows users:* installing `geopandas` with conda avoids most build problems:

```bash
conda create -n geo_env
conda activate geo_env
conda config --env --add channels conda-forge
conda config --env --set channel_priority strict
conda install python=3 geopandas folium
pip install "git+https://github.com/pamelahaji/medbr.git#subdirectory=python-package"
```

## Data

The data prepared by the aggregator scripts (about 6 files) are published as a zip in the [releases](https://github.com/pamelahaji/medbr/releases). **You do not need to do anything:** the first time a function needs a file, `medbr` downloads the bundle into `~/.cache/medbr` and reuses it afterwards. Only `facilities` (CNES API) and the population denominators (IBGE API, cached after the first call) use the internet at run time.

Useful environment variables:

| Variable | Effect |
|---|---|
| `MEDBR_DATA_DIR` | use this folder for the data instead of `~/.cache/medbr` |
| `MEDBR_NO_DOWNLOAD=1` | never download; fail with a clear message if a file is missing |
| `MEDBR_BUNDLE_URL` | download the bundle from another address |

### Building the data from the official sources

`python -m medbr.build_data` downloads and prepares, straight from the official sources:

| Data set | Source |
|---|---|
| municipal mesh and states | IBGE municipal mesh 2022 (203 MB, simplified to ~5 MB) |
| population | IBGE SIDRA, Census 2022 |
| beneficiaries, plans | ANS open data (latest quarter; ~1 GB for the plans file) |
| deaths | SIM "Mortalidade Geral" 2021-2022 (OpenDataSUS), non-fetal deaths |
| births | SINASC 2021-2022 (OpenDataSUS) |
| beds | CNES "Leitos 2023" (OpenDataSUS), latest month of the file |
| vaccination | SI-PNI routine immunisation coverage by municipality, 2018 (DATASUS FTP, `CPNI<UF>18.DBF`) |

Use `--only cities population` to choose and `--bundle medbr-data.zip` to also write the zip. The whole build downloads about 2 GB, so it is meant to run on GitHub: the **build-data** Action does it and can publish the result as the `data-v1` release that `medbr` downloads (Actions → build-data → *Run workflow*, check *publish*).

To fetch a newer bundle: `python -m medbr.download`.

# Counts or rates?

By default the maps show **absolute counts**, so populous places look more intense simply because they have more people. Pass `rate=True` to divide by the resident population of the Census 2022 (IBGE, SIDRA table 9514):

| Function | `rate=True` shows |
|---|---|
| `beds` | beds per 1,000 inhabitants (by state) |
| `beneficiaries` | medical-plan beneficiaries per 100 inhabitants (by state, latest quarter) |
| `plancoverage` | plans per 100,000 inhabitants (by city) |
| `birth`, `mortality` | daily births/deaths per 100,000 inhabitants (by city) |

For `birth` and `mortality`, filter by `ufs`/`cities_code` and dates: the whole country over two years is a very large map.

Caveats: births and deaths are counted by the city where they **occurred**, not where the person lives, so cities with large hospitals are over-represented; one census population is used as the denominator for all years.

# Basic Usage

All functions return a [folium](https://python-visualization.github.io/folium/) map. Filters are optional.

```python
import medbr

medbr.facilities(city=355030).save("facilities.html")          # CNES API
medbr.beds(ufs=["SP", "RJ"], rate=True).save("beds.html")   # beds per 1,000 inhabitants
medbr.beneficiaries().save("beneficiaries.html")
medbr.plancoverage(ufs=["SP"], operators=[326305]).save("plans.html")
medbr.birth(start_at="2021-01-01", end_at="2022-01-01").save("birth.html")
medbr.mortality(cities_code=[355030]).save("mortality.html")
```

More examples in [`python-package/examples/run_all.py`](python-package/examples/run_all.py).

# Functions

|Function|Group|Description|Source|
|-----|-----|-----|-----|
|`medbr.facilities(city, facility_type, state, ...)`| Health Infrastructure | Markers for establishments of the National Registry of Health Establishments (CNES), filtered by city, state or type of unit | CNES |
|`medbr.beds(ufs, rate)`| Health Infrastructure | Choropleth of existing hospital beds by state (2023) | Open Data Portal |
|`medbr.vaccination(vaccine, ufs)`| Health Infrastructure | Choropleth of routine vaccination coverage (%) by municipality, 2018 (12 vaccines) | DATASUS (SI-PNI) |
|`medbr.mortality(cities_code, start_at, end_at, rate)`| Population Health | Time heat map of deaths per day by city (2021-2022) | SIM |
|`medbr.birth(cities_code, start_at, end_at, rate)`| Population Health | Time heat map of births per day by city (2021-2022) | SINASC |
|`medbr.plancoverage(ufs, operators, rate)`| Complementary Health | Choropleth of health plans sold by city | ANS |
|`medbr.beneficiaries(ufs, rate, kind)`| Complementary Health | Choropleth of supplementary health beneficiaries by state (latest quarter); `kind`: `medical` (default), `dental`, `all` | ANS |

Under development (not exported yet): sanitation (`sanitation`).

**Vaccination data notes.** `vaccination` uses routine-immunisation coverage (not COVID-19). The year is 2018 on purpose:
in the DATASUS FTP, 2019 covers only about a quarter of the doses (reporting moved to a new system), and later years are not
published there. Coverage is the official figure (doses / target population of each vaccine, by municipality), so it can pass
100% in small towns. COVID-19 vaccination is not included: the Ministry's public API refuses automated access from GitHub
and the open data are monthly microdata files of ~1.4 GB each. Contributions are welcome (see CONTRIBUTING).

# Adding data sets

The package is built to grow: a data set is a registered *builder* (download + prepare), one line to get its map function (`uf_choropleth`, `city_choropleth`, `daily_heatmap`) and a test. `python -m medbr.build_data` and the release bundle pick it up automatically. See the [guide](CONTRIBUTING.md).

# Contributing to medbr
If you would like to contribute to medbr and add new functions or data sets, please check the [guide](CONTRIBUTING.md) to propose your contribution.

# License

[MIT](LICENSE)
