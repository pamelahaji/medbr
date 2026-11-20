from medbr.utils import temporal_heatmap


def mortality(cities_code=None, start_at=None, end_at=None, rate=False):
    """Time heat map of deaths per day by municipality (of occurrence).

    cities_code: city code (or list of codes); default: all.
    start_at, end_at: ISO dates (``YYYY-MM-DD``); default: whole data set.
    rate: if True, show deaths per 100,000 inhabitants (Census 2022) instead of counts.
    """
    return temporal_heatmap(
        ("mortality", "transformed", "mortality.csv"), "death_date", "death_count",
        cities_code, start_at, end_at, rate=rate,
    )
