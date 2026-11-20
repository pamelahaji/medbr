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


def plancoverage(ufs=None, operators=None):
    """Number of health plans sold by municipality.

    ufs: state abbreviation (or list); default: all states.
    operators: operator code (or list); default: all operators.
    """
    data = read_data("plancoverage", "transformed", "plancoverage.csv")
    return colormap_create(plancoverage_data(data, operators), ufs=ufs)
