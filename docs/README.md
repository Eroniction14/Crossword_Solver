# Crossword Solving Agent

An AI-powered crossword puzzle solver that combines FAISS retrieval, Claude LLM reasoning, and belief propagation to solve NYT crossword puzzles.

## Overview

This system uses a three-machine architecture to solve crossword puzzles:

1. **The Guesser** — FAISS retrieval over 1M+ clue-answer pairs, plus Claude LLM for novel clues
2. **The Referee** — Loopy belief propagation propagates letter constraints across crossing slots
3. **The Fixer** — Multi-pass re-querying with crossing letter hints and local search

The intelligent agent classifies each clue by type (fill-in-blank, trivia, wordplay, etc.), selects the optimal solving strategy, and explains its reasoning throughout.

## Results

| Puzzle | Size | Words | Accuracy | Time |
|---|---|---|---|---|
| NYT Mini May 7 | 5×5 | 10/10 | 100% | ~12s |
| NYT Mini May 12 | 5×5 | 10/10 | 100% | ~12s |
| NYT Monday May 11 | 15×15 | 76/76 | 100% | ~30s |

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Crossword Agent                 │
│  (Clue classification, strategy selection)       │
├──────────────┬──────────────┬────────────────────┤
│   FAISS      │   Claude     │   Belief           │
│   Retrieval  │   LLM        │   Propagation      │
│   (1M clues) │   (parallel) │   (constraint sat.) │
├──────────────┴──────────────┴────────────────────┤
│              Semantic Verification                │
│  (Retrieval + LLM scoring of answers)            │
└─────────────────────────────────────────────────┘
```

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the web UI)
- Anthropic API key

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd NY-AI-agent

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Set up API key
# Create .env file with: ANTHROPIC_API_KEY=your-key-here

# Download the sentence-transformer model locally
python scripts/11_download_model.py

# Download and preprocess data
python scripts/01_download_data.py
python scripts/02_preprocess_data.py

# Build the FAISS index (takes ~25 min on CPU)
python scripts/10_build_1m_index.py
```

### Running the Solver (CLI)

```bash
python scripts/09_solve_agent.py
```

### Running the Web UI

```bash
# Terminal 1: Start the backend
python server.py

# Terminal 2: Start the frontend
cd crossword-ui
npm install
npm start
```

Open `http://localhost:3000` in your browser.

## Project Structure

```
NY-AI agent/
├── config/
│   ├── __init__.py          # Config loader
│   └── default.yaml         # All settings
├── src/
│   ├── data/                # Data download and preprocessing
│   │   ├── download.py      # HuggingFace dataset download
│   │   └── preprocess.py    # Clue/answer cleaning
│   ├── retrieval/           # FAISS-based candidate retrieval
│   │   ├── encoder.py       # Sentence-transformer embeddings
│   │   ├── index.py         # FAISS index wrapper
│   │   └── retriever.py     # High-level retrieval interface
│   ├── llm/                 # Claude API integration
│   │   └── generator.py     # Parallel candidate generation
│   ├── solver/              # Core solving components
│   │   ├── agent.py         # Intelligent solving agent
│   │   ├── belief_propagation.py  # BP constraint solver
│   │   ├── puzzle.py        # Data structures
│   │   ├── grid_analyzer.py # Grid slot/crossing detection
│   │   ├── json_loader.py   # JSON puzzle parser
│   │   ├── puz_loader.py    # .puz file parser
│   │   └── loader.py        # Universal format detector
│   └── verification/        # Answer validation
│       └── verifier.py      # Semantic verification
├── scripts/                 # Pipeline scripts (01-11)
├── data/
│   ├── raw/                 # Raw CrosswordQA dataset
│   ├── processed/           # Cleaned, deduplicated data
│   └── indexes/             # FAISS indexes (v1: 6.4M, v2: 1M)
├── models/
│   └── sentence_transformer/ # Local model files
├── puzzles/                 # Puzzle JSON files
├── results/
│   └── evaluations/         # Saved solve results
├── tests/                   # Unit tests
├── crossword-ui/            # React web application
│   └── src/
│       ├── CrosswordAgentUI.js
│       └── components/      # UI components
├── server.py                # Flask API server
└── docs/                    # Documentation
```

## Data Pipeline

```
01_download_data.py     → data/raw/           (6.8M raw records)
02_preprocess_data.py   → data/processed/     (5.9M clean, deduplicated)
04_build_index.py       → data/indexes/v1     (50k FAISS index)
10_build_1m_index.py    → data/indexes/v2     (1M FAISS index, active)
```

## Configuration

All settings are in `config/default.yaml`:

```yaml
retrieval:
  index_dir: "data/indexes/v2"
  model_name: "models/sentence_transformer"
  confidence_threshold: 0.85

llm:
  model: "claude-sonnet-4-6"
  temperature: 0
  max_workers: 10

solver:
  max_passes: 3
  bp_max_iterations: 15
```

## How It Works

### 1. Clue Classification

The agent classifies each clue into categories:
- **fill_in_blank** — "A-___ (top-quality)" → LLM first
- **long_phrase** — 11+ letters → LLM first
- **abbreviation** — "Abbr." indicator → retrieval only
- **foreign** — "French for..." → both sources
- **wordplay** — "?" indicator → both sources
- **definition** — standard clues → retrieval (short) or both (long)

### 2. Candidate Generation

- **FAISS Retrieval**: Encodes the clue with a sentence-transformer, searches 1M clue-answer pairs by vector similarity
- **Claude LLM**: Prompts Claude with the clue and length constraint, parses response into candidates
- **Parallel execution**: All LLM calls fire simultaneously (10 threads)

### 3. Belief Propagation

Loopy BP propagates letter-level constraints across all crossing slots:
- Each slot starts with candidate beliefs from retrieval/LLM scores
- Slots exchange messages about expected letters at crossings
- After 15 iterations, pick the highest-belief candidate per slot

### 4. Multi-Pass Re-querying

If conflicts remain after BP:
- Identify weak slots (low confidence, involved in conflicts)
- Extract known crossing letters from confident neighbors
- Re-query Claude with letter hints (e.g., "8 letters, pattern: _W_N_O_T")
- Re-run BP with expanded candidates

### 5. Semantic Verification

After solving, verify each answer:
- Check if the answer appears in retrieval results for its clue
- Flag answers with low verification scores

## Testing

```bash
python -m pytest tests/ -v
```

## Technologies

- **Python 3.13** — Core solver
- **FAISS** — Vector similarity search
- **Sentence-Transformers** — Clue embedding (all-MiniLM-L6-v2)
- **Anthropic Claude API** — LLM reasoning
- **Flask** — API server with SSE streaming
- **React** — Web UI with real-time visualization
- **NumPy** — Belief propagation math

## Dataset

CrosswordQA from HuggingFace (`albertxu/CrosswordQA`):
- 6.4M+ clue-answer pairs from historical crossword puzzles
- Preprocessed to 5.9M unique records after deduplication
- 1M subset used for the active FAISS index

## References

- Berkeley Crossword Solver (BCS): [arxiv.org/abs/2205.09665](https://arxiv.org/abs/2205.09665)
- CrosswordQA Dataset: [huggingface.co/datasets/albertxu/CrosswordQA](https://huggingface.co/datasets/albertxu/CrosswordQA)