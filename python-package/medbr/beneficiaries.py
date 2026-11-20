from medbr.utils import colormap_create_uf, read_data, as_list


def beneficiaries_data(data, ufs=None):
    ufs = as_list(ufs)
    if ufs is not None:
        data = data[data["uf"].isin(ufs)]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data.set_index("uf")["beneficiaries_count"]


def beneficiaries(ufs=None, rate=False):
    """Supplementary health beneficiaries by state.

    ufs: state abbreviation (or list); default: all states.
    rate: if True, show the value per 100 inhabitants (Census 2022) instead of the total.
    """
    data = read_data("beneficiaries", "transformed", "beneficiaries.csv")
    series = beneficiaries_data(data, ufs)
    caption = "Beneficiaries"
    if rate:
        from medbr.population import population, to_rate

        series = to_rate(series, population("uf"), 100)
        caption = "Beneficiaries per 100 inhabitants"
    return colormap_create_uf(series, caption=caption)
