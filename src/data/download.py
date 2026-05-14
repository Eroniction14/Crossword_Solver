"""
Download and cache the CrosswordQA dataset from HuggingFace.
"""

import os
from datasets import load_dataset


def download_crosswordqa(cache_dir: str = "data/raw") -> dict:
    """
    Download the CrosswordQA dataset.

    Returns the dataset object with train split containing 6M+ clue-answer pairs.
    Data is cached locally after first download so subsequent calls are instant.

    Args:
        cache_dir: Where to cache the raw download files.

    Returns:
        HuggingFace Dataset object.
    """
    os.makedirs(cache_dir, exist_ok=True)

    print("Loading CrosswordQA dataset...")
    print("(First download is ~500MB. Cached locally after that.)")
    print()

    dataset = load_dataset("albertxu/CrosswordQA", cache_dir=cache_dir)
    train = dataset["train"]

    print(f"Loaded {len(train):,} clue-answer pairs")
    print(f"Columns: {train.column_names}")

    return dataset