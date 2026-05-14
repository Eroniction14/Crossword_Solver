"""
Unit tests for the belief propagation solver.

Run:
    python -m pytest tests/test_solver.py -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.solver.puzzle import Puzzle, Slot, Crossing
from src.solver.belief_propagation import BeliefPropagationSolver


def make_mini_puzzle():
    """Create a minimal 3x3 puzzle for testing."""
    grid = [
        [".", ".", "."],
        ["#", ".", "#"],
        [".", ".", "."],
    ]
    slots = {
        "1-across": Slot(1, "across", "Test across 1", 3, 0, 0,
                         [(0, 0), (0, 1), (0, 2)], answer="CAT"),
        "2-down": Slot(2, "down", "Test down", 3, 0, 1,
                       [(0, 1), (1, 1), (2, 1)], answer="ATE"),
        "3-across": Slot(3, "across", "Test across 2", 3, 2, 0,
                         [(2, 0), (2, 1), (2, 2)], answer="BED"),
    }
    crossings = [
        Crossing((0, 1), "1-across", 1, "2-down", 0),
        Crossing((2, 1), "3-across", 1, "2-down", 2),
    ]
    return Puzzle(rows=3, cols=3, grid=grid, slots=slots, crossings=crossings)


class TestBeliefPropagation:
    """Tests for the BP solver."""

    def test_perfect_solve_with_correct_candidates(self):
        """BP should find the correct answer when it's in the candidates."""
        puzzle = make_mini_puzzle()
        candidates = {
            "1-across": [
                {"answer": "CAT", "score": 0.9},
                {"answer": "DOG", "score": 0.5},
            ],
            "2-down": [
                {"answer": "ATE", "score": 0.9},
                {"answer": "OWL", "score": 0.3},
            ],
            "3-across": [
                {"answer": "BED", "score": 0.9},
                {"answer": "RED", "score": 0.7},
            ],
        }

        solver = BeliefPropagationSolver(puzzle, candidates, max_iterations=10)
        solution = solver.solve(verbose=False)

        assert solution["1-across"] == "CAT"
        assert solution["2-down"] == "ATE"
        assert solution["3-across"] == "BED"

    def test_no_conflicts_with_correct_solution(self):
        """Correct solution should have zero conflicts."""
        puzzle = make_mini_puzzle()
        candidates = {
            "1-across": [{"answer": "CAT", "score": 0.9}],
            "2-down": [{"answer": "ATE", "score": 0.9}],
            "3-across": [{"answer": "BED", "score": 0.9}],
        }

        solver = BeliefPropagationSolver(puzzle, candidates)
        solution = solver.solve(verbose=False)
        conflicts = solver.get_conflicts(solution)

        assert len(conflicts) == 0

    def test_detects_conflicts(self):
        """Should detect letter mismatches at crossings."""
        puzzle = make_mini_puzzle()
        # Force wrong answers
        solution = {
            "1-across": "DOG",  # position 1 = O
            "2-down": "ATE",    # position 0 = A (conflict: O != A)
            "3-across": "BED",  # position 1 = E (matches ATE position 2)
        }

        solver = BeliefPropagationSolver(puzzle, {
            "1-across": [{"answer": "DOG", "score": 1.0}],
            "2-down": [{"answer": "ATE", "score": 1.0}],
            "3-across": [{"answer": "BED", "score": 1.0}],
        })
        conflicts = solver.get_conflicts(solution)

        assert len(conflicts) == 1
        assert conflicts[0]["cell"] == (0, 1)

    def test_evaluate_perfect(self):
        """Evaluation should report 100% for correct solution."""
        puzzle = make_mini_puzzle()
        candidates = {
            "1-across": [{"answer": "CAT", "score": 0.9}],
            "2-down": [{"answer": "ATE", "score": 0.9}],
            "3-across": [{"answer": "BED", "score": 0.9}],
        }

        solver = BeliefPropagationSolver(puzzle, candidates)
        solution = solver.solve(verbose=False)
        metrics = solver.evaluate(solution)

        assert metrics["perfect"] is True
        assert metrics["word_accuracy"] == 1.0
        assert metrics["letter_accuracy"] == 1.0

    def test_evaluate_partial(self):
        """Evaluation should correctly report partial accuracy."""
        puzzle = make_mini_puzzle()
        solution = {
            "1-across": "CAT",  # correct
            "2-down": "AXE",    # wrong
            "3-across": "BED",  # correct
        }

        solver = BeliefPropagationSolver(puzzle, {
            "1-across": [{"answer": "CAT", "score": 1.0}],
            "2-down": [{"answer": "AXE", "score": 1.0}],
            "3-across": [{"answer": "BED", "score": 1.0}],
        })
        metrics = solver.evaluate(solution)

        assert metrics["perfect"] is False
        assert metrics["correct_words"] == 2
        assert metrics["total_words"] == 3

    def test_bp_prefers_crossing_compatible(self):
        """BP should prefer candidates that agree at crossings."""
        puzzle = make_mini_puzzle()
        candidates = {
            "1-across": [
                {"answer": "CAT", "score": 0.5},  # A at pos 1
                {"answer": "DOG", "score": 0.8},  # O at pos 1 (higher score but conflicts)
            ],
            "2-down": [
                {"answer": "ATE", "score": 0.9},  # A at pos 0
            ],
            "3-across": [
                {"answer": "BED", "score": 0.9},  # E at pos 1
            ],
        }

        solver = BeliefPropagationSolver(puzzle, candidates, max_iterations=15)
        solution = solver.solve(verbose=False)

        # BP should choose CAT over DOG because A matches ATE's first letter
        assert solution["1-across"] == "CAT"

    def test_empty_candidates(self):
        """Solver should handle slots with no candidates."""
        puzzle = make_mini_puzzle()
        candidates = {
            "1-across": [{"answer": "CAT", "score": 0.9}],
            "2-down": [],  # No candidates
            "3-across": [{"answer": "BED", "score": 0.9}],
        }

        solver = BeliefPropagationSolver(puzzle, candidates)
        solution = solver.solve(verbose=False)

        # Should still produce a solution (with placeholder for empty slot)
        assert "1-across" in solution
        assert "3-across" in solution


if __name__ == "__main__":
    pytest.main([__file__, "-v"])