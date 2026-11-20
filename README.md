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

### Rebuilding the data from the raw files (maintainers)

1. Download the raw files into `medbr/data/<dataset>/raw/` (file names are in each `*_aggregator.py`; the municipal mesh is IBGE's `BR_Municipios_2022.shp`; the states file is `medbr/data/cities/raw/br_states.json`).
2. Run the scripts, e.g. `python medbr/data/cities/cities.py` (paths do not depend on the current directory).
3. Build and publish the bundle:

```bash
python -m medbr.bundle --simplify 0.005 --out medbr-data.zip   # --simplify shrinks the municipal mesh
gh release create data-v1 medbr-data.zip --title "medbr data v1"
```

# Counts or rates?

By default the maps show **absolute counts**, so populous places look more intense simply because they have more people. Pass `rate=True` to divide by the resident population of the Census 2022 (IBGE, SIDRA table 9514):

| Function | `rate=True` shows |
|---|---|
| `beds` | beds per 1,000 inhabitants (by state) |
| `beneficiaries` | beneficiaries per 100 inhabitants (by state, latest quarter) |
| `plancoverage` | plans per 100,000 inhabitants (by city) |
| `birth`, `mortality` | daily births/deaths per 100,000 inhabitants (by city) |

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
|`medbr.mortality(cities_code, start_at, end_at, rate)`| Population Health | Time heat map of deaths per day by city (2021-2022) | SIM |
|`medbr.birth(cities_code, start_at, end_at, rate)`| Population Health | Time heat map of births per day by city (2021-2022) | SINASC |
|`medbr.plancoverage(ufs, operators, rate)`| Complementary Health | Choropleth of health plans sold by city | ANS |
|`medbr.beneficiaries(ufs, rate)`| Complementary Health | Choropleth of supplementary health beneficiaries by state | ANS |

Under development (not exported yet): COVID-19 vaccination (`covid_vaccine`) and sanitation (`sanitation`).

# Contributing to medbr
If you would like to contribute to medbr and add new functions or data sets, please check the [guide](CONTRIBUTING.md) to propose your contribution.

# License

[MIT](LICENSE)
