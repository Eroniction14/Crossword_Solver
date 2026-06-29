import { themes, strategyColors } from "./themes";

export function StrategyLegend({ theme }) {
  const t = themes[theme];
  return (
    <div style={{
      display: "flex", gap: 12, fontSize: 10, fontFamily: "monospace",
      color: t.textFaint, padding: "6px 0",
    }}>
      <span>Strategy:</span>
      <span style={{ color: strategyColors["RETRIEVAL"] }}>● RETRIEVAL</span>
      <span style={{ color: strategyColors["LLM"] }}>● LLM</span>
      <span style={{ color: strategyColors["BOTH"] }}>● BOTH</span>
    </div>
  );
}

export default function CluePanel({ puzzle, slotStatuses, highlightSlot, setHighlightSlot, filledAnswers, slotSources, theme }) {
  if (!puzzle) return null;
  const t = themes[theme];
  const across = Object.entries(puzzle.slots)
    .filter(([, s]) => s.direction === "across")
    .sort((a, b) => a[1].number - b[1].number);
  const down = Object.entries(puzzle.slots)
    .filter(([, s]) => s.direction === "down")
    .sort((a, b) => a[1].number - b[1].number);

  const renderClue = ([id, slot]) => {
    const status = slotStatuses[id] || "pending";
    const answer = filledAnswers[id] || "";
    const source = slotSources[id] || "";
    const srcColor = strategyColors[source] || t.textFaint;

    return (
      <div key={id}
        onMouseEnter={() => setHighlightSlot(id)}
        onMouseLeave={() => setHighlightSlot(null)}
        style={{
          padding: "3px 6px", borderRadius: 4, cursor: "pointer",
          fontSize: 11, color: highlightSlot === id ? t.text : t.textDim,
          background: highlightSlot === id ? (theme === "dark" ? "rgba(59,130,246,0.1)" : "rgba(59,130,246,0.08)") : "transparent",
          transition: "all 0.2s", display: "flex", gap: 6, alignItems: "flex-start",
          borderLeft: status === "solved" ? `2px solid ${srcColor}` :
            status === "working" ? `2px solid ${t.yellow}` : "2px solid transparent",
        }}>
        <span style={{ color: t.textFaint, fontWeight: 600, minWidth: 18 }}>{slot.number}.</span>
        <span style={{ flex: 1 }}>{slot.clue} <span style={{ color: theme === "dark" ? "#334155" : "#cbd5e1" }}>({slot.length})</span></span>
        {answer && (
          <span style={{
            color: srcColor,
            fontFamily: "'JetBrains Mono', monospace", fontSize: 10, fontWeight: 600,
          }}>{answer}</span>
        )}
      </div>
    );
  };

  return (
    <div style={{ display: "flex", gap: 16, fontSize: 11, height: "100%" }}>
      <div style={{ flex: 1, overflowY: "auto" }}>
        <div style={{ color: t.accent, fontWeight: 700, fontSize: 10, letterSpacing: 2, marginBottom: 6, fontFamily: "monospace" }}>ACROSS</div>
        {across.map(renderClue)}
      </div>
      <div style={{ flex: 1, overflowY: "auto" }}>
        <div style={{ color: t.accent, fontWeight: 700, fontSize: 10, letterSpacing: 2, marginBottom: 6, fontFamily: "monospace" }}>DOWN</div>
        {down.map(renderClue)}
      </div>
    </div>
  );
}