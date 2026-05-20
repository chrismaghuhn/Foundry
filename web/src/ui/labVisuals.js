export function renderLabVisual(visual, escapeHtml) {
  if (!visual?.type) {
    return `<p class="lab-visual-empty">No visual for this run.</p>`;
  }
  const d = visual.data || {};
  switch (visual.type) {
    case "graph-path": {
      const path = (d.path || []).join(" → ");
      const visited = (d.visited || []).join(", ");
      return `
        <div class="lab-visual-graph">
          <p><strong>Path:</strong> ${escapeHtml(path || "—")}</p>
          <p class="stats-line">Visited order: ${escapeHtml(visited)}</p>
          <p class="stats-line">${escapeHtml(d.start || "")} → ${escapeHtml(d.goal || "")}</p>
        </div>`;
    }
    case "diff-chunks": {
      const chunks = d.chunks || [];
      const html = chunks
        .map(
          (c) =>
            `<span class="diff-chunk diff-${escapeHtml(c.kind)}">${escapeHtml(c.text)}</span>`
        )
        .join("");
      return `<div class="lab-visual-diff">${html}</div>`;
    }
    case "grid": {
      const w = d.width || 20;
      const h = d.height || 15;
      const live = new Set((d.cells || []).map((c) => `${c[0]},${c[1]}`));
      let rows = "";
      for (let y = 0; y < h; y++) {
        let row = "";
        for (let x = 0; x < w; x++) {
          row += live.has(`${x},${y}`)
            ? '<span class="cell-alive">■</span>'
            : '<span class="cell-dead">·</span>';
        }
        rows += `<div class="life-row">${row}</div>`;
      }
      return `<div class="lab-visual-grid" data-gen="${d.generation ?? 0}">${rows}</div>`;
    }
    case "tape":
      return `
        <div class="lab-visual-tape">
          <pre>${escapeHtml(d.tape || "")}</pre>
          <p class="stats-line">Head @ ${d.head} · state ${escapeHtml(d.state || "")} · step ${d.step ?? 0}</p>
        </div>`;
    case "regex-trace": {
      const steps = (d.steps || [])
        .slice(0, 12)
        .map(
          (s) =>
            `<li>@${s.position} '${escapeHtml(s.char || "")}' active=${s.active} ${escapeHtml(s.note || "")}</li>`
        )
        .join("");
      return `<ul class="lab-trace">${steps}</ul>`;
    }
    case "shares": {
      const shares = (d.shares || [])
        .map((s) => `<li>Share #${s.index} (x=${s.x})</li>`)
        .join("");
      return `<ul class="lab-shares">${shares}</ul><p class="stats-line">Selected: ${escapeHtml((d.selected || []).join(", "))} · k=${d.k}</p>`;
    }
    case "fsm": {
      const log = (d.log || [])
        .map(
          (e) =>
            `<li>${escapeHtml(e.event)}: ${escapeHtml(e.from)} → ${escapeHtml(e.to)}</li>`
        )
        .join("");
      return `<p><strong>State:</strong> ${escapeHtml(d.state || "")}</p><ul>${log}</ul>`;
    }
    case "replicas":
      return `<p>Replica A: ${d.replicaA} · Replica B: ${d.replicaB} → <strong>${d.merged}</strong></p>`;
    case "sketch-stats":
      return `<p>Query <code>${escapeHtml(d.query || "")}</code> → ${d.maybe ? "maybe in set" : "not in set"} (≈ FPR ${Number(d.approxFpr || 0).toFixed(4)})</p>`;
    case "huffman":
      return `<p><strong>${escapeHtml(d.text || "")}</strong> → ${d.bitLength} bits</p><pre class="lab-bits">${escapeHtml((d.bits || "").slice(0, 120))}</pre>`;
    case "scenario-log": {
      const log = (d.log || []).map((l) => `<li>${escapeHtml(l)}</li>`).join("");
      return `<ul class="lab-scenario-log">${log}</ul>`;
    }
    case "guided-cards": {
      const cards = (d.cards || [])
        .map(
          (c) =>
            `<div class="lab-card"><h4>${escapeHtml(c.title)}</h4><p>${escapeHtml(c.body)}</p></div>`
        )
        .join("");
      return `<div class="lab-guided-cards">${cards}</div>`;
    }
    case "json-result":
    default:
      return `<pre class="lab-json">${escapeHtml(JSON.stringify(d, null, 2))}</pre>`;
  }
}
