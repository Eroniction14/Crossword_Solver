"""
Script 02: Preprocess raw CrosswordQA data and save to data/processed/.

Uses src/data/download.py and src/data/preprocess.py for the actual logic.

Data pipeline:
    data/raw/ → preprocess → data/processed/ → build_index → data/indexes/

Run from project root:
    python scripts/02_preprocess_data.py
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.download import download_crosswordqa
from src.data.preprocess import clean_clue, clean_answer

OUTPUT_DIR = "data/processed"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load raw dataset using the src/data module
    print("Loading raw dataset...")
    dataset = download_crosswordqa(cache_dir="data/raw")
    print()

    # Process both splits using src/data cleaning functions
    all_records = []
    seen = set()
    skipped_null = 0
    skipped_empty = 0
    skipped_duplicate = 0

    for split_name in ["train", "validation"]:
        split = dataset[split_name]
        print(f"Processing {split_name} split ({len(split):,} records)...")

        for record in split:
            raw_clue = record.get("clue") or record.get("question", "")
            raw_answer = record.get("answer", "")

            # Skip nulls
            if not raw_clue or not raw_answer:
                skipped_null += 1
                continue

            # Clean using src/data/preprocess.py functions
            clue = clean_clue(raw_clue)
            answer = clean_answer(raw_answer)

            # Skip empty after cleaning
            if not clue or not answer:
                skipped_empty += 1
                continue

            # Skip duplicates
            key = f"{clue}|{answer}"
            if key in seen:
                skipped_duplicate += 1
                continue
            seen.add(key)

            all_records.append({
                "clue": clue,
                "answer": answer,
                "answer_length": len(answer),
            })

    # Sort by clue for consistency
    all_records.sort(key=lambda r: r["clue"])

    print(f"\nPreprocessing complete:")
    print(f"  Total clean records: {len(all_records):,}")
    print(f"  Skipped (null):      {skipped_null:,}")
    print(f"  Skipped (empty):     {skipped_empty:,}")
    print(f"  Skipped (duplicate): {skipped_duplicate:,}")

    # Save full processed dataset
    full_path = os.path.join(OUTPUT_DIR, "crossword_qa_full.json")
    print(f"\nSaving full dataset to {full_path}...")
    with open(full_path, "w") as f:
        json.dump(all_records, f)
    size_mb = os.path.getsize(full_path) / 1e6
    print(f"  Saved: {size_mb:.1f} MB ({len(all_records):,} records)")

    # Also save a 1M subset for the active index
    subset_path = os.path.join(OUTPUT_DIR, "crossword_qa_1m.json")
    subset = all_records[:1_000_000]
    print(f"\nSaving 1M subset to {subset_path}...")
    with open(subset_path, "w") as f:
        json.dump(subset, f)
    size_mb = os.path.getsize(subset_path) / 1e6
    print(f"  Saved: {size_mb:.1f} MB ({len(subset):,} records)")

    # Print sample records
    print(f"\nSample records:")
    for r in all_records[:5]:
        print(f"  [{r['answer_length']}] {r['answer']:<20} \"{r['clue']}\"")

    print(f"\nData pipeline:")
    print(f"  data/raw/          -> Raw CrosswordQA from HuggingFace")
    print(f"  data/processed/    -> Cleaned, deduplicated JSON")
    print(f"  data/indexes/      -> FAISS indexes built from processed data")


if __name__ == "__main__":
    main()