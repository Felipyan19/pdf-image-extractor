/**
 * NODE 00 — Config & Validation
 *
 * This is the FIRST Code node after the Webhook trigger.
 * It:
 *   1. Validates and normalizes the webhook input (pdf_url required)
 *   2. Provides the slots_spec (calibrated for AMEX Merchant Newsletter)
 *   3. Provides the template_html (pass in body, or embed here)
 *
 * INPUT (webhook body):
 *   { "pdf_url": "https://...", "extractor_url": "https://..." }
 *
 * OUTPUT:
 *   - pdf_url, extractor_url, slots_spec, template_html
 *
 * ─────────────────────────────────────────────────────────────
 * TEMPLATE USAGE:
 *   1. Load  n8n-pipeline/template_amex.html  (has {{placeholders}} inserted)
 *   2. POST its contents as body.template_html in the webhook request
 *   3. Or embed it below (OPTION B)
 * ─────────────────────────────────────────────────────────────
 */

const body = $input.first().json.body || $input.first().json;

// ── Validate input ────────────────────────────────────────────────────────────

const pdfUrl = body.pdf_url || body.url;
if (!pdfUrl) {
  throw new Error('pdf_url is required in the request body. Example: { "pdf_url": "https://..." }');
}

const extractorUrl = (body.extractor_url || 'https://n8n.149-130-164-187.sslip.io').replace(/\/$/, '');

// ── SLOTS SPEC ────────────────────────────────────────────────────────────────
// Calibrated from real AMEX Merchant Newsletter – December 2025
// PDF dimensions: 620.0 × 4791.4 pt  (3 pages, 353 elements on page 0)
// bbox values are normalised (0-1) against page width/height.
//
// Zone layout (y_norm):
//   header  0.000–0.132  Brand panel (AMEX logo, "Mi cuenta") + Hero banner
//   compras 0.132–0.256  COMPRAS: Shopping Days (left) + PedidosYa Plus (right)
//   gastro  0.256–0.350  GASTRONOMIA: discount badges + NH hotel photos
//   hoteles 0.350–0.494  HOTELES: discount badge + hotel photos + nights offer
//   cta     0.494–0.523  Main dark-blue CTA bar ("Descubrí todos los beneficios")
//   footer  0.523–1.000  Social icons + legal text (1)-(n) footnotes

