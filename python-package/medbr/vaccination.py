from medbr.factories import city_series
from medbr.utils import colormap_create, read_data

# immunobiological code in the SI-PNI files -> (key used by ``vaccination``, label)
VACCINES = {
    "072": ("bcg", "BCG"), "073": ("hepatitis_b", "Hepatitis B"), "061": ("rotavirus", "Rotavirus"),
    "053": ("meningococcal_c", "Meningococcal C"), "080": ("penta", "Pentavalent"),
    "012": ("pneumococcal", "Pneumococcal"), "074": ("polio", "Poliomyelitis"),
    "006": ("yellow_fever", "Yellow fever"), "096": ("hepatitis_a", "Hepatitis A"),
    "021": ("mmr_d1", "MMR dose 1"), "098": ("mmr_d2", "MMR dose 2"), "097": ("tetra_viral", "Tetra viral"),
}
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
