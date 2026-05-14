"""
Universal puzzle loader with automatic format detection.

Supports JSON (.json) and AcrossLite (.puz) formats.
"""

import os
from src.solver.puzzle import Puzzle


def load_puzzle(filepath: str) -> Puzzle:
    """
    Load a crossword puzzle from any supported format.

    Supported formats:
        .json — Simple JSON format (easiest for hand-crafted test puzzles)
        .puz  — Standard AcrossLite format (most crossword databases)

    Args:
        filepath: Path to the puzzle file.

    Returns:
        A Puzzle object ready for solving.

    Raises:
        ValueError: If the file format is not supported.
        FileNotFoundError: If the file doesn't exist.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Puzzle file not found: {filepath}")

    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".json":
        from src.solver.json_loader import load_from_json
        return load_from_json(filepath)

    elif ext == ".puz":
        from src.solver.puz_loader import load_from_puz
        return load_from_puz(filepath)

    else:
        supported = [".json", ".puz"]
        raise ValueError(
            f"Unsupported file format: '{ext}'. "
            f"Supported formats: {supported}. "
            f"To add a new format, create a loader in src/solver/ "
            f"and register it in loader.py."
        )