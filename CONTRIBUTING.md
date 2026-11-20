# Become a contributor to **medbr**

If you would like to contribute to **medbr**, the first thing to do is to open a [Github issue](https://github.com/pamelahaji/medbr/issues) with your suggestion of ***function*** or ***dataset*** you would like to see in the package. Keep in mind that, as a rule, the package only includes geospatial data sets with national spatial coverage that are created/managed by governmental institutions and which are publicly available.

Adding a data set takes three small pieces, all in `python-package/medbr/`. As a running example, a state-level data set called `dengue` with one row per state:

### Step 1. Builder: get the data from the official source

Write a function that downloads the file into `tmp`, keeps only what the map needs and writes `data/<name>/transformed/<name>.csv` (`;` separated, English lower-case column names). Register it with `@dataset(name, description)` in `build_data.py` (or in a module imported there):

```python
from medbr.registry import dataset

@dataset("dengue", "Dengue cases by state, 2024 (Ministry of Health)")
def build_dengue(tmp, simplify):
    path = download("https://.../dengue_2024.csv", tmp / "dengue.csv")   # helper in build_data.py
    df = summarize_dengue(path)            # -> columns: uf, cases
    _write_csv(df, "dengue", "transformed", "dengue.csv")
```

Keep the parsing in a small function that takes a file object (`summarize_dengue`) so it can be tested with a few lines of text. Rules of the road: use the official **direct link**, say in the docstring which period/snapshot is used, never sum snapshots of the same population, and check totals against an official number.

Expected columns by kind of map:

| Map | Columns |
|---|---|
| by state | `uf` (abbreviation) + a count column |
| by municipality | `city_code` (6 digits) + a count column |
| daily heat map | `city_code`, a date (`YYYY-MM-DD`), a count column |

### Step 2. Map function: one line

```python
# medbr/dengue.py
from medbr.factories import uf_choropleth

dengue = uf_choropleth("dengue", "cases", "Dengue cases", per=100_000)
```

Use `city_choropleth` for municipalities and `daily_heatmap` for time heat maps. `rate=True` and the `ufs` filter come for free. If the data set needs its own parameters (like `kind` in `beneficiaries`), write the function by hand using `read_data`, `colormap_create_uf` and `to_rate` as `beneficiaries.py` does. Export it in `__init__.py` and add a row to the table in the README.

### Step 3. Tests

Add the parser test to `tests/test_build_data.py` (plain text in, DataFrame out) and a case to `tests/test_maps.py` (tiny synthetic data in the fixture). Run `pytest`. The `python -m medbr.bundle` zip already includes everything under `<name>/transformed/`.

Then open a pull request. After the merge, run the **build-data** Action with *publish* so users get the new data.

**Spelling conventions**: Names should be lower case, short, use underscore when necessary, use English American spelling. Please have a look at the columns names and functions used in in medbr, and don't hesitate to contact if you have any question.

-----
