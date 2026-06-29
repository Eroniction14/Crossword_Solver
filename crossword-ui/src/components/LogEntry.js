import { themes } from "./themes";

export default function LogEntry({ entry, isLatest, theme }) {
  const t = themes[theme];
  const styles = {
    think: { color: t.accent, label: "THINK" },
    action: { color: t.yellow, label: "ACT" },
    result: { color: t.green, label: "DONE" },
    decision: { color: t.purple, label: "PLAN" },
    slot_working: { color: t.yellow, label: "CLUE" },
    slot_done: { color: t.green, label: "CLUE" },
  };
  const s = styles[entry.type] || styles.think;
  return (
    <div style={{
      display: "flex", gap: 8, padding: "3px 0",
      fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
      lineHeight: 1.6, opacity: isLatest ? 1 : 0.65,
      animation: isLatest ? "slideIn 0.25s ease" : "none",
    }}>
      <span style={{ color: s.color, fontWeight: 700, minWidth: 40, fontSize: 9.5 }}>
        {s.label}
      </span>
      <span style={{ color: t.textDim, wordBreak: "break-word" }}>{entry.message}</span>
    </div>
  );
}