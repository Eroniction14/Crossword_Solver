# System Architecture

## High-Level Design

The crossword solver follows a three-stage pipeline with an intelligent agent orchestrating the process.

```
Input (puzzle) → Agent → Candidates → BP Solver → Verification → Output (solution)
                  │
                  ├── Clue Classification
                  ├── Strategy Selection  
                  ├── FAISS Retrieval (parallel)
                  ├── Claude LLM (parallel)
                  ├── Belief Propagation
                  ├── Multi-Pass Re-querying
                  └── Semantic Verification
```

## Component Details

### 1. Puzzle Parser (`src/solver/`)

Handles input format detection and conversion to the universal `Puzzle` data structure.

**Files:**
- `puzzle.py` — Core data structures (Puzzle, Slot, Crossing)
- `grid_analyzer.py` — Computes slots and crossings from a 2D grid
- `json_loader.py` — Parses JSON puzzle files
- `puz_loader.py` — Parses AcrossLite .puz files
- `loader.py` — Universal loader with auto-detection

**Data flow:**
```
puzzle.json → json_loader → grid_analyzer → Puzzle object
puzzle.puz  → puz_loader  → grid_analyzer → Puzzle object
```

### 2. Candidate Generation (`src/retrieval/`, `src/llm/`)

Two complementary sources produce ranked answer candidates for each clue.

**FAISS Retrieval:**
- Encodes clue text into a 384-dim vector using sentence-transformer
- Searches 1M pre-indexed clue vectors for nearest neighbors
- Returns top-k candidates ranked by cosine similarity
- Fast (~0.1s per query) but limited to clues similar to training data

**Claude LLM:**
- Prompts Claude with clue text and length constraint
- Parses response into ranked candidates
- Supports known letter constraints for re-querying
- Accurate for novel clues but slower (~3s per query)
- Parallelized with ThreadPoolExecutor (10 concurrent calls)

**Merge strategy:**
- Candidates from both sources are merged
- LLM scores boosted by 1.1x (reasoning advantage)
- Duplicates resolved by keeping higher score

### 3. Belief Propagation (`src/solver/belief_propagation.py`)

Loopy BP finds globally consistent answers across crossing constraints.

**Algorithm:**
1. Initialize beliefs from candidate scores (softmax normalization)
2. For each crossing, compute compatibility messages
3. Update beliefs by multiplying incoming messages
4. Apply damping (0.5 blend with previous messages)
5. Repeat for 15 iterations or until convergence
6. Extract solution: highest-belief candidate per slot

**Key parameters:**
- `max_iterations: 15` — sufficient for most puzzles
- `damping: 0.5` — balances speed and stability
- `convergence_threshold: 0.001` — early stopping criterion

### 4. Multi-Pass Re-querying

When BP cannot resolve all conflicts:

1. Identify weak slots (low confidence, involved in conflicts)
2. Extract known crossing letters from confident neighbors
3. Re-query Claude with letter pattern hints
4. Merge new candidates and re-run BP
5. Repeat up to 3 passes

This is the key innovation — crossing letters from confident slots bootstrap uncertain ones.

### 5. Semantic Verification (`src/verification/`)

Post-solve validation using two methods:

**Retrieval scoring:**
- Search FAISS for the clue
- Check if the proposed answer appears in results
- Score based on rank (1st = 1.0, 50th = low)

**LLM scoring (optional):**
- Ask Claude to rate clue-answer compatibility (0.0 to 1.0)
- Used for flagged answers when retrieval score is low

### 6. Intelligent Agent (`src/solver/agent.py`)

The agent orchestrates the full pipeline with strategic decisions:

**Clue classification:**
- fill_in_blank, long_phrase, abbreviation, foreign, wordplay, trivia, definition

**Strategy selection:**
- `llm_first` — for fill-in-blank and long phrases
- `retrieval_only` — for short definitions and abbreviations
- `both` — for wordplay, foreign, trivia, and uncertain clues

**Confidence upgrade:**
- After retrieval, slots with score < 0.85 are upgraded to also use LLM
- This catches clues that retrieval handles poorly

## Web Architecture

```
React UI (localhost:3000)
    │
    ├── GET /api/puzzles          → List available puzzles
    ├── GET /api/puzzle/:file     → Load puzzle data
    ├── GET /api/solve/:file      → SSE stream of solve events
    └── POST /api/upload          → Upload .puz or .json file
    │
Flask Server (localhost:5000)
    │
    ├── CrosswordAgent            → Orchestrates solving
    ├── Retriever                 → FAISS search
    ├── LLMGenerator              → Claude API (parallel)
    └── BeliefPropagationSolver   → Constraint satisfaction
```

**Server-Sent Events (SSE):**
The solve endpoint streams events in real-time:
- `slot_done` — Answer placed on grid
- `slot_confident` — Answer confirmed (cell turns green)
- `slot_correction` — BP changed an answer (cell flashes)
- `think/action/result/decision` — Agent reasoning log
- `final` — Complete solution with metrics

## Performance

| Component | Time | Notes |
|---|---|---|
| FAISS retrieval (76 clues) | ~10s | 1M index, CPU |
| LLM parallel (51 calls) | ~12s | 10 concurrent threads |
| Belief propagation | <1s | 15 iterations, 188 crossings |
| Re-query pass | ~3s | 8-14 slots, parallel |
| Verification | ~5s | Retrieval-based scoring |
| **Total** | **~30s** | **Full 15×15 puzzle** |