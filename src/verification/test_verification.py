"""
Unit tests for semantic verification.

Run:
    python -m pytest tests/test_verification.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.solver.puzzle import Puzzle, Slot, Crossing
from src.verification.verifier import SemanticVerifier


def make_test_puzzle():
    """Create a simple puzzle for verification testing."""
    slots = {
        "1-across": Slot(1, "across", "Capital of France", 5, 0, 0,
                         [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4)], answer="PARIS"),
        "2-across": Slot(2, "across", "Man's best friend", 3, 1, 0,
                         [(1, 0), (1, 1), (1, 2)], answer="DOG"),
        "3-across": Slot(3, "across", "Lumberjack's tool", 3, 2, 0,
                         [(2, 0), (2, 1), (2, 2)], answer="AXE"),
    }
    return Puzzle(rows=3, cols=5, grid=[], slots=slots, crossings=[])


class TestSemanticVerifier:
    """Tests for the SemanticVerifier."""

    def test_verify_returns_structure(self):
        """Verify result has expected keys."""
        verifier = SemanticVerifier(confidence_threshold=0.5)
        puzzle = make_test_puzzle()
        solution = {"1-across": "PARIS", "2-across": "DOG", "3-across": "AXE"}

        # Without any scoring backends, all scores default empty
        result = verifier.verify_solution(puzzle, solution)
        assert "verified" in result
        assert "flagged" in result
        assert "scores" in result
        assert "total" in result

    def test_retrieval_scoring(self):
        """Test retrieval-based scoring with a mock retriever."""

        class MockRetriever:
            def get_candidates(self, clue, answer_length, top_k):
                # PARIS is the top result for "Capital of France"
                if "France" in clue:
                    return [{"answer": "PARIS", "score": 0.95}]
                # DOG not found for "Man's best friend"
                if "friend" in clue:
                    return [{"answer": "CAT", "score": 0.8}]
                return [{"answer": "AXE", "score": 0.9}]

        verifier = SemanticVerifier(
            retriever=MockRetriever(),
            confidence_threshold=0.5,
        )
        puzzle = make_test_puzzle()
        solution = {"1-across": "PARIS", "2-across": "DOG", "3-across": "AXE"}

        result = verifier.verify_solution(puzzle, solution)

        # PARIS should be verified (found in retrieval)
        assert "1-across" in result["verified"]
        # DOG should be flagged (not found in retrieval)
        assert "2-across" in result["flagged"]

    def test_flagged_details(self):
        """Test getting detailed info about flagged answers."""
        verifier = SemanticVerifier(confidence_threshold=0.5)
        puzzle = make_test_puzzle()
        solution = {"1-across": "PARIS", "2-across": "CAT", "3-across": "AXE"}

        verify_result = {
            "verified": ["1-across", "3-across"],
            "flagged": ["2-across"],
            "scores": {"1-across": 0.9, "2-across": 0.1, "3-across": 0.8},
        }

        details = verifier.get_flagged_details(puzzle, solution, verify_result)
        assert len(details) == 1
        assert details[0]["slot_id"] == "2-across"
        assert details[0]["answer"] == "CAT"
        assert details[0]["expected"] == "DOG"
        assert details[0]["actually_wrong"] is True

    def test_empty_solution(self):
        """Verifier should handle empty solution."""
        verifier = SemanticVerifier()
        puzzle = make_test_puzzle()
        result = verifier.verify_solution(puzzle, {})
        assert result["total"] == 0
        assert result["flagged_count"] == 0

    def test_confidence_threshold(self):
        """Answers below threshold should be flagged."""

        class MockRetriever:
            def get_candidates(self, clue, answer_length, top_k):
                # Return answer at low rank (low score)
                results = [{"answer": f"WRONG{i}", "score": 0.9 - i*0.02} for i in range(40)]
                results.append({"answer": "PARIS", "score": 0.1})
                return results

        verifier = SemanticVerifier(
            retriever=MockRetriever(),
            confidence_threshold=0.5,
        )
        puzzle = make_test_puzzle()
        solution = {"1-across": "PARIS"}

        result = verifier.verify_solution(puzzle, solution)
        # PARIS found but at low rank, so score should be low
        assert result["scores"]["1-across"] < 0.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])