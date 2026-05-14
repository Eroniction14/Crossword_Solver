"""
Unit tests for core crossword solver components.

Run all tests:
    python -m pytest tests/ -v

Run a specific test:
    python -m pytest tests/test_core.py::test_puzzle_creation -v
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.solver.puzzle import Puzzle, Slot, Crossing
from src.solver.grid_analyzer import analyze_grid
from src.solver.json_loader import load_from_json
from src.solver.loader import load_puzzle
from src.data.preprocess import clean_clue, clean_answer


# === Data preprocessing tests ===

class TestPreprocessing:
    """Tests for clue and answer cleaning functions."""

    def test_clean_answer_uppercase(self):
        assert clean_answer("hello") == "HELLO"

    def test_clean_answer_strips_whitespace(self):
        assert clean_answer("  hello  ") == "HELLO"

    def test_clean_answer_removes_non_alpha(self):
        assert clean_answer("hello-world!") == "HELLOWORLD"

    def test_clean_answer_empty(self):
        assert clean_answer("") == ""

    def test_clean_answer_spaces_removed(self):
        assert clean_answer("new york") == "NEWYORK"

    def test_clean_clue_strips_whitespace(self):
        assert clean_clue("  hello  ") == "hello"

    def test_clean_clue_collapses_spaces(self):
        assert clean_clue("hello   world") == "hello world"

    def test_clean_clue_empty(self):
        assert clean_clue("") == ""


# === Puzzle data structure tests ===

class TestPuzzle:
    """Tests for Puzzle, Slot, and Crossing data structures."""

    def test_slot_creation(self):
        slot = Slot(
            number=1, direction="across", clue="Test clue",
            length=3, start_row=0, start_col=0,
            cells=[(0, 0), (0, 1), (0, 2)], answer="CAT",
        )
        assert slot.number == 1
        assert slot.direction == "across"
        assert slot.length == 3
        assert slot.answer == "CAT"

    def test_crossing_creation(self):
        crossing = Crossing(
            cell=(0, 2), slot_a_id="1-across", slot_a_pos=2,
            slot_b_id="2-down", slot_b_pos=0,
        )
        assert crossing.cell == (0, 2)
        assert crossing.slot_a_id == "1-across"

    def test_puzzle_get_across_slots(self):
        slots = {
            "1-across": Slot(1, "across", "clue", 3, 0, 0, [(0,0),(0,1),(0,2)]),
            "2-down": Slot(2, "down", "clue", 3, 0, 2, [(0,2),(1,2),(2,2)]),
            "3-across": Slot(3, "across", "clue", 3, 1, 0, [(1,0),(1,1),(1,2)]),
        }
        puzzle = Puzzle(rows=3, cols=3, grid=[], slots=slots, crossings=[])
        across = puzzle.get_across_slots()
        assert len(across) == 2
        assert across[0].number == 1
        assert across[1].number == 3

    def test_puzzle_get_down_slots(self):
        slots = {
            "1-across": Slot(1, "across", "clue", 3, 0, 0, [(0,0),(0,1),(0,2)]),
            "2-down": Slot(2, "down", "clue", 3, 0, 2, [(0,2),(1,2),(2,2)]),
        }
        puzzle = Puzzle(rows=3, cols=3, grid=[], slots=slots, crossings=[])
        down = puzzle.get_down_slots()
        assert len(down) == 1
        assert down[0].number == 2

    def test_puzzle_get_crossings_for_slot(self):
        crossing = Crossing((0, 2), "1-across", 2, "2-down", 0)
        puzzle = Puzzle(rows=3, cols=3, grid=[], slots={}, crossings=[crossing])
        result = puzzle.get_crossings_for_slot("1-across")
        assert len(result) == 1
        assert result[0].slot_b_id == "2-down"


# === Grid analyzer tests ===

class TestGridAnalyzer:
    """Tests for grid analysis — slot detection and crossing computation."""

    def test_simple_3x3_grid(self):
        grid = [
            [".", ".", "."],
            [".", "#", "."],
            [".", ".", "."],
        ]
        slots, crossings = analyze_grid(grid)

        # Should find across and down slots
        across_slots = [s for s in slots.values() if s.direction == "across"]
        down_slots = [s for s in slots.values() if s.direction == "down"]
        assert len(across_slots) >= 2
        assert len(down_slots) >= 2

    def test_5x5_mini_grid(self):
        grid = [
            ["#", "#", ".", ".", "."],
            ["#", ".", ".", ".", "."],
            [".", ".", ".", ".", "."],
            [".", ".", ".", ".", "#"],
            [".", ".", ".", "#", "#"],
        ]
        slots, crossings = analyze_grid(grid)

        # Verify slot count
        assert len(slots) > 0
        # Verify crossings exist
        assert len(crossings) > 0

    def test_slot_cells_correct(self):
        grid = [
            [".", ".", "."],
            ["#", "#", "#"],
            [".", ".", "."],
        ]
        slots, _ = analyze_grid(grid)

        # Should have two across slots (row 0 and row 2)
        across = [s for s in slots.values() if s.direction == "across"]
        assert len(across) == 2
        for slot in across:
            assert slot.length == 3
            assert len(slot.cells) == 3

    def test_no_single_cell_slots(self):
        """Single cells should not create slots."""
        grid = [
            [".", "#", "."],
            ["#", "#", "#"],
            [".", "#", "."],
        ]
        slots, _ = analyze_grid(grid)
        # No slot should have length 1
        for slot in slots.values():
            assert slot.length >= 2

    def test_crossing_positions_valid(self):
        grid = [
            [".", ".", "."],
            [".", ".", "."],
            [".", ".", "."],
        ]
        slots, crossings = analyze_grid(grid)

        for crossing in crossings:
            # Verify crossing cell is within grid
            r, c = crossing.cell
            assert 0 <= r < 3
            assert 0 <= c < 3

            # Verify positions are within slot lengths
            slot_a = slots[crossing.slot_a_id]
            slot_b = slots[crossing.slot_b_id]
            assert crossing.slot_a_pos < slot_a.length
            assert crossing.slot_b_pos < slot_b.length


# === Puzzle loader tests ===

class TestLoader:
    """Tests for puzzle file loading."""

    def test_load_json_puzzle(self):
        """Test loading the Mini puzzle."""
        path = "puzzles/nyt_mini_2026_05_07.json"
        if not os.path.exists(path):
            pytest.skip("Puzzle file not found")

        puzzle = load_puzzle(path)
        assert puzzle.rows == 5
        assert puzzle.cols == 5
        assert len(puzzle.slots) == 10
        assert len(puzzle.crossings) > 0

    def test_load_daily_puzzle(self):
        """Test loading the 15x15 daily puzzle."""
        path = "puzzles/nyt_daily_2026_05_11.json"
        if not os.path.exists(path):
            pytest.skip("Puzzle file not found")

        puzzle = load_puzzle(path)
        assert puzzle.rows == 15
        assert puzzle.cols == 15
        assert len(puzzle.slots) == 76

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_puzzle("nonexistent.json")

    def test_load_unsupported_format(self):
        # Create a temp file with wrong extension
        with open("test_temp.xyz", "w") as f:
            f.write("test")
        try:
            with pytest.raises(ValueError):
                load_puzzle("test_temp.xyz")
        finally:
            os.remove("test_temp.xyz")

    def test_puzzle_answers_attached(self):
        """Verify answers are loaded from JSON."""
        path = "puzzles/nyt_mini_2026_05_07.json"
        if not os.path.exists(path):
            pytest.skip("Puzzle file not found")

        puzzle = load_puzzle(path)
        # At least some slots should have answers
        answers = [s.answer for s in puzzle.slots.values() if s.answer]
        assert len(answers) > 0

    def test_puzzle_clues_attached(self):
        """Verify clues are loaded from JSON."""
        path = "puzzles/nyt_mini_2026_05_07.json"
        if not os.path.exists(path):
            pytest.skip("Puzzle file not found")

        puzzle = load_puzzle(path)
        clues = [s.clue for s in puzzle.slots.values() if s.clue]
        assert len(clues) == len(puzzle.slots)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])