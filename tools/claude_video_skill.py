#!/usr/bin/env python3
"""
Script Python: transcribe audio con whisper y envía la transcripción a la API de Anthropic (Claude).
Intenta adjuntar frames como archivos multipart; si falla, sube las imágenes a S3 o transfer.sh y envía URLs.
Requisitos:
  pip install openai-whisper requests boto3
  export ANTHROPIC_API_KEY=sk-...
Opcional (S3): configurar AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION y AWS_S3_BUCKET
Uso ejemplo:
  python claude_video_skill.py --audio ./output/audio.wav --frames-dir ./output --video ./output/video.mp4
"""
import os
import sys
import argparse
import glob
import json
import requests
import tempfile
import time
from typing import List

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/complete"


def transcribe_with_whisper(audio_path: str) -> str:
    try:
        import whisper
    except Exception:
        print("Error: falta la librería 'whisper'. Instala con: pip install openai-whisper")
        raise
    model = whisper.load_model("small")
    print("Transcribiendo audio (whisper small, CPU puede ser lento)...")
    result = model.transcribe(audio_path)
    text = result.get("text", "")
    return text


def try_send_multipart(prompt: str, frames: List[str], model: str, api_key: str) -> str:
    """Intentar enviar prompt + archivos como multipart/form-data. Si la API no soporta multipart, lanzar excepción."""
    files = []
    try:
        for p in frames:
            fname = os.path.basename(p)
            files.append(("files", (fname, open(p, "rb"), "image/jpeg")))
        data = {
            "model": model,
            "prompt": prompt,
            "max_tokens": 800,
            "temperature": 0.0
        }
        headers = {
            "Authorization": f"Bearer {api_key}"
        }
        print("Intentando envío multipart a Anthropic con frames...")
        resp = requests.post(ANTHROPIC_API_URL, headers=headers, data=data, files=files, timeout=120)
        resp.raise_for_status()
        return parse_anthropic_response(resp)
    finally:
        # cerrar handles
        for _, f in files:
            try:
                f[1].close()
            except Exception:
                pass


def parse_anthropic_response(resp: requests.Response) -> str:
    data = resp.json()
    text_out = data.get("completion") or data.get("text") or ""
    if not text_out:
        choices = data.get("choices")
        if choices and len(choices) > 0:
            text_out = choices[0].get("text") or choices[0].get("message", {}).get("content", "")
    return text_out


def upload_frames_to_s3(frames: List[str]) -> List[str]:
    """Upload frames to S3 if AWS env vars are configured. Return list of presigned URLs."""
    try:
        import boto3
        from botocore.exceptions import BotoCoreError
    except Exception:
        raise RuntimeError("boto3 no está disponible; instala boto3 para usar S3 upload")

    bucket = os.environ.get("AWS_S3_BUCKET")
    if not bucket:
        raise RuntimeError("AWS_S3_BUCKET no está configurado")

    s3 = boto3.client("s3")
    urls = []
    for p in frames:
        key = f"claude-video-skill/{int(time.time())}-{os.path.basename(p)}"
        try:
            s3.upload_file(p, bucket, key, ExtraArgs={"ACL": "private", "ContentType": "image/jpeg"})
            url = s3.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=7*24*3600)
            urls.append(url)
        except Exception as e:
            raise RuntimeError(f"Error subiendo {p} a S3: {e}")
    return urls


def upload_frames_to_transfer_sh(frames: List[str]) -> List[str]:
    """Upload frames to transfer.sh as fallback; returns list of URLs."""
    urls = []
    for p in frames:
        fname = os.path.basename(p)
        with open(p, "rb") as fh:
            print(f"Subiendo {fname} a transfer.sh...")
            r = requests.put(f"https://transfer.sh/{fname}", data=fh, timeout=120)
            if r.status_code in (200, 201):
                urls.append(r.text.strip())
            else:
                raise RuntimeError(f"transfer.sh upload failed for {fname}: {r.status_code}")
    return urls


def call_anthropic_json(prompt: str, model: str, api_key: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {"model": model, "prompt": prompt, "max_tokens": 800, "temperature": 0.0}
    print("Enviando prompt JSON a Anthropic (Claude)...")
    r = requests.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    return parse_anthropic_response(r)


def prepare_prompt(transcription: str, frames_listing: List[str]) -> str:
    prompt = (
        "You are Claude, a helpful assistant. Answer questions about the provided video content. "
        "Be concise and include timestamps when relevant.\n\n"
        "TRANSCRIPTION:\n" + transcription.strip() + "\n\n"
        "VISUAL REFERENCES (URLs or filenames):\n"
    )
    for u in frames_listing:
        prompt += f"- {u}\n"
    prompt += "\nIf the user asks for visual details, reference the visual items above by index or name.\n"
    return prompt


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio and send to Claude (Anthropic).")
    parser.add_argument("--audio", required=True, help="Ruta al archivo audio WAV")
    parser.add_argument("--frames-dir", required=True, help="Directorio donde están los frames extraídos")
    parser.add_argument("--video", required=False, help="Ruta del vídeo (opcional)")
    parser.add_argument("--model", default="claude-2.1", help="Nombre del modelo Anthropic (por defecto claude-2.1)")
    parser.add_argument("--max-frames", type=int, default=8, help="Número máximo de frames a listar en el prompt")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("La variable de entorno ANTHROPIC_API_KEY no está definida.")
        sys.exit(1)

    if not os.path.exists(args.audio):
        print(f"Audio no encontrado: {args.audio}")
        sys.exit(1)

    frames = sorted(glob.glob(os.path.join(args.frames_dir, "frame_*.jpg")))[: args.max_frames]

    transcription = transcribe_with_whisper(args.audio)
    print("--- Transcripción (primeros 1000 chars) ---")
    print(transcription[:1000])

    # Construir prompt parcial
    frames_list = [os.path.basename(f) for f in frames]
    prompt = prepare_prompt(transcription, frames_list)

    # Intentar multipart (adjuntar imágenes directamente)
    try:
        response_text = try_send_multipart(prompt, frames, args.model, api_key)
        print("--- Respuesta de Claude (multipart) ---")
        print(response_text)
        return
    except Exception as e:
        print(f"Multipart failed or not supported: {e}. Falling back to hosted URLs...")

    # Fallback: subir imágenes a S3 si está configurado, si no, a transfer.sh
    urls = []
    try:
        if os.environ.get("AWS_S3_BUCKET"):
            urls = upload_frames_to_s3(frames)
        else:
            urls = upload_frames_to_transfer_sh(frames)
    except Exception as e:
        print(f"Error subiendo frames a hosting: {e}")
        sys.exit(1)

    # Preparar prompt con URLs
    prompt_with_urls = prepare_prompt(transcription, urls)

    try:
        response_text = call_anthropic_json(prompt_with_urls, args.model, api_key)
    except Exception as e:
        print("Error llamando a la API de Anthropic:", e)
        sys.exit(1)

    print("--- Respuesta de Claude (URLs) ---")
    if response_text:
        print(response_text)
    else:
        print(json.dumps(response_text, indent=2))


if __name__ == "__main__":
    main()
