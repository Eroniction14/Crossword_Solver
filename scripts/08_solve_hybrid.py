"""
Script 08: Solve a crossword with FAISS retrieval + LLM hybrid.

Run from the project root:
    python scripts/08_solve_hybrid.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.solver.loader import load_puzzle
from src.retrieval.retriever import Retriever
from src.llm.generator import LLMGenerator
from src.solver.belief_propagation import BeliefPropagationSolver

INDEX_DIR = "data/indexes/v1"
MODEL_NAME = "all-MiniLM-L6-v2"
PUZZLE_PATH = "puzzles/nyt_daily_2026_05_11.json"
RETRIEVAL_CANDIDATES = 50
LLM_CANDIDATES = 10


def merge_candidates(retrieval_results: list[dict],
                     llm_results: list[dict]) -> list[dict]:
    """
    Merge candidates from retrieval and LLM, removing duplicates.
    If the same answer appears in both, keep the higher score.
    """
    merged = {}

    for r in retrieval_results:
        answer = r["answer"]
        if answer not in merged or r["score"] > merged[answer]["score"]:
            merged[answer] = r

    for r in llm_results:
        answer = r["answer"]
        # Boost LLM candidates slightly since they come from reasoning
        boosted_score = r["score"] * 1.1
        if answer not in merged or boosted_score > merged[answer]["score"]:
            merged[answer] = {**r, "score": boosted_score}

    # Sort by score descending
    result = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
    return result


def main():
    print("=" * 60)
    print("STEP 8: Hybrid Solve (FAISS + LLM)")
    print("=" * 60)
    print()

    # --- Load puzzle ---
    print("Loading puzzle...")
    puzzle = load_puzzle(PUZZLE_PATH)
    print(puzzle.summary())
    print()

    # --- Load retriever ---
    print("Loading retriever...")
    retriever = Retriever.load(INDEX_DIR, model_name=MODEL_NAME)
    print()

    # --- Load LLM generator ---
    print("Loading LLM generator...")
    llm = LLMGenerator()
    print("LLM ready.")
    print()

    # --- Generate candidates from both sources ---
    print("=" * 60)
    print("GENERATING CANDIDATES (Retrieval + LLM)")
    print("=" * 60)
    print()

    candidates = {}
    for slot_id, slot in puzzle.slots.items():
        # Get retrieval candidates
        retrieval_results = retriever.get_candidates(
            clue=slot.clue,
            answer_length=slot.length,
            top_k=RETRIEVAL_CANDIDATES,
        )

        # Get LLM candidates
        print(f"  {slot_id}: \"{slot.clue}\" ({slot.length} letters)")
        print(f"    Retrieval: {len(retrieval_results)} candidates", end="")

        llm_results = llm.get_candidates(
            clue=slot.clue,
            answer_length=slot.length,
            num_candidates=LLM_CANDIDATES,
        )
        print(f" | LLM: {len(llm_results)} candidates")

        # Show LLM's top answers
        if llm_results:
            llm_top = ", ".join(r["answer"] for r in llm_results[:5])
            print(f"    LLM suggests: {llm_top}")

        # Merge
        merged = merge_candidates(retrieval_results, llm_results)
        candidates[slot_id] = merged

        # Check if correct answer is in merged candidates
        has_correct = any(r["answer"] == slot.answer for r in merged)
        retrieval_has = any(r["answer"] == slot.answer for r in retrieval_results)
        llm_has = any(r["answer"] == slot.answer for r in llm_results)

        source = ""
        if retrieval_has and llm_has:
            source = "BOTH"
        elif retrieval_has:
            source = "RETRIEVAL"
        elif llm_has:
            source = "LLM SAVED IT"
        else:
            source = "MISSING"

        if slot.answer:
            print(f"    Correct '{slot.answer}': {source}")
        print()

    # --- Run Belief Propagation ---
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

    # --- Conflict check ---
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

    # --- Evaluate ---
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

    # --- Show filled grid ---
    print()
    print("=" * 60)
    print("FILLED GRID")
    print("=" * 60)
    filled = [row[:] for row in puzzle.grid]
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