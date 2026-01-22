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
- ✅ API REST con documentación automática (Swagger/OpenAPI)
- ✅ Soporte para múltiples formatos de salida (PNG, JPG/JPEG)
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

### Probar en Swagger UI (recomendado)

1. Abre la documentación interactiva: http://localhost:5050/docs
2. Expande el endpoint que quieras probar.
3. Haz clic en **Try it out**.
4. Completa los parámetros:
   - Para `POST /api/v1/extract`, selecciona un PDF en el campo `file`.
   - (Opcional) agrega `output_format` con `png`, `jpg` o `jpeg`.
5. Presiona **Execute** y revisa la respuesta.

Ejemplo rápido:
- Endpoint: `POST /api/v1/extract`
- Params: `output_format=png`
- file: selecciona `tu-archivo.pdf`

Respuesta esperada (200):
```json
{
  "success": true,
  "message": "Images extracted successfully",
  "total_pages": 10,
  "total_images": 5,
  "images": [
    {
      "filename": "page_1_img_1.png",
      "page_number": 1,
      "width": 1920,
      "height": 1080,
      "format": "png",
      "size_bytes": 245678,
      "color_space": "DeviceRGB"
    }
  ],
  "extraction_time": 0.45,
  "timestamp": "2026-01-21T10:30:00"
}
```

### Endpoint: Extraer imágenes

**POST** `/api/v1/extract`

Sube un archivo PDF y extrae todas las imágenes.

#### Usando cURL:

```bash
curl -X POST "http://localhost:5050/api/v1/extract" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your-file.pdf" \
  -F "output_format=png"
```

#### Usando Python:

```python
import requests

url = "http://localhost:5050/api/v1/extract"
files = {"file": open("your-file.pdf", "rb")}
params = {"output_format": "png"}

response = requests.post(url, files=files, params=params)
print(response.json())
```

#### Usando el script de ejemplo:

```bash
python example_client.py
```

### Respuesta de ejemplo:

```json
{
  "success": true,
  "message": "Images extracted successfully",
  "total_pages": 10,
  "total_images": 5,
  "images": [
    {
      "filename": "page_1_img_1.png",
      "page_number": 1,
      "width": 1920,
      "height": 1080,
      "format": "png",
      "size_bytes": 245678,
      "color_space": "DeviceRGB"
    }
  ],
  "extraction_time": 0.45,
  "timestamp": "2026-01-21T10:30:00"
}
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
OUTPUT_FORMAT=png  # png, jpg, jpeg
IMAGE_QUALITY=95
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

- Preserva la calidad original de las imágenes
- Convierte automáticamente entre formatos (PNG, JPEG)
- Maneja correctamente imágenes RGBA al convertir a JPEG
- Optimiza el tamaño de archivo sin pérdida de calidad

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
