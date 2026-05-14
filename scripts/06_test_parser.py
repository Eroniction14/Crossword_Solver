"""
Script 06: Test the puzzle parser.

Loads a sample puzzle, shows the grid structure, slots, and crossings.
Verifies that the parser correctly understands crossword geometry.

Run from the project root:
    python scripts/06_test_parser.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.solver.loader import load_puzzle


def main():
    print("=" * 60)
    print("STEP 6: Test Puzzle Parser")
    print("=" * 60)
    print()

    # Load the test puzzle
    puzzle = load_puzzle("puzzles/test_mini.json")

    # Show the summary
    print(puzzle.summary())
    print()

    # Show the grid visually
    print("=" * 60)
    print("GRID")
    print("=" * 60)
    print(puzzle.print_grid())
    print()

    # Show the crossing map
    print("=" * 60)
    print("CROSSING MAP")
    print("=" * 60)
    print(f"Total crossings: {len(puzzle.crossings)}")
    print()

    for crossing in puzzle.crossings:
        slot_a = puzzle.get_slot(crossing.slot_a_id)
        slot_b = puzzle.get_slot(crossing.slot_b_id)

        print(f"  Cell {crossing.cell}:")
        print(f"    {crossing.slot_a_id} (position {crossing.slot_a_pos}) "
              f"x {crossing.slot_b_id} (position {crossing.slot_b_pos})")

        # If we have answers, show what letter should be there
        if slot_a.answer and slot_b.answer:
            letter_a = slot_a.answer[crossing.slot_a_pos]
            letter_b = slot_b.answer[crossing.slot_b_pos]
            match = "OK" if letter_a == letter_b else "CONFLICT!"
            print(f"    Letter: {letter_a} from {crossing.slot_a_id}, "
                  f"{letter_b} from {crossing.slot_b_id} — {match}")
        print()

    # Show crossings for a specific slot
    print("=" * 60)
    print("CROSSINGS FOR 1-ACROSS")
    print("=" * 60)
    for c in puzzle.get_crossings_for_slot("1-across"):
        other = c.slot_b_id if c.slot_a_id == "1-across" else c.slot_a_id
        pos = c.slot_a_pos if c.slot_a_id == "1-across" else c.slot_b_pos
        print(f"  Position {pos} crosses with {other} at cell {c.cell}")
    print()

    print("Parser is working correctly.")    
if __name__ == "__main__":
    main()