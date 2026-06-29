import { useState, useEffect, useRef, useCallback } from "react";
import { themes } from "./components/themes";
import CrosswordGrid from "./components/CrosswordGrid";
import CluePanel, { StrategyLegend } from "./components/CluePanel";
import StatsBar from "./components/StatsBar";
import LogEntry from "./components/LogEntry";
import PuzzleSelector from "./components/PuzzleSelector";

const API = window.location.hostname === "localhost" && window.location.port === "3000"
  ? "http://localhost:5000/api"
  : "/api";

export default function CrosswordAgentUI() {
  const [puzzle, setPuzzle] = useState(null);
  const [puzzleFile, setPuzzleFile] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [logEntries, setLogEntries] = useState([]);
  const [filledCells, setFilledCells] = useState({});
  const [cellStates, setCellStates] = useState({});
  const [workingSlots, setWorkingSlots] = useState([]);
  const [slotStatuses, setSlotStatuses] = useState({});
  const [filledAnswers, setFilledAnswers] = useState({});
  const [slotSources, setSlotSources] = useState({});
  const [highlightSlot, setHighlightSlot] = useState(null);
  const [wordsFound, setWordsFound] = useState(0);
  const [conflicts, setConflicts] = useState(0);
  const [passNum, setPassNum] = useState(1);
  const [elapsed, setElapsed] = useState("0.0");
  const [phase, setPhase] = useState("");
  const [finalResult, setFinalResult] = useState(null);
  const [theme, setTheme] = useState("dark");
  const logRef = useRef(null);
  const timerRef = useRef(null);
  const esRef = useRef(null);

  const t = themes[theme];

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logEntries]);

  const loadPuzzle = async (filename, customData) => {
    if (customData) {
      const rows = customData.grid.length;
      const cols = customData.grid[0].length;
      setPuzzle({ ...customData, rows, cols, slots: customData.slots || {}, crossings: 0 });
      setPuzzleFile(null);
    } else {
      const res = await fetch(`${API}/puzzle/${filename}`);
      const data = await res.json();
      setPuzzle(data);
      setPuzzleFile(filename);
    }
    resetState();
  };

  const resetState = () => {
    setIsDone(false);
    setLogEntries([]);
    setFilledCells({});
    setCellStates({});
    setWorkingSlots([]);
    setSlotStatuses({});
    setFilledAnswers({});
    setSlotSources({});
    setWordsFound(0);
    setConflicts(0);
    setPassNum(1);
    setElapsed("0.0");
    setPhase("");
    setFinalResult(null);
  };

  const fillSlot = useCallback((slotId, answer) => {
    if (!puzzle || !puzzle.slots[slotId]) return;
    setFilledCells(prev => {
      const next = { ...prev };
      puzzle.slots[slotId].cells.forEach(([r, c], i) => {
        if (i < answer.length) next[`${r}-${c}`] = answer[i];
      });
      return next;
    });
    setFilledAnswers(prev => ({ ...prev, [slotId]: answer }));
  }, [puzzle]);

  const setCellConfidence = useCallback((slotId, state) => {
    if (!puzzle || !puzzle.slots[slotId]) return;
    setCellStates(prev => {
      const next = { ...prev };
      puzzle.slots[slotId].cells.forEach(([r, c]) => {
        next[`${r}-${c}`] = state;
      });
      return next;
    });
  }, [puzzle]);

  const startSolving = () => {
    if (!puzzleFile) return;
    setIsRunning(true);
    resetState();

    const startTime = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed(((Date.now() - startTime) / 1000).toFixed(1));
    }, 100);

    const es = new EventSource(`${API}/solve/${puzzleFile}`);
    esRef.current = es;
    

    es.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "final") {
        clearInterval(timerRef.current);
        for (const [slotId, answer] of Object.entries(data.solution)) {
          fillSlot(slotId, answer);
          setSlotStatuses(prev => ({ ...prev, [slotId]: "solved" }));
        }
        if (data.solution) {
          for (const [slotId] of Object.entries(data.solution)) {
            const answer = data.solution[slotId];
            const expected = puzzle.slots[slotId]?.answer;
            const isCorrect = !expected || answer === expected;
            setCellConfidence(slotId, isCorrect ? "confident" : "conflict");
          }
        }
        if (data.analyses) {
          const sources = {};
          for (const [slotId, analysis] of Object.entries(data.analyses)) {
            sources[slotId] = analysis.source || "";
          }
          setSlotSources(sources);
        }
        setWordsFound(data.metrics.correct_words || Object.keys(data.solution).length);
        setConflicts(data.metrics.conflicts);
        setFinalResult(data);
        setIsRunning(false);
        setIsDone(true);
        setElapsed(data.elapsed.toFixed(1));
        setPhase("Complete");
        es.close();
        return;
      }

      if (data.type === "slot_working") {
        setWorkingSlots(prev => [...new Set([...prev, data.slot_id])]);
        setSlotStatuses(prev => ({ ...prev, [data.slot_id]: "working" }));
        setPhase(`Solving ${data.slot_id}`);
        return;
      }

      if (data.type === "slot_done") {
        setWorkingSlots(prev => prev.filter(s => s !== data.slot_id));
        if (data.answer) {
          fillSlot(data.slot_id, data.answer);
          setSlotStatuses(prev => {
            const next = { ...prev, [data.slot_id]: "solved" };
            setWordsFound(Object.values(next).filter(s => s === "solved").length);
            return next;
          });
        }
        return;
      }

      if (data.type === "slot_confident") {
        if (data.answer) {
          fillSlot(data.slot_id, data.answer);
          setCellConfidence(data.slot_id, "confident");
          setSlotStatuses(prev => ({ ...prev, [data.slot_id]: "solved" }));
        }
        return;
      }

      if (data.type === "slot_correction") {
        if (data.answer) {
          setCellConfidence(data.slot_id, "conflict");
          fillSlot(data.slot_id, data.answer);
          setTimeout(() => setCellConfidence(data.slot_id, "confident"), 600);
          setSlotStatuses(prev => ({ ...prev, [data.slot_id]: "solved" }));
        }
        setLogEntries(prev => [...prev, {
          type: "result",
          message: `BP corrected ${data.slot_id}: ${data.old_answer} -> ${data.answer}`,
        }]);
        return;
      }

      if (data.message) {
        if (data.message.includes("Phase 2a")) setPhase("Retrieval");
        else if (data.message.includes("Phase 2b") || data.message.includes("Firing")) setPhase("LLM (parallel)");
        else if (data.message.includes("Phase 3") || data.message.includes("Belief")) setPhase("Belief Propagation");
        else if (data.message.includes("Phase 4") || data.message.includes("Re-querying")) setPhase("Re-querying");
        else if (data.message.includes("Pass 2")) setPassNum(2);
        else if (data.message.includes("Pass 3")) setPassNum(3);
      }

      setLogEntries(prev => [...prev, { type: data.type, message: data.message }]);
    };

    es.onerror = () => {
      es.close();
      setIsRunning(false);
      clearInterval(timerRef.current);
    };
  };

  const fullReset = () => {
    if (esRef.current) esRef.current.close();
    clearInterval(timerRef.current);
    resetState();
    setPuzzle(null);
    setPuzzleFile(null);
  };

  const handleCellHover = (r, c) => {
    if (r === null) { setHighlightSlot(null); return; }
    if (!puzzle) return;
    for (const [id, slot] of Object.entries(puzzle.slots)) {
      if (slot.cells.some(([cr, cc]) => cr === r && cc === c)) {
        setHighlightSlot(id);
        return;
      }
    }
    setHighlightSlot(null);
  };

  const totalWords = puzzle ? Object.keys(puzzle.slots).length : 0;

  return (
    <div style={{
      minHeight: "100vh", background: t.bg,
      color: t.text, padding: "16px 20px",
      fontFamily: "'IBM Plex Sans', -apple-system, sans-serif",
      transition: "background 0.3s, color 0.3s",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
        @keyframes fadeIn { from { opacity:0; transform:translateY(3px); } to { opacity:1; transform:translateY(0); } }
        @keyframes slideIn { from { opacity:0; transform:translateX(-6px); } to { opacity:1; transform:translateX(0); } }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.4; } }
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: ${theme === "dark" ? "#334155" : "#cbd5e1"}; border-radius: 3px; }
      `}</style>

      {/* Header + Theme Toggle */}
      <div style={{ textAlign: "center", marginBottom: 16, position: "relative" }}>
        {puzzle && (
          <button onClick={fullReset} style={{
            position: "absolute", left: 0, top: 0,
            background: t.panel, border: `1px solid ${t.border}`, borderRadius: 20,
            color: t.textDim, padding: "4px 12px", cursor: "pointer",
            fontFamily: "monospace", fontSize: 11,
          }}>
            ← Back
          </button>
        )}
        <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")} style={{
          position: "absolute", right: 0, top: 0,
          background: t.panel, border: `1px solid ${t.border}`, borderRadius: 20,
          color: t.textDim, padding: "4px 12px", cursor: "pointer",
          fontFamily: "monospace", fontSize: 11,
        }}>
          {theme === "dark" ? "☀ Light" : "● Dark"}
        </button>
        <h1 style={{
          fontFamily: "'IBM Plex Sans', sans-serif",
          fontSize: 26, fontWeight: 700, color: t.text,
          margin: 0, letterSpacing: -0.5,
        }}>
          <span style={{ color: t.green }}>●</span> Crossword Solving Agent
        </h1>
        <p style={{
          color: t.textFaint, fontSize: 11, marginTop: 3,
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          FAISS retrieval · Belief propagation
        </p>
      </div>

      {/* Puzzle Selector */}
      {!puzzle && (
        <div style={{
          background: t.panel, borderRadius: 10, padding: 16,
          border: `1px solid ${t.border}`, maxWidth: 700, margin: "0 auto",
        }}>
          <PuzzleSelector onSelect={loadPuzzle} theme={theme} />
        </div>
      )}

      {puzzle && (
        <>
          <StatsBar wordsFound={wordsFound} totalWords={totalWords}
            conflicts={conflicts} passNum={passNum} elapsed={elapsed} phase={phase} theme={theme} />

          {/* TOP ROW: Grid (left) + Clues (right) */}
          <div style={{ display: "flex", gap: 14, marginTop: 14, alignItems: "flex-start" }}>

            {/* Left: Grid + Controls */}
            <div style={{ flex: "0 0 auto", display: "flex", flexDirection: "column", gap: 10 }}>
              <CrosswordGrid puzzle={puzzle} filledCells={filledCells}
                cellStates={cellStates} workingSlots={workingSlots}
                highlightSlot={highlightSlot} onCellHover={handleCellHover} theme={theme} />

              <div>
                {!isRunning && !isDone && (
                  <button onClick={startSolving} style={{
                    width: "100%", padding: "10px",
                    background: "transparent", border: `2px solid ${t.green}`,
                    borderRadius: 6, cursor: "pointer", color: t.green,
                    fontWeight: 700, fontSize: 13, fontFamily: "monospace", letterSpacing: 1,
                  }}>
                    ▶ SOLVE PUZZLE
                  </button>
                )}
                {isDone && (
                  <div style={{ display: "flex", gap: 6 }}>
                    <button onClick={() => { resetState(); }} style={{
                      flex: 1, padding: 8, background: "transparent",
                      border: `1px solid ${t.border}`, borderRadius: 6, cursor: "pointer",
                      color: t.textDim, fontWeight: 600, fontSize: 11, fontFamily: "monospace",
                    }}>↺ RESET</button>
                    <button onClick={fullReset} style={{
                      flex: 1, padding: 8, background: "transparent",
                      border: `1px solid ${t.accent}`, borderRadius: 6, cursor: "pointer",
                      color: t.accent, fontWeight: 600, fontSize: 11, fontFamily: "monospace",
                    }}>NEW PUZZLE</button>
                  </div>
                )}
                {isRunning && (
                  <div style={{
                    textAlign: "center", padding: 8, color: t.yellow,
                    fontSize: 12, fontFamily: "monospace", animation: "pulse 1.5s infinite",
                  }}>● Agent is solving...</div>
                )}
              </div>

              {finalResult && (
                <div style={{
                  padding: 10, textAlign: "center", borderRadius: 8,
                  background: finalResult.metrics.perfect ? (theme === "dark" ? "#052e16" : "#f0fdf4") : (theme === "dark" ? "#1c1917" : "#fef2f2"),
                  border: `1px solid ${finalResult.metrics.perfect ? t.green : t.red}`,
                  fontFamily: "monospace",
                }}>
                  <div style={{
                    fontSize: 14, fontWeight: 700,
                    color: finalResult.metrics.perfect ? t.green : t.red,
                  }}>
                    {finalResult.metrics.perfect ? "PERFECT SOLVE" : `${finalResult.metrics.correct_words}/${finalResult.metrics.total_words} WORDS`}
                  </div>
                  <div style={{ fontSize: 10, color: t.textDim, marginTop: 3 }}>
                    {finalResult.metrics.correct_words}/{finalResult.metrics.total_words} words
                    · {(finalResult.metrics.letter_accuracy * 100).toFixed(1)}% letters
                    · {finalResult.passes_used} pass{finalResult.passes_used > 1 ? "es" : ""}
                    · {finalResult.elapsed.toFixed(1)}s
                  </div>
                </div>
              )}
            </div>

            {/* Right: Clue Panel */}
            <div style={{
              flex: 1, background: t.panel, border: `1px solid ${t.border}`,
              borderRadius: 10, padding: 12, minWidth: 0,
              height: puzzle.rows * (puzzle.rows > 10 ? 37 : 49) + 6,
              overflow: "hidden", display: "flex", flexDirection: "column",
            }}>
              <StrategyLegend theme={theme} />
              <div style={{ flex: 1, overflow: "hidden" }}>
                <CluePanel puzzle={puzzle} slotStatuses={slotStatuses}
                  highlightSlot={highlightSlot} setHighlightSlot={setHighlightSlot}
                  filledAnswers={filledAnswers} slotSources={slotSources} theme={theme} />
              </div>
            </div>
          </div>

          {/* BOTTOM: Agent Thinking Log */}
          <div style={{
            marginTop: 14, background: t.panel, border: `1px solid ${t.border}`,
            borderRadius: 10, padding: 12, display: "flex", flexDirection: "column",
            height: 220,
          }}>
            <div style={{
              display: "flex", justifyContent: "center", alignItems: "center", position: "relative",
              borderBottom: `1px solid ${t.border}`, paddingBottom: 6, marginBottom: 6,
            }}>
              <span style={{
                color: t.accent, fontWeight: 700, fontSize: 10,
                letterSpacing: 2, fontFamily: "monospace",
              }}>AGENT THINKING LOG</span>
              <span style={{
                color: t.textFaint, fontSize: 10, fontFamily: "monospace",
                position: "absolute", right: 0,
              }}>{logEntries.length} events</span>
            </div>
            <div ref={logRef} style={{ flex: 1, overflowY: "auto", paddingRight: 4 }}>
              {logEntries.length === 0 && !isRunning && (
                <div style={{
                  color: t.textFaint, fontSize: 12, padding: 20,
                  textAlign: "center", fontStyle: "italic", opacity: 0.5,
                }}>
                  {puzzle ? "Press SOLVE PUZZLE to watch the agent think..." : "Select a puzzle"}
                </div>
              )}
              {logEntries.map((entry, i) => (
                <LogEntry key={i} entry={entry} isLatest={i === logEntries.length - 1} theme={theme} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}