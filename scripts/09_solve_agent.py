"""
Script 09: Solve with the Crossword Agent.

Uses config/default.yaml for settings.
Saves results to results/evaluations/.

Run from project root:
    python scripts/09_solve_agent.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import cfg
from results import save_result, print_summary
from src.solver.loader import load_puzzle
from src.retrieval.retriever import Retriever
from src.llm.generator import LLMGenerator
from src.solver.agent import CrosswordAgent

PUZZLE_PATH = "puzzles/nyt_daily_2026_05_11.json"


def main():
    print("=" * 60)
    print("  CROSSWORD SOLVING AGENT")
    print("=" * 60)
    print()

    print("Loading puzzle...")
    puzzle = load_puzzle(PUZZLE_PATH)
    print(f"  {puzzle.title}")
    print(f"  {puzzle.rows}x{puzzle.cols}, {len(puzzle.slots)} slots, "
          f"{len(puzzle.crossings)} crossings")
    print()

    print(f"Loading retriever from {cfg.retrieval.index_dir}...")
    retriever = Retriever.load(cfg.retrieval.index_dir, model_name=cfg.retrieval.model_name)
    print()

    print(f"Loading LLM ({cfg.llm.model})...")
    llm = LLMGenerator(model=cfg.llm.model, max_workers=cfg.llm.max_workers)
    print()

    print("=" * 60)
    print("  AGENT SOLVING LOG")
    print("=" * 60)
    print()

    agent = CrosswordAgent(
        puzzle=puzzle,
        retriever=retriever,
        llm=llm,
        max_passes=cfg.solver.max_passes,
    )
    result = agent.solve()

    # Save result
    print()
    save_result(puzzle, result)

    # Final results
    metrics = result["metrics"]
    print()
    print("=" * 60)
    print("  FINAL RESULTS")
    print("=" * 60)
    print(f"  Passes used:       {result['passes_used']}")
    print(f"  Solve time:        {result['elapsed']:.1f} seconds")
    print(f"  Letter accuracy:   {metrics['letter_accuracy']:.1%}")
    print(f"  Word accuracy:     {metrics['word_accuracy']:.1%} "
          f"({metrics['correct_words']}/{metrics['total_words']})")
    print(f"  Perfect solve:     {'YES' if metrics['perfect'] else 'NO'}")
    print(f"  Conflicts:         {metrics['conflicts']}")

    # Filled grid
    print()
    print("=" * 60)
    print("  FILLED GRID")
    print("=" * 60)
    filled = [row[:] for row in puzzle.grid]
    for slot_id, answer in result["solution"].items():
        slot = puzzle.slots[slot_id]
        for i, (r, c) in enumerate(slot.cells):
            if i < len(answer):
                filled[r][c] = answer[i]

    for row in filled:
        line = " "
        for cell in row:
            if cell == "#":
                line += "██"
            else:
                line += f" {cell}"
        print(line)

    # Show all-time summary
    print()
    print("=" * 60)
    print("  ALL RESULTS")
    print("=" * 60)
    print_summary()
    print()


if __name__ == "__main__":
    main()