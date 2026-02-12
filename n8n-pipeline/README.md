# PDF → Template HTML — Slot-Based n8n Pipeline

## Arquitectura general

```
[PDF input]
    │
    ▼
[Python /extract-structured]  ← SOLO extrae: text+bbox+style, images+bbox+phash, shapes+bbox+colors
    │
    ▼ extractor_output.json
[n8n: Normalize & Zone Segment]  ← bbox → 0..1, asigna zone (header/main/footer), filtra ruido
    │
    ▼ elements[] con bbox_norm + zone
[n8n: Score & Map]  ← IoU + distancia + estilo + anchors → data.json + match_report
    │
    ▼ data_json + match_report
[n8n: Render HTML v1]  ← template.html + {{placeholders}} → html_v1
    │
    ▼ html_v1
[n8n: Diff Generator]  ← detecta qué slots fallaron → direct_patches + llm_patches
    │
    ├── [sin LLM] ──────────────────────────────────────────────────────────────┐
    │                                                                            │
    └── [con LLM] → Split → Build Prompt → Anthropic API → Parse → Collect ───►│
                                                                                 │
    ▼                                                                            │
[n8n: Merge Patches] ◄───────────────────────────────────────────────────────────┘
    │
    ▼ all_patches[]
[n8n: Patch Applier]  ← simple_replace / css_adjust / fragment_patch / fallback_absolute
    │
    ▼ html_final
[n8n: Validator & Report]  ← required slots, unreplaced placeholders, image URLs
    │
    ▼
[Respond to Webhook]  → { html, success, report }
```

## Archivos

```
n8n-pipeline/
├── workflow.json                    ← IMPORTAR EN N8N (flujo completo)
├── README.md                        ← Este archivo
├── schemas/
│   ├── extractor_output.example.json   ← Formato de salida del Python
│   ├── slots_spec.example.json         ← Contrato de slots del template
│   ├── match_report.example.json       ← Resultado del mapper
│   └── patches.example.json            ← Patches generados
└── n8n-nodes/
    ├── 00_config.js                    ← Config & Validation (editar aquí)
    ├── 01_normalize_and_segment.js     ← Normalize + zonas
    ├── 02_score_and_map.js             ← Scoring IoU + mapper
    ├── 03_render_html_v1.js            ← Render template + placeholders
    ├── 04_diff_generator.js            ← Diff: qué slots parchear
    ├── 04b_build_llm_prompt.js         ← Prompt mínimo para Anthropic
    ├── 04c_parse_llm_patch.js          ← Parsea respuesta LLM
    ├── 05b_merge_patches.js            ← Merge direct + LLM patches
    ├── 05_patch_applier.js             ← Aplica patches → html_final
    └── 06_validator.js                 ← Validaciones + report final
```

El microservicio Python tiene el nuevo endpoint en:
```
app/services/structured_extractor.py   ← Nueva lógica de extracción
app/api/endpoints.py                   ← Nuevo endpoint POST /api/v1/extract-structured
```

---

## Setup rápido

### 1. Importar el workflow en n8n

1. Ir a n8n → Import from file → seleccionar `workflow.json`
2. En el nodo **"Config & Validation"**, editar:
   - `SLOTS_SPEC`: ajustar `expected_bbox_norm` para tu template
   - `TEMPLATE_HTML`: pegar tu `template.html` (o cambiar para leer de URL)
   - `extractorUrl`: tu URL del microservicio
3. En el nodo **"Anthropic API (Patch Agent)"**: configurar el header `x-api-key` con tu credencial de Anthropic (usar `$vars.ANTHROPIC_API_KEY` o una credencial n8n)

### 2. Preparar el template.html

Tu `template.html` debe tener:
- Placeholders `{{slot_name}}` para cada slot
- Marcadores de sección para slots con `fragment_patch` o `fallback_absolute`:

```html
<!-- slot:footer_legal -->
<table width="620" ...>
  <tr><td>{{footer_legal}}</td></tr>
</table>
<!-- /slot:footer_legal -->
```

