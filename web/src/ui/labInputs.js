export function collectLabInput(formEl) {
  const input = {};
  formEl?.querySelectorAll("[data-lab-input]").forEach((el) => {
    const name = el.dataset.labInput;
    if (el.type === "checkbox") {
      input[name] = el.checked;
    } else if (el.dataset.type === "json") {
      try {
        input[name] = JSON.parse(el.value || "{}");
      } catch {
        input[name] = el.value;
      }
    } else {
      input[name] = el.value;
    }
  });
  return input;
}

export function renderLabInputs(definition, escapeHtml) {
  if (!definition?.inputs?.length) return "";
  const fields = definition.inputs
    .map((field) => {
      const id = `lab-${definition.moduleId}-${field.name}`;
      const def =
        field.default !== undefined && field.default !== null
          ? String(field.default)
          : "";
      if (field.type === "select" && field.options) {
        const opts = field.options
          .map(
            (o) =>
              `<option value="${escapeHtml(o.value)}" ${
                String(o.value) === String(field.default) ? "selected" : ""
              }>${escapeHtml(o.label)}</option>`
          )
          .join("");
        return `
        <label class="lab-field" for="${id}">
          <span>${escapeHtml(field.label)}</span>
          <select id="${id}" data-lab-input="${escapeHtml(field.name)}">${opts}</select>
        </label>`;
      }
      if (field.type === "textarea") {
        return `
        <label class="lab-field" for="${id}">
          <span>${escapeHtml(field.label)}</span>
          <textarea id="${id}" data-lab-input="${escapeHtml(field.name)}" rows="4">${escapeHtml(def)}</textarea>
        </label>`;
      }
      if (field.type === "json") {
        const val =
          typeof field.default === "object"
            ? JSON.stringify(field.default, null, 2)
            : def;
        return `
        <label class="lab-field" for="${id}">
          <span>${escapeHtml(field.label)}</span>
          <textarea id="${id}" data-lab-input="${escapeHtml(field.name)}" data-type="json" rows="6">${escapeHtml(val)}</textarea>
        </label>`;
      }
      return `
      <label class="lab-field" for="${id}">
        <span>${escapeHtml(field.label)}</span>
        <input id="${id}" type="text" data-lab-input="${escapeHtml(field.name)}" value="${escapeHtml(def)}" />
      </label>`;
    })
    .join("");
  return `<form class="lab-inputs" data-lab-form>${fields}</form>`;
}

export function applyPresetToForm(formEl, presetInput) {
  if (!formEl || !presetInput) return;
  Object.entries(presetInput).forEach(([name, value]) => {
    const el = formEl.querySelector(`[data-lab-input="${name}"]`);
    if (!el) return;
    if (el.dataset.type === "json" && typeof value === "object") {
      el.value = JSON.stringify(value, null, 2);
    } else {
      el.value = String(value ?? "");
    }
  });
}
