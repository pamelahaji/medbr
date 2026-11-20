"""Shared helpers for the medbr package."""
import json
import os
from pathlib import Path

import pandas as pd
import requests

# Default map center/zoom (Brazil)
BR_CENTER = [-14.2, -51.9]
BR_ZOOM = 4

REQUEST_TIMEOUT = 30


def data_dir():
    """Return the folder that holds the medbr data sets.

    Order: ``MEDBR_DATA_DIR`` (if set); the ``data`` folder inside the package
    when it already has the municipal mesh (development checkout); otherwise a
    per-user cache folder (``~/.cache/medbr``), where the data bundle is
    downloaded on first use.
    """
    env = os.environ.get("MEDBR_DATA_DIR")
    if env:
        return Path(env)
    local = Path(__file__).resolve().parent / "data"
    if (local / "cities" / "transformed" / "cities.shp").exists():
        return local
    cache = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(cache) / "medbr"


def ensure_data(*parts):
    """Return the path of a data file, downloading the data bundle if it is missing."""
    from medbr import download

    path = data_path(*parts)
    if path.exists():
        return path
    reason = "automatic download is disabled (MEDBR_NO_DOWNLOAD)"
    if download.downloads_enabled():
        try:
            download.fetch_bundle(data_dir())
            if path.exists():
                return path
            reason = "the downloaded bundle does not contain this file"
        except Exception as exc:  # network error, 404 (bundle not published yet), bad zip...
            reason = f"download failed: {exc}"
    raise FileNotFoundError(
        f"Data file not found: {path} ({reason}). See README, section "
        "'Preparing the data', or set MEDBR_DATA_DIR."
    )


def data_path(*parts):
    """Build a path inside the data folder, e.g. ``data_path("beds", "transformed", "beds.csv")``."""
    return data_dir().joinpath(*parts)


def read_data(*parts, **kwargs):
    """Read a transformed CSV (``;`` separated) with a clear error if it is missing."""
    return pd.read_csv(ensure_data(*parts), sep=";", **kwargs)


