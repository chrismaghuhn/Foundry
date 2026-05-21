const API_BASE =
  import.meta.env.VITE_FOUNDRY_API_URL || "http://127.0.0.1:8000";

async function labsFetch(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!res.ok) {
    const err = new Error(`Labs API ${res.status}`);
    err.status = res.status;
    try {
      err.detail = (await res.json()).detail;
    } catch {
      /* ignore */
    }
    throw err;
  }
  return res.json();
}

export async function fetchLabsHealth() {
  try {
    const data = await labsFetch("/api/health");
    return { ok: true, root: data.root };
  } catch {
    return { ok: false };
  }
}

export async function fetchLabs() {
  return labsFetch("/api/labs");
}

export async function fetchLabDefinition(moduleId) {
  return labsFetch(`/api/labs/${encodeURIComponent(moduleId)}`);
}

export async function runLab(moduleId, body) {
  return labsFetch(`/api/labs/${encodeURIComponent(moduleId)}/run`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export { API_BASE };
