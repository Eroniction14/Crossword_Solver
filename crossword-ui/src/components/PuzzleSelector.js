import { useState, useEffect } from "react";
import { themes } from "./themes";

const API = window.location.hostname === "localhost" && window.location.port === "3000"
  ? "http://localhost:5000/api"
  : "/api";

export default function PuzzleSelector({ onSelect, theme }) {
  const t = themes[theme];
  const [puzzles, setPuzzles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCustom, setShowCustom] = useState(false);
  const [customJson, setCustomJson] = useState("");
  const [customError, setCustomError] = useState("");

  useEffect(() => {
    fetch(`${API}/puzzles`)
      .then(r => r.json())
      .then(data => { setPuzzles(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const handleCustomSubmit = () => {
    try {
      const parsed = JSON.parse(customJson);
      if (!parsed.grid || !parsed.clues) {
        setCustomError("JSON must have 'grid' and 'clues' fields");
        return;
      }
      setCustomError("");
      onSelect(null, parsed);
    } catch (e) {
      setCustomError("Invalid JSON: " + e.message);
    }
  };

  if (loading) return <div style={{ color: t.textFaint, padding: 20, textAlign: "center" }}>Loading puzzles...</div>;

  return (
    <div>
      <div style={{ color: t.textDim, fontSize: 12, marginBottom: 10, fontFamily: "monospace" }}>
        Select a puzzle to solve:
      </div>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        {puzzles.map(p => (
          <button key={p.filename} onClick={() => onSelect(p.filename)}
            style={{
              padding: "10px 16px", background: theme === "dark" ? "#1e293b" : "#f1f5f9",
              border: `1px solid ${t.border}`, borderRadius: 6, cursor: "pointer",
              color: t.text, fontFamily: "monospace", fontSize: 12,
              transition: "all 0.2s",
            }}
            onMouseOver={e => { e.target.style.borderColor = t.accent; }}
            onMouseOut={e => { e.target.style.borderColor = t.border; }}
          >
            <div style={{ fontWeight: 600 }}>{p.title}</div>
            <div style={{ fontSize: 10, color: t.textFaint, marginTop: 2 }}>{p.rows}x{p.cols}</div>
          </button>
        ))}
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <label style={{
          display: "inline-block", padding: "8px 16px",
          background: theme === "dark" ? "#1e293b" : "#f1f5f9",
          border: `1px solid ${t.border}`, borderRadius: 6, cursor: "pointer",
          color: t.text, fontFamily: "monospace", fontSize: 12,
        }}>
          Upload .puz or .json
          <input type="file" accept=".puz,.json" style={{ display: "none" }}
            onChange={async (e) => {
              const file = e.target.files[0];
              if (!file) return;
              const formData = new FormData();
              formData.append("file", file);
              try {
                const res = await fetch(`${API}/upload`, { method: "POST", body: formData });
                const data = await res.json();
                if (data.error) { alert(data.error); return; }
                onSelect(data.filename);
              } catch (err) { alert("Upload failed: " + err.message); }
            }}
          />
        </label>
      </div>

      <button onClick={() => setShowCustom(!showCustom)} style={{
        background: "transparent", border: `1px solid ${t.border}`, borderRadius: 6,
        color: t.textFaint, padding: "6px 12px", cursor: "pointer",
        fontFamily: "monospace", fontSize: 11,
      }}>
        {showCustom ? "Hide" : "Paste custom puzzle JSON"}
      </button>

      {showCustom && (
        <div style={{ marginTop: 10 }}>
          <textarea value={customJson} onChange={e => setCustomJson(e.target.value)}
            placeholder='{"title":"My Puzzle","grid":[...],"clues":{...},"answers":{...}}'
            style={{
              width: "100%", height: 120, background: theme === "dark" ? "#0f172a" : "#f8fafc",
              color: t.text, border: `1px solid ${t.border}`, borderRadius: 6, padding: 10,
              fontFamily: "monospace", fontSize: 11, resize: "vertical",
            }} />
          {customError && <div style={{ color: t.red, fontSize: 11, marginTop: 4 }}>{customError}</div>}
          <button onClick={handleCustomSubmit} style={{
            marginTop: 6, padding: "8px 16px",
            background: theme === "dark" ? "#1e293b" : "#f1f5f9",
            border: `1px solid ${t.accent}`, borderRadius: 6, cursor: "pointer",
            color: t.accent, fontFamily: "monospace", fontSize: 12, fontWeight: 600,
          }}>
            Load Custom Puzzle
          </button>
        </div>
      )}
    </div>
  );
}