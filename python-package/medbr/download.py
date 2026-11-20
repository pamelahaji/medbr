"""Download of the prepared data bundle (a zip published as a GitHub release asset)."""
import os
import shutil
import tempfile
import zipfile
from pathlib import Path

import requests

BUNDLE_URL = os.environ.get(
    "MEDBR_BUNDLE_URL",
    "https://github.com/pamelahaji/medbr/releases/download/data-v1/medbr-data.zip",
)


def downloads_enabled():
    return os.environ.get("MEDBR_NO_DOWNLOAD", "") in ("", "0")


def safe_extract(zip_path, dest):
    """Extract a zip refusing members that would land outside ``dest``."""
    dest = Path(dest).resolve()
    with zipfile.ZipFile(zip_path) as zf:
        for name in zf.namelist():
            target = (dest / name).resolve()
            if dest != target and dest not in target.parents:
                raise ValueError(f"Unsafe path in zip: {name}")
        zf.extractall(dest)


def fetch_bundle(dest, url=None, timeout=120):
    """Download the data bundle and extract it into ``dest``."""
    url = url or BUNDLE_URL
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "bundle.zip"
        with requests.get(url, stream=True, timeout=timeout) as response:
            response.raise_for_status()
            with open(zip_path, "wb") as f:
                shutil.copyfileobj(response.raw, f)
        safe_extract(zip_path, dest)


def bundle_marker():
    from medbr.utils import data_dir

    return data_dir() / ".bundle_downloaded"


def update_data(url=None):
    """Download the data bundle into the data folder (replacing files with the same name)."""
    from medbr.utils import data_dir

    fetch_bundle(data_dir(), url)
    bundle_marker().touch()


if __name__ == "__main__":
    update_data()
    print("data updated")
