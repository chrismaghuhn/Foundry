import { fetchHealth, fetchModules } from "../api/client.js";
import {
  bindRunnerPanel,
  createRunnerState,
  renderRunnerPanel,
} from "./runnerPanel.js";
import {
  createLabState,
  initLabPanel,
  renderLabPanelShell,
  bindLabPanel,
} from "./labPanel.js";

export async function loadRunnerContext() {
  const health = await fetchHealth();
  if (!health.ok) {
    return { apiOnline: false, modulesById: {} };
  }
  try {
    const modules = await fetchModules();
    return {
      apiOnline: true,
      modulesById: Object.fromEntries(modules.map((m) => [m.moduleId, m])),
    };
  } catch {
    return { apiOnline: true, modulesById: {} };
  }
}

export function renderModuleDetail(mod, cluster, helpers, runnerState, labState) {
  const { escapeHtml, clusterBadge, statusBadge, renderPlayground } = helpers;

  const examples = mod.examples?.length
    ? mod.examples.map((f) => `<li>${escapeHtml(f)}</li>`).join("")
    : "<li>No examples.py in package</li>";
  const tests = mod.tests?.length
    ? mod.tests.map((f) => `<li>${escapeHtml(f)}</li>`).join("")
    : "<li>No test suite in package</li>";

  const meta = runnerState.modulesById?.[mod.id];
  if (meta) {
    runnerState.runnerMeta = meta;
  }

  const hideStaticPlayground =
    labState?.apiOnline && labState?.definition && mod.playground;
  const playground = hideStaticPlayground ? "" : renderPlayground(mod);

  return `
    <article class="detail-layout">
      <div class="detail-main">
        <header class="detail-header">
          <h1>${escapeHtml(mod.name)}</h1>
          <div class="detail-badges">
            ${clusterBadge(mod.cluster)}
            ${statusBadge(mod.status)}
          </div>
        </header>
        <div class="prose">
          <p>${escapeHtml(mod.summary)}</p>
          <h2>Purpose</h2>
          <p>${escapeHtml(mod.purpose)}</p>
          ${
            mod.productionNote
              ? `<h2>Deployment note</h2><p>${escapeHtml(mod.productionNote)}</p>`
              : ""
          }
          ${renderLabPanelShell(mod, labState || createLabState(), escapeHtml)}
          <details class="runner-collapse panel">
            <summary>Technical runner (pytest / examples)</summary>
            ${renderRunnerPanel(mod, runnerState, escapeHtml)}
          </details>
          ${playground}
        </div>
      </div>
      <aside class="detail-aside">
        <div class="panel">
          <h3>Run locally (terminal)</h3>
          <p class="prose" style="margin:0 0 var(--space-md)">
            <code>${escapeHtml(mod.runHint || `cd ${mod.id}`)}</code>
          </p>
          ${
            cluster
              ? `<p class="stats-line">${escapeHtml(cluster.description)}</p>`
              : ""
          }
        </div>
        <div class="panel" style="margin-top: var(--space-md)">
          <h3>Example files</h3>
          <ul class="file-list">${examples}</ul>
        </div>
        <div class="panel" style="margin-top: var(--space-md)">
          <h3>Tests</h3>
          <ul class="file-list">${tests}</ul>
        </div>
      </aside>
    </article>
  `;
}

export function setupModuleDetail(mod, runnerState, labState, rerender) {
  bindRunnerPanel(mod, runnerState, rerender);
  if (labState.definition) {
    bindLabPanel(mod, labState, rerender);
  }
}

export { createRunnerState, createLabState, initLabPanel };
