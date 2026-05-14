"""
Core data structures for crossword puzzles.

Defines Puzzle, Slot, and Crossing objects used throughout the system.
All input formats (JSON, PUZ) convert to these structures.
"""

from dataclasses import dataclass, field


@dataclass
class Slot:
    """
    One answer slot in the crossword (e.g., "1-Across" or "3-Down").

    Attributes:
        number: The clue number (1, 2, 3, ...).
        direction: "across" or "down".
        clue: The clue text.
        length: How many letters the answer has.
        start_row: Row of the first cell (0-indexed).
        start_col: Column of the first cell (0-indexed).
        cells: List of (row, col) tuples this slot occupies.
        answer: The correct answer, if known (for evaluation). None otherwise.
    """
    number: int
    direction: str          # "across" or "down"
    clue: str
    length: int
    start_row: int
    start_col: int
    cells: list[tuple[int, int]]
    answer: str = None      # Only set if we have the solution


@dataclass
class Crossing:
    """
    A crossing between two slots — they share a cell.

    Attributes:
        cell: The (row, col) of the shared cell.
        slot_a_id: ID of the first slot (e.g., "1-across").
        slot_a_pos: Position within slot A where the crossing is (0-indexed).
        slot_b_id: ID of the second slot (e.g., "2-down").
        slot_b_pos: Position within slot B where the crossing is (0-indexed).
    """
    cell: tuple[int, int]
    slot_a_id: str
    slot_a_pos: int
    slot_b_id: str
    slot_b_pos: int


@dataclass
class Puzzle:
    """
    A complete crossword puzzle — the universal format.

    This is what every loader produces and what every solver component consumes.

    Attributes:
        rows: Number of rows in the grid.
        cols: Number of columns in the grid.
        grid: 2D list where grid[row][col] is:
              "#" for a black cell,
              "." for an empty white cell,
              or a letter (A-Z) for a pre-filled cell.
        slots: Dict mapping slot ID ("1-across", "3-down") to Slot objects.
        crossings: List of Crossing objects describing where slots intersect.
        title: Optional puzzle title.
        author: Optional puzzle author.
    """
    rows: int
    cols: int
    grid: list[list[str]]
    slots: dict[str, Slot] = field(default_factory=dict)
    crossings: list[Crossing] = field(default_factory=list)
    title: str = ""
    author: str = ""

    def get_slot(self, slot_id: str) -> Slot:
        """Get a slot by its ID (e.g., '1-across')."""
        return self.slots[slot_id]

    def get_crossings_for_slot(self, slot_id: str) -> list[Crossing]:
        """Get all crossings involving a specific slot."""
        return [c for c in self.crossings
                if c.slot_a_id == slot_id or c.slot_b_id == slot_id]

    def get_across_slots(self) -> list[Slot]:
        """Get all across slots, sorted by number."""
        return sorted(
            [s for s in self.slots.values() if s.direction == "across"],
            key=lambda s: s.number
        )

    def get_down_slots(self) -> list[Slot]:
        """Get all down slots, sorted by number."""
        return sorted(
            [s for s in self.slots.values() if s.direction == "down"],
            key=lambda s: s.number
        )

    def summary(self) -> str:
        """Print a human-readable summary of the puzzle."""
        across = self.get_across_slots()
        down = self.get_down_slots()

        lines = [
            f"Puzzle: {self.title or 'Untitled'} ({self.rows}x{self.cols})",
            f"Slots: {len(across)} across, {len(down)} down",
            f"Crossings: {len(self.crossings)}",
            "",
            "ACROSS:",
        ]
        for s in across:
            ans = f" [{s.answer}]" if s.answer else ""
            lines.append(f"  {s.number}. {s.clue} ({s.length} letters){ans}")

        lines.append("")
        lines.append("DOWN:")
        for s in down:
            ans = f" [{s.answer}]" if s.answer else ""
            lines.append(f"  {s.number}. {s.clue} ({s.length} letters){ans}")

        return "\n".join(lines)

    def print_grid(self) -> str:
        """Return a visual representation of the grid."""
        lines = []
        for row in self.grid:
            line = ""
            for cell in row:
                if cell == "#":
                    line += "██"
                elif cell == ".":
                    line += " ."
                else:
                    line += f" {cell}"
            lines.append(line)
        return "\n".join(lines)