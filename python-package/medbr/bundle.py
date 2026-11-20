"""Build the data bundle that ``medbr`` downloads on first use.

    python -m medbr.bundle                 # -> medbr-data.zip
    python -m medbr.bundle --simplify 0.005 --out medbr-data.zip

Run it on a machine where the aggregator scripts already produced the
transformed data. Then publish the zip as a release asset:

    gh release create data-v1 medbr-data.zip --title "medbr data v1"
"""
import argparse
import tempfile
import zipfile
from pathlib import Path

from medbr.utils import data_dir


def collect_files(root):
    """Every ``<dataset>/transformed/*`` file (new data sets are included automatically)
    plus the states file; ``raw`` folders are never shipped."""
    root = Path(root)
    files = [p for p in root.glob("*/transformed/*") if p.is_file() and not p.name.startswith(".")]
    states = root / "cities" / "raw" / "br_states.json"
    if states.exists():
        files.append(states)
    return sorted(files)


def build_bundle(out="medbr-data.zip", simplify=None, root=None):
    root = Path(root) if root else data_dir()
    files = collect_files(root)
    if not files:
        raise FileNotFoundError(f"No transformed data found in {root}.")
    with tempfile.TemporaryDirectory() as tmp, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            arcname = path.relative_to(root)
            if simplify and path.name == "cities.shp":
                import geopandas as gpd

                gdf = gpd.read_file(path)
                gdf["geometry"] = gdf.geometry.simplify(simplify, preserve_topology=True)
                gdf.to_file(Path(tmp) / "cities.shp")
                for sidecar in Path(tmp).glob("cities.*"):
                    zf.write(sidecar, arcname.parent / sidecar.name)
                continue
            if simplify and path.stem == "cities" and path.suffix != ".shp":
                continue  # sidecars were written together with the simplified shapefile
            zf.write(path, arcname)
    return Path(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default="medbr-data.zip")
    parser.add_argument("--simplify", type=float, default=None,
                        help="geometry tolerance in degrees (e.g. 0.005) to shrink the municipal mesh")
    args = parser.parse_args()
    print(build_bundle(args.out, args.simplify))


if __name__ == "__main__":
    main()
