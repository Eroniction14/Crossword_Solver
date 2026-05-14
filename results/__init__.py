"""
Results logger.

Saves solve results to results/evaluations/ as JSON files.
Each solve gets a timestamped file with full details:
  - Puzzle info
  - Solution and accuracy
  - Per-clue analysis (strategy, source, confidence)
  - Timing breakdown

Usage:
    from results import save_result
    save_result(puzzle, result)

    from results import load_results
    all_results = load_results()  # Load all saved results
"""

import os
import json
from datetime import datetime


EVAL_DIR = "results/evaluations"
LOG_DIR = "results/logs"


def save_result(puzzle, result: dict, notes: str = ""):
    """
    Save a solve result to results/evaluations/.

    Args:
        puzzle: The Puzzle object that was solved
        result: The dict returned by agent.solve()
        notes: Optional notes about this run
    """
    os.makedirs(EVAL_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    puzzle_name = puzzle.title.replace(" ", "_").replace("-", "_").lower()
    filename = f"{timestamp}_{puzzle_name}.json"

    metrics = result["metrics"]

    record = {
        "timestamp": datetime.now().isoformat(),
        "puzzle": {
            "title": puzzle.title,
            "rows": puzzle.rows,
            "cols": puzzle.cols,
            "total_slots": len(puzzle.slots),
            "total_crossings": len(puzzle.crossings),
        },
        "results": {
            "word_accuracy": metrics["word_accuracy"],
            "letter_accuracy": metrics["letter_accuracy"],
            "correct_words": metrics["correct_words"],
            "total_words": metrics["total_words"],
            "perfect": metrics["perfect"],
            "conflicts": metrics["conflicts"],
            "passes_used": result["passes_used"],
            "elapsed_seconds": round(result["elapsed"], 1),
        },
        "analyses": {
            slot_id: {
                "clue": a.clue,
                "clue_type": a.clue_type,
                "strategy": a.strategy,
                "source": a.source,
                "confidence": round(a.confidence, 3),
                "answer": a.answer,
                "expected": puzzle.slots[slot_id].answer if puzzle.slots.get(slot_id) else "",
                "correct": a.answer == (puzzle.slots[slot_id].answer if puzzle.slots.get(slot_id) else ""),
            }
            for slot_id, a in result["analyses"].items()
        },
        "solution": result["solution"],
        "notes": notes,
    }

    path = os.path.join(EVAL_DIR, filename)
    with open(path, "w") as f:
        json.dump(record, f, indent=2)

    print(f"  Result saved: {path}")
    return path


def load_results():
    """Load all saved results and return as a list of dicts."""
    if not os.path.exists(EVAL_DIR):
        return []

    results = []
    for f in sorted(os.listdir(EVAL_DIR)):
        if f.endswith(".json"):
            path = os.path.join(EVAL_DIR, f)
            with open(path) as fh:
                results.append(json.load(fh))

    return results


def print_summary():
    """Print a summary table of all saved results."""
    results = load_results()
    if not results:
        print("No results saved yet.")
        return

    print(f"\n{'Puzzle':<35} {'Words':>8} {'Letters':>8} {'Time':>6} {'Pass':>5} {'Perfect':>8}")
    print("-" * 75)

    for r in results:
        p = r["puzzle"]
        m = r["results"]
        print(f"{p['title']:<35} "
              f"{m['correct_words']}/{m['total_words']:>3}   "
              f"{m['letter_accuracy']*100:>5.1f}%  "
              f"{m['elapsed_seconds']:>5.1f}s "
              f"{m['passes_used']:>4}  "
              f"{'YES' if m['perfect'] else 'NO':>7}")

    total = len(results)
    perfect = sum(1 for r in results if r["results"]["perfect"])
    avg_time = sum(r["results"]["elapsed_seconds"] for r in results) / total
    avg_accuracy = sum(r["results"]["word_accuracy"] for r in results) / total

    print("-" * 75)
    print(f"{'TOTAL: ' + str(total) + ' puzzles':<35} "
          f"{'avg':>8} "
          f"{avg_accuracy*100:>5.1f}%  "
          f"{avg_time:>5.1f}s "
          f"{'':>5} "
          f"{perfect}/{total:>6}")