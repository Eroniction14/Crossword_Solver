"""
Production server for the Crossword Solving Agent.

Serves both the API and the React frontend from a single Flask server.
No need for separate React dev server in production.

Development:
    python server.py

Production:
    pip install gunicorn
    gunicorn -w 1 --threads 4 -b 0.0.0.0:5000 server:app
"""

import sys
import os
import json
import time
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS

from config import cfg
from src.solver.loader import load_puzzle
from src.retrieval.retriever import Retriever
from src.llm.generator import LLMGenerator
from src.solver.agent import CrosswordAgent

# Serve React build if it exists
REACT_BUILD = os.path.join(os.path.dirname(__file__), "crossword-ui", "build")
HAS_BUILD = os.path.exists(REACT_BUILD)

app = Flask(__name__, static_folder=REACT_BUILD if HAS_BUILD else None)
CORS(app)

# Load heavy components once at startup
print(f"Loading retriever from {cfg.retrieval.index_dir}...")
retriever = Retriever.load(cfg.retrieval.index_dir, model_name=cfg.retrieval.model_name)
print("Loading LLM...")
llm = LLMGenerator(model=cfg.llm.model, max_workers=cfg.llm.max_workers)
print("Server ready!")
if HAS_BUILD:
    print(f"Serving React UI from {REACT_BUILD}")
else:
    print("No React build found. Run 'npm run build' in crossword-ui/ for production mode.")
    print("Using React dev server at localhost:3000 for development.")


# === React frontend routes ===

@app.route("/")
def serve_index():
    """Serve the React app."""
    if HAS_BUILD:
        return send_from_directory(REACT_BUILD, "index.html")
    return jsonify({"message": "API is running. React build not found."}), 200


@app.route("/<path:path>")
def serve_static(path):
    """Serve React static files (JS, CSS, images)."""
    if HAS_BUILD:
        # Don't intercept API routes
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404
        file_path = os.path.join(REACT_BUILD, path)
        if os.path.exists(file_path):
            return send_from_directory(REACT_BUILD, path)
        return send_from_directory(REACT_BUILD, "index.html")
    return jsonify({"error": "Not found"}), 404


# === API routes ===

@app.route("/api/puzzles", methods=["GET"])
def list_puzzles():
    """List available puzzle files."""
    puzzle_dir = cfg.paths.puzzles_dir
    if not os.path.exists(puzzle_dir):
        return jsonify([])

    puzzles = []
    for f in os.listdir(puzzle_dir):
        if f.endswith(".json"):
            path = os.path.join(puzzle_dir, f)
            try:
                with open(path) as fh:
                    data = json.load(fh)
                puzzles.append({
                    "filename": f,
                    "title": data.get("title", f),
                    "rows": len(data.get("grid", [])),
                    "cols": len(data.get("grid", [[]])[0]) if data.get("grid") else 0,
                })
            except Exception:
                pass

    return jsonify(puzzles)