def uri_request(uris, params, request_type="get", auth=None):
    """Request the first uri that answers with status 200 and return its content."""
    last_error = None
    for uri in uris:
        uri = uri_creator(uri, params)
        try:
            if request_type == "get":
                response = requests.get(uri, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.post(uri, data=params, auth=auth, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                return response.content
            last_error = f"HTTP {response.status_code} for {uri}"
        except requests.RequestException as exc:
            last_error = str(exc)
    raise ValueError(f"Request failed: {last_error}")


def uri_creator(uri, params: dict):
    params = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{uri}?{params}"


def remove_nil(data: dict):
    """Remove nil values from dict."""
    return {k: v for k, v in data.items() if v is not None}


def as_list(value):
    """Return ``None`` as is, a scalar as a one-item list, an iterable as a list."""
    if value is None:
        return None
    if isinstance(value, (str, bytes, int)) or not hasattr(value, "__iter__"):
        return [value]
    return list(value)


def as_code_list(value):
    """Normalize city codes to a list of strings (``None`` stays ``None``)."""
    value = as_list(value)
    return None if value is None else [str(v) for v in value]


def filter_dates(data, column, start_at=None, end_at=None):
    """Keep rows whose ISO date string in ``column`` is within [start_at, end_at].

    Either bound can be omitted. Raises ``ValueError`` when nothing is left.
    """
    dates = data[column].astype(str)
    mask = pd.Series(True, index=data.index)
    if start_at is not None:
        mask &= dates >= str(start_at)
    if end_at is not None:
        mask &= dates <= str(end_at)
    data = data[mask]
    if len(data) == 0:
        raise ValueError("No data found.")
    return data


def group_by_date(data, date_col, count_col, points):
    """Build the input of a time heat map.

    ``points`` maps ``city_code`` (str) to ``(lat, lon)``. Returns
    ``(time_index, frames)`` where each frame is a list of ``[lat, lon, count]``.
    """
    data = data.copy()
    data["city_code"] = data["city_code"].astype(str)
    data[date_col] = data[date_col].astype(str)
    time_index, frames = [], []
    for date, day in data.groupby(date_col, sort=True):
        frame = [
            [points[code][0], points[code][1], count]
            for code, count in zip(day["city_code"], day[count_col])
            if code in points
        ]
        if frame:
            time_index.append(date)
            frames.append(frame)
    if not frames:
        raise ValueError("No data found.")
    return time_index, frames


def map_create(data, endpoint, city_name=None, city_code=None, location=None, **kwargs):
    import folium

    if city_name is not None and city_code is not None:
        city = get_cities(city_name=city_name, city_code=city_code)
        centroid = city["geometry"].iloc[0].centroid
        location = [centroid.y, centroid.x]

        m = folium.Map(location, **kwargs)
        folium.GeoJson(city["geometry"]).add_to(m)
    else:
        m = folium.Map(location, **kwargs)

    for i in data:
        folium.Marker([i[endpoint["lat"]], i[endpoint["long"]]], popup=i[endpoint["name"]]).add_to(m)

    return m


def get_cities(ufs=None, city_name=None, city_code=None):
    """Municipalities as a GeoDataFrame (``city_code`` is always a string)."""
    import geopandas as gpd

    cities = gpd.read_file(ensure_data("cities", "transformed", "cities.shp"))
    cities["city_code"] = cities["city_code"].astype(str)

    if city_name is not None:
        return cities[cities["city_name"].isin(as_list(city_name))]
    if city_code is not None:
        return cities[cities["city_code"].isin(as_code_list(city_code))]
    if ufs is not None:
        return cities[cities["uf"].isin(as_list(ufs))]
    return cities


def city_centroids(cities):
    """Centroids in lat/lon, computed in a projected CRS (SIRGAS 2000 / Brazil Polyconic)."""
    geometry = cities.geometry
    if geometry.crs is None:
        geometry = geometry.set_crs(4674)  # IBGE mesh datum
    return geometry.to_crs(5880).centroid.to_crs(4326)


def new_map(location=None, zoom_start=None):
    import folium

    return folium.Map(
        location=location or BR_CENTER,
        tiles="OpenStreetMap",
        zoom_start=zoom_start or BR_ZOOM,
        control_scale=True,
    )


def colormap_create(data, ufs=None, caption=None):
    """Choropleth by municipality. ``data`` is a Series indexed by city_code (str)."""
    import folium
    from branca.colormap import linear

    cities = get_cities(ufs=ufs).set_index("city_code")
    data = data.copy()
    data.index = data.index.astype(str)
    cities = cities.join(data.rename("count"), how="inner")
    if len(cities) == 0:
        raise ValueError("No data found.")

    colormap = linear.YlOrRd_09.scale(data.min(), data.max())
    m = new_map()
    folium.GeoJson(
        cities[["geometry", "count"]].to_json(),
        name="count",
        style_function=lambda feature: {
            "fillColor": colormap(feature["properties"]["count"]),
            "color": "black",
            "weight": 0.3,
        },
    ).add_to(m)
    if caption:
        colormap.caption = caption
    colormap.add_to(m)
    return m


def colormap_create_uf(data, caption=None):
    """Choropleth by state. ``data`` is a Series indexed by UF (e.g. ``SP``)."""
    import folium
    from branca.colormap import linear

    with open(ensure_data("cities", "raw", "br_states.json"), encoding="utf-8") as f:
        geo_json_data = json.load(f)

    # keep only the states present in the data
    geo_json_data["features"] = [f for f in geo_json_data["features"] if f["id"] in data.index]
    if not geo_json_data["features"]:
        raise ValueError("No data found.")

    colormap = linear.YlOrRd_09.scale(data.min(), data.max())
    m = new_map()
    folium.GeoJson(
        geo_json_data,
        name="count",
        style_function=lambda feature: {
            "fillColor": colormap(data[feature["id"]]),
            "color": "black",
            "weight": 0.3,
        },
    ).add_to(m)
    if caption:
        colormap.caption = caption
    colormap.add_to(m)
    return m


def temporal_heatmap(filename, date_col, count_col, cities_code=None, start_at=None, end_at=None,
                     rate=False, per=100_000):
    """Time heat map of daily counts by municipality (used by birth and mortality).

    With ``rate=True`` the intensity is the daily count per ``per`` inhabitants.
    """
    from folium.plugins import HeatMapWithTime

    data = read_data(*filename, dtype={"city_code": str})
    codes = as_code_list(cities_code)
    if codes is not None:
        data = data[data["city_code"].isin(codes)]
    data = filter_dates(data, date_col, start_at, end_at)
    if rate:
        from medbr.population import population, add_rate

        data = add_rate(data, population("city"), count_col, per)

    cities = get_cities(city_code=sorted(data["city_code"].unique()))
    centroids = city_centroids(cities)
    points = dict(zip(cities["city_code"], zip(centroids.y, centroids.x)))

    time_index, frames = group_by_date(data, date_col, count_col, points)

    m = new_map(location=frames[0][0][:2])
    HeatMapWithTime(frames, index=time_index, auto_play=False, use_local_extrema=True).add_to(m)
    return m
