"""Registry of the data sets medbr can build.

To add a data set, write a builder function and decorate it::

    from medbr.registry import dataset

    @dataset("sanitation", "PNSB basic sanitation by municipality (IBGE)")
    def build_sanitation(tmp, simplify):
        ...  # download into ``tmp``, write data/sanitation/transformed/sanitation.csv

``python -m medbr.build_data`` runs every registered builder (``--only name`` runs some) and
``python -m medbr.bundle`` ships every ``<name>/transformed/*`` file automatically.
"""
REGISTRY = {}


def dataset(name, description):
    """Register ``fn(tmp: Path, simplify: float)`` as the builder of data set ``name``."""

    def decorator(fn):
        if name in REGISTRY:
            raise ValueError(f"Data set '{name}' is already registered")
        REGISTRY[name] = (fn, description)
        return fn

    return decorator
