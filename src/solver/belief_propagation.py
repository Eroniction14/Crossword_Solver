"""
Loopy belief propagation solver for crossword grid constraint satisfaction.

Propagates letter-level constraints between crossing slots to find a
globally consistent grid filling. Uses damped message passing with
greedy fallback for slots without candidates.
"""

import numpy as np
from collections import defaultdict
from src.solver.puzzle import Puzzle, Crossing


class BeliefPropagationSolver:
    """
    Loopy Belief Propagation solver for crossword grids.

    Usage:
        solver = BeliefPropagationSolver(puzzle, candidates)
        solution = solver.solve()
    """

    def __init__(self, puzzle: Puzzle, candidates: dict[str, list[dict]],
                 max_iterations: int = 15, damping: float = 0.5,
                 convergence_threshold: float = 0.001):
        """
        Args:
            puzzle: The parsed Puzzle object with slots and crossings.
            candidates: Dict mapping slot_id to list of candidate dicts.
                       Each candidate dict has 'answer' and 'score'.
                       Example: {"1-across": [{"answer": "CAT", "score": 0.9}, ...]}
            max_iterations: Max rounds of message passing.
            damping: Blend factor between old and new messages (0-1).
                    Higher = more conservative updates, better convergence.
            convergence_threshold: Stop when max message change is below this.
        """
        self.puzzle = puzzle
        self.candidates = candidates
        self.max_iterations = max_iterations
        self.damping = damping
        self.convergence_threshold = convergence_threshold

        # Build internal data structures
        self._build_structures()

    def _build_structures(self):
        """Set up the internal arrays for message passing."""

        # For each slot, store candidate answers and initial beliefs
        self.slot_ids = list(self.candidates.keys())
        self.num_candidates = {}  # slot_id -> number of candidates
        self.candidate_answers = {}  # slot_id -> list of answer strings
        self.beliefs = {}  # slot_id -> numpy array of probabilities

        for slot_id in self.slot_ids:
            cands = self.candidates[slot_id]
            answers = [c["answer"] for c in cands]
            scores = np.array([c["score"] for c in cands], dtype=np.float64)

            # Convert scores to probabilities (softmax-like normalization)
            if len(scores) > 0 and scores.max() > 0:
                # Shift scores to avoid numerical issues
                scores = scores - scores.max()
                probs = np.exp(scores)
                probs = probs / probs.sum()
            else:
                probs = np.ones(len(scores)) / max(len(scores), 1)

            self.num_candidates[slot_id] = len(answers)
            self.candidate_answers[slot_id] = answers
            self.beliefs[slot_id] = probs

        # Index crossings by slot for fast lookup
        # crossing_map[slot_id] = list of (crossing, other_slot_id)
        self.crossing_map = defaultdict(list)
        for crossing in self.puzzle.crossings:
            self.crossing_map[crossing.slot_a_id].append(
                (crossing, crossing.slot_b_id)
            )
            self.crossing_map[crossing.slot_b_id].append(
                (crossing, crossing.slot_a_id)
            )

        # Initialize messages: message[from_slot][to_slot] = array
        # Each message is a probability distribution over the receiver's candidates
        self.messages = defaultdict(dict)
        for slot_id in self.slot_ids:
            for crossing, other_id in self.crossing_map[slot_id]:
                if other_id in self.candidates:
                    n = self.num_candidates[other_id]
                    # Start with uniform messages
                    self.messages[slot_id][other_id] = np.ones(n) / max(n, 1)

    def _get_letter_at_crossing(self, answer: str, crossing: Crossing,
                                 slot_id: str) -> str:
        """Get the letter that an answer contributes at a crossing cell."""
        if slot_id == crossing.slot_a_id:
            pos = crossing.slot_a_pos
        else:
            pos = crossing.slot_b_pos

        if pos < len(answer):
            return answer[pos].upper()
        return "?"

    def _compute_message(self, from_slot: str, to_slot: str,
                          crossing: Crossing) -> np.ndarray:
        """
        Compute the message from from_slot to to_slot.

        The message tells to_slot: "for each of your candidates, here's how
        compatible it is with what I currently believe about my answer."
        """
        from_answers = self.candidate_answers[from_slot]
        to_answers = self.candidate_answers[to_slot]

        # Get current beliefs for from_slot, excluding the message
        # that to_slot previously sent to from_slot (to avoid circular reasoning)
        beliefs = self.beliefs[from_slot].copy()

        # Cavity: remove influence of to_slot's message to from_slot
        if to_slot in self.messages and from_slot in self.messages[to_slot]:
            old_msg = self.messages[to_slot][from_slot]
            if old_msg.sum() > 0:
                beliefs = beliefs / (old_msg + 1e-30)
                beliefs = beliefs / (beliefs.sum() + 1e-30)

        # For each candidate of to_slot, compute compatibility
        message = np.zeros(len(to_answers))

        for j, to_answer in enumerate(to_answers):
            to_letter = self._get_letter_at_crossing(to_answer, crossing, to_slot)

            # Sum over from_slot's candidates that agree on the crossing letter
            for i, from_answer in enumerate(from_answers):
                from_letter = self._get_letter_at_crossing(
                    from_answer, crossing, from_slot
                )
                if from_letter == to_letter:
                    message[j] += beliefs[i]

        # Normalize
        total = message.sum()
        if total > 0:
            message = message / total
        else:
            message = np.ones(len(to_answers)) / max(len(to_answers), 1)

        return message

    def _update_beliefs(self):
        """Recompute beliefs for each slot based on initial scores and all messages."""
        for slot_id in self.slot_ids:
            cands = self.candidates[slot_id]
            scores = np.array([c["score"] for c in cands], dtype=np.float64)

            # Start from initial scores
            if len(scores) > 0 and scores.max() > 0:
                scores = scores - scores.max()
                belief = np.exp(scores)
            else:
                belief = np.ones(len(scores))

            # Multiply in all incoming messages
            for crossing, other_id in self.crossing_map[slot_id]:
                if other_id in self.messages and slot_id in self.messages[other_id]:
                    msg = self.messages[other_id][slot_id]
                    belief = belief * (msg + 1e-30)  # Small epsilon to avoid zeros

            # Normalize
            total = belief.sum()
            if total > 0:
                belief = belief / total
            else:
                belief = np.ones(len(belief)) / max(len(belief), 1)

            self.beliefs[slot_id] = belief

    def solve(self, verbose: bool = True) -> dict[str, str]:
        """
        Run belief propagation and return the solution.

        Args:
            verbose: Print progress information.

        Returns:
            Dict mapping slot_id to chosen answer string.
        """
        if verbose:
            print(f"Running Belief Propagation...")
            print(f"  Slots: {len(self.slot_ids)}")
            print(f"  Crossings: {len(self.puzzle.crossings)}")
            print(f"  Max iterations: {self.max_iterations}")
            print()

        for iteration in range(self.max_iterations):
            max_change = 0.0

            # Send messages along every crossing
            for slot_id in self.slot_ids:
                for crossing, other_id in self.crossing_map[slot_id]:
                    if other_id not in self.candidates:
                        continue

                    new_message = self._compute_message(
                        slot_id, other_id, crossing
                    )

                    # Damping: blend new message with old
                    old_message = self.messages[slot_id].get(
                        other_id, np.ones(len(new_message)) / max(len(new_message), 1)
                    )

                    damped = (self.damping * old_message +
                              (1 - self.damping) * new_message)

                    # Normalize
                    total = damped.sum()
                    if total > 0:
                        damped = damped / total

                    # Track convergence
                    if len(damped) > 0:
                        change = np.abs(damped - old_message).max()
                    else:
                        change = 0.0
                    max_change = max(max_change, change)

                    self.messages[slot_id][other_id] = damped

            # Update beliefs based on new messages
            self._update_beliefs()

            if verbose:
                print(f"  Iteration {iteration + 1}: max message change = {max_change:.6f}")

            # Check convergence
            if max_change < self.convergence_threshold:
                if verbose:
                    print(f"  Converged after {iteration + 1} iterations!")
                break

        # Extract solution: pick highest-belief candidate for each slot
        solution = {}
        confidences = {}

        for slot_id in self.slot_ids:
            if len(self.beliefs[slot_id]) > 0:
                best_idx = np.argmax(self.beliefs[slot_id])
                solution[slot_id] = self.candidate_answers[slot_id][best_idx]
                confidences[slot_id] = float(self.beliefs[slot_id][best_idx])
            else:
                solution[slot_id] = "?" * self.puzzle.slots[slot_id].length
                confidences[slot_id] = 0.0

        if verbose:
            print()
            print("Solution:")
            for slot_id in sorted(solution.keys()):
                slot = self.puzzle.slots[slot_id]
                conf = confidences[slot_id]
                correct = ""
                if slot.answer:
                    match = "OK" if solution[slot_id] == slot.answer else "WRONG"
                    correct = f" (expected: {slot.answer}) {match}"
                print(f"  {slot_id}: {solution[slot_id]} "
                      f"(confidence: {conf:.3f}){correct}")

        return solution

    def get_conflicts(self, solution: dict[str, str]) -> list[dict]:
        """
        Check a solution for crossing conflicts.

        Returns a list of conflicts (empty = perfect solution).
        """
        conflicts = []

        for crossing in self.puzzle.crossings:
            id_a = crossing.slot_a_id
            id_b = crossing.slot_b_id

            if id_a not in solution or id_b not in solution:
                continue

            answer_a = solution[id_a]
            answer_b = solution[id_b]

            if crossing.slot_a_pos < len(answer_a):
                letter_a = answer_a[crossing.slot_a_pos]
            else:
                letter_a = "?"

            if crossing.slot_b_pos < len(answer_b):
                letter_b = answer_b[crossing.slot_b_pos]
            else:
                letter_b = "?"

            if letter_a != letter_b:
                conflicts.append({
                    "cell": crossing.cell,
                    "slot_a": id_a,
                    "letter_a": letter_a,
                    "slot_b": id_b,
                    "letter_b": letter_b,
                })

        return conflicts

    def evaluate(self, solution: dict[str, str]) -> dict:
        """
        Evaluate a solution against the ground truth answers.

        Returns dict with letter_accuracy, word_accuracy, and perfect flag.
        """
        total_letters = 0
        correct_letters = 0
        total_words = 0
        correct_words = 0

        for slot_id, proposed in solution.items():
            slot = self.puzzle.slots.get(slot_id)
            if not slot or not slot.answer:
                continue

            expected = slot.answer
            total_words += 1

            if proposed == expected:
                correct_words += 1

            for i in range(min(len(proposed), len(expected))):
                total_letters += 1
                if proposed[i] == expected[i]:
                    correct_letters += 1

            # Count missing letters as wrong
            total_letters += abs(len(proposed) - len(expected))

        return {
            "letter_accuracy": correct_letters / max(total_letters, 1),
            "word_accuracy": correct_words / max(total_words, 1),
            "perfect": correct_words == total_words and total_words > 0,
            "correct_words": correct_words,
            "total_words": total_words,
            "correct_letters": correct_letters,
            "total_letters": total_letters,
            "conflicts": len(self.get_conflicts(solution)),
        }