### 3. Activar el endpoint Python

Asegurarse de que el microservicio tenga `ENABLE_PUBLIC_URLS=true` en su configuración.
El nuevo endpoint es: `POST /api/v1/extract-structured`

Acepta:
```json
{ "pdf_url": "https://..." }
```

### 4. Invocar el workflow

```bash
curl -X POST https://tu-n8n.host/webhook/pdf-to-html-v2 \
  -H "Content-Type: application/json" \
  -d '{
    "pdf_url": "https://tu-servidor.com/newsletter.pdf",
    "extractor_url": "https://tu-extractor.com"
  }'
```

**Respuesta:**
```json
{
  "html": "<!DOCTYPE html>...",
  "success": true,
  "report": {
    "match_summary": { "total_slots": 8, "matched_high": 6, "matched_low": 1, "missing": 1 },
    "patch_summary": { "total": 2, "applied": 2, "failed": 0, "fallbacks": 0, "llm_used": 1 },
    "slots_detail": [...]
  }
}
```

---

## Diseño de `slots_spec.json` — Referencia completa

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | string | ID único del slot |
| `type` | `text\|image\|link` | Tipo de elemento buscado |
| `zone` | `header\|main\|footer` | Zona de búsqueda |
| `expected_bbox_norm` | `{x0,y0,x1,y1}` | Bbox esperado normalizado (0..1) |
| `style_hints.font_size_min/max` | number | Rango esperado de font-size en pt |
| `style_hints.font_weight` | `bold\|normal` | Peso esperado |
| `style_hints.color_hint` | `light\|dark` | Hint de luminancia del color |
| `required` | boolean | Si falta → error en report |
| `patch_policy` | ver abajo | Cómo parchear si falla |
| `anchors` | string[] | Keywords para scoring (presence = 1.0, absence = 0.5) |
| `placeholder` | string | `{{nombre}}` a reemplazar en template.html |
| `fallback_value` | string\|null | Valor si slot missing y no required |

### Políticas de patch (`patch_policy`)

| Política | Cuándo usar | Qué hace el patch applier |
|---|---|---|
| `simple_replace` | Slots de texto/imagen simples | Reemplaza `{{placeholder}}` o valor actual en el HTML |
| `css_adjust` | Ajustes de layout/tamaño | Inyecta `<style data-patch="slot">` antes de `</head>` |
| `fragment_patch` | Bloques HTML complejos (footer, secciones) | Reemplaza entre `<!-- slot:name -->` y `<!-- /slot:name -->` |
| `fallback_absolute` | Bloque totalmente cambiado | Reemplaza con `<img>` del render_png completo |

---

## Scoring — Umbrales y pesos

### Pesos por componente

```
Score total = IoU×0.36 + Distancia×0.28 + Estilo×0.16 + Anchors×0.10 + Hints×0.10
```

| Componente | Peso | Cálculo |
|---|---|---|
| **IoU** | 36% | Intersection-over-Union entre bbox_norm del candidato y `expected_bbox_norm` |
| **Distancia** | 28% | `max(0, 1 - dist_centros × 3.0)` — dist 0.33 → score 0 |
| **Estilo** | 16% | font_size en rango → 1.0, fuera del rango → penalización proporcional; font_weight match → 1.0/0.65 |
| **Anchors** | 10% | Algún anchor presente en el texto → 1.0; ninguno → 0.5 |
| **Hints** | 10% | Penaliza candidatos que rompen `style_hints` geométricos (`min_x_norm`, `max_x_norm`, tamaños, etc.) |

### Umbrales de decisión

| Score | Estado | Acción |
|---|---|---|
| ≥ 0.80 | `matched_high` | Directo al template, sin patch |
| 0.50 – 0.79 | `matched_low` | `direct_patch` (simple_replace) o `llm_patch` si policy lo requiere |
| < 0.50 | `missing` | LLM patch si required, fallback_value si not required |
| < 0.30 | `missing + high severity` | Siempre LLM |

