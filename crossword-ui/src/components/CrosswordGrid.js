import { themes } from "./themes";

function getCellNumbers(slots) {
  const nums = {};
  for (const [, slot] of Object.entries(slots)) {
    const [r, c] = slot.cells[0];
    const key = `${r}-${c}`;
    if (!nums[key] || slot.number < nums[key]) nums[key] = slot.number;
  }
  return nums;
}

export default function CrosswordGrid({ puzzle, filledCells, cellStates, workingSlots, highlightSlot, onCellHover, theme }) {
  if (!puzzle) return null;
  const t = themes[theme];
  const cellNums = getCellNumbers(puzzle.slots);
  const cellSize = puzzle.rows > 10 ? 36 : 48;

  const hlCells = new Set();
  if (highlightSlot && puzzle.slots[highlightSlot]) {
    puzzle.slots[highlightSlot].cells.forEach(([r, c]) => hlCells.add(`${r}-${c}`));
  }
  const wkCells = new Set();
  for (const sid of workingSlots) {
    if (puzzle.slots[sid]) {
      puzzle.slots[sid].cells.forEach(([r, c]) => wkCells.add(`${r}-${c}`));
    }
  }

  return (
    <div style={{
      display: "inline-block", background: "#333",
      padding: 1, borderRadius: 0, border: `2px solid #333`,
    }}>
      {Array.from({ length: puzzle.rows }, (_, r) => (
        <div key={r} style={{ display: "flex", gap: 0, marginBottom: 0 }}>
          {Array.from({ length: puzzle.cols }, (_, c) => {
            const isBlack = puzzle.grid[r][c] === "#";
            const k = `${r}-${c}`;
            const letter = filledCells[k] || "";
            const num = cellNums[k];
            const isHl = hlCells.has(k);
            const isWk = wkCells.has(k);
            const state = cellStates[k] || "empty";

            const bg = isBlack ? t.cellBlack :
              state === "conflict" ? t.cellRed :
              state === "confident" ? t.cellGreen :
              isHl ? "#dbeafe" :
              isWk ? "#fef3c7" :
              t.cellWhite;

            const letterColor = isBlack ? "transparent" :
              state === "conflict" ? t.cellRedText :
              state === "confident" ? t.cellGreenText :
              t.cellText;

            const cellBorder = isBlack
              ? "1px solid #333"
              : "1px solid #333";

            return (
              <div key={c}
                onMouseEnter={() => onCellHover && onCellHover(r, c)}
                onMouseLeave={() => onCellHover && onCellHover(null, null)}
                style={{
                  width: cellSize, height: cellSize, background: bg,
                  borderRadius: 0, position: "relative",
                  border: cellBorder,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "background 0.3s ease",
                  cursor: isBlack ? "default" : "pointer",
                }}>
                {num && !isBlack && (
                  <span style={{
                    position: "absolute", top: 1, left: 2,
                    fontSize: cellSize > 40 ? 9 : 7, color: "#666",
                    fontFamily: "'Arial', sans-serif", fontWeight: 600,
                  }}>{num}</span>
                )}
                {letter && !isBlack && (
                  <span style={{
                    fontSize: cellSize > 40 ? 20 : 14, fontWeight: 700,
                    color: letterColor,
                    fontFamily: "'Arial', sans-serif",
                    animation: "fadeIn 0.3s ease",
                  }}>{letter}</span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}