from medbr.utils import colormap_create, read_data, as_list


def plancoverage_data(data, operators=None):
    """Plans per municipality, optionally restricted to some operators."""
    operators = as_list(operators)
    if operators is not None:
        data = data[data["operator"].isin(operators)]
    if len(data) == 0:
        raise ValueError("No data found.")
    data = data.assign(city_code=data["city_code"].astype(str))
    return data.groupby("city_code")["count"].sum()


def plancoverage(ufs=None, operators=None, rate=False):
    """Number of health plans sold by municipality.

    ufs: state abbreviation (or list); default: all states.
    operators: operator code (or list); default: all operators.
    rate: if True, show plans per 100,000 inhabitants (Census 2022).
    """
    data = read_data("plancoverage", "transformed", "plancoverage.csv")
    series = plancoverage_data(data, operators)
    caption = "Health plans"
    if rate:
        from medbr.population import population, to_rate

        series = to_rate(series, population("city"), 100_000)
        caption = "Health plans per 100,000 inhabitants"
    return colormap_create(series, ufs=ufs, caption=caption)
