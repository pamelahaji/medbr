"""Ready-made map functions: a new data set usually needs one line here.

    beds = uf_choropleth("beds", "beds_count", "Hospital beds", per=1000)
    cases = daily_heatmap("dengue", "case_date", "case_count")

The data must be in ``<dataset>/transformed/<dataset>.csv`` (``;`` separated) with the columns
used below. ``rate=True`` divides by the Census 2022 population.
"""
from medbr.utils import as_list, colormap_create, colormap_create_uf, read_data, temporal_heatmap


def uf_series(data, column, ufs=None):
    """Series indexed by ``uf`` (state abbreviation), optionally restricted to some states."""
    if column not in data.columns:
        raise ValueError(f"Column '{column}' not found: rebuild the data (python -m medbr.build_data).")
    ufs = as_list(ufs)
    if ufs is not None:
        data = data[data["uf"].isin(ufs)]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data.set_index("uf")[column]


def city_series(data, column):
    """Series indexed by ``city_code`` (str), summed by municipality."""
    data = data.assign(city_code=data["city_code"].astype(str))
    return data.groupby("city_code")[column].sum()


def uf_choropleth(dataset, column, label, per=100_000, doc=None):
    """Map function ``f(ufs=None, rate=False)``: choropleth by state from ``uf`` + ``column``."""

    def func(ufs=None, rate=False):
        series = uf_series(read_data(dataset, "transformed", f"{dataset}.csv"), column, ufs)
        caption = label
        if rate:
            from medbr.population import population, to_rate

            series = to_rate(series, population("uf"), per)
            caption = f"{label} per {per:,} inhabitants"
        return colormap_create_uf(series, caption=caption)

    func.__name__ = dataset
    func.__doc__ = doc or f"{label} by state.\n\n    ufs: state abbreviation (or list); default: all.\n    rate: per {per:,} inhabitants."
    return func


def city_choropleth(dataset, column, label, per=100_000, doc=None):
    """Map function ``f(ufs=None, rate=False)``: choropleth by municipality from ``city_code`` + ``column``."""

    def func(ufs=None, rate=False):
        series = city_series(read_data(dataset, "transformed", f"{dataset}.csv"), column)
        caption = label
        if rate:
            from medbr.population import population, to_rate

            series = to_rate(series, population("city"), per)
            caption = f"{label} per {per:,} inhabitants"
        return colormap_create(series, ufs=ufs, caption=caption)

    func.__name__ = dataset
    func.__doc__ = doc or f"{label} by municipality.\n\n    ufs: state abbreviation (or list); default: all.\n    rate: per {per:,} inhabitants."
    return func


def daily_heatmap(dataset, date_col, count_col, per=100_000, doc=None):
    """Map function: time heat map of daily counts by municipality (``city_code``, date, count)."""

    def func(cities_code=None, start_at=None, end_at=None, rate=False, ufs=None):
        return temporal_heatmap(
            (dataset, "transformed", f"{dataset}.csv"), date_col, count_col,
            cities_code, start_at, end_at, rate=rate, per=per, ufs=ufs,
        )

    func.__name__ = dataset
    func.__doc__ = doc or (
        f"Time heat map of {count_col} per day by municipality.\n\n"
        "    cities_code: city code (or list); ufs: state(s); start_at, end_at: ISO dates;\n"
        f"    rate: per {per:,} inhabitants. Filter by state/city and dates: the whole country is a very large map."
    )
    return func
