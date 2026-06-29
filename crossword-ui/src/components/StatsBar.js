import { themes } from "./themes";

export default function StatsBar({ wordsFound, totalWords, conflicts, passNum, elapsed, phase, theme }) {
  const t = themes[theme];
  const pct = totalWords > 0 ? Math.round((wordsFound / totalWords) * 100) : 0;
  return (
    <div style={{
      display: "flex", gap: 8, padding: "8px 12px", flexWrap: "wrap",
      background: t.panel, borderRadius: 8, border: `1px solid ${t.border}`,
      fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
      alignItems: "center",
    }}>
      <div style={{ flex: 1, minWidth: 120 }}>
        <div style={{ color: t.textFaint, fontSize: 9, letterSpacing: 1.5 }}>PROGRESS</div>
        <div style={{ marginTop: 3, background: theme === "dark" ? "#1e293b" : "#e2e8f0", borderRadius: 4, height: 5, overflow: "hidden" }}>
          <div style={{
            width: `${pct}%`, height: "100%",
            background: conflicts > 0 ? `linear-gradient(90deg, ${t.yellow}, ${t.red})` :
              `linear-gradient(90deg, ${t.green}, ${t.accent})`,
            borderRadius: 4, transition: "width 0.5s ease",
          }} />
        </div>
      </div>
      {[
        { label: "WORDS", value: `${wordsFound}/${totalWords}`, color: t.green },
        { label: "CONFLICTS", value: conflicts, color: conflicts > 0 ? t.red : t.green },
        { label: "PASS", value: passNum, color: t.purple },
        { label: "TIME", value: `${elapsed}s`, color: t.yellow },
      ].map(({ label, value, color }) => (
        <div key={label} style={{ textAlign: "center", minWidth: 48 }}>
          <div style={{ color: t.textFaint, fontSize: 9, letterSpacing: 1 }}>{label}</div>
          <div style={{ color, fontSize: 16, fontWeight: 600, marginTop: 1 }}>{value}</div>
        </div>
      ))}
      {phase && (
        <div style={{ minWidth: 100, textAlign: "right" }}>
          <div style={{ color: t.textFaint, fontSize: 9, letterSpacing: 1 }}>PHASE</div>
          <div style={{ color: t.accent, fontSize: 11, marginTop: 2 }}>{phase}</div>
        </div>
      )}
    </div>
  );
}