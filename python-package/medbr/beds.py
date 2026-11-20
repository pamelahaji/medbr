from medbr.factories import uf_choropleth, uf_series

beds = uf_choropleth(
    "beds", "beds_count", "Hospital beds", per=1000,
    doc="""Existing hospital beds by state (latest month of 2023, CNES).

    ufs: state abbreviation (or list); default: all states.
    rate: if True, show beds per 1,000 inhabitants (Census 2022) instead of the total.
    """,
)


def beds_data(data, ufs=None):
    return uf_series(data, "beds_count", ufs)
