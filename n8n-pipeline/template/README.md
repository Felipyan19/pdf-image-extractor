# Template + JSON externo

Este directorio ahora soporta separar el HTML en:

- `template.dynamic.html`: plantilla con placeholders `{{text_XXXX}}` y `{{image_XXXX}}`
- `template.content.json`: contenido editable (textos e imágenes)

## Generar archivos desde `template.html`

```bash
python3 n8n-pipeline/template/extract_template_content.py \
  --input n8n-pipeline/template/template.html \
  --output-template n8n-pipeline/template/template.dynamic.html \
  --output-json n8n-pipeline/template/template.content.json
```

## Estructura del JSON

`template.content.json` incluye:

- `data`: objeto plano listo para usar como `data_json` en n8n
- `texts`: solo textos
- `images`: solo imágenes

Si solo querés editar contenido para renderizar, modificá `data`.

## Uso en el nodo `Render HTML v1`

Pasale:

- `template_html`: contenido de `template.dynamic.html`
- `data_json`: `template.content.json.data`

El nodo ya reemplaza `{{slot}}` automáticamente.
