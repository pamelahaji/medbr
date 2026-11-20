from medbr.build_data import VACCINES
from medbr.factories import city_series
from medbr.utils import colormap_create, read_data

LABELS = {key: label for key, label in VACCINES.values()}


def vaccination(vaccine="penta", ufs=None):
    """Routine vaccination coverage (%) by municipality, 2018 (SI-PNI, Ministry of Health).

    vaccine: one of ``bcg``, ``hepatitis_b``, ``rotavirus``, ``meningococcal_c``, ``penta``,
        ``pneumococcal``, ``polio``, ``yellow_fever``, ``hepatitis_a``, ``mmr_d1``, ``mmr_d2``,
        ``tetra_viral``.
    ufs: state abbreviation (or list); default: all.

    The value is the official coverage (doses applied / target population of the vaccine, by
    municipality of residence): it can exceed 100% because of denominator and registration issues.
    Coverage is a percentage, so there is no ``rate`` option.
    """
    if vaccine not in LABELS:
        raise ValueError(f"vaccine must be one of {sorted(LABELS)}")
    data = read_data("vaccination", "transformed", "vaccination.csv", dtype={"city_code": str})
    data = data[data["vaccine"] == vaccine].dropna(subset=["coverage"])
    series = city_series(data, "coverage")
    return colormap_create(series, ufs=ufs, caption=f"{LABELS[vaccine]} coverage (%), 2018")
