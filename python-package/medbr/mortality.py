from medbr.utils import temporal_heatmap


def mortality(cities_code=None, start_at=None, end_at=None):
    """Time heat map of deaths per day by municipality.

    cities_code: city code (or list of codes); default: all.
    start_at, end_at: ISO dates (``YYYY-MM-DD``); default: whole data set.
    """
    return temporal_heatmap(
        ("mortality", "transformed", "mortality.csv"), "death_date", "death_count",
        cities_code, start_at, end_at,
    )
