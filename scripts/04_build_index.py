"""
Script 04: Build the FAISS index.

Encodes 50,000 clues into vectors and builds the searchable index.
Takes ~3-5 minutes on a laptop CPU.

Run from the project root:
    python scripts/04_build_index.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.download import download_crosswordqa
from src.data.preprocess import preprocess_dataset
from src.retrieval.encoder import ClueEncoder
from src.retrieval.index import ClueIndex

# --- Configuration ---
SUBSET_SIZE = 50_000   # Start with 50k. Increase later on a GPU.
INDEX_DIR = "data/indexes/v1"
MODEL_NAME = "all-MiniLM-L6-v2"


def main():
    print("=" * 60)
    print("STEP 4: Build FAISS Index")
    print("=" * 60)
    print()

    # 1. Load and preprocess
    dataset = download_crosswordqa(cache_dir="data/raw")
    print()
    records = preprocess_dataset(dataset, subset_size=SUBSET_SIZE)
    print()

    # 2. Extract clue texts for encoding
    clue_texts = [r["clue"] for r in records]

    # 3. Encode all clues into vectors
    encoder = ClueEncoder(model_name=MODEL_NAME)
    print()
    print(f"Encoding {len(clue_texts):,} clues into vectors...")
    print("(This takes 3-5 minutes on a laptop. Be patient.)")
    print()

    start_time = time.time()
    vectors = encoder.encode(clue_texts, batch_size=64, show_progress=True)
    elapsed = time.time() - start_time

    print()
    print(f"Encoding complete in {elapsed:.1f} seconds")
    print(f"Vector matrix shape: {vectors.shape}")
    print()

    # 4. Build and save the FAISS index
    index = ClueIndex(dimension=encoder.dimension)
    index.add(vectors, records)
    index.save(INDEX_DIR)

    print()
    print(f"Index saved to {INDEX_DIR}/")
    print(f"  - faiss.index: the vector index")
    print(f"  - metadata.json: the clue/answer data")
    print()
    print("Next: python scripts/05_test_retrieval.py")


if __name__ == "__main__":
    main()