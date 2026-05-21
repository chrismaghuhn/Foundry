import { fetchLabDefinition, fetchLabsHealth, runLab } from "../api/labsClient.js";
import { collectLabInput, renderLabInputs } from "./labInputs.js";
import { renderLabPresets } from "./labPresets.js";
import { renderLabVisual } from "./labVisuals.js";

export function createLabState() {
  return {
    apiOnline: false,
    definition: null,
    status: "idle",
    lastResult: null,
    running: false,
    selectedPreset: null,
  };
}

export function renderLabPanelShell(mod, labState, escapeHtml) {
  const offline = !labState.apiOnline
    ? `
    <div class="lab-offline-banner panel">
      <p><strong>Interactive Lab unavailable</strong> — start the local API:</p>
      <pre>cd api
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000</pre>
    </div>`
    : "";

  const def = labState.definition;
  if (!def && labState.apiOnline) {
    return `<section class="lab-panel panel"><p class="stats-line">Loading lab…</p></section>`;
  }
  if (!def) {
    return `<section class="lab-panel panel">${offline}</section>`;
  }

  const security =
    def.securityNote || def.safety === "demo" || def.safety === "read-only"
      ? `<div class="lab-security-banner">${escapeHtml(
          def.securityNote ||
            "Educational demo — not for production security or cryptography."
        )}</div>`
      : "";

  const status = labState.running ? "running" : labState.status;
  const result = labState.lastResult;
  const primary = def.primaryAction || "Run";

  let resultBlock = "";
  if (result) {
    const expl = (result.explanation || [])
      .map((e) => `<li>${escapeHtml(e)}</li>`)
      .join("");
    resultBlock = `
      <div class="lab-result">
        <div class="lab-status-row">
          <span class="lab-status lab-status-${status}">${escapeHtml(status)}</span>
          <span class="stats-line">${escapeHtml(result.summary || "")}</span>
        </div>
        ${result.visual ? `<div class="lab-visual-wrap">${renderLabVisual(result.visual, escapeHtml)}</div>` : ""}
        ${
          expl
            ? `<div class="lab-explanation"><h4>What happened?</h4><ul>${expl}</ul></div>`
            : ""
        }
      </div>`;
  }

  return `
    <section class="lab-panel panel" data-module-id="${escapeHtml(mod.id)}">
      <header class="lab-header">
        <h2>Interactive Lab</h2>
        <p class="lab-mission">${escapeHtml(def.mission || def.description)}</p>
      </header>
      ${offline}
      ${security}
      ${renderLabPresets(def, escapeHtml)}
      ${renderLabInputs(def, escapeHtml)}
      <div class="lab-actions">
        <button type="button" class="btn btn-primary" id="lab-run" ${
          labState.running ? "disabled" : ""
        }>${escapeHtml(primary)}</button>
        ${
          mod.id === "automata" || mod.id === "turing"
            ? '<button type="button" class="btn btn-ghost" id="lab-step">Step</button>'
            : ""
        }
        <button type="button" class="btn btn-ghost" id="lab-reset">Reset</button>
      </div>
      ${resultBlock}
    </section>`;
}

export async function loadLabContext(moduleId) {
  const health = await fetchLabsHealth();
  if (!health.ok) {
    return { apiOnline: false, definition: null };
  }
  try {
    const definition = await fetchLabDefinition(moduleId);
    return { apiOnline: true, definition };
  } catch {
    return { apiOnline: true, definition: null };
  }
}

export function bindLabPanel(mod, labState, rerender) {
  const panel = document.querySelector(".lab-panel");
  if (!panel || !labState.definition) return;

  const form = panel.querySelector("[data-lab-form]");

  async function executeRun(extra = {}) {
    labState.running = true;
    labState.status = "running";
    rerender();
    try {
      const input = collectLabInput(form);
      const prev = labState.lastResult?.visual?.data;
      if (extra.action === "step" && prev) {
        input.state = {
          cells: prev.cells,
          width: prev.width,
          height: prev.height,
          generation: prev.generation,
        };
      }
      const body = {
        presetId: labState.selectedPreset,
        input: { ...input, ...extra },
        action: extra.action,
      };
      const result = await runLab(mod.id, body);
      labState.lastResult = result;
      labState.status = result.status === "ok" ? "passed" : "failed";
      if (result.status === "error") labState.status = "failed";
    } catch (err) {
      labState.lastResult = {
        status: "error",
        summary: err.detail || err.message || "Lab request failed",
        explanation: [],
      };
      labState.status = "failed";
    } finally {
      labState.running = false;
      rerender();
    }
  }

  panel.querySelectorAll("[data-preset-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      labState.selectedPreset = btn.dataset.presetId;
      executeRun();
    });
  });

  const defPreset = labState.definition.presets?.find((p) => p.isDefault);
  if (defPreset && !labState.selectedPreset) {
    labState.selectedPreset = defPreset.id;
  }

  document.getElementById("lab-run")?.addEventListener("click", () => executeRun());
  document.getElementById("lab-step")?.addEventListener("click", () =>
    executeRun({ action: "step" })
  );
  document.getElementById("lab-reset")?.addEventListener("click", () => {
    labState.lastResult = null;
    labState.status = "idle";
    labState.selectedPreset =
      labState.definition.presets?.find((p) => p.isDefault)?.id || null;
    rerender();
  });
}

export async function initLabPanel(mod, labState, rerender) {
  const ctx = await loadLabContext(mod.id);
  labState.apiOnline = ctx.apiOnline;
  labState.definition = ctx.definition;
  const defPreset = ctx.definition?.presets?.find((p) => p.isDefault);
  if (defPreset) {
    labState.selectedPreset = defPreset.id;
  }
  rerender();
  if (ctx.definition && ctx.apiOnline) {
    bindLabPanel(mod, labState, rerender);
    if (defPreset && !labState.lastResult) {
      document.getElementById("lab-run")?.click();
    }
  }
}
