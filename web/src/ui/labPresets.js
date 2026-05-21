export function renderLabPresets(definition, escapeHtml) {
  if (!definition?.presets?.length) return "";
  const chips = definition.presets
    .map(
      (p) => `
    <button type="button" class="lab-preset btn btn-ghost" data-preset-id="${escapeHtml(p.id)}" ${
        p.isDefault ? 'data-default="1"' : ""
      }>
      ${escapeHtml(p.label)}
    </button>`
    )
    .join("");
  return `
    <div class="lab-presets">
      <span class="lab-presets-label">Try this</span>
      <div class="lab-preset-row">${chips}</div>
    </div>`;
}
