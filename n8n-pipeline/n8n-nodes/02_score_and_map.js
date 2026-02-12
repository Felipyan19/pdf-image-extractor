/**
 * NODE 02 — Score & Map (Deterministic Mapper, tuned for /extract-structured)
 *
 * INPUT (items[0].json):
 *   - doc_id, elements (normalized with bbox_norm + zone), slots_spec, render_png, template_html
 *
 * OUTPUT (items[0].json):
 *   - doc_id, data_json, match_report, render_png, slots_spec, template_html
 */

const input = $input.first().json;
const { doc_id, source_filename, elements, slots_spec, render_png, page_index, template_html } = input;

// ── Scoring config (overridable per slots_spec) ──────────────────────────────

const scoringCfg = slots_spec.scoring_config || {};
const W = scoringCfg.weights || {};
const rawWeights = {
  iou: W.iou ?? 0.40,
  distance: W.distance ?? 0.30,
  style: W.style ?? 0.20,
  anchor: W.anchor ?? 0.10,
  hint: W.hint ?? 0.10, // new: honors style_hints geometric constraints
};
const weightSum = Object.values(rawWeights).reduce((acc, v) => acc + (v > 0 ? v : 0), 0) || 1;
const WEIGHT_IOU = rawWeights.iou / weightSum;
const WEIGHT_DISTANCE = rawWeights.distance / weightSum;
const WEIGHT_STYLE = rawWeights.style / weightSum;
const WEIGHT_ANCHOR = rawWeights.anchor / weightSum;
const WEIGHT_HINT = rawWeights.hint / weightSum;

const T = scoringCfg.thresholds || {};
const THRESHOLD_HIGH = T.high_match ?? 0.80;
const THRESHOLD_LOW = T.low_match ?? 0.50;
const DISTANCE_SCALE = T.distance_scale ?? 3.0; // norm dist 0.33 → score ~0
const HINT_TOLERANCE_NORM = T.hint_tolerance_norm ?? 0.02;
const ZONE_RELAX_DELTA = T.zone_relax_delta ?? 0.05;
const REUSE_PENALTY = T.reuse_penalty ?? 0.08;

// ── Helpers ───────────────────────────────────────────────────────────────────

