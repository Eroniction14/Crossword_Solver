"""
Semantic verification for crossword answers.

After belief propagation produces a solution, this module validates
each answer against its clue using Claude as a semantic judge.
Catches errors where an answer has correct crossing letters but
doesn't actually match the clue meaning.

Two verification strategies:
    1. LLM verification — asks Claude to score clue-answer pairs
    2. Retrieval verification — checks if the answer appears in
       retrieval results for the clue
"""

from concurrent.futures import ThreadPoolExecutor, as_completed


class SemanticVerifier:
    """Verifies crossword answers by scoring clue-answer pair compatibility.

    Args:
        llm: LLMGenerator instance for Claude API calls.
        retriever: Retriever instance for FAISS lookup.
        confidence_threshold: Answers scoring below this are flagged.
    """

    def __init__(self, llm=None, retriever=None, confidence_threshold=0.5):
        self.llm = llm
        self.retriever = retriever
        self.confidence_threshold = confidence_threshold

    def verify_solution(self, puzzle, solution, max_workers=10):
        """Verify all answers in a solution.

        Args:
            puzzle: The Puzzle object with clues.
            solution: Dict mapping slot_id to answer string.
            max_workers: Parallel verification threads.

        Returns:
            Dict with 'verified' (list of verified slots),
            'flagged' (list of suspicious slots), and
            'scores' (dict of slot_id to score).
        """
        scores = {}
        flagged = []
        verified = []

        # Score each answer
        slot_scores = self._score_all(puzzle, solution, max_workers)

        for slot_id, score in slot_scores.items():
            scores[slot_id] = score
            if score >= self.confidence_threshold:
                verified.append(slot_id)
            else:
                flagged.append(slot_id)

        return {
            "verified": verified,
            "flagged": flagged,
            "scores": scores,
            "total": len(scores),
            "flagged_count": len(flagged),
        }

    def _score_all(self, puzzle, solution, max_workers):
        """Score all clue-answer pairs, using available methods."""
        scores = {}

        # Method 1: Retrieval-based scoring (fast, no API cost)
        if self.retriever:
            retrieval_scores = self._retrieval_scores(puzzle, solution)
            for slot_id, score in retrieval_scores.items():
                scores[slot_id] = score

        # Method 2: LLM-based scoring (accurate, costs API calls)
        if self.llm:
            llm_scores = self._llm_scores(puzzle, solution, max_workers)
            for slot_id, score in llm_scores.items():
                # Combine with retrieval score if both available
                if slot_id in scores:
                    scores[slot_id] = (scores[slot_id] + score) / 2
                else:
                    scores[slot_id] = score

        return scores

    def _retrieval_scores(self, puzzle, solution):
        """Score answers by checking if they appear in retrieval results.

        A high retrieval score means the answer is commonly associated
        with similar clues in the database.
        """
        scores = {}

        for slot_id, answer in solution.items():
            slot = puzzle.slots.get(slot_id)
            if not slot:
                continue

            # Search for the clue and see if this answer appears
            results = self.retriever.get_candidates(
                clue=slot.clue,
                answer_length=len(answer),
                top_k=50,
            )

            # Check if answer is in results and at what rank
            found = False
            for i, r in enumerate(results):
                if r["answer"] == answer:
                    # Score based on rank (1st = 1.0, 50th = 0.02)
                    scores[slot_id] = max(1.0 - (i * 0.02), 0.1)
                    found = True
                    break

            if not found:
                scores[slot_id] = 0.0

        return scores

    def _llm_scores(self, puzzle, solution, max_workers):
        """Score answers by asking Claude to judge clue-answer compatibility."""
        scores = {}

        def score_one(slot_id, clue, answer):
            prompt = f"""You are a crossword puzzle judge. Rate how well this answer fits the clue.

Clue: "{clue}"
Answer: {answer} ({len(answer)} letters)

Rate the fit from 0.0 to 1.0:
- 1.0 = perfect, this is definitely the correct answer
- 0.7 = good, this is a plausible answer
- 0.3 = weak, this could work but seems unlikely
- 0.0 = wrong, this answer does not fit the clue at all

Respond with ONLY a number between 0.0 and 1.0, nothing else."""

            try:
                response = self.llm.client.messages.create(
                    model=self.llm.model,
                    max_tokens=10,
                    temperature=0,
                    messages=[{"role": "user", "content": prompt}],
                )
                text = response.content[0].text.strip()
                score = float(text)
                return slot_id, min(max(score, 0.0), 1.0)
            except (ValueError, Exception):
                return slot_id, 0.5  # Default to uncertain

        # Run in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for slot_id, answer in solution.items():
                slot = puzzle.slots.get(slot_id)
                if not slot:
                    continue
                future = executor.submit(score_one, slot_id, slot.clue, answer)
                futures[future] = slot_id

            for future in as_completed(futures):
                try:
                    slot_id, score = future.result()
                    scores[slot_id] = score
                except Exception:
                    scores[futures[future]] = 0.5

        return scores

    def get_flagged_details(self, puzzle, solution, verify_result):
        """Get detailed information about flagged answers.

        Returns list of dicts with slot_id, clue, answer, score,
        and expected answer (if available).
        """
        details = []
        for slot_id in verify_result["flagged"]:
            slot = puzzle.slots.get(slot_id)
            if not slot:
                continue
            details.append({
                "slot_id": slot_id,
                "clue": slot.clue,
                "answer": solution.get(slot_id, ""),
                "expected": slot.answer or "",
                "score": verify_result["scores"].get(slot_id, 0),
                "actually_wrong": slot.answer and solution.get(slot_id) != slot.answer,
            })
        return details