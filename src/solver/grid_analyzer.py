"""
Grid analyzer for computing slots and crossings from a 2D grid layout.

Given a grid of black (#) and white (.) cells, determines numbered
slot positions, cell assignments, and crossing relationships.
"""

from src.solver.puzzle import Slot, Crossing


def analyze_grid(grid: list[list[str]]) -> tuple[dict[str, Slot], list[Crossing]]:
    """
    Given a 2D grid, find all slots and crossings.

    Args:
        grid: 2D list where "#" = black cell, anything else = white cell.

    Returns:
        (slots_dict, crossings_list)
        - slots_dict: maps slot ID ("1-across") to Slot objects (clue will be empty)
        - crossings_list: list of Crossing objects
    """
    rows = len(grid)
    cols = len(grid[0])

    # --- Step 1: Find numbered cells ---
    # A cell gets a number if it starts an across or down slot.
    # Across start: white cell with either a black cell or edge to its left
    # Down start: white cell with either a black cell or edge above it

    def is_white(r, c):
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return False
        return grid[r][c] != "#"

    def starts_across(r, c):
        if not is_white(r, c):
            return False
        if is_white(r, c - 1):      # Has a white cell to the left — not a start
            return False
        if not is_white(r, c + 1):   # No white cell to the right — single cell
            return False
        return True

    def starts_down(r, c):
        if not is_white(r, c):
            return False
        if is_white(r - 1, c):       # Has a white cell above — not a start
            return False
        if not is_white(r + 1, c):   # No white cell below — single cell
            return False
        return True

    # Assign numbers to cells
    number = 1
    cell_numbers = {}  # (row, col) -> number

    for r in range(rows):
        for c in range(cols):
            if starts_across(r, c) or starts_down(r, c):
                cell_numbers[(r, c)] = number
                number += 1

    # --- Step 2: Build slots ---
    slots = {}

    for (r, c), num in cell_numbers.items():
        # Check for across slot
        if starts_across(r, c):
            cells = []
            cc = c
            while cc < cols and is_white(r, cc):
                cells.append((r, cc))
                cc += 1

            slot_id = f"{num}-across"
            slots[slot_id] = Slot(
                number=num,
                direction="across",
                clue="",           # Loaders fill this in later
                length=len(cells),
                start_row=r,
                start_col=c,
                cells=cells,
            )

        # Check for down slot
        if starts_down(r, c):
            cells = []
            rr = r
            while rr < rows and is_white(rr, c):
                cells.append((rr, c))
                rr += 1

            slot_id = f"{num}-down"
            slots[slot_id] = Slot(
                number=num,
                direction="down",
                clue="",           # Loaders fill this in later
                length=len(cells),
                start_row=r,
                start_col=c,
                cells=cells,
            )

    # --- Step 3: Find crossings ---
    # Build a map: cell (row, col) -> list of (slot_id, position_in_slot)
    cell_to_slots = {}

    for slot_id, slot in slots.items():
        for pos, cell in enumerate(slot.cells):
            if cell not in cell_to_slots:
                cell_to_slots[cell] = []
            cell_to_slots[cell].append((slot_id, pos))

    crossings = []
    for cell, slot_list in cell_to_slots.items():
        if len(slot_list) == 2:
            (id_a, pos_a), (id_b, pos_b) = slot_list
            crossings.append(Crossing(
                cell=cell,
                slot_a_id=id_a,
                slot_a_pos=pos_a,
                slot_b_id=id_b,
                slot_b_pos=pos_b,
            ))

    return slots, crossings