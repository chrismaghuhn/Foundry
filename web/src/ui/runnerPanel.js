import { runExample, runTest } from "../api/client.js";

export function createRunnerState() {
  return {
    status: "idle",
    lastResult: null,
    running: false,
    apiOnline: false,
    runnerMeta: null,
  };
}

export function renderRunnerPanel(mod, runnerState, escapeHtml) {
  const meta = runnerState.runnerMeta;
  const testAvail =
    meta?.testAvailable ?? (mod.tests?.length > 0);
  const exampleAvail =
    meta?.exampleAvailable ?? (mod.examples?.length > 0);

  const offlineBanner = !runnerState.apiOnline
    ? `
    <div class="runner-offline-banner panel">
      <p><strong>Runner API is not running.</strong></p>
      <p class="stats-line">Start it in a second terminal:</p>
      <pre>cd api
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000</pre>
      <p class="stats-line">Catalog and details still work without the API.</p>
    </div>`
    : "";

  const result = runnerState.lastResult;
  const status = runnerState.running ? "running" : runnerState.status;
  const statusClass = `runner-status-${status}`;

  let outputBlock = "";
  if (result) {
    outputBlock = `
      <div class="runner-output-meta">
        <span class="badge ${statusClass}">${escapeHtml(result.status)}</span>
        <span class="stats-line">${result.durationMs} ms · limit ${result.timeoutMs} ms</span>
        ${
          result.exitCode !== null && result.exitCode !== undefined
            ? `<span class="stats-line">exit ${result.exitCode}</span>`
            : ""
        }
      </div>
      <p class="stats-line">Command</p>
      <pre class="runner-cmd">${escapeHtml(
        (result.command || []).join(" ") || "(none)"
      )}</pre>
      <p class="stats-line">stdout</p>
      <pre class="runner-stream">${escapeHtml(result.stdout || "(empty)")}</pre>
      <p class="stats-line">stderr</p>
      <pre class="runner-stream runner-stream-err">${escapeHtml(
        result.stderr || "(empty)"
      )}</pre>
      ${result.truncated ? '<p class="mock-note">Output was truncated.</p>' : ""}
    `;
  } else if (status === "idle") {
    outputBlock =
      '<p class="stats-line">Run tests or an example to see output here.</p>';
  }

  return `
    <section class="runner-section panel" id="runner-section">
      <h2>Run locally from browser</h2>
      <p class="stats-line">Localhost only. Whitelisted commands — nothing from this page is executed as raw input.</p>
      ${offlineBanner}
      <div class="runner-actions">
        <button type="button" class="btn btn-primary" id="runner-test" ${
          !runnerState.apiOnline || runnerState.running ? "disabled" : ""
        } ${!testAvail ? 'title="No test suite configured"' : ""}>
          Run tests
        </button>
        <button type="button" class="btn" id="runner-example" ${
          !runnerState.apiOnline || runnerState.running ? "disabled" : ""
        } ${!exampleAvail ? 'title="No example runner configured"' : ""}>
          Run example
        </button>
        <button type="button" class="btn btn-ghost" id="runner-copy" ${
          runnerState.running ? "disabled" : ""
        }>
          Copy command
        </button>
      </div>
      ${
        !testAvail
          ? '<p class="stats-line runner-hint">No test suite configured for this module.</p>'
          : ""
      }
      ${
        !exampleAvail
          ? '<p class="stats-line runner-hint">No example runner configured for this module.</p>'
          : ""
      }
      <div class="runner-panel ${statusClass}">
        ${runnerState.running ? `<p class="stats-line">Running <strong>${escapeHtml(mod.name)}</strong>…</p>` : ""}
        ${outputBlock}
      </div>
    </section>
  `;
}

export function bindRunnerPanel(mod, runnerState, onUpdate) {
  const testBtn = document.getElementById("runner-test");
  const exampleBtn = document.getElementById("runner-example");
  const copyBtn = document.getElementById("runner-copy");

  async function execute(action, fn) {
    if (!runnerState.apiOnline || runnerState.running) return;
    runnerState.running = true;
    runnerState.status = "running";
    runnerState.lastResult = null;
    onUpdate();

    try {
      const result = await fn(mod.id);
      runnerState.lastResult = result;
      runnerState.status = result.status;
    } catch (err) {
      runnerState.lastResult = {
        status: "failed",
        command: [],
        durationMs: 0,
        timeoutMs: 0,
        stdout: "",
        stderr: String(err.message || err),
        exitCode: null,
        truncated: false,
      };
      runnerState.status = "failed";
    } finally {
      runnerState.running = false;
      onUpdate();
    }
  }

  testBtn?.addEventListener("click", () => execute("test", runTest));
  exampleBtn?.addEventListener("click", () => execute("example", runExample));

  copyBtn?.addEventListener("click", async () => {
    const r = runnerState.lastResult;
    const text =
      r?.command?.length > 0
        ? `cd ${mod.id}\n${r.command.join(" ")}`
        : mod.runHint || `cd ${mod.id}`;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
      setTimeout(() => {
        copyBtn.textContent = "Copy command";
      }, 1500);
    } catch {
      copyBtn.textContent = "Copy failed";
    }
  });
}
