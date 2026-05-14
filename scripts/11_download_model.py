"""
Download the sentence-transformer model to the local models/ folder.

This makes the project portable — anyone cloning the repo knows
exactly where the model lives instead of relying on HuggingFace's
hidden cache directory.

Run once:
    python scripts/11_download_model.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import cfg
from sentence_transformers import SentenceTransformer

MODEL_NAME = cfg.retrieval.model_name_hf
SAVE_DIR = "models/sentence_transformer"


def main():
    os.makedirs(SAVE_DIR, exist_ok=True)

    print(f"Downloading model: {MODEL_NAME}")
    print(f"Saving to: {SAVE_DIR}")
    print()

    model = SentenceTransformer(MODEL_NAME)
    model.save(SAVE_DIR)

    print(f"\nModel saved to {SAVE_DIR}/")
    print(f"Size: {sum(f.stat().st_size for f in __import__('pathlib').Path(SAVE_DIR).rglob('*') if f.is_file()) / 1e6:.1f} MB")
    print(f"\nThe encoder will now load from this local path instead of HuggingFace cache.")


if __name__ == "__main__":
    main()