"""
Script 01: Download the CrosswordQA dataset.

Run from the project root:
    python scripts/01_download_data.py
"""

import sys
import os

# Add project root to path so we can import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.download import download_crosswordqa


def main():
    print("=" * 60)
    print("STEP 1: Download CrosswordQA Dataset")
    print("=" * 60)
    print()

    dataset = download_crosswordqa(cache_dir="data/raw")

    train = dataset["train"]
    print()
    print(f"Total entries: {len(train):,}")
    print(f"Columns: {train.column_names}")
    print()

    # Show a few examples
    print("Sample entries:")
    print("-" * 40)
    for i in range(5):
        print(f"  Clue:   {train[i]['clue']}")
        print(f"  Answer: {train[i]['answer']}")
        print()

    print("Data downloaded and cached. You won't need to download again.")
    print("Next: python scripts/02_preprocess_data.py")


if __name__ == "__main__":
    main()