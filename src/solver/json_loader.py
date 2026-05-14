"""
JSON puzzle loader.

Parses crossword puzzles from JSON files with grid, clues, and answers.
See puzzles/ directory for example format.
"""

import json
from src.solver.puzzle import Puzzle
from src.solver.grid_analyzer import analyze_grid


def load_from_json(filepath: str) -> Puzzle:
    """
    Load a crossword puzzle from a JSON file.

    Args:
        filepath: Path to the JSON file.

    Returns:
        A Puzzle object ready for solving.
    """
    with open(filepath, "r") as f:
        data = json.load(f)

    grid = data["grid"]
    rows = len(grid)
    cols = len(grid[0])

    # Analyze the grid to find slots and crossings
    slots, crossings = analyze_grid(grid)

    # Attach clues to slots
    clue_data = data.get("clues", {})
    for direction in ["across", "down"]:
        for num_str, clue_text in clue_data.get(direction, {}).items():
            slot_id = f"{num_str}-{direction}"
            if slot_id in slots:
                slots[slot_id].clue = clue_text

    # Attach answers if provided (for evaluation)
    answer_data = data.get("answers", {})
    for direction in ["across", "down"]:
        for num_str, answer in answer_data.get(direction, {}).items():
            slot_id = f"{num_str}-{direction}"
            if slot_id in slots:
                slots[slot_id].answer = answer.upper()

    puzzle = Puzzle(
        rows=rows,
        cols=cols,
        grid=grid,
        slots=slots,
        crossings=crossings,
        title=data.get("title", ""),
        author=data.get("author", ""),
    )

    return puzzle