#!/usr/bin/env python3
"""
Script Python: transcribe audio con whisper y envía la transcripción a la API de Anthropic (Claude).
Requisitos:
  pip install openai-whisper requests
  export ANTHROPIC_API_KEY=sk-...
Uso ejemplo:
  python claude_video_skill.py --audio ./output/audio.wav --frames-dir ./output --video ./output/video.mp4
"""
import os
import sys
import argparse
import glob
import json
import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/complete"


def transcribe_with_whisper(audio_path: str) -> str:
    try:
        import whisper
    except Exception as e:
        print("Error: falta la librería 'whisper'. Instala con: pip install openai-whisper")
        raise
    model = whisper.load_model("small")
    print("Transcribiendo audio (whisper small, CPU puede ser lento)...")
    result = model.transcribe(audio_path)
    text = result.get("text", "")
    return text


def call_anthropic(transcription: str, frames: list, video_path: str, model: str = "claude-2.1") -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("La variable de entorno ANTHROPIC_API_KEY no está definida.")

    # Construir prompt: incluir transcripción y lista de frames con nombres
    prompt = (
        "You are Claude, a helpful assistant. "
        "Answer questions about the provided video content. Be concise and include timestamps when relevant.\n\n"
        "TRANSCRIPTION:\n" + transcription.strip() + "\n\n"
        "KEY FRAMES (filenames):\n"
    )
    for f in frames:
        prompt += f"- {os.path.basename(f)}\n"
    prompt += "\nIf the user asks for visual details, reference the frame filenames above by index or name.\n"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "prompt": prompt,
        "max_tokens": 800,
        "temperature": 0.0
    }
    print("Enviando prompt a Anthropic (Claude)...")
    r = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    # La respuesta real depende del formato de la API. Aquí se intenta leer de campos comunes.
    text_out = data.get("completion", None) or data.get("completion", "") or data.get("text", "")
    if not text_out:
        # Intentar extraer de choices (formato similar a OpenAI)
        choices = data.get("choices")
        if choices and len(choices) > 0:
            text_out = choices[0].get("text") or choices[0].get("message", {}).get("content", "")
    return text_out


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio and send to Claude (Anthropic).")
    parser.add_argument("--audio", required=True, help="Ruta al archivo audio WAV")
    parser.add_argument("--frames-dir", required=True, help="Directorio donde están los frames extraídos")
    parser.add_argument("--video", required=False, help="Ruta del vídeo (opcional)")
    parser.add_argument("--model", default="claude-2.1", help="Nombre del modelo Anthropic (por defecto claude-2.1)")
    parser.add_argument("--max-frames", type=int, default=8, help="Número máximo de frames a listar en el prompt")
    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"Audio no encontrado: {args.audio}")
        sys.exit(1)

    # Buscar frames en el directorio, ordenarlos por nombre
    frames = sorted(glob.glob(os.path.join(args.frames_dir, "frame_*.jpg")))
    frames = frames[: args.max_frames]

    transcription = transcribe_with_whisper(args.audio)
    print("--- Transcripción (primeros 1000 chars) ---")
    print(transcription[:1000])

    try:
        response_text = call_anthropic(transcription, frames, args.video or "")
    except Exception as e:
        print("Error llamando a la API de Anthropic:", e)
        sys.exit(1)

    print("--- Respuesta de Claude ---")
    if response_text:
        print(response_text)
    else:
        print(json.dumps(response_text, indent=2))


if __name__ == "__main__":
    main()