const SLOTS_SPEC = {
  version: '1.1',
  template_id: 'amex_newsletter_merchant',
  page_width_ref: 620.0,
  page_height_ref: 4791.4,
  zone_config: {
    header:  { y_start: 0.000, y_end: 0.132 },
    compras: { y_start: 0.132, y_end: 0.256 },
    gastro:  { y_start: 0.256, y_end: 0.350 },
    hoteles: { y_start: 0.350, y_end: 0.494 },
    cta:     { y_start: 0.494, y_end: 0.523 },
    footer:  { y_start: 0.523, y_end: 1.000 },
  },
  scoring_config: {
    weights: { iou: 0.36, distance: 0.28, style: 0.16, anchor: 0.10, hint: 0.10 },
    thresholds: {
      high_match: 0.80,
      low_match: 0.50,
      distance_scale: 3.0,
      hint_tolerance_norm: 0.02,
      zone_relax_delta: 0.05,
      reuse_penalty: 0.08,
    },
  },
  slots: [
    // ── HEADER ─────────────────────────────────────────────────────────────────
    {
      // Full-bleed hero background image.
      // Appears 3× in template: background="", CSS url(''), VML <v:image src="">
      name: 'hero_bg_img',
      type: 'image',
      zone: 'header',
      expected_bbox_norm: { x0: 0.000, y0: 0.018, x1: 1.000, y1: 0.126 },
      style_hints: { min_width_px: 400 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{hero_bg_img}}',
      fallback_value: null,
    },
    {
      // Overlay image containing the tagline + month name ("Tenés más #conAmex. | DICIEMBRE").
      // Used for the mobile fallback <img>.  The text is baked into the image in the PDF.
      name: 'hero_mobile_img',
      type: 'image',
      zone: 'header',
      expected_bbox_norm: { x0: 0.063, y0: 0.058, x1: 0.353, y1: 0.081 },
      style_hints: { max_width_px: 300 },
      required: false,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{hero_mobile_img}}',
      fallback_value: null,
    },

    // ── COMPRAS — Shopping Days (left column, x < 0.5) ─────────────────────────
    {
      // "20% OFF" promotional badge image (replaces _05.png)
      name: 'shopping_discount_img',
      type: 'image',
      zone: 'compras',
      expected_bbox_norm: { x0: 0.118, y0: 0.177, x1: 0.377, y1: 0.191 },
      style_hints: { max_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{shopping_discount_img}}',
      fallback_value: null,
    },
    {
      // "3 y 6 cuotas sin interés" badge image (replaces _07.png)
      name: 'shopping_cuotas_img',
      type: 'image',
      zone: 'compras',
      expected_bbox_norm: { x0: 0.047, y0: 0.197, x1: 0.452, y1: 0.214 },
      style_hints: { max_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{shopping_cuotas_img}}',
      fallback_value: null,
    },

    // ── COMPRAS — PedidosYa Plus (right column, x > 0.5) ──────────────────────
    {
      // PedidosYa Plus logo image (replaces _08.png)
      name: 'pedidos_logo_img',
      type: 'image',
      zone: 'compras',
      expected_bbox_norm: { x0: 0.612, y0: 0.162, x1: 0.850, y1: 0.175 },
      style_hints: { min_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{pedidos_logo_img}}',
      fallback_value: null,
    },
    {
      // "GRATIS POR 3 MESES" image (replaces _09.png)
      name: 'pedidos_gratis_img',
      type: 'image',
      zone: 'compras',
      expected_bbox_norm: { x0: 0.572, y0: 0.181, x1: 0.894, y1: 0.196 },
      style_hints: { min_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{pedidos_gratis_img}}',
      fallback_value: null,
    },
    {
      // "50% OFF" image (replaces _10.png)
      name: 'pedidos_50off_img',
      type: 'image',
      zone: 'compras',
      expected_bbox_norm: { x0: 0.627, y0: 0.207, x1: 0.838, y1: 0.218 },
      style_hints: { min_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{pedidos_50off_img}}',
      fallback_value: null,
    },

    // ── GASTRONOMIA — discount badges ──────────────────────────────────────────
    {
      // "20% OFF" restaurantes badge – left column (replaces _12.png)
      name: 'gastro_left_img',
      type: 'image',
      zone: 'gastro',
      expected_bbox_norm: { x0: 0.115, y0: 0.285, x1: 0.391, y1: 0.299 },
      style_hints: { max_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{gastro_left_img}}',
      fallback_value: null,
    },
    {
      // "20% OFF Cenas de Navidad y Año Nuevo" badge – right column (replaces _13.png)
      name: 'gastro_right_img',
      type: 'image',
      zone: 'gastro',
      expected_bbox_norm: { x0: 0.621, y0: 0.285, x1: 0.898, y1: 0.299 },
      style_hints: { min_x_norm: 0.5 },
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{gastro_right_img}}',
      fallback_value: null,
    },

    // ── GASTRONOMIA — NH hotel photos (inside right column, side-by-side) ──────
    {
      // NH City Hotel Buenos Aires photo (replaces _14.jpg)
      name: 'gastro_hotel_l_img',
      type: 'image',
      zone: 'gastro',
      expected_bbox_norm: { x0: 0.521, y0: 0.311, x1: 0.772, y1: 0.330 },
      style_hints: { min_x_norm: 0.5 },
      required: false,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{gastro_hotel_l_img}}',
      fallback_value: null,
    },
    {
      // NH Collection Lancaster photo (replaces _15.jpg)
      name: 'gastro_hotel_r_img',
      type: 'image',
      zone: 'gastro',
      expected_bbox_norm: { x0: 0.730, y0: 0.310, x1: 0.981, y1: 0.329 },
      style_hints: { min_x_norm: 0.7 },
      required: false,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{gastro_hotel_r_img}}',
      fallback_value: null,
    },

    // ── HOTELES ────────────────────────────────────────────────────────────────
    {
      // "20% OFF" hotel discount badge – centered (replaces HOTELES section badge img)
      name: 'hotel_discount_img',
      type: 'image',
      zone: 'hoteles',
      expected_bbox_norm: { x0: 0.370, y0: 0.376, x1: 0.642, y1: 0.390 },
      style_hints: {},
      required: true,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{hotel_discount_img}}',
      fallback_value: null,
    },
    {
      // Left hotel exterior photo
      name: 'hotel_img_l',
      type: 'image',
      zone: 'hoteles',
      expected_bbox_norm: { x0: 0.136, y0: 0.428, x1: 0.388, y1: 0.442 },
      style_hints: { max_x_norm: 0.5 },
      required: false,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{hotel_img_l}}',
      fallback_value: null,
    },
    {
      // Right hotel exterior photo
      name: 'hotel_img_r',
      type: 'image',
      zone: 'hoteles',
      expected_bbox_norm: { x0: 0.591, y0: 0.428, x1: 0.867, y1: 0.442 },
      style_hints: { min_x_norm: 0.5 },
      required: false,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{hotel_img_r}}',
      fallback_value: null,
    },
    {
      // "3 noches + 1 noche gratis" nights offer image
      name: 'hotel_nights_img',
      type: 'image',
      zone: 'hoteles',
      expected_bbox_norm: { x0: 0.611, y0: 0.453, x1: 0.849, y1: 0.465 },
      style_hints: { min_x_norm: 0.5 },
      required: false,
      patch_policy: 'simple_replace',
      anchors: [],
      placeholder: '{{hotel_nights_img}}',
      fallback_value: null,
    },
  ],
};

