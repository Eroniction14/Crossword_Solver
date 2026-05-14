# API Documentation

## Base URL

```
http://localhost:5000/api
```

## Endpoints

### GET /api/puzzles

List all available puzzle files in the `puzzles/` directory.

**Response:**
```json
[
  {
    "filename": "nyt_daily_2026_05_11.json",
    "title": "NYT Daily - May 11, 2026 (Monday)",
    "rows": 15,
    "cols": 15
  },
  {
    "filename": "nyt_mini_2026_05_07.json",
    "title": "NYT Mini - May 7, 2026",
    "rows": 5,
    "cols": 5
  }
]
```

### GET /api/puzzle/:filename

Load a specific puzzle file with full grid and clue data.

**Parameters:**
- `filename` — Name of the puzzle file (e.g., `nyt_daily_2026_05_11.json`)

**Response:**
```json
{
  "title": "NYT Daily - May 11, 2026 (Monday)",
  "rows": 15,
  "cols": 15,
  "grid": [["#", ".", ".", ...], ...],
  "slots": {
    "1-across": {
      "number": 1,
      "direction": "across",
      "clue": "___ Spiegel (German magazine)",
      "length": 3,
      "cells": [[0, 0], [0, 1], [0, 2]],
      "answer": "DER"
    }
  },
  "crossings": 188
}
```

### GET /api/solve/:filename

Solve a puzzle and stream the agent's thinking as Server-Sent Events (SSE).

**Parameters:**
- `filename` — Name of the puzzle file

**Response:** SSE stream with events:

```
data: {"type": "think", "message": "Analyzing puzzle..."}

data: {"type": "slot_done", "slot_id": "1-across", "answer": "DER", "source": "retrieval"}

data: {"type": "slot_confident", "slot_id": "1-across", "answer": "DER"}

data: {"type": "slot_correction", "slot_id": "30-across", "old_answer": "GEESE", "answer": "POACH"}

data: {"type": "final", "solution": {...}, "metrics": {...}, "passes_used": 2, "elapsed": 30.5, "analyses": {...}}
```

**Event types:**

| Type | Description | Fields |
|---|---|---|
| `think` | Agent reasoning | `message` |
| `action` | Action being taken | `message` |
| `result` | Completed result | `message` |
| `decision` | Strategic decision | `message` |
| `slot_done` | Answer placed | `slot_id`, `answer`, `source` |
| `slot_confident` | Answer confirmed | `slot_id`, `answer` |
| `slot_correction` | BP changed answer | `slot_id`, `old_answer`, `answer` |
| `final` | Complete solution | `solution`, `metrics`, `passes_used`, `elapsed`, `analyses` |

**Final event metrics:**
```json
{
  "word_accuracy": 1.0,
  "letter_accuracy": 1.0,
  "correct_words": 76,
  "total_words": 76,
  "perfect": true,
  "conflicts": 0
}
```

### POST /api/upload

Upload a `.puz` or `.json` puzzle file.

**Request:** Multipart form data with `file` field.

**Response (success):**
```json
{
  "filename": "my_puzzle.json",
  "title": "My Custom Puzzle",
  "rows": 15,
  "cols": 15,
  "slots": 76
}
```

**Response (error):**
```json
{
  "error": "Failed to parse: Invalid grid format"
}
```

## Puzzle JSON Format

To create a puzzle manually, use this format:

```json
{
  "title": "My Puzzle",
  "author": "Author Name",
  "grid": [
    ["#", "#", ".", ".", "."],
    ["#", ".", ".", ".", "."],
    [".", ".", ".", ".", "."],
    [".", ".", ".", ".", "#"],
    [".", ".", ".", "#", "#"]
  ],
  "clues": {
    "across": {
      "1": "First across clue",
      "5": "Second across clue"
    },
    "down": {
      "1": "First down clue",
      "2": "Second down clue"
    }
  },
  "answers": {
    "across": {
      "1": "ANS",
      "5": "REPLY"
    },
    "down": {
      "1": "ARROW",
      "2": "NERVE"
    }
  }
}
```

**Grid format:**
- `"#"` — Black cell
- `"."` — Empty white cell

**Clue numbering:**
Clue numbers must match the standard crossword numbering (cells that start across or down slots).

**Answers (optional):**
If provided, used for accuracy evaluation. Omit for blind solving.