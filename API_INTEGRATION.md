# API Integration Usage

## Quick Start (Local API Calls)

1. **Instalar dependencias:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Ejecutar con URL e pregunta:**
   ```powershell
   $env:ANTHROPIC_API_KEY = "tu-clave-aqui"
   python tools/claude_video_api.py --url "https://www.youtube.com/watch?v=..." --question "¿Qué ves en el vídeo?"
   ```

3. **Parámetros opcionales:**
   ```powershell
   python tools/claude_video_api.py `
     --url "https://..." `
     --question "Tu pregunta aquí" `
     --model "claude-3-5-sonnet-20241022" `
     --frame-interval 3 `
     --max-frames 10 `
     --temp-dir "./temp_output"
   ```

## Qué Sucede

1. Descarga el vídeo (YouTube, Instagram, TikTok, etc.)
2. Extrae audio y lo transcribe con Whisper
3. Extrae frames clave del vídeo
4. Codifica frames como base64
5. Envía todo a Claude via API de Anthropic
6. Claude devuelve la respuesta (directamente en tu script/CLI)

## Modelos Disponibles

- `claude-3-5-sonnet-20241022` (recomendado — rápido, barato)
- `claude-3-opus-20250219` (más potente, más caro)

## En Tu Código (Python)

```python
from tools.claude_video_api import query_claude_with_video

api_key = "tu-clave"
response = query_claude_with_video(
    api_key=api_key,
    transcription="audio transcript here",
    frames=["frame_0001.jpg", "frame_0002.jpg"],
    question="¿Qué sucede en el vídeo?"
)
print(response)
```

## Ventajas

- ✅ Completo control programático
- ✅ Automatizable en scripts/CI
- ✅ Soporta loops/múltiples preguntas sobre el mismo vídeo
- ✅ Sin limites de frames (solo costo API)
- ✅ Respuestas directas en tu código

## Costos

- Anthropic cobra por tokens (transcripción + frames + respuesta)
- Whisper (OpenAI) puede cobrar por audio (~$0.01 min)
- Alternativa: usar faster-whisper localmente (gratis, CPU/GPU)