### Cuándo se llama al LLM

El agente LLM solo se activa si al menos uno de:
- `patch_policy` es `fragment_patch` o `fallback_absolute`
- score < 0.30
- status = `missing` y slot es `required`

**Promedio esperado de llamadas LLM**: 0–2 por PDF (para un template con 8 slots y PDFs ~90% iguales).

---

## Estrategia de fallback

### Nivel 1 — Determinístico (score ≥ 0.80)
El template se rellena directamente. Sin LLM.

### Nivel 2 — Direct patch (0.50 ≤ score < 0.80, policy=simple_replace)
El valor extraído se usa aunque el score sea bajo. LLM no se invoca.

### Nivel 3 — LLM patch (score < 0.50 o policy=fragment_patch)
El agente recibe: slot_spec + match_info + html_fragment (si aplica) + render_png URL.
El agente devuelve un JSON de patch mínimo.
Si el LLM devuelve confidence < 0.50, se escala a Nivel 4.

### Nivel 4 — Fallback absoluto (última instancia)
El slot se reemplaza con una `<img>` del `render_png` del extractor (la página completa).
Se loguea en el report con `fallbacks_used[]`.
El resto del template queda intacto.

---

## Plan de pruebas

### Dataset recomendado
- Mínimo 5 PDFs con variaciones del mismo diseño base:
  - PDF-001: template base (referencia) → debería tener 0 patches
  - PDF-002: título hero diferente → 1 patch simple_replace
  - PDF-003: imagen hero diferente + CTA diferente → 2 patches
  - PDF-004: sección completa cambiada → 1 patch fragment_patch
  - PDF-005: footer legal diferente → 1 patch fragment_patch (LLM)

### Métricas a medir

| Métrica | Objetivo | Cómo medirla |
|---|---|---|
| Cobertura de slots | ≥ 90% `matched_high` | `match_report.summary.matched_high / total_slots` |
| Score promedio | ≥ 0.82 | Promedio de `score` en `match_report.slots` |
| Tasa de LLM | ≤ 25% de slots | `llm_used / total_slots` |
| Tasa de fallback | ≤ 5% de slots | `fallbacks / total_slots` |
| Slots faltantes en reporte | 0 required | `errors[]` vacío |

### Proceso de calibración
1. Correr todos los PDFs y revisar los `match_report.slots` de los que tienen score bajo
2. Para esos slots, ajustar `expected_bbox_norm` para que coincida mejor con la posición real en el PDF
3. Si un slot siempre tiene `style_mismatch`, revisar los `style_hints` y actualizarlos
4. Si hay muchos `layout_shift`, reducir el `distance_scale` de 3.0 a 2.0 para ser más tolerante

---

## FAQ

**¿Cómo agrego un nuevo slot?**
1. Agregar al array `slots` en el nodo "Config & Validation" con su `expected_bbox_norm`
2. Agregar `{{nuevo_slot}}` en el `template.html` en el lugar correcto
3. Si usa `fragment_patch`, envolver en `<!-- slot:nuevo_slot --> ... <!-- /slot:nuevo_slot -->`

**¿Qué pasa si el PDF tiene 2 páginas?**
El pipeline procesa `page_index=0` por defecto. Para multi-página, cambiar `pageIndex` en el nodo Normalize o iterar sobre las páginas.

**¿Puedo usar GPT-4 en lugar de Claude?**
Sí: cambiar el nodo "Anthropic API" por un HTTP Request a OpenAI y ajustar el formato del payload en "Build LLM Prompt".

**¿Cómo actualizo el template.html sin re-importar el workflow?**
Opción A: Servir el template desde una URL y fetchearlo en el nodo Config.
Opción B: Usar n8n Variables o Credentials para almacenar el HTML.
Opción C: Pasar `template_html` en el body del webhook desde el llamador.
