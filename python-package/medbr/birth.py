from medbr.factories import daily_heatmap

birth = daily_heatmap(
    "birth", "birth_date", "birth_count",
    doc="""Time heat map of births per day by municipality (of occurrence), 2021-2022.

    cities_code: city code (or list of codes); default: all.
    ufs: state abbreviation (or list); default: all. Filter by state or city and a date range:
        the whole country over two years makes a very large map.
    start_at, end_at: ISO dates (``YYYY-MM-DD``); default: whole data set.
    rate: if True, show births per 100,000 inhabitants (Census 2022) instead of counts.
    """,
)
