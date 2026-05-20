import catalog from "./data/modules.json";

const CLUSTER_LABELS = Object.fromEntries(
  catalog.clusters.map((c) => [c.id, c.label])
);

const state = {
  modules: catalog.modules,
  clusters: catalog.clusters,
  filterCluster: "all",
  search: "",
  route: parseRoute(),
};

function parseRoute() {
  const hash = window.location.hash.slice(1) || "/";
  const parts = hash.split("/").filter(Boolean);
  if (parts[0] === "module" && parts[1]) {
    return { view: "detail", id: parts[1] };
  }
  return { view: "catalog" };
}

function navigate(path) {
  window.location.hash = path;
}

function onRouteChange() {
  state.route = parseRoute();
  render();
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function statusBadge(status) {
  const label =
    status === "stable"
      ? "stable"
      : status === "demo"
        ? "demo"
        : "experimental";
  return `<span class="badge badge-${label}">${label}</span>`;
}

function clusterBadge(clusterId) {
  const label = CLUSTER_LABELS[clusterId] || clusterId;
  return `<span class="badge badge-cluster">${escapeHtml(label)}</span>`;
}

function filteredModules() {
  const q = state.search.trim().toLowerCase();
  return state.modules.filter((m) => {
    if (state.filterCluster !== "all" && m.cluster !== state.filterCluster) {
      return false;
    }
    if (!q) return true;
    const hay = [
      m.id,
      m.name,
      m.summary,
      m.purpose,
      CLUSTER_LABELS[m.cluster],
    ]
      .join(" ")
      .toLowerCase();
    return hay.includes(q);
  });
}

function renderHeader() {
  const isCatalog = state.route.view === "catalog";
  return `
    <div class="header-inner">
      <a href="#/" class="brand" data-nav>
        <span class="brand-mark">Foundry</span>
        <span class="brand-name">Console</span>
      </a>
      ${
        isCatalog
          ? `
        <div class="search-wrap">
          <span class="search-icon" aria-hidden="true">⌕</span>
          <input
            type="search"
            class="search-input"
            id="search-input"
            placeholder="Search modules…"
            value="${escapeHtml(state.search)}"
            aria-label="Search modules"
          />
        </div>`
          : `<a href="#/" class="btn btn-ghost" data-nav>← Catalog</a>`
      }
    </div>
  `;
}

function renderFooter() {
  return `
    <p>Foundry developer lab — Python packages on disk, console in the browser. No code execution here.</p>
  `;
}

function renderFilterBar(modules) {
  const counts = { all: state.modules.length };
  for (const c of state.clusters) {
    counts[c.id] = state.modules.filter((m) => m.cluster === c.id).length;
  }

  const chips = [
    { id: "all", label: "All" },
    ...state.clusters.map((c) => ({ id: c.id, label: c.label })),
  ];

  return `
    <div class="filter-bar" role="toolbar" aria-label="Filter by cluster">
      ${chips
        .map(
          (chip) => `
        <button
          type="button"
          class="filter-chip ${state.filterCluster === chip.id ? "is-active" : ""}"
          data-filter="${chip.id}"
        >
          ${escapeHtml(chip.label)}<span class="count">${counts[chip.id] ?? 0}</span>
        </button>`
        )
        .join("")}
    </div>
    <p class="stats-line">${modules.length} module${modules.length === 1 ? "" : "s"} shown</p>
  `;
}

function renderModuleCard(mod) {
  return `
    <a href="#/module/${mod.id}" class="module-card" data-nav>
      <div class="card-top">
        <h2 class="card-name">${escapeHtml(mod.name)}</h2>
        ${statusBadge(mod.status)}
      </div>
      <p class="card-summary">${escapeHtml(mod.summary)}</p>
      <div class="card-meta">
        ${clusterBadge(mod.cluster)}
      </div>
    </a>
  `;
}

function renderPlayground(mod) {
  const pg = mod.playground;
  if (!pg) return "";

  if (pg.type === "static") {
    let body = "";
    if (pg.query) {
      body = `
        <p><strong>Query</strong></p>
        <pre>${escapeHtml(pg.query)}</pre>
        <p><strong>Data</strong></p>
        <pre>${escapeHtml(pg.data)}</pre>
        <p><strong>Result (illustration)</strong></p>
        <pre>${escapeHtml(pg.result)}</pre>
      `;
    } else if (pg.before) {
      body = `
        <p><strong>Before</strong></p>
        <pre>${escapeHtml(pg.before)}</pre>
        <p><strong>After</strong></p>
        <pre>${escapeHtml(pg.after)}</pre>
      `;
    } else if (pg.sample) {
      body = `<pre>${escapeHtml(pg.sample)}</pre>`;
    }
    return `
      <section class="mock-playground panel">
        <h3>${escapeHtml(pg.title)}</h3>
        ${body}
        <p class="mock-note">${escapeHtml(pg.note)}</p>
      </section>
    `;
  }
  return "";
}

function renderDetail(mod) {
  const cluster = state.clusters.find((c) => c.id === mod.cluster);
  const examples = mod.examples?.length
    ? mod.examples.map((f) => `<li>${escapeHtml(f)}</li>`).join("")
    : "<li>No examples.py in package</li>";
  const tests = mod.tests?.length
    ? mod.tests.map((f) => `<li>${escapeHtml(f)}</li>`).join("")
    : "<li>No test suite in package</li>";

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
          ${renderPlayground(mod)}
        </div>
      </div>
      <aside class="detail-aside">
        <div class="panel">
          <h3>Run locally</h3>
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

function renderCatalog() {
  const modules = filteredModules();
  const clusterDesc =
    state.filterCluster !== "all"
      ? state.clusters.find((c) => c.id === state.filterCluster)?.description
      : "Browse algorithms, DSLs, async utilities, and protocol sketches from the Foundry monorepo.";

  return `
    <section class="page-hero">
      <h1>Module archive</h1>
      <p class="lede">${escapeHtml(clusterDesc)}</p>
    </section>
    <div class="toolbar">${renderFilterBar(modules)}</div>
    ${
      modules.length === 0
        ? `
      <div class="empty-state">
        <h2>No modules match</h2>
        <p>Try clearing the search or choosing another cluster filter.</p>
        <button type="button" class="btn btn-primary" id="reset-filters" style="margin-top: var(--space-lg)">
          Reset filters
        </button>
      </div>`
        : `<div class="catalog-grid">${modules.map(renderModuleCard).join("")}</div>`
    }
  `;
}

function renderNotFound() {
  return `
    <div class="not-found">
      <h1>Module not found</h1>
      <p class="prose">No package with that id exists in the catalog.</p>
      <a href="#/" class="btn btn-primary" data-nav style="margin-top: var(--space-lg)">Back to catalog</a>
    </div>
  `;
}

function render() {
  document.getElementById("site-header").innerHTML = renderHeader();
  document.getElementById("site-footer").innerHTML = renderFooter();

  const main = document.getElementById("site-main");
  if (state.route.view === "detail") {
    const mod = state.modules.find((m) => m.id === state.route.id);
    main.innerHTML = mod ? renderDetail(mod) : renderNotFound();
  } else {
    main.innerHTML = renderCatalog();
  }

  bindEvents();
}

function bindEvents() {
  const search = document.getElementById("search-input");
  if (search) {
    search.addEventListener("input", (e) => {
      state.search = e.target.value;
      render();
      const next = document.getElementById("search-input");
      if (next) {
        next.focus();
        const len = next.value.length;
        next.setSelectionRange(len, len);
      }
    });
  }

  document.querySelectorAll("[data-filter]").forEach((btn) => {
    btn.addEventListener("click", () => {
      state.filterCluster = btn.dataset.filter;
      render();
    });
  });

  const reset = document.getElementById("reset-filters");
  if (reset) {
    reset.addEventListener("click", () => {
      state.search = "";
      state.filterCluster = "all";
      render();
    });
  }

  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", () => {
      state.route = parseRoute();
    });
  });
}

window.addEventListener("hashchange", onRouteChange);
render();