function normalizeText(text) {
  if (!text) return '';
  return String(text)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

function iou(a, b) {
  const ix0 = Math.max(a.x0, b.x0);
  const iy0 = Math.max(a.y0, b.y0);
  const ix1 = Math.min(a.x1, b.x1);
  const iy1 = Math.min(a.y1, b.y1);
  if (ix1 <= ix0 || iy1 <= iy0) return 0;
  const intersection = (ix1 - ix0) * (iy1 - iy0);
  const areaA = (a.x1 - a.x0) * (a.y1 - a.y0);
  const areaB = (b.x1 - b.x0) * (b.y1 - b.y0);
  const union = areaA + areaB - intersection;
  return union > 0 ? intersection / union : 0;
}

function distanceScore(a, b) {
  const cax = (a.x0 + a.x1) / 2;
  const cay = (a.y0 + a.y1) / 2;
  const cbx = (b.x0 + b.x1) / 2;
  const cby = (b.y0 + b.y1) / 2;
  const dist = Math.sqrt((cax - cbx) ** 2 + (cay - cby) ** 2);
  return { score: Math.max(0, 1 - dist * DISTANCE_SCALE), dist };
}

function styleScore(el, hints) {
  if (!hints || el.type !== 'text' || !el.style) return 1.0;
  let score = 1.0;
  let checks = 0;

  if (hints.font_size_min !== undefined && hints.font_size_max !== undefined && el.style.font_size) {
    checks++;
    const fs = el.style.font_size;
    if (fs < hints.font_size_min || fs > hints.font_size_max) {
      const deviation =
        Math.min(Math.abs(fs - hints.font_size_min), Math.abs(fs - hints.font_size_max)) /
        Math.max(hints.font_size_max, 1);
      score *= Math.max(0.1, 1 - deviation * 2);
    }
  }

  if (hints.font_weight && el.style.font_weight) {
    checks++;
    score *= hints.font_weight === el.style.font_weight ? 1.0 : 0.65;
  }

  if (hints.color_hint === 'light' && el.style.color) {
    checks++;
    const hex = String(el.style.color).replace('#', '');
    if (hex.length === 6) {
      const r = parseInt(hex.slice(0, 2), 16);
      const g = parseInt(hex.slice(2, 4), 16);
      const b = parseInt(hex.slice(4, 6), 16);
      const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      score *= luminance > 0.5 ? 1.0 : 0.6;
    }
  }

  return checks > 0 ? score : 1.0;
}

function anchorScore(el, anchors) {
  if (!anchors || anchors.length === 0 || el.type !== 'text') {
    return { score: 1.0, matched: false };
  }

  const textNorm = el.normalized_text || normalizeText(el.text || el.raw_text || '');
  if (!textNorm) return { score: 0.4, matched: false };

  let exactMatch = false;
  let bestTokenRatio = 0;
  const textTokens = new Set(textNorm.split(' ').filter(Boolean));

  for (const anchor of anchors) {
    const anchorNorm = normalizeText(anchor);
    if (!anchorNorm) continue;
    if (textNorm.includes(anchorNorm)) {
      exactMatch = true;
      break;
    }
    const anchorTokens = anchorNorm.split(' ').filter(Boolean);
    if (!anchorTokens.length) continue;
    const hits = anchorTokens.filter(t => textTokens.has(t)).length;
    const ratio = hits / anchorTokens.length;
    if (ratio > bestTokenRatio) bestTokenRatio = ratio;
  }

  if (exactMatch) return { score: 1.0, matched: true };
  if (bestTokenRatio >= 0.75) return { score: 0.85, matched: true };
  if (bestTokenRatio >= 0.40) return { score: 0.70, matched: false };
  if (bestTokenRatio > 0) return { score: 0.55, matched: false };
  return { score: 0.40, matched: false };
}

function hintScore(el, hints) {
  if (!hints) return { score: 1.0, reasons: [] };

  const reasons = [];
  let score = 1.0;
  const bbox = el.bbox_norm;
  const cx = (bbox.x0 + bbox.x1) / 2;
  const cy = (bbox.y0 + bbox.y1) / 2;
  const wNorm = bbox.x1 - bbox.x0;
  const hNorm = bbox.y1 - bbox.y0;

  const minX = hints.min_x_norm;
  const maxX = hints.max_x_norm;
  const minY = hints.min_y_norm;
  const maxY = hints.max_y_norm;
  const minWNorm = hints.min_width_norm;
  const maxWNorm = hints.max_width_norm;
  const minHNorm = hints.min_height_norm;
  const maxHNorm = hints.max_height_norm;

  if (minX !== undefined && cx < minX - HINT_TOLERANCE_NORM) {
    score *= 0.55;
    reasons.push('hint_min_x');
  }
  if (maxX !== undefined && cx > maxX + HINT_TOLERANCE_NORM) {
    score *= 0.55;
    reasons.push('hint_max_x');
  }
  if (minY !== undefined && cy < minY - HINT_TOLERANCE_NORM) {
    score *= 0.70;
    reasons.push('hint_min_y');
  }
  if (maxY !== undefined && cy > maxY + HINT_TOLERANCE_NORM) {
    score *= 0.70;
    reasons.push('hint_max_y');
  }
  if (minWNorm !== undefined && wNorm < minWNorm - HINT_TOLERANCE_NORM) {
    score *= 0.70;
    reasons.push('hint_min_width_norm');
  }
  if (maxWNorm !== undefined && wNorm > maxWNorm + HINT_TOLERANCE_NORM) {
    score *= 0.70;
    reasons.push('hint_max_width_norm');
  }
  if (minHNorm !== undefined && hNorm < minHNorm - HINT_TOLERANCE_NORM) {
    score *= 0.70;
    reasons.push('hint_min_height_norm');
  }
  if (maxHNorm !== undefined && hNorm > maxHNorm + HINT_TOLERANCE_NORM) {
    score *= 0.70;
    reasons.push('hint_max_height_norm');
  }

  if (el.type === 'image') {
    const minWpx = hints.min_width_px;
    const maxWpx = hints.max_width_px;
    const minHpx = hints.min_height_px;
    const maxHpx = hints.max_height_px;

    if (minWpx !== undefined && el.width_px && el.width_px < minWpx * 0.85) {
      score *= 0.60;
      reasons.push('hint_min_width_px');
    }
    if (maxWpx !== undefined && el.width_px && el.width_px > maxWpx * 1.15) {
      score *= 0.60;
      reasons.push('hint_max_width_px');
    }
    if (minHpx !== undefined && el.height_px && el.height_px < minHpx * 0.85) {
      score *= 0.75;
      reasons.push('hint_min_height_px');
    }
    if (maxHpx !== undefined && el.height_px && el.height_px > maxHpx * 1.15) {
      score *= 0.75;
      reasons.push('hint_max_height_px');
    }
  }

  return { score, reasons };
}

function scoreCandidate(el, slot) {
  const expected = slot.expected_bbox_norm;
  const iouVal = iou(el.bbox_norm, expected);
  const { score: distScore, dist } = distanceScore(el.bbox_norm, expected);
  const sScore = styleScore(el, slot.style_hints);
  const anchor = anchorScore(el, slot.anchors);
  const hints = hintScore(el, slot.style_hints);

  const totalRaw =
    iouVal * WEIGHT_IOU +
    distScore * WEIGHT_DISTANCE +
    sScore * WEIGHT_STYLE +
    anchor.score * WEIGHT_ANCHOR +
    hints.score * WEIGHT_HINT;

  return {
    total: Math.round(totalRaw * 1000) / 1000,
    iou: Math.round(iouVal * 1000) / 1000,
    dist: Math.round(dist * 1000) / 1000,
    dist_score: Math.round(distScore * 1000) / 1000,
    style_score: Math.round(sScore * 1000) / 1000,
    anchor_score: Math.round(anchor.score * 1000) / 1000,
    hint_score: Math.round(hints.score * 1000) / 1000,
    anchor_matched: anchor.matched,
    hint_reasons: hints.reasons,
  };
}

function extractValue(el, slotType) {
  if (!el) return null;
  if (slotType === 'image') return el.type === 'image' ? el.src : null;
  if (slotType === 'text') return el.type === 'text' ? (el.text || el.raw_text || '') : null;
  if (slotType === 'link') {
    const t = (el.text || el.raw_text || '');
    const urlMatch = t.match(/https?:\/\/[^\s]+/);
    return urlMatch ? urlMatch[0] : t;
  }
  return el.src || el.text || null;
}

function isTypeCompatible(el, slotType) {
  if (slotType === 'image') return el.type === 'image';
  if (slotType === 'text') return el.type === 'text';
  if (slotType === 'link') return el.type === 'text'; // link-like text in PDF
  return true;
}

function filterCandidates(elementsIn, slot, mode = 'strict_zone') {
  const expected = slot.expected_bbox_norm;
  const expCy = (expected.y0 + expected.y1) / 2;

  return elementsIn.filter(el => {
    if (!isTypeCompatible(el, slot.type)) return false;

    if (mode === 'strict_zone' && el.zone !== slot.zone) return false;
    if (mode === 'relaxed_zone') {
      const cy = el.center_norm ? el.center_norm.y : ((el.bbox_norm.y0 + el.bbox_norm.y1) / 2);
      if (Math.abs(cy - expCy) > ZONE_RELAX_DELTA) return false;
    }
    return true;
  });
}

// ── Main matching loop ────────────────────────────────────────────────────────

const dataJson = {};
const matchReport = {
  doc_id,
  source_filename,
  template_id: slots_spec.template_id,
  matched_at: new Date().toISOString(),
  page_index: page_index ?? 0,
  summary: {
    total_slots: 0,
    matched_high: 0,
    matched_low: 0,
    missing: 0,
    needs_patch: 0,
  },
  slots: {},
};

const usedCandidateIds = new Set();

const sortedSlots = [...slots_spec.slots].sort((a, b) => {
  if (a.required && !b.required) return -1;
  if (!a.required && b.required) return 1;
  return 0;
});

for (const slot of sortedSlots) {
  matchReport.summary.total_slots++;

  let candidateSource = 'strict_zone';
  let candidates = filterCandidates(elements, slot, 'strict_zone');

  if (candidates.length === 0) {
    candidateSource = 'relaxed_zone';
    candidates = filterCandidates(elements, slot, 'relaxed_zone');
  }
  if (candidates.length === 0) {
    candidateSource = 'global_type';
    candidates = filterCandidates(elements, slot, 'global_type');
  }

  if (candidates.length === 0) {
    matchReport.summary.missing++;
    if (slot.required) matchReport.summary.needs_patch++;

    matchReport.slots[slot.name] = {
      status: 'missing',
      candidate_id: null,
      score: 0,
      iou: 0,
      distance_norm: 1.0,
      style_score: 0,
      anchor_score: 0,
      hint_score: 0,
      value: slot.fallback_value ?? null,
      needs_patch: !!slot.required,
      reasons: ['no_candidates'],
      alternatives: [],
      candidate_bbox_norm: null,
      candidate_source: candidateSource,
    };
    dataJson[slot.name] = slot.fallback_value ?? '';
    continue;
  }

  const scored = candidates
    .map(el => {
      const scores = scoreCandidate(el, slot);
      const reused = usedCandidateIds.has(el.id);
      const totalAdjusted = reused ? Math.max(0, scores.total - REUSE_PENALTY) : scores.total;
      return { el, scores, reused, totalAdjusted };
    })
    .sort((a, b) => b.totalAdjusted - a.totalAdjusted);

  const best = scored[0];
  const alternatives = scored.slice(1, 4).map(s => s.el.id);
  usedCandidateIds.add(best.el.id);

  let status;
  let needsPatch;
  const reasons = [];

  if (best.totalAdjusted >= THRESHOLD_HIGH) {
    status = 'matched_high';
    needsPatch = false;
    matchReport.summary.matched_high++;
    reasons.push('score_high');
  } else if (best.totalAdjusted >= THRESHOLD_LOW) {
    status = 'matched_low';
    needsPatch = true;
    matchReport.summary.matched_low++;
    matchReport.summary.needs_patch++;
    reasons.push('score_low');
  } else {
    status = 'missing';
    needsPatch = !!slot.required;
    matchReport.summary.missing++;
    if (needsPatch) matchReport.summary.needs_patch++;
    reasons.push('score_too_low');
  }

  if (candidateSource !== 'strict_zone') reasons.push(`candidate_${candidateSource}`);
  if (best.reused) reasons.push('candidate_reused');
  if (best.scores.iou < 0.50) reasons.push('low_iou');
  if (best.scores.iou >= 0.70) reasons.push('high_iou');
  if (best.scores.style_score < 0.70) reasons.push('style_mismatch');
  if (best.scores.dist > 0.15) reasons.push('layout_shift');
  if (best.scores.anchor_matched && (slot.anchors || []).length > 0) reasons.push('anchor_match');
  if (best.scores.hint_score < 0.75) reasons.push('hint_mismatch');
  reasons.push(...best.scores.hint_reasons);

  const value = extractValue(best.el, slot.type);

  matchReport.slots[slot.name] = {
    status,
    candidate_id: best.el.id,
    score: Math.round(best.totalAdjusted * 1000) / 1000,
    iou: best.scores.iou,
    distance_norm: best.scores.dist,
    style_score: best.scores.style_score,
    anchor_score: best.scores.anchor_score,
    hint_score: best.scores.hint_score,
    value,
    needs_patch: needsPatch,
    reasons: [...new Set(reasons)],
    alternatives,
    candidate_bbox_norm: best.el.bbox_norm,
    candidate_source: candidateSource,
  };

  dataJson[slot.name] = value ?? (slot.fallback_value ?? '');
}

return [{
  json: {
    doc_id,
    source_filename,
    data_json: dataJson,
    match_report: matchReport,
    render_png,
    slots_spec,
    template_html,
  }
}];
