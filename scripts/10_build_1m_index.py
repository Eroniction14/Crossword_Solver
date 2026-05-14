"""
Script 10: Build a 1M subset index from the existing 6.4M metadata.

Runs on laptop CPU in ~20 minutes. Result fits in 8GB RAM.

Run from project root:
    python scripts/10_build_1m_index.py
"""

import sys
import os
import json
import time
import gc
import numpy as np
import faiss

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUBSET = 1_000_000
INPUT_META = "data/indexes/v1/metadata.json"
OUTPUT_DIR = "data/indexes/v2"


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load existing cleaned metadata
    print("Loading metadata from v1...")
    with open(INPUT_META) as f:
        records = json.load(f)
    print(f"Total records: {len(records):,}")

    # Take first 1M
    records = records[:SUBSET]
    print(f"Using {len(records):,} records")

    # Save subset metadata
    print("Saving subset metadata...")
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w") as f:
        json.dump(records, f)
    print(f"Metadata saved ({os.path.getsize(os.path.join(OUTPUT_DIR, 'metadata.json')) / 1e6:.0f} MB)")

    # Extract clues
    clues = [r["clue"] for r in records]
    del records
    gc.collect()

    # Encode
    print("\nLoading sentence-transformer...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"Encoding {len(clues):,} clues (this takes ~20 min on CPU)...")
    start = time.time()
    vecs = model.encode(
        clues, batch_size=64, show_progress_bar=True,
        convert_to_numpy=True
    ).astype(np.float32)
    faiss.normalize_L2(vecs)
    elapsed = time.time() - start
    print(f"Encoded in {elapsed / 60:.1f} minutes")

    # Build index
    print("Building FAISS index...")
    index = faiss.IndexFlatIP(384)
    index.add(vecs)

    # Save
    index_path = os.path.join(OUTPUT_DIR, "faiss.index")
    faiss.write_index(index, index_path)
    size_gb = os.path.getsize(index_path) / 1e9
    print(f"Index saved: {index_path} ({size_gb:.2f} GB)")

    # Quick test
    print("\nQuick search test...")
    query = model.encode(["Capital of France"], convert_to_numpy=True).astype(np.float32)
    faiss.normalize_L2(query)
    t = time.time()
    scores, indices = index.search(query, 10)
    search_time = time.time() - t

    with open(os.path.join(OUTPUT_DIR, "metadata.json")) as f:
        meta = json.load(f)

    print(f"Search took {search_time:.4f}s")
    for s, i in zip(scores[0], indices[0]):
        if i >= 0:
            print(f"  {meta[i]['answer']:<15} ({s:.3f}) \"{meta[i]['clue']}\"")

    print(f"\nDone! Now update your scripts to use '{OUTPUT_DIR}' instead of 'data/indexes/v1'")


if __name__ == "__main__":
    main()