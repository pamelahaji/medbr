from medbr.utils import temporal_heatmap


def birth(cities_code=None, start_at=None, end_at=None, rate=False):
    """Time heat map of births per day by municipality (of occurrence).

    cities_code: city code (or list of codes); default: all.
    start_at, end_at: ISO dates (``YYYY-MM-DD``); default: whole data set.
    rate: if True, show births per 100,000 inhabitants (Census 2022) instead of counts.
    """
    return temporal_heatmap(
        ("birth", "transformed", "birth.csv"), "birth_date", "birth_count",
        cities_code, start_at, end_at, rate=rate,
    )
