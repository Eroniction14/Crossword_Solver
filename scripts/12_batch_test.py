"""
Script 12: Batch solve all puzzles and generate a benchmark report.

Runs the agent on every puzzle in the puzzles/ folder and
saves results to results/evaluations/.

Run from project root:
    python scripts/12_batch_test.py
"""

import sys
import os
import glob
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import cfg
from results import save_result, print_summary
from src.solver.loader import load_puzzle
from src.retrieval.retriever import Retriever
from src.llm.generator import LLMGenerator
from src.solver.agent import CrosswordAgent


def main():
    print("=" * 60)
    print("  BATCH CROSSWORD SOLVER")
    print("=" * 60)
    print()

    # Load shared components once
    print(f"Loading retriever from {cfg.retrieval.index_dir}...")
    retriever = Retriever.load(cfg.retrieval.index_dir, model_name=cfg.retrieval.model_name)
    print()

    print(f"Loading LLM ({cfg.llm.model})...")
    llm = LLMGenerator(model=cfg.llm.model, max_workers=cfg.llm.max_workers)
    print()

    # Find all puzzle files
    puzzle_dir = cfg.paths.puzzles_dir
    puzzle_files = sorted(glob.glob(os.path.join(puzzle_dir, "*.json")))

    if not puzzle_files:
        print(f"No puzzle files found in {puzzle_dir}/")
        return

    print(f"Found {len(puzzle_files)} puzzles to solve:")
    for f in puzzle_files:
        print(f"  {os.path.basename(f)}")
    print()

    # Solve each puzzle
    results = []
    for i, filepath in enumerate(puzzle_files, 1):
        filename = os.path.basename(filepath)
        print("=" * 60)
        print(f"  PUZZLE {i}/{len(puzzle_files)}: {filename}")
        print("=" * 60)
        print()

        try:
            puzzle = load_puzzle(filepath)
            print(f"  {puzzle.title} ({puzzle.rows}x{puzzle.cols}, "
                  f"{len(puzzle.slots)} slots)")
            print()

            agent = CrosswordAgent(
                puzzle=puzzle,
                retriever=retriever,
                llm=llm,
                max_passes=cfg.solver.max_passes,
            )
            result = agent.solve()

            # Save result
            save_result(puzzle, result)

            metrics = result["metrics"]
            status = "PERFECT" if metrics["perfect"] else f"{metrics['correct_words']}/{metrics['total_words']}"
            print(f"\n  Result: {status} in {result['elapsed']:.1f}s")

            results.append({
                "filename": filename,
                "title": puzzle.title,
                "metrics": metrics,
                "elapsed": result["elapsed"],
                "passes": result["passes_used"],
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "filename": filename,
                "title": filename,
                "metrics": None,
                "elapsed": 0,
                "passes": 0,
                "error": str(e),
            })

        print()

        # Wait between puzzles to avoid API rate limits (50 req/min)
        if i < len(puzzle_files):
            print("  Waiting 15s to avoid rate limits...")
            time.sleep(15)
            print()

    # Summary
    print("=" * 60)
    print("  BATCH RESULTS")
    print("=" * 60)
    print()
    print(f"  {'Puzzle':<40} {'Words':>8} {'Letters':>8} {'Time':>6} {'Pass':>5}")
    print(f"  {'-'*40} {'-'*8} {'-'*8} {'-'*6} {'-'*5}")

    total_correct = 0
    total_words = 0
    total_time = 0
    perfect_count = 0

    for r in results:
        if r["metrics"]:
            m = r["metrics"]
            total_correct += m["correct_words"]
            total_words += m["total_words"]
            total_time += r["elapsed"]
            if m["perfect"]:
                perfect_count += 1
            print(f"  {r['title']:<40} "
                  f"{m['correct_words']:>3}/{m['total_words']:<3}  "
                  f"{m['letter_accuracy']*100:>5.1f}%  "
                  f"{r['elapsed']:>5.1f}s "
                  f"{r['passes']:>4}")
        else:
            print(f"  {r['title']:<40} {'ERROR':>8}")

    print(f"  {'-'*40} {'-'*8} {'-'*8} {'-'*6} {'-'*5}")

    solved = len([r for r in results if r["metrics"]])
    avg_accuracy = total_correct / max(total_words, 1)
    avg_time = total_time / max(solved, 1)

    print(f"  {'TOTAL':<40} "
          f"{total_correct:>3}/{total_words:<3}  "
          f"{avg_accuracy*100:>5.1f}%  "
          f"{avg_time:>5.1f}s "
          f"  {perfect_count}/{solved}")
    print()

    # All-time results
    print("=" * 60)
    print("  ALL-TIME RESULTS")
    print("=" * 60)
    print_summary()


if __name__ == "__main__":
    main()