// ── TEMPLATE HTML ─────────────────────────────────────────────────────────────
// OPTION A (recommended): POST the contents of n8n-pipeline/template_amex.html
//   as body.template_html in the webhook request body.
//   The file already has all {{placeholders}} inserted at the right positions.
//
// OPTION B: Embed below.  Paste the full content of template_amex.html here
//   and remove the `body.template_html || ` part.
//
// NOTES:
//  - The hero bg image appears 3× in the template: background=, CSS url(), VML src=
//    All three occurrences use the same {{hero_bg_img}} placeholder — all get replaced.
//  - For fragment_patch slots (if added), include <!-- slot:name -->...<!-- /slot:name -->
//    markers around the replaceable fragment.
//  - Slots that are NOT in the template (no {{placeholder}}) are silently skipped.

const TEMPLATE_HTML = body.template_html || `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>AMEX Newsletter</title></head>
<body style="background:#E0E0E0;font-family:Helvetica,Arial,sans-serif;margin:0">
<table width="620" cellpadding="0" cellspacing="0" border="0" style="margin:0 auto;background:#fff">
  <!-- slot:hero_bg_img -->
  <tr><td background="{{hero_bg_img}}" bgcolor="#00175a" height="320"
          style="background:url('{{hero_bg_img}}') center/cover no-repeat #00175a">
    <!--[if gte mso 9]><v:image src="{{hero_bg_img}}" style="width:465pt;height:240pt"/><![endif]-->
  </td></tr>
  <!-- /slot:hero_bg_img -->
  <tr><td align="center" bgcolor="#006FCF" style="padding:25px 0">
    <strong style="color:#fff;font-size:20px">COMPRAS</strong></td></tr>
  <tr><td><table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="50%" align="center" style="padding:15px 10px 15px 15px">
      <img src="{{shopping_discount_img}}" width="169" style="display:block;margin:0 auto">
      <img src="{{shopping_cuotas_img}}" width="259" style="display:block;margin:10px auto 0">
    </td>
    <td width="50%" align="center" style="padding:15px 15px 15px 10px">
      <img src="{{pedidos_logo_img}}" width="154" style="display:block;margin:0 auto">
      <img src="{{pedidos_gratis_img}}" width="214" style="display:block;margin:5px auto 0">
      <img src="{{pedidos_50off_img}}" width="137" style="display:block;margin:5px auto 0">
    </td>
  </tr></table></td></tr>
  <tr><td align="center" bgcolor="#006FCF" style="padding:25px 0">
    <strong style="color:#fff;font-size:20px">GASTRONOM&Iacute;A</strong></td></tr>
  <tr><td><table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="50%" align="center" style="padding:15px 10px 15px 15px">
      <img src="{{gastro_left_img}}" width="182" style="display:block;margin:0 auto">
    </td>
    <td width="50%" align="center" style="padding:15px 15px 15px 10px">
      <img src="{{gastro_right_img}}" width="176" style="display:block;margin:0 auto">
      <table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
        <td align="center"><img src="{{gastro_hotel_l_img}}" width="129" style="display:block"></td>
        <td align="center"><img src="{{gastro_hotel_r_img}}" width="109" style="display:block"></td>
      </tr></table>
    </td>
  </tr></table></td></tr>
  <tr><td align="center" bgcolor="#006FCF" style="padding:25px 0">
    <strong style="color:#fff;font-size:20px">HOTELES</strong></td></tr>
  <tr><td align="center" style="padding:15px">
    <img src="{{hotel_discount_img}}" width="168" style="display:block;margin:0 auto"></td></tr>
  <tr><td><table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="50%" align="center" style="padding:10px 10px 10px 15px">
      <img src="{{hotel_img_l}}" width="156" style="display:block;margin:0 auto">
    </td>
    <td width="50%" align="center" style="padding:10px 15px 10px 10px">
      <img src="{{hotel_img_r}}" width="170" style="display:block;margin:0 auto">
      <img src="{{hotel_nights_img}}" width="147" style="display:block;margin:10px auto 0">
    </td>
  </tr></table></td></tr>
  <tr><td align="center" bgcolor="#00175a" style="padding:25px">
    <a href="https://www.americanexpress.com/es-ar/beneficios/"
       style="color:#fff;font-size:18px;text-decoration:none">
      Descubr&#237; todos los beneficios ac&#225;
    </a>
  </td></tr>
</table>
</body></html>`;

// ── Output ────────────────────────────────────────────────────────────────────

return [{
  json: {
    pdf_url: pdfUrl,
    extractor_url: extractorUrl,
    slots_spec: SLOTS_SPEC,
    template_html: TEMPLATE_HTML,
  }
}];
