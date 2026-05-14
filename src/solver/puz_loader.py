"""
AcrossLite (.puz) puzzle loader.

Parses the standard .puz binary format used by most crossword archives.
Requires the puzpy library.
"""

import puz
from src.solver.puzzle import Puzzle
from src.solver.grid_analyzer import analyze_grid


def load_from_puz(filepath: str) -> Puzzle:
    """
    Load a crossword puzzle from a .puz file.

    Args:
        filepath: Path to the .puz file.

    Returns:
        A Puzzle object ready for solving.
    """
    p = puz.read(filepath)

    rows = p.height
    cols = p.width

    # --- Build the grid ---
    # p.fill is a flat string where "." = white, "-" = black
    # p.solution is a flat string with the actual letters
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            idx = r * cols + c
            if p.fill[idx] == ".":
                row.append(".")    # Empty white cell
            elif p.fill[idx] == "-":
                row.append(".")    # Also a white cell (has a letter in solution)
            else:
                row.append("#")    # Black cell
        grid.append(row)

    # Fix: puz uses "." in fill for black cells sometimes depending on version
    # More reliable: check the solution string
    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            idx = r * cols + c
            if p.solution[idx] == ".":
                row.append("#")    # Black cell
            else:
                row.append(".")    # White cell
        grid.append(row)

    # Analyze the grid to find slots and crossings
    slots, crossings = analyze_grid(grid)

    # --- Attach clues ---
    # puz stores clues in order: all across clues first, then all down clues
    numbering = p.clue_numbering()

    for clue_info in numbering.across:
        num = clue_info["num"]
        slot_id = f"{num}-across"
        if slot_id in slots:
            slots[slot_id].clue = clue_info["clue"]

    for clue_info in numbering.down:
        num = clue_info["num"]
        slot_id = f"{num}-down"
        if slot_id in slots:
            slots[slot_id].clue = clue_info["clue"]

    # --- Attach answers from solution ---
    for slot_id, slot in slots.items():
        answer_letters = []
        for r, c in slot.cells:
            idx = r * cols + c
            letter = p.solution[idx]
            answer_letters.append(letter)
        slot.answer = "".join(answer_letters)

    puzzle = Puzzle(
        rows=rows,
        cols=cols,
        grid=grid,
        slots=slots,
        crossings=crossings,
        title=p.title or "",
        author=p.author or "",
    )

    return puzzle