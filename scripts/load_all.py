"""Load every dataset whose raw files are present (IPL reference loader first, then easy -> hard).

Run from the project root:  python -m scripts.load_all
"""
import time
from types import ModuleType

from scripts import (
    load_air_quality,
    load_chinook,
    load_ecommerce,
    load_ipl,
    load_netflix,
    load_olist,
    load_placements,
    load_startups,
)

# dataset name -> loader module (each has main(raw_dir=...)); keep in sync with DATASETS.
LOADERS: dict[str, ModuleType] = {
    "ipl": load_ipl,
    "placements": load_placements,
    "netflix": load_netflix,
    "startups": load_startups,
    "air_quality": load_air_quality,
    "ecommerce": load_ecommerce,
    "olist": load_olist,
    "chinook": load_chinook,
}


def main() -> None:
    for name, loader in LOADERS.items():
        start = time.perf_counter()
        try:
            loader.main()
            print(f"  ({name} took {time.perf_counter() - start:.1f} s)\n")
        except FileNotFoundError as err:
            print(f"  [SKIP] {err}\n")
    print("Done.")


if __name__ == "__main__":
    main()