@app.route("/api/puzzle/<filename>", methods=["GET"])
def get_puzzle(filename):
    """Load a specific puzzle file."""
    path = os.path.join(cfg.paths.puzzles_dir, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Puzzle not found"}), 404

    puzzle = load_puzzle(path)

    slots = {}
    for slot_id, slot in puzzle.slots.items():
        slots[slot_id] = {
            "number": slot.number,
            "direction": slot.direction,
            "clue": slot.clue,
            "length": slot.length,
            "cells": slot.cells,
            "answer": slot.answer,
        }

    return jsonify({
        "title": puzzle.title,
        "rows": puzzle.rows,
        "cols": puzzle.cols,
        "grid": puzzle.grid,
        "slots": slots,
        "crossings": len(puzzle.crossings),
    })


@app.route("/api/upload", methods=["POST"])
def upload_puzzle():
    """Upload a .puz or .json puzzle file."""
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    filename = file.filename

    if not filename:
        return jsonify({"error": "No filename"}), 400

    save_path = os.path.join(cfg.paths.puzzles_dir, filename)
    file.save(save_path)

    try:
        puzzle = load_puzzle(save_path)
        return jsonify({
            "filename": filename,
            "title": puzzle.title,
            "rows": puzzle.rows,
            "cols": puzzle.cols,
            "slots": len(puzzle.slots),
        })
    except Exception as e:
        os.remove(save_path)
        return jsonify({"error": f"Failed to parse: {str(e)}"}), 400


@app.route("/api/solve/<filename>", methods=["GET"])
def solve_puzzle(filename):
    """Solve a puzzle and stream the agent's thinking as SSE."""
    path = os.path.join(cfg.paths.puzzles_dir, filename)
    if not os.path.exists(path):
        return jsonify({"error": "Puzzle not found"}), 404

    puzzle = load_puzzle(path)

    def generate():
        agent = CrosswordAgent(
            puzzle=puzzle,
            retriever=retriever,
            llm=llm,
            max_passes=cfg.solver.max_passes,
        )

        event_queue = queue.Queue()

        original_think = agent._think
        original_action = agent._action
        original_result = agent._result
        original_decision = agent._decision

        def stream_think(msg):
            original_think(msg)
            event_queue.put({"type": "think", "message": msg})

        def stream_action(msg):
            original_action(msg)
            event_queue.put({"type": "action", "message": msg})

        def stream_result(msg):
            original_result(msg)
            event_queue.put({"type": "result", "message": msg})

        def stream_decision(msg):
            original_decision(msg)
            event_queue.put({"type": "decision", "message": msg})

        agent._think = stream_think
        agent._action = stream_action
        agent._result = stream_result
        agent._decision = stream_decision

        original_slot_update = agent._slot_update

        def stream_slot_update(slot_id, answer, source):
            original_slot_update(slot_id, answer, source)
            event_queue.put({
                "type": "slot_done",
                "slot_id": slot_id,
                "answer": answer,
                "source": source,
            })

        agent._slot_update = stream_slot_update

        original_slot_confident = agent._slot_confident

        def stream_slot_confident(slot_id, answer):
            original_slot_confident(slot_id, answer)
            event_queue.put({
                "type": "slot_confident",
                "slot_id": slot_id,
                "answer": answer,
            })

        agent._slot_confident = stream_slot_confident

        original_slot_correction = agent._slot_correction

        def stream_slot_correction(slot_id, old_answer, answer):
            original_slot_correction(slot_id, old_answer, answer)
            event_queue.put({
                "type": "slot_correction",
                "slot_id": slot_id,
                "old_answer": old_answer,
                "answer": answer,
            })

        agent._slot_correction = stream_slot_correction

        result_holder = [None]

        def run_solver():
            result_holder[0] = agent.solve()
            event_queue.put(None)

        thread = threading.Thread(target=run_solver)
        thread.start()

        while True:
            try:
                event = event_queue.get(timeout=300)
                if event is None:
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                break

        if result_holder[0]:
            result = result_holder[0]
            final = {
                "type": "final",
                "solution": result["solution"],
                "metrics": result["metrics"],
                "passes_used": result["passes_used"],
                "elapsed": result.get("elapsed", 0),
                "analyses": {
                    slot_id: {
                        "clue_type": a.clue_type,
                        "strategy": a.strategy,
                        "source": a.source,
                        "confidence": a.confidence,
                        "answer": a.answer,
                    }
                    for slot_id, a in result["analyses"].items()
                },
            }
            yield f"data: {json.dumps(final)}\n\n"

        thread.join()

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "ok",
        "index_size": retriever.index.index.ntotal,
        "model": cfg.llm.model,
    })


if __name__ == "__main__":
    port = cfg.server.port
    debug = cfg.server.debug
    print(f"\nStarting server on http://localhost:{port}")
    if HAS_BUILD:
        print(f"Open http://localhost:{port} in your browser")
    else:
        print(f"API only. Start React dev server separately: cd crossword-ui && npm start")
    app.run(
        debug=debug,
        port=port,
        threaded=True,
    )