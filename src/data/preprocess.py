"""
Clean and preprocess crossword clue-answer pairs.
"""

from collections import Counter


def clean_answer(answer: str) -> str:
    """
    Normalize an answer string.
    - Uppercase (crossword convention)
    - Strip whitespace
    - Remove any non-alphabetic characters
    """
    return "".join(c for c in answer.upper().strip() if c.isalpha())


def clean_clue(clue: str) -> str:
    """
    Normalize a clue string.
    - Strip whitespace
    - Collapse multiple spaces
    """
    return " ".join(clue.strip().split())


def preprocess_dataset(dataset, subset_size: int = None) -> list[dict]:
    """
    Clean and structure the raw dataset into a list of records.

    Each record has:
        - clue: cleaned clue text
        - answer: cleaned answer (uppercase, letters only)
        - answer_length: number of letters in the answer

    Args:
        dataset: HuggingFace dataset with 'question' and 'answer' columns.
        subset_size: If set, only process this many entries (for development).

    Returns:
        List of cleaned records.
    """
    train = dataset["train"]
    n = min(subset_size, len(train)) if subset_size else len(train)

    records = []
    skipped = 0

    for i in range(n):
        raw_clue = train[i]["clue"]
        raw_answer = train[i]["answer"]

        # Skip entries with missing data
        if raw_clue is None or raw_answer is None:
            skipped += 1
            continue

        clue = clean_clue(raw_clue)
        answer = clean_answer(raw_answer)

        # Skip entries with empty clues or answers
        if not clue or not answer:
            skipped += 1
            continue

        records.append({
            "clue": clue,
            "answer": answer,
            "answer_length": len(answer),
        })

    print(f"Preprocessed {len(records):,} records ({skipped} skipped)")
    return records


def get_length_distribution(records: list[dict]) -> dict:
    """
    Return a count of answers by length.
    Useful for understanding the data.
    """
    lengths = [r["answer_length"] for r in records]
    return dict(sorted(Counter(lengths).items()))