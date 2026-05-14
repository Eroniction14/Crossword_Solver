"""
Sentence-transformer encoder for crossword clue embeddings.

Converts clue text into 384-dimensional dense vectors using the
all-MiniLM-L6-v2 model. Loads from local models/ directory if available.
"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"

import numpy as np
from sentence_transformers import SentenceTransformer


class ClueEncoder:
    """
    Wraps a sentence-transformer model for encoding crossword clues.

    Usage:
        encoder = ClueEncoder()
        vectors = encoder.encode(["Capital of France", "Fishing equipment"])
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        print(f"Loading encoder model: {model_name}")

        # Try local path first, then HuggingFace name
        if os.path.exists(model_name):
            print(f"  Loading from local path: {model_name}")
            self.model = SentenceTransformer(model_name)
        else:
            print(f"  Loading from HuggingFace cache: {model_name}")
            self.model = SentenceTransformer(model_name)

        self.dimension = self.model.get_sentence_embedding_dimension()
        print(f"Embedding dimension: {self.dimension}")

    def encode(self, clues: list, batch_size: int = 64,
               show_progress: bool = True) -> np.ndarray:
        """Encode a list of clue strings into a numpy array of vectors."""
        vectors = self.model.encode(
            clues,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True,
        )
        return vectors

    def encode_single(self, clue: str) -> np.ndarray:
        """Encode a single clue string. Returns shape (1, dimension)."""
        return self.model.encode([clue], convert_to_numpy=True)