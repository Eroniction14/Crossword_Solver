"""
Crossword solving agent with intelligent strategy selection and parallel LLM calls.

Classifies each clue by type (fill-in-blank, trivia, wordplay, etc.),
selects the optimal candidate source (retrieval, LLM, or both), and
solves using multi-pass belief propagation with crossing letter hints.
"""

import time
import re
from dataclasses import dataclass, field
from src.solver.puzzle import Puzzle
from src.retrieval.retriever import Retriever
from src.llm.generator import LLMGenerator
from src.solver.belief_propagation import BeliefPropagationSolver
from src.verification.verifier import SemanticVerifier


@dataclass
class ClueAnalysis:
    """Analysis result for a single clue including type, strategy, and outcome."""
    slot_id: str
    clue: str
    length: int
    clue_type: str
    strategy: str
    reasoning: str
    confidence: float = 0.0
    answer: str = ""
    source: str = ""


@dataclass
class PassReport:
    """Summary of a single solving pass."""
    pass_number: int
    word_accuracy: float
    letter_accuracy: float
    conflicts: int
    total_slots: int
    correct_slots: int
    weak_slots: list = field(default_factory=list)
    reasoning: str = ""


class CrosswordAgent:
    """Intelligent crossword solving agent.

    Orchestrates the full solving pipeline: clue classification,
    candidate generation (retrieval + LLM), belief propagation,
    and multi-pass re-querying with crossing letter hints.

    Args:
        puzzle: Parsed Puzzle object to solve.
        retriever: FAISS-based retriever for candidate lookup.
        llm: Claude API generator for LLM candidates.
        max_passes: Maximum number of re-query passes.
    """

    def __init__(self, puzzle: Puzzle, retriever: Retriever,
                 llm: LLMGenerator, max_passes: int = 3):
        self.puzzle = puzzle
        self.retriever = retriever
        self.llm = llm
        self.verifier = SemanticVerifier(llm=llm, retriever=retriever,confidence_threshold=0.15)
        self.max_passes = max_passes
        self.log = []
        self.analyses = {}

    # --- Event logging methods (also used by server for SSE streaming) ---

    def _think(self, message: str):
        """Log a reasoning/analysis event."""
        self.log.append({"type": "thought", "message": message})
        print(f"  [THINK] {message}")

    def _action(self, message: str):
        """Log an action being taken."""
        self.log.append({"type": "action", "message": message})
        print(f"  [ACT  ] {message}")

    def _result(self, message: str):
        """Log a completed result."""
        self.log.append({"type": "result", "message": message})
        print(f"  [DONE ] {message}")

    def _decision(self, message: str):
        """Log a strategic decision."""
        self.log.append({"type": "decision", "message": message})
        print(f"  [PLAN ] {message}")

    def _slot_update(self, slot_id: str, answer: str, source: str):
        """Emit a slot answer update for live UI grid filling."""
        self.log.append({"type": "slot_done", "message": f"{slot_id}: {answer}",
                         "slot_id": slot_id, "answer": answer, "source": source})
        print(f"  [FILL ] {slot_id}: {answer} ({source})")

    def _slot_confident(self, slot_id: str, answer: str):
        """Emit a confident answer event (turns cell green in UI)."""
        self.log.append({"type": "slot_confident", "message": f"{slot_id}: {answer} (confirmed)",
                         "slot_id": slot_id, "answer": answer})
        print(f"  [CONF ] {slot_id}: {answer}")

    def _slot_correction(self, slot_id: str, old_answer: str, new_answer: str):
        """Emit a BP correction event (flashes cell in UI)."""
        self.log.append({"type": "slot_correction", "message": f"{slot_id}: {old_answer} -> {new_answer}",
                         "slot_id": slot_id, "old_answer": old_answer, "answer": new_answer})
        print(f"  [FIX  ] {slot_id}: {old_answer} -> {new_answer}")

    # --- Clue classification ---

    def classify_clue(self, slot_id, clue, length):
        """Classify a clue and select the solving strategy.

        Returns:
            ClueAnalysis with clue_type and strategy fields set.
        """
        clue_type = self._detect_clue_type(clue, length)
        strategy = self._choose_strategy(clue_type, length)
        reasoning = self._explain_strategy(clue, clue_type, strategy, length)
        return ClueAnalysis(
            slot_id=slot_id, clue=clue, length=length,
            clue_type=clue_type, strategy=strategy, reasoning=reasoning,
        )

    def _detect_clue_type(self, clue, length):
        """Detect the clue type based on textual patterns and answer length.

        Returns one of: fill_in_blank, long_phrase, abbreviation,
        foreign, wordplay, trivia, definition.
        """
        cl = clue.lower()
        if "___" in clue or "_ _ _" in clue:
            return "fill_in_blank"
        if length >= 11:
            return "long_phrase"
        if any(m in cl for m in ["abbr.", "abbr", "in brief", "for short", ": abbr"]):
            return "abbreviation"
        if any(m in cl for m in ["french for", "spanish for", "italian for",
                                  "german for", "in french", "in spanish",
                                  "l'", "la ___", "le ___", "french", "german", "spanish"]):
            return "foreign"
        if any(m in cl for m in ["?", "perhaps", "maybe", "say", "so to speak",
                                  "in a way", "of sorts"]):
            return "wordplay"
        if any(m in cl for m in ["star", "author", "director", "capital of",
                                  "city in", "president", "river in", "mountain"]):
            return "trivia"
        return "definition"

    def _choose_strategy(self, clue_type, length):
        """Map clue type to candidate generation strategy.

        Returns one of: llm_first, retrieval_only, both.
        """
        if clue_type == "fill_in_blank": return "llm_first"
        if clue_type == "long_phrase": return "llm_first"
        if clue_type == "wordplay": return "both"
        if clue_type == "abbreviation": return "retrieval_only"
        if clue_type == "foreign": return "both"
        if clue_type == "trivia": return "both"
        if length <= 5: return "retrieval_only"
        return "both"

    def _explain_strategy(self, clue, clue_type, strategy, length):
        """Generate a brief explanation of the strategy choice."""
        return f"{clue_type} | {strategy}"

    # --- Main solving pipeline ---

    def solve(self):
        """Run the full solving pipeline.

        Pipeline:
            1. Classify all clues by type
            2a. Run FAISS retrieval for all clues
            2b. Run parallel LLM calls for eligible clues
            3. Merge candidates and run belief propagation
            4. Re-query weak slots with crossing letter hints
            5. Local search for remaining conflicts

        Returns:
            Dict with 'solution', 'metrics', 'passes_used', 'elapsed',
            'log', and 'analyses' keys.
        """
        start_time = time.time()

        self._think(f"Analyzing puzzle: {self.puzzle.title}")
        self._think(f"Grid: {self.puzzle.rows}x{self.puzzle.cols}, "
                    f"{len(self.puzzle.slots)} slots, "
                    f"{len(self.puzzle.crossings)} crossings")

        # Phase 1: Classify all clues
        self._think("Phase 1: Classifying all clues...")
        type_counts = {}
        strategy_counts = {}
        for slot_id, slot in self.puzzle.slots.items():
            analysis = self.classify_clue(slot_id, slot.clue, slot.length)
            self.analyses[slot_id] = analysis
            type_counts[analysis.clue_type] = type_counts.get(analysis.clue_type, 0) + 1
            strategy_counts[analysis.strategy] = strategy_counts.get(analysis.strategy, 0) + 1

        self._result(f"Clue types: {dict(sorted(type_counts.items()))}")
        self._result(f"Strategies: {dict(sorted(strategy_counts.items()))}")

        llm_calls = sum(1 for a in self.analyses.values()
                        if a.strategy in ("llm_only", "llm_first", "both"))
        retrieval_only = sum(1 for a in self.analyses.values()
                             if a.strategy == "retrieval_only")
        self._decision(f"LLM for {llm_calls} clues, retrieval-only for {retrieval_only}. "
                       f"Saves {retrieval_only} API calls.")

        # Phase 2a: FAISS retrieval (fast, sequential)
        self._think("Phase 2a: Running retrieval for all clues...")
        t0 = time.time()

        retrieval_results = {}
        for slot_id, slot in self.puzzle.slots.items():
            retrieval_results[slot_id] = self.retriever.get_candidates(
                clue=slot.clue, answer_length=slot.length, top_k=50
            )
            if retrieval_results[slot_id]:
                top = retrieval_results[slot_id][0]["answer"]
                self._slot_update(slot_id, top, "retrieval")

        self._result(f"Retrieval done in {time.time()-t0:.1f}s")

        # Upgrade low-confidence retrieval-only slots to also use LLM
        CONFIDENCE_THRESHOLD = 0.85
        upgraded = 0
        for slot_id, a in self.analyses.items():
            if a.strategy == "retrieval_only":
                top_score = retrieval_results[slot_id][0]["score"] if retrieval_results[slot_id] else 0
                if top_score < CONFIDENCE_THRESHOLD:
                    a.strategy = "both"
                    upgraded += 1

        if upgraded > 0:
            self._decision(f"Upgraded {upgraded} low-confidence retrieval slots to also use LLM")

        # Phase 2b: Parallel LLM calls
        llm_slots = [
            slot_id for slot_id, a in self.analyses.items()
            if a.strategy in ("llm_only", "llm_first", "both")
        ]

        llm_results = {}
        if llm_slots:
            self._think(f"Phase 2b: Firing {len(llm_slots)} LLM calls in parallel...")
            t0 = time.time()

            batch_requests = []
            for slot_id in llm_slots:
                slot = self.puzzle.slots[slot_id]
                batch_requests.append({
                    "slot_id": slot_id,
                    "clue": slot.clue,
                    "answer_length": slot.length,
                    "num_candidates": 10,
                })

            completed = [0]
            def on_complete(sid, cands):
                completed[0] += 1
                top = ", ".join(c["answer"] for c in cands[:3]) if cands else "none"
                self._result(f"  [{completed[0]}/{len(llm_slots)}] {sid}: {top}")

            llm_results = self.llm.get_candidates_batch(
                batch_requests, callback=on_complete
            )

            self._result(f"LLM done in {time.time()-t0:.1f}s "
                        f"({len(llm_slots)} calls in parallel)")

        # Merge candidates from both sources
        self._think("Merging retrieval + LLM candidates...")
        candidates = {}
        for slot_id, slot in self.puzzle.slots.items():
            r_cands = retrieval_results.get(slot_id, [])
            l_cands = llm_results.get(slot_id, [])
            candidates[slot_id] = self._merge(r_cands, l_cands)
            if candidates[slot_id]:
                top = candidates[slot_id][0]["answer"]
                self._slot_update(slot_id, top, "merged")

            # Track which source found the correct answer
            analysis = self.analyses[slot_id]
            r_top = r_cands[0]["answer"] if r_cands else ""
            l_top = l_cands[0]["answer"] if l_cands else ""

            if slot.answer:
                r_has = any(c["answer"] == slot.answer for c in r_cands)
                l_has = any(c["answer"] == slot.answer for c in l_cands)
                if r_has and l_has: analysis.source = "BOTH"
                elif r_has: analysis.source = "RETRIEVAL"
                elif l_has: analysis.source = "LLM"
                else: analysis.source = "MISSING"

            # Mark as confident if both sources agree or retrieval score is high
            if r_top and l_top and r_top == l_top:
                self._slot_confident(slot_id, r_top)
            elif r_cands and r_cands[0]["score"] >= 0.95:
                self._slot_confident(slot_id, r_top)

        # Phase 3: Belief propagation
        self._action("Phase 3: Running Belief Propagation...")
        bp = BeliefPropagationSolver(
            puzzle=self.puzzle, candidates=candidates,
            max_iterations=15, damping=0.5,
        )
        solution = bp.solve(verbose=False)
        conflicts = bp.get_conflicts(solution)
        metrics = bp.evaluate(solution)

        # Emit corrections and confidence updates from BP
        for slot_id in bp.slot_ids:
            if len(bp.beliefs[slot_id]) > 0:
                conf = float(bp.beliefs[slot_id].max())
                if slot_id in self.analyses:
                    old_answer = self.analyses[slot_id].answer
                    new_answer = solution.get(slot_id, "")
                    self.analyses[slot_id].confidence = conf
                    self.analyses[slot_id].answer = new_answer

                    if old_answer and new_answer and old_answer != new_answer:
                        self._slot_correction(slot_id, old_answer, new_answer)
                    elif conf >= 0.95:
                        self._slot_confident(slot_id, new_answer)

        self._result(f"Pass 1: {metrics['word_accuracy']:.1%} words, "
                     f"{len(conflicts)} conflicts")

        if metrics["perfect"]:
            self._think("Perfect solve on first pass!")
            return self._build_result(solution, metrics, 1, start_time)

        # Phase 4: Multi-pass re-querying with crossing letter hints
        for pass_num in range(2, self.max_passes + 1):
            self._think(f"Phase 4: Analyzing failures, pass {pass_num}...")
            weak_slots = self._find_weak_spots(solution, conflicts, bp)

            if not weak_slots:
                self._think("No weak spots. Stopping.")
                break

            self._decision(f"Re-querying {len(weak_slots)} weak slots with "
                          f"crossing letter hints (parallel)...")

            batch_requests = []
            for slot_id in weak_slots:
                slot = self.puzzle.slots[slot_id]
                known = self._get_known_letters(slot_id, solution)
                pattern = self._format_pattern(slot.length, known)
                self._action(f"  {slot_id}: \"{slot.clue}\" pattern={pattern}")

                batch_requests.append({
                    "slot_id": slot_id,
                    "clue": slot.clue,
                    "answer_length": slot.length,
                    "known_letters": known,
                    "num_candidates": 10,
                })

            t0 = time.time()
            improved_count = 0

            def on_requery(sid, cands):
                nonlocal improved_count
                top = ", ".join(c["answer"] for c in cands[:3]) if cands else "none"
                self._result(f"  {sid}: {top}")
                slot = self.puzzle.slots.get(sid)
                if slot and slot.answer and any(c["answer"] == slot.answer for c in cands):
                    self._result(f"  Found '{slot.answer}'!")
                    improved_count += 1

            requery_results = self.llm.get_candidates_batch(
                batch_requests, callback=on_requery
            )

            self._result(f"Re-queries done in {time.time()-t0:.1f}s, "
                        f"{improved_count} new correct answers")

            # Merge new candidates and re-run BP
            for slot_id, new_cands in requery_results.items():
                candidates[slot_id] = self._merge(candidates[slot_id], new_cands)

            self._action("Re-running Belief Propagation...")
            bp = BeliefPropagationSolver(
                puzzle=self.puzzle, candidates=candidates,
                max_iterations=15, damping=0.5,
            )
            solution = bp.solve(verbose=False)
            conflicts = bp.get_conflicts(solution)
            metrics = bp.evaluate(solution)

            self._result(f"Pass {pass_num}: {metrics['word_accuracy']:.1%} words, "
                        f"{len(conflicts)} conflicts")

            if metrics["perfect"]:
                self._think(f"Perfect solve on pass {pass_num}!")
                return self._build_result(solution, metrics, pass_num, start_time)

        # Phase 5: Local search for remaining conflicts
        if conflicts:
            self._think("Local search for remaining conflicts...")
            solution, conflicts = self._local_search(solution, candidates, bp)
            metrics = bp.evaluate(solution)

        return self._build_result(solution, metrics, self.max_passes, start_time)

    # --- Helper methods ---

    def _merge(self, list_a, list_b):
        """Merge candidate lists from two sources, boosting LLM scores slightly."""
        merged = {}
        for r in list_a:
            merged[r["answer"]] = r
        for r in list_b:
            boosted = r["score"] * 1.1
            if r["answer"] not in merged or boosted > merged[r["answer"]]["score"]:
                merged[r["answer"]] = {**r, "score": boosted}
        return sorted(merged.values(), key=lambda x: x["score"], reverse=True)

    def _find_weak_spots(self, solution, conflicts, bp):
        """Identify slots that need re-querying: conflicting, wrong, or low-confidence."""
        weak = set()
        for c in conflicts:
            weak.add(c["slot_a"])
            weak.add(c["slot_b"])
        for sid, ans in solution.items():
            slot = self.puzzle.slots.get(sid)
            if slot and slot.answer and ans != slot.answer:
                weak.add(sid)
        for sid in bp.slot_ids:
            if len(bp.beliefs[sid]) > 0 and float(bp.beliefs[sid].max()) < 0.5:
                weak.add(sid)
        return list(weak)

    def _get_known_letters(self, slot_id, solution):
        """Extract confirmed crossing letters from the current solution."""
        known = {}
        for crossing in self.puzzle.get_crossings_for_slot(slot_id):
            if crossing.slot_a_id == slot_id:
                other_id, my_pos, other_pos = crossing.slot_b_id, crossing.slot_a_pos, crossing.slot_b_pos
            else:
                other_id, my_pos, other_pos = crossing.slot_a_id, crossing.slot_b_pos, crossing.slot_a_pos
            if other_id in solution:
                other_answer = solution[other_id]
                if other_pos < len(other_answer):
                    known[my_pos] = other_answer[other_pos]
        return known

    def _format_pattern(self, length, known):
        """Format known letters as a pattern string (e.g., '_W_N_O_T')."""
        return "".join(known.get(i, "_") for i in range(length))

    def _local_search(self, solution, candidates, bp):
        """Greedy local search: swap answers to reduce crossing conflicts."""
        best = dict(solution)
        best_conflicts = bp.get_conflicts(best)
        for _ in range(50):
            if not best_conflicts: break
            conflict = best_conflicts[0]
            for try_slot in [conflict["slot_a"], conflict["slot_b"]]:
                if try_slot not in candidates: continue
                current = best[try_slot]
                for cand in candidates[try_slot]:
                    if cand["answer"] == current: continue
                    test = dict(best)
                    test[try_slot] = cand["answer"]
                    tc = bp.get_conflicts(test)
                    if len(tc) < len(best_conflicts):
                        best, best_conflicts = test, tc
                        self._result(f"  Swapped {try_slot}: {current} -> {cand['answer']}")
                        break
                if not best_conflicts: break
        return best, best_conflicts

    def _build_result(self, solution, metrics, passes, start_time):
        """Package the final result with metrics and source statistics."""
        elapsed = time.time() - start_time
        self._think(f"Solve complete in {elapsed:.1f}s using {passes} pass(es).")
        self._result(f"Final: {metrics['word_accuracy']:.1%} words, "
                    f"{metrics['letter_accuracy']:.1%} letters, "
                    f"{metrics['conflicts']} conflicts")

        source_counts = {}
        for a in self.analyses.values():
            source_counts[a.source] = source_counts.get(a.source, 0) + 1
        self._think(f"Sources: {dict(sorted(source_counts.items()))}")

        # Verify solution
        self._think("Running semantic verification...")
        verify_result = self.verifier.verify_solution(
            self.puzzle, solution, max_workers=10
        )
        self._result(f"Verified: {len(verify_result['verified'])}/{verify_result['total']} answers, "
                    f"{verify_result['flagged_count']} flagged")

        if verify_result["flagged"]:
            details = self.verifier.get_flagged_details(
                self.puzzle, solution, verify_result
            )
            for d in details:
                self._action(f"  Flagged {d['slot_id']}: \"{d['clue']}\" -> {d['answer']} "
                           f"(score: {d['score']:.2f})")

        return {
            "solution": solution,
            "metrics": metrics,
            "passes_used": passes,
            "elapsed": elapsed,
            "log": self.log,
            "analyses": self.analyses,
        }