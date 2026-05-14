"""
High-level retrieval interface combining encoder and FAISS index.

Provides a single get_candidates() method that encodes a query clue,
searches the index, and returns ranked answer candidates.
"""

from src.retrieval.encoder import ClueEncoder
from src.retrieval.index import ClueIndex


class Retriever:
    """
    Combines the encoder and FAISS index into a single interface.
    Takes a clue string in, returns ranked candidate answers out.
    """

    def __init__(self, encoder: ClueEncoder, index: ClueIndex):
        self.encoder = encoder
        self.index = index

    def get_candidates(self, clue: str, answer_length: int = None,
                       top_k: int = 200) -> list[dict]:
        """
        Given a crossword clue, return ranked candidate answers.

        Args:
            clue: The clue text (e.g., "Capital of France").
            answer_length: Required answer length (e.g., 5).
            top_k: Max number of candidates to return.

        Returns:
            List of dicts with 'answer', 'clue', 'answer_length', 'score',
            sorted by descending similarity score.
        """
        query_vector = self.encoder.encode_single(clue)
        results = self.index.search(query_vector, top_k=top_k,
                                    answer_length=answer_length)
        return results

    @classmethod
    def load(cls, index_dir: str,
             model_name: str = "all-MiniLM-L6-v2") -> "Retriever":
        """
        Load a pre-built retriever from disk.

        Args:
            index_dir: Path to the saved FAISS index directory.
            model_name: Sentence-transformer model to use for encoding queries.
        """
        encoder = ClueEncoder(model_name=model_name)
        index = ClueIndex.load(index_dir)
        return cls(encoder, index)