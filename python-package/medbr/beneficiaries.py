from medbr.utils import colormap_create_uf, read_data, as_list

KINDS = {
    "medical": ("medical_count", "medical plan"),
    "dental": ("dental_count", "dental plan"),
    "all": ("beneficiaries_count", "plan (medical + dental; a person can count twice)"),
}


def beneficiaries_data(data, ufs=None, kind="medical"):
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {sorted(KINDS)}")
    column = KINDS[kind][0]
    if column not in data.columns:
        raise ValueError(
            f"Column '{column}' not found: rebuild the data (python -m medbr.build_data "
            "--only beneficiaries) or update it (python -m medbr.download)."
        )
    ufs = as_list(ufs)
    if ufs is not None:
        data = data[data["uf"].isin(ufs)]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data.set_index("uf")[column]


def beneficiaries(ufs=None, rate=False, kind="medical"):
    """Supplementary health beneficiaries by state (latest quarter of the ANS data).

    ufs: state abbreviation (or list); default: all states.
    rate: if True, show beneficiaries per 100 inhabitants (Census 2022) instead of the total.
    kind: ``"medical"`` (default), ``"dental"`` or ``"all"`` (medical + dental, people with
        both are counted twice).
    """
    data = read_data("beneficiaries", "transformed", "beneficiaries.csv")
    series = beneficiaries_data(data, ufs, kind)
    label = KINDS[kind][1]
    caption = f"Beneficiaries of {label}"
    if rate:
        from medbr.population import population, to_rate

        series = to_rate(series, population("uf"), 100)
        caption = f"Beneficiaries of {label} per 100 inhabitants"
    return colormap_create_uf(series, caption=caption)
