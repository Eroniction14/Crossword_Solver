"""
Script 05: Test the retrieval system interactively.

Type crossword clues and see candidate answers ranked by similarity.

Run from the project root:
    python scripts/05_test_retrieval.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.retrieval.retriever import Retriever

INDEX_DIR = "data/indexes/v1"
MODEL_NAME = "all-MiniLM-L6-v2"


def print_results(results: list[dict], max_show: int = 10):
    """Pretty-print search results."""
    if not results:
        print("  No matches found. Try without a length filter.")
        return

    for i, r in enumerate(results[:max_show], 1):
        print(f"  {i:2d}. {r['answer']:<15} (score: {r['score']:.3f}, "
              f"{r['answer_length']} letters)")
        print(f"      matched clue: \"{r['clue']}\"")


def main():
    print("=" * 60)
    print("STEP 5: Interactive Retrieval Testing")
    print("=" * 60)
    print()

    # Load the pre-built retriever
    retriever = Retriever.load(INDEX_DIR, model_name=MODEL_NAME)
    print()

    # --- Run some benchmark clues first ---
    print("=" * 60)
    print("BENCHMARK TESTS")
    print("=" * 60)
    print()

    benchmarks = [
        ("Capital of France", 5),
        ("Man's best friend", 3),
        ("Coarse fabric", 5),
        ("Part of the eye", 4),
        ("Italian for eight", 4),
        ("Statue of Liberty feature", 5),
        ("Goes with peanut butter", 5),
        ("Shakespeare's theatre", 5),
    ]

    for clue, length in benchmarks:
        print(f"CLUE: \"{clue}\" ({length} letters)")
        print("-" * 50)
        results = retriever.get_candidates(clue, answer_length=length, top_k=5)
        print_results(results, max_show=5)
        print()

    # --- Interactive mode ---
    print("=" * 60)
    print("INTERACTIVE MODE")
    print("=" * 60)
    print()
    print("Type a crossword clue to search. Add a number at the end")
    print("to filter by answer length.")
    print()
    print("Examples:")
    print("  > Capital of France 5")
    print("  > Tree type")
    print("  > Famous painter 7")
    print("  > quit")
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if not user_input:
            continue

        # Check if last word is a number (answer length filter)
        parts = user_input.rsplit(" ", 1)
        answer_len = None
        clue_text = user_input

        if len(parts) == 2 and parts[1].isdigit():
            clue_text = parts[0]
            answer_len = int(parts[1])

        results = retriever.get_candidates(
            clue_text, answer_length=answer_len, top_k=10
        )

        print()
        print_results(results)
        print()


if __name__ == "__main__":
    main()