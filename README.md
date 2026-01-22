# PDF Image Extractor

Una API REST de alto rendimiento construida con **FastAPI** y **PyMuPDF** para extraer imágenes de archivos PDF. Completamente dockerizada y lista para producción.

## Por qué PyMuPDF (Fitz)?

Después de una investigación exhaustiva de las bibliotecas disponibles en 2026, **PyMuPDF** es la mejor opción por las siguientes razones:

- **Velocidad superior**: Procesa PDFs extremadamente rápido, incluso archivos grandes
- **Alta calidad**: Preserva la resolución y calidad original de las imágenes
- **Confiable**: Ampliamente utilizado y mantenido activamente
- **Completo**: Soporta múltiples formatos de imagen y proporciona metadata detallada
- **Rendimiento probado**: Puede procesar 1,310 páginas y extraer 180 imágenes en solo 1.5-2 segundos

### Comparación con otras bibliotecas

| Biblioteca | Velocidad | Calidad de imágenes | Facilidad de uso | Recomendado para |
|------------|-----------|---------------------|------------------|------------------|
| **PyMuPDF** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Extracción de imágenes |
| pypdf | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Manipulación básica de PDFs |
| pdfplumber | ⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | Extracción de tablas |

## Características

- ✅ Extracción rápida y confiable de imágenes de PDFs
- ✅ **Dos métodos de extracción**: desde archivo multipart/form-data o desde URL pública
- ✅ API REST con documentación automática (Swagger/OpenAPI)
- ✅ ZIP con imágenes embebidas + renders de páginas (PNG)
- ✅ Dockerizado con Docker Compose
- ✅ Configuración mediante variables de entorno
- ✅ Metadata detallada de cada imagen extraída
- ✅ Health checks y manejo robusto de errores
- ✅ CORS habilitado para uso en frontend
- ✅ Validación de archivos y límites de tamaño

## Requisitos previos

- Docker y Docker Compose instalados
- O Python 3.11+ (para ejecución sin Docker)

## Instalación y uso

### Opción 1: Con Docker Compose (Recomendado)

1. Clona el repositorio:
```bash
git clone <repository-url>
cd pdf-image-extractor
```

2. Copia el archivo de configuración:
```bash
cp .env.example .env
```

3. Construye y ejecuta con Docker Compose:
```bash
docker-compose up --build
```

O usando el Makefile:
```bash
make build
make up
```

4. La API estará disponible en:
- API: http://localhost:5050
- Documentación: http://localhost:5050/docs
- Health check: http://localhost:5050/api/v1/health

### Opción 2: Sin Docker (Desarrollo local)

1. Crea un entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Copia el archivo de configuración:
```bash
cp .env.example .env
```

4. Ejecuta la aplicación:
```bash
python -m app.main
```

O usando uvicorn directamente:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 5050
```

## Uso de la API

La API ofrece **dos métodos** para extraer imágenes de PDFs y siempre devuelve un **ZIP**:

1. **Upload de archivo** (`POST /api/v1/extract`): Sube un archivo PDF desde tu sistema
2. **Desde URL pública** (`POST /api/v1/extract-from-url`): Proporciona una URL pública de un PDF

### Probar en Swagger UI (recomendado)

1. Abre la documentación interactiva: http://localhost:5050/docs
2. Expande el endpoint que quieras probar.
3. Haz clic en **Try it out**.
4. Completa los parámetros:
   - Para `POST /api/v1/extract`, selecciona un PDF en el campo `file`.
5. Presiona **Execute** y revisa la respuesta.

Ejemplo rápido:
- Endpoint: `POST /api/v1/extract`
- file: selecciona `tu-archivo.pdf`

Respuesta esperada (200):
- Se descarga un archivo `.zip` con todas las imágenes embebidas y los renders de página.

### Endpoint: Extraer imágenes (archivo)

**POST** `/api/v1/extract`

Sube un archivo PDF y devuelve un ZIP con:
- Renders de cada página en PNG
- Imágenes embebidas (en su formato original)

#### Usando cURL:

```bash
curl -X POST "http://localhost:5050/api/v1/extract" \
  -H "accept: application/zip" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-file.pdf" \
  -o extracted_images.zip
```

#### Usando Python:

```python
import requests

url = "http://localhost:5050/api/v1/extract"
files = {"file": open("your-file.pdf", "rb")}

response = requests.post(url, files=files)
with open("extracted_images.zip", "wb") as f:
    f.write(response.content)
```

#### Usando el script de ejemplo:

```bash
python example_client.py
```

### Método 2: Extraer desde URL pública

**POST** `/api/v1/extract-from-url`

Descarga un PDF desde una URL pública y devuelve un ZIP con las imágenes.

#### Usando cURL:

```bash
curl -X POST "http://localhost:5050/api/v1/extract-from-url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://example.com/document.pdf"
  }' \
  -o extracted_images.zip
