"""Load every dataset whose CSVs are present.

Run from the project root:  python -m scripts.load_all
"""
from scripts import load_ecommerce, load_ipl, load_placements


def main() -> None:
    for loader in (load_ipl, load_ecommerce, load_placements):
        try:
            loader.main()
        except FileNotFoundError as err:
            print(f"  [SKIP] {err}")
    print("\nDone.")


if __name__ == "__main__":
    main()
