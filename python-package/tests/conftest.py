import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Tests never download the data bundle (individual tests re-enable it explicitly)."""
    monkeypatch.setenv("MEDBR_NO_DOWNLOAD", "1")
