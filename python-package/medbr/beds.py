from medbr.utils import colormap_create_uf, read_data, as_list


def beds_data(data, ufs=None):
    ufs = as_list(ufs)
    if ufs is not None:
        data = data[data["uf"].isin(ufs)]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data.set_index("uf")["beds_count"]


def beds(ufs=None, rate=False):
    """Hospital beds by state (2023).

    ufs: state abbreviation (or list); default: all states.
    rate: if True, show the value per 1,000 inhabitants (Census 2022) instead of the total.
    """
    data = read_data("beds", "transformed", "beds.csv")
    series = beds_data(data, ufs)
    caption = "Hospital beds"
    if rate:
        from medbr.population import population, to_rate

        series = to_rate(series, population("uf"), 1000)
        caption = "Hospital beds per 1,000 inhabitants"
    return colormap_create_uf(series, caption=caption)
