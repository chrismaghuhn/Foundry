export const API_BASE =
  import.meta.env.VITE_FOUNDRY_API_URL || "http://127.0.0.1:8000";

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`, { method: "GET" });
    if (!res.ok) return { ok: false };
    const data = await res.json();
    return { ok: data.ok === true, root: data.root };
  } catch {
    return { ok: false };
  }
}

export async function fetchModules() {
  const res = await fetch(`${API_BASE}/api/modules`, { method: "GET" });
  if (!res.ok) throw new Error("Failed to load runner modules");
  const data = await res.json();
  return data.modules || [];
}

export async function runTest(moduleId) {
  const res = await fetch(`${API_BASE}/api/modules/${moduleId}/test`, {
    method: "POST",
  });
  if (res.status === 404) throw new Error("Unknown module");
  if (!res.ok) throw new Error(`Runner error (${res.status})`);
  return res.json();
}

export async function runExample(moduleId) {
  const res = await fetch(`${API_BASE}/api/modules/${moduleId}/example`, {
    method: "POST",
  });
  if (res.status === 404) throw new Error("Unknown module");
  if (!res.ok) throw new Error(`Runner error (${res.status})`);
  return res.json();
}
