"""
Script 03: Explore the dataset — understand what you're working with.

Run from the project root:
    python scripts/03_explore_data.py
"""

import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.download import download_crosswordqa
from src.data.preprocess import preprocess_dataset, get_length_distribution


def main():
    print("=" * 60)
    print("STEP 3: Explore the Dataset")
    print("=" * 60)
    print()

    # Load (uses cache from step 1)
    dataset = download_crosswordqa(cache_dir="data/raw")

    # Preprocess a sample
    print()
    print("Preprocessing 100,000 entries for exploration...")
    records = preprocess_dataset(dataset, subset_size=100_000)
    print()

    # --- Answer length distribution ---
    print("=" * 60)
    print("ANSWER LENGTH DISTRIBUTION")
    print("=" * 60)
    dist = get_length_distribution(records)
    for length, count in dist.items():
        if length <= 15:  # Focus on typical crossword lengths
            bar = "#" * (count // 300)
            print(f"  {length:2d} letters: {count:6,}  {bar}")
    print()

    # --- Most common answers ---
    print("=" * 60)
    print("MOST COMMON ANSWERS (top 20)")
    print("=" * 60)
    from collections import Counter
    answer_counts = Counter(r["answer"] for r in records)
    for answer, count in answer_counts.most_common(20):
        print(f"  {answer:<15} appeared {count} times")
    print()

    # --- Sample clues for common answers ---
    print("=" * 60)
    print("DIFFERENT CLUES FOR THE SAME ANSWER")
    print("=" * 60)
    print()
    print("This shows WHY we need semantic similarity — the same answer")
    print("gets clued in many different ways using different words.")
    print()

    # Find all clues for a common answer
    target_answers = ["ERA", "AREA", "ORE"]
    for target in target_answers:
        target_clues = [r["clue"] for r in records if r["answer"] == target]
        random.seed(42)
        sample = random.sample(target_clues, min(5, len(target_clues)))

        print(f"  Answer: {target}")
        for clue in sample:
            print(f"    - \"{clue}\"")
        print()

    # --- Duplicate clues ---
    print("=" * 60)
    print("CLUE RECYCLING")
    print("=" * 60)
    clue_counts = Counter(r["clue"] for r in records)
    repeated = sum(1 for c in clue_counts.values() if c > 1)
    total_unique = len(clue_counts)
    print(f"  Unique clues: {total_unique:,}")
    print(f"  Clues appearing more than once: {repeated:,}")
    print(f"  Recycling rate: {repeated / total_unique * 100:.1f}%")
    print()
    print("  Most recycled clues:")
    for clue, count in clue_counts.most_common(10):
        matching = [r["answer"] for r in records if r["clue"] == clue]
        answers_str = ", ".join(set(matching))
        print(f"    \"{clue}\" ({count}x) -> {answers_str}")
    print()

    print("Next: python scripts/04_build_index.py")


if __name__ == "__main__":
    main()