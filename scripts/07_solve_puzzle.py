"""
Script 07: Solve a crossword puzzle end-to-end (retrieval only).

Run from the project root:
    python scripts/07_solve_puzzle.py
"""
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.solver.loader import load_puzzle
from src.retrieval.retriever import Retriever
from src.solver.belief_propagation import BeliefPropagationSolver

INDEX_DIR = "data/indexes/v1"
MODEL_NAME = "all-MiniLM-L6-v2"
PUZZLE_PATH = "puzzles/nyt_mini_2026_05_07.json"
CANDIDATES_PER_CLUE = 50


def main():
    print("=" * 60)
    print("STEP 7: Solve a Crossword Puzzle")
    print("=" * 60)
    print()

    # --- Step 1: Load the puzzle ---
    print("Loading puzzle...")
    puzzle = load_puzzle(PUZZLE_PATH)
    print(puzzle.summary())
    print()
    print("Grid:")
    print(puzzle.print_grid())
    print()

    # --- Step 2: Load the retriever ---
    print("Loading retriever...")
    retriever = Retriever.load(INDEX_DIR, model_name=MODEL_NAME)
    print()

    # --- Step 3: Generate candidates for each clue ---
    print("=" * 60)
    print("GENERATING CANDIDATES")
    print("=" * 60)
    print()

    candidates = {}
    for slot_id, slot in puzzle.slots.items():
        results = retriever.get_candidates(
            clue=slot.clue,
            answer_length=slot.length,
            top_k=CANDIDATES_PER_CLUE,
        )

        candidates[slot_id] = results

        # Show top 3 for each clue
        top3 = results[:3]
        answers_str = ", ".join(
            f"{r['answer']}({r['score']:.2f})" for r in top3
        )
        has_correct = any(r["answer"] == slot.answer for r in results)
        correct_flag = "FOUND" if has_correct else "MISSING"

        print(f"  {slot_id}: \"{slot.clue}\" ({slot.length} letters)")
        print(f"    Top 3: {answers_str}")
        if slot.answer:
            print(f"    Correct answer '{slot.answer}' in candidates: {correct_flag}")
        print()

    # --- Step 4: Run Belief Propagation ---
    print("=" * 60)
    print("RUNNING BELIEF PROPAGATION")
    print("=" * 60)
    print()

    start_time = time.time()

    solver = BeliefPropagationSolver(
        puzzle=puzzle,
        candidates=candidates,
        max_iterations=15,
        damping=0.5,
    )
    solution = solver.solve(verbose=True)

    elapsed = time.time() - start_time
    print(f"\nSolve time: {elapsed:.2f} seconds")

    # --- Step 5: Check for conflicts ---
    print()
    print("=" * 60)
    print("CONFLICT CHECK")
    print("=" * 60)
    conflicts = solver.get_conflicts(solution)
    if conflicts:
        print(f"  {len(conflicts)} conflicts found:")
        for c in conflicts:
            print(f"    Cell {c['cell']}: {c['slot_a']}={c['letter_a']} "
                  f"vs {c['slot_b']}={c['letter_b']}")
    else:
        print("  No conflicts! All crossing letters agree.")

    # --- Step 6: Evaluate against ground truth ---
    print()
    print("=" * 60)
    print("EVALUATION")
    print("=" * 60)
    metrics = solver.evaluate(solution)
    print(f"  Letter accuracy: {metrics['letter_accuracy']:.1%}")
    print(f"  Word accuracy:   {metrics['word_accuracy']:.1%} "
          f"({metrics['correct_words']}/{metrics['total_words']})")
    print(f"  Perfect solve:   {'YES' if metrics['perfect'] else 'NO'}")
    print(f"  Crossing conflicts: {metrics['conflicts']}")

    # --- Show the filled grid ---
    print()
    print("=" * 60)
    print("FILLED GRID")
    print("=" * 60)

    # Build a filled grid from the solution
    filled = [row[:] for row in puzzle.grid]  # Copy
    for slot_id, answer in solution.items():
        slot = puzzle.slots[slot_id]
        for i, (r, c) in enumerate(slot.cells):
            if i < len(answer):
                filled[r][c] = answer[i]

    for row in filled:
        line = ""
        for cell in row:
            if cell == "#":
                line += "██"
            else:
                line += f" {cell}"
        print(line)

    print()


if __name__ == "__main__":
    main()