```

#### Ejemplo con URL real:

```bash
curl -X POST "http://localhost:5050/api/v1/extract-from-url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://149.130.164.187:2020/files/download/by-name/MERCHANT-Newsletter-Dic25%20%281%29.pdf"
  }' \
  -o extracted_images.zip
```

#### Usando Python:

```python
import requests

url = "http://localhost:5050/api/v1/extract-from-url"
payload = {
    "url": "http://example.com/document.pdf"
}

response = requests.post(url, json=payload)
with open("extracted_images.zip", "wb") as f:
    f.write(response.content)
```

### Contenido del ZIP (ejemplo):

```
document_images/
  page001_render.png
  page001_img01_xref12.png
  page002_render.png
  page002_img01_xref17.jpg
```

### Endpoint: Health Check

**GET** `/api/v1/health`

Verifica el estado de la API.

```bash
curl http://localhost:5050/api/v1/health
```

Respuesta:
```json
{
  "status": "healthy",
  "app_name": "PDF Image Extractor",
  "version": "1.0.0",
  "timestamp": "2026-01-21T10:30:00"
}
```

## Configuración

Todas las configuraciones se pueden ajustar en el archivo `.env`:

```env
# Configuración de la aplicación
APP_NAME=PDF Image Extractor
APP_VERSION=1.0.0
DEBUG=True

# Configuración del servidor
HOST=0.0.0.0
PORT=5050

# Configuración de subida
MAX_FILE_SIZE=50  # MB
ALLOWED_EXTENSIONS=pdf

# Configuración de salida
# Nota: el ZIP incluye renders PNG a 200 DPI y las imágenes embebidas en su formato original.
```

## Estructura del proyecto

```
pdf-image-extractor/
├── app/
│   ├── __init__.py
│   ├── main.py                 # Punto de entrada de FastAPI
│   ├── config.py               # Configuración y settings
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py        # Endpoints de la API
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Modelos Pydantic
│   └── services/
│       ├── __init__.py
│       └── image_extractor.py  # Lógica de extracción con PyMuPDF
├── uploads/                    # Directorio temporal para PDFs subidos
├── outputs/                    # Directorio para imágenes extraídas
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── Makefile
├── example_client.py           # Script de ejemplo
└── README.md
```

## Comandos útiles con Makefile

```bash
make help      # Muestra todos los comandos disponibles
make build     # Construye las imágenes de Docker
make up        # Inicia los servicios
make down      # Detiene los servicios
make restart   # Reinicia los servicios
make logs      # Muestra los logs
make clean     # Limpia contenedores e imágenes
make test      # Ejecuta el script de ejemplo
```

## Documentación de la API

Una vez que la aplicación esté en ejecución, puedes acceder a:

- **Swagger UI**: http://localhost:5050/docs
- **ReDoc**: http://localhost:5050/redoc

Estas interfaces proporcionan documentación interactiva donde puedes probar todos los endpoints.

## Características técnicas

### Manejo de imágenes

- Renderiza cada página a PNG (DPI 200)
- Extrae imágenes embebidas en su formato original
- Empaqueta todo en un ZIP para descarga inmediata

### Seguridad

- Validación de tipo de archivo
- Límites de tamaño de archivo configurables
- Limpieza automática de archivos temporales
- Manejo robusto de errores

### Rendimiento

- Procesamiento extremadamente rápido gracias a PyMuPDF
- Manejo eficiente de memoria
- Soporte para archivos PDF grandes
- Health checks para monitoreo

## Casos de uso

- Extracción de imágenes de documentos escaneados
- Procesamiento de PDFs con contenido multimedia
- Análisis de contenido visual en documentos
- Conversión de PDFs a galerías de imágenes
- Preparación de datos para machine learning

## Solución de problemas

### El contenedor no inicia

Verifica que los puertos no estén en uso:
```bash
docker-compose logs
```

### Error al procesar PDF

Asegúrate de que:
- El archivo sea un PDF válido
- El tamaño del archivo no exceda el límite configurado
- El PDF no esté protegido con contraseña

### No se extraen imágenes

Algunos PDFs pueden no contener imágenes embebidas. Verifica el contenido del PDF primero.

## Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## Licencia

Este proyecto está bajo la licencia MIT.

## Referencias y fuentes

Este proyecto utiliza las mejores prácticas y bibliotecas recomendadas en 2026:

- [PyMuPDF Documentation](https://pymupdf.readthedocs.io/en/latest/)
- [I Tested 7 Python PDF Extractors So You Don't Have To (2025 Edition)](https://onlyoneaman.medium.com/i-tested-7-python-pdf-extractors-so-you-dont-have-to-2025-edition-c88013922257)
- [Battle of the PDF Titans](https://openwebtech.com/battle-of-the-pdf-titans-apache-tika-pymupdf-pdfplumber-pdf2image-and-textract/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## Soporte

Si encuentras algún problema o tienes preguntas, por favor abre un issue en el repositorio.

---

Desarrollado con ❤️ usando **PyMuPDF** y **FastAPI**
