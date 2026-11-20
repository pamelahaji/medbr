from medbr.utils import colormap_create_uf, read_data, as_list


def beds_data(data, ufs=None):
    ufs = as_list(ufs)
    if ufs is not None:
        data = data[data["uf"].isin(ufs)]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data.set_index("uf")["beds_count"]


def beds(ufs=None):
    """Hospital beds by state (2023).

    ufs: state abbreviation (or list); default: all states.
    """
    data = read_data("beds", "transformed", "beds.csv")
    return colormap_create_uf(beds_data(data, ufs))
