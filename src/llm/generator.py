"""
LLM candidate generator using Claude API.

Generates crossword answer candidates by prompting Claude with clue text
and length constraints. Supports parallel batch requests via ThreadPoolExecutor.
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import anthropic


class LLMGenerator:
    """Claude-based crossword answer candidate generator.

    Sends clue text and length constraints to Claude and parses
    the response into ranked candidate answers. Supports both
    single and parallel batch requests.

    Args:
        api_key: Anthropic API key. Reads from .env if not provided.
        model: Claude model identifier.
        max_workers: Maximum concurrent API calls for batch requests.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens: Maximum response tokens per API call.
    """

    def __init__(self, api_key: str = None, model: str = "claude-sonnet-4-6",
                 max_workers: int = 10, temperature: float = 0,
                 max_tokens: int = 300):
        load_dotenv()
        key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "No API key found. Set ANTHROPIC_API_KEY in your .env file."
            )

        self.client = anthropic.Anthropic(api_key=key)
        self.model = model
        self.max_workers = max_workers
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_candidates(self, clue: str, answer_length: int,
                       known_letters: dict = None,
                       num_candidates: int = 10) -> list:
        """Generate ranked answer candidates for a single clue.

        Args:
            clue: The crossword clue text.
            answer_length: Required number of letters.
            known_letters: Optional dict mapping position -> letter for
                          crossing constraints (e.g., {0: 'A', 3: 'E'}).
            num_candidates: Number of candidates to request.

        Returns:
            List of dicts with 'answer', 'score', 'clue', and 'answer_length'.
        """
        prompt = self._build_prompt(clue, answer_length, known_letters,
                                     num_candidates)
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            return self._parse_response(text, answer_length)

        except Exception as e:
            print(f"  LLM error for clue '{clue}': {e}")
            return []

    def get_candidates_batch(self, requests: list, callback=None) -> dict:
        """Generate candidates for multiple clues in parallel.

        Fires all API calls simultaneously using ThreadPoolExecutor,
        reducing total wall time from N * latency to ~1 * latency.

        Args:
            requests: List of dicts, each with 'slot_id', 'clue',
                     'answer_length', and optional 'known_letters'.
            callback: Optional function(slot_id, candidates) called
                     after each clue completes.

        Returns:
            Dict mapping slot_id to list of candidate dicts.
        """
        results = {}

        def process_one(req):
            slot_id = req["slot_id"]
            candidates = self.get_candidates(
                clue=req["clue"],
                answer_length=req["answer_length"],
                known_letters=req.get("known_letters"),
                num_candidates=req.get("num_candidates", 10),
            )
            return slot_id, candidates

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(process_one, req): req["slot_id"]
                for req in requests
            }

            for future in as_completed(futures):
                slot_id = futures[future]
                try:
                    sid, candidates = future.result()
                    results[sid] = candidates
                    if callback:
                        callback(sid, candidates)
                except Exception as e:
                    print(f"  LLM batch error for {slot_id}: {e}")
                    results[slot_id] = []

        return results

    def _build_prompt(self, clue, answer_length, known_letters=None,
                       num_candidates=10):
        """Build the Claude prompt with clue, length, and optional letter hints."""
        pattern = ""
        if known_letters:
            for i in range(answer_length):
                if i in known_letters:
                    pattern += known_letters[i].upper()
                else:
                    pattern += "_"
            pattern_line = f"\nKnown letters: {pattern}"
        else:
            pattern_line = ""

        return f"""You are a crossword puzzle expert. Given a crossword clue, provide the most likely answers.

Clue: "{clue}"
Answer length: {answer_length} letters{pattern_line}

List your top {num_candidates} answers, one per line, in order of confidence.
Each line should be ONLY the answer in uppercase letters, nothing else.
Every answer MUST be exactly {answer_length} letters long.

Answers:"""

    def _parse_response(self, text, answer_length):
        """Parse Claude's text response into a ranked list of candidate dicts."""
        candidates = []
        lines = text.strip().split("\n")

        for i, line in enumerate(lines):
            # Strip numbering, punctuation, whitespace
            cleaned = re.sub(r'^[\d\.\-\)\s]+', '', line).strip().upper()
            cleaned = re.sub(r'[^A-Z]', '', cleaned)

            if len(cleaned) == answer_length:
                score = max(1.0 - (i * 0.08), 0.1)
                candidates.append({
                    "answer": cleaned,
                    "score": score,
                    "clue": f"[LLM] {cleaned}",
                    "answer_length": answer_length,
                })

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for c in candidates:
            if c["answer"] not in seen:
                seen.add(c["answer"])
                unique.append(c)

        return unique