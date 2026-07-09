Claude video skill

Requisitos:
- Windows 10+, Python 3.9+, ffmpeg en PATH
- Clave de Anthropic en la variable ANTHROPIC_API_KEY

Instalación:
1. Instalar ffmpeg y añadir a PATH: https://ffmpeg.org/download.html
2. Abrir PowerShell y ejecutar:
   python -m pip install -r requirements.txt
   setx ANTHROPIC_API_KEY "tu_api_key_aqui"
   (cierra y abre la shell para que la variable quede disponible)

Uso (ejemplo):
1. Ejecutar el wrapper PowerShell:
   .\scripts\claude_video_skill.ps1 -url "https://www.youtube.com/watch?v=..." -outDir .\output -frameIntervalSec 2

Notas:
- El script extrae audio (WAV 16k), frames y transcribe con Whisper (CPU puede ser lento).
- Define ANTHROPIC_API_KEY antes de ejecutar el script Python.
- Respeta DRM, privacidad y derechos de autor al descargar contenido.

Archivos principales:
- scripts\claude_video_skill.ps1  (descarga + preprocesado)
- tools\claude_video_skill.py    (transcribe y llama a la API de Claude)

Hosting de frames: S3 y transfer.sh

- Opción A — S3 (recomendado si procesas muchos vídeos):
  1. Crear un bucket privado en AWS S3.
  2. Configurar variables de entorno en tu máquina o CI:
     - AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION, AWS_S3_BUCKET
  3. El script tools/claude_video_skill.py detecta AWS_S3_BUCKET y sube frames al bucket, generando URLs pre-firmadas (válidas 7 días).

- Opción B — transfer.sh (fácil, sin cuenta):
  1. El script usará transfer.sh como fallback si no hay AWS_S3_BUCKET configurado.
  2. transfer.sh es temporal y público — no usar para contenido privado o sujeto a copyright.

Uso seguro y derechos:
- Asegúrate de tener permiso para descargar y compartir los vídeos que pruebes. No subas contenido privado o protegido por derechos sin autorización.

¿Quieres que añada un ejemplo con manejo de chunks largos o soporte para faster-whisper/CPU/GPU?