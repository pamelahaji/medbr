from medbr.utils import colormap_create_uf, read_data, as_list


def beneficiaries_data(data, ufs=None):
    ufs = as_list(ufs)
    if ufs is not None:
        data = data[data["uf"].isin(ufs)]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data.set_index("uf")["beneficiaries_count"]


def beneficiaries(ufs=None):
    """Supplementary health beneficiaries by state.

    ufs: state abbreviation (or list); default: all states.
    """
    data = read_data("beneficiaries", "transformed", "beneficiaries.csv")
    return colormap_create_uf(beneficiaries_data(data, ufs))
