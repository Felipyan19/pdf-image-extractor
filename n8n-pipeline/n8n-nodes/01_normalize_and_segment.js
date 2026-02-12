/**
 * NODE 01 — Normalize & Zone Segmentation
 *
 * INPUT (items[0].json):
 *   - extractor_output: { doc_id, pages: [{ width_pt, height_pt, elements[], render_png }] }
 *   - slots_spec: { zone_config, slots[] }
 *   - page_index (optional, default 0)
 *
 * OUTPUT (items[0].json):
 *   - doc_id, page_index, width_pt, height_pt
 *   - elements: each element with added bbox_norm + zone + normalized helpers
 *   - lines, blocks: forwarded with normalized bboxes/text where available
 *   - render_png
 *   - slots_spec (forwarded)
 */

const input = $input.first().json;
const extractorOutput = input.extractor_output;
const slotsSpec = input.slots_spec;
const pageIndex = input.page_index ?? 0;

if (!extractorOutput || !extractorOutput.pages || extractorOutput.pages.length === 0) {
  throw new Error('extractor_output.pages is empty or missing');
}
if (!slotsSpec || !slotsSpec.zone_config) {
  throw new Error('slots_spec.zone_config is missing');
}

const page = extractorOutput.pages[pageIndex];
const W = page.width_pt;
const H = page.height_pt;

// ── Helpers ──────────────────────────────────────────────────────────────────

function normalizeBbox(bbox) {
  const safe = bbox || { x0: 0, y0: 0, x1: 0, y1: 0 };
  return {
    x0: Math.max(0, safe.x0 / W),
    y0: Math.max(0, safe.y0 / H),
    x1: Math.min(1, safe.x1 / W),
    y1: Math.min(1, safe.y1 / H),
  };
}

/**
 * Returns the zone name for a normalized bbox.
 * Uses the centroid of the bbox to decide zone.
 */
function getZone(normBbox, zoneConfig) {
  const cy = (normBbox.y0 + normBbox.y1) / 2;
  for (const [zoneName, range] of Object.entries(zoneConfig)) {
    if (cy >= range.y_start && cy < range.y_end) return zoneName;
  }
  return 'main'; // fallback
}

/**
 * Filter noise elements.
 * - Text elements with empty text
 * - Elements whose normalized bbox is degenerate (too small)
 * - Rect elements with no fill AND no stroke (invisible)
 */
function isNoise(el, normBbox) {
  const w = normBbox.x1 - normBbox.x0;
  const h = normBbox.y1 - normBbox.y0;

  // Degenerate bbox
  if (w < 0.004 || h < 0.003) return true;

  // Empty text
  if (el.type === 'text' && !((el.text || el.raw_text || '').trim())) return true;

  // Invisible rect
  if (el.type === 'rect' && !el.fill_color && !el.stroke_color) return true;

  return false;
}

function normalizeText(text) {
  if (!text) return '';
  return String(text)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

// ── Main processing ───────────────────────────────────────────────────────────

const normalizedElements = [];

for (const el of page.elements) {
  const normBbox = normalizeBbox(el.bbox);

  if (isNoise(el, normBbox)) continue;

  const zone = getZone(normBbox, slotsSpec.zone_config);
  const widthNorm = normBbox.x1 - normBbox.x0;
  const heightNorm = normBbox.y1 - normBbox.y0;
  const area = widthNorm * heightNorm;
  const textValue = el.type === 'text' ? (el.text || el.raw_text || '') : undefined;

  normalizedElements.push({
    ...el,
    ...(el.type === 'text' ? { text: textValue } : {}),
    ...(el.type === 'text'
      ? { normalized_text: el.normalized_text || normalizeText(textValue) }
      : {}),
    bbox_norm: normBbox,
    bbox_width_norm: Math.round(widthNorm * 10000) / 10000,
    bbox_height_norm: Math.round(heightNorm * 10000) / 10000,
    bbox_area_norm: Math.round(area * 10000) / 10000,
    center_norm: {
      x: Math.round(((normBbox.x0 + normBbox.x1) / 2) * 10000) / 10000,
      y: Math.round(((normBbox.y0 + normBbox.y1) / 2) * 10000) / 10000,
    },
    zone,
  });
}

// Sort: first by order (paint order), then by vertical position within same order
normalizedElements.sort((a, b) => {
  if (a.order !== b.order) return a.order - b.order;
  return a.bbox_norm.y0 - b.bbox_norm.y0;
});

const normalizedLines = (page.lines || []).map(line => {
  const bbox_norm = normalizeBbox(line.bbox);
  return {
    ...line,
    normalized_text: line.normalized_text || normalizeText(line.text || ''),
    bbox_norm,
  };
});

const normalizedBlocks = (page.blocks || []).map(block => {
  const bbox_norm = normalizeBbox(block.bbox);
  return {
    ...block,
    normalized_text: block.normalized_text || normalizeText(block.text || ''),
    bbox_norm,
    lines: (block.lines || []).map(line => ({
      ...line,
      normalized_text: line.normalized_text || normalizeText(line.text || ''),
      bbox_norm: normalizeBbox(line.bbox),
    })),
  };
});

return [{
  json: {
    doc_id: extractorOutput.doc_id,
    source_filename: extractorOutput.source_filename,
    page_index: pageIndex,
    width_pt: W,
    height_pt: H,
    elements: normalizedElements,
    lines: normalizedLines,
    blocks: normalizedBlocks,
    render_png: page.render_png,
    slots_spec: slotsSpec,
    // Carry template_html forward if present
    template_html: input.template_html,
  }
}];
