#!/usr/bin/env python3
"""
Claude Video Skill - API Integration Script
Descarga vídeo, procesa audio/frames y hace preguntas a Claude via API de Anthropic.

Requisitos:
  pip install anthropic yt-dlp openai-whisper requests boto3

Uso:
  python claude_video_api.py --url "https://instagram.com/reel/..." --question "¿Qué ves en el vídeo?"

Enviroment:
  ANTHROPIC_API_KEY=sk-... (requerido)
  AWS_S3_BUCKET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY (opcional, para S3 upload)
"""
import os
import sys
import argparse
import glob
import tempfile
import time
import subprocess
import base64
from pathlib import Path
from typing import List

# API client
try:
    from anthropic import Anthropic
except ImportError:
    print("Error: anthropic library not found. Install with: pip install anthropic")
    sys.exit(1)


def download_video(url: str, out_dir: str) -> str:
    """Download video using yt-dlp. Return video file path."""
    print(f"Downloading video from {url}...")
    cmd = f'yt-dlp -f best -o "{out_dir}/video.%(ext)s" "{url}" --no-warnings'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr}")
    
    # Find the downloaded video file
    video_files = glob.glob(os.path.join(out_dir, "video.*"))
    if not video_files:
        raise RuntimeError("No video file found after download")
    return sorted(video_files)[-1]


def extract_audio(video_path: str, out_dir: str) -> str:
    """Extract audio as WAV using ffmpeg."""
    audio_path = os.path.join(out_dir, "audio.wav")
    print(f"Extracting audio to {audio_path}...")
    cmd = f'ffmpeg -hide_banner -loglevel error -y -i "{video_path}" -vn -ar 16000 -ac 1 "{audio_path}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg audio extraction failed: {result.stderr}")
    return audio_path


def extract_frames(video_path: str, out_dir: str, interval: int = 2) -> List[str]:
    """Extract keyframes using ffmpeg."""
    print(f"Extracting frames every {interval}s...")
    frame_pattern = os.path.join(out_dir, "frame_%04d.jpg")
    cmd = f'ffmpeg -hide_banner -loglevel error -y -i "{video_path}" -vf "fps=1/{interval}" -vsync vfr "{frame_pattern}"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg frame extraction failed: {result.stderr}")
    frames = sorted(glob.glob(os.path.join(out_dir, "frame_*.jpg")))
    return frames[:8]  # Limit to 8 frames


def transcribe_audio(audio_path: str) -> str:
    """Transcribe audio using Whisper."""
    try:
        import whisper
    except ImportError:
        print("Error: openai-whisper not found. Install with: pip install openai-whisper")
        sys.exit(1)
    
    print("Transcribing audio with Whisper (this may take a few minutes)...")
    model = whisper.load_model("small")
    result = model.transcribe(audio_path)
    return result.get("text", "")


def encode_frame_base64(frame_path: str) -> str:
    """Encode frame as base64 for API submission."""
    with open(frame_path, "rb") as fh:
        return base64.standard_b64encode(fh.read()).decode("utf-8")


def query_claude_with_video(api_key: str, transcription: str, frames: List[str], question: str, model: str = "claude-3-5-sonnet-20241022") -> str:
    """Query Claude with video transcription and frames using Anthropic API."""
    client = Anthropic(api_key=api_key)
    
    # Build message content with text and images
    content = [
        {
            "type": "text",
            "text": f"Video Transcription:\n{transcription}\n\nUser Question:\n{question}"
        }
    ]
    
    # Add frames as images
    for frame_path in frames:
        b64_image = encode_frame_base64(frame_path)
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": b64_image
            }
        })
    
    print("Sending request to Claude API...")
    response = client.messages.create(
        model=model,
        max_tokens=2048,
        messages=[
            {
                "role": "user",
                "content": content
            }
        ]
    )
    
    return response.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Claude Video Skill - Process videos and ask Claude questions.")
    parser.add_argument("--url", required=True, help="Video URL (YouTube, Instagram, etc.)")
    parser.add_argument("--question", required=True, help="Question to ask Claude about the video")
    parser.add_argument("--model", default="claude-3-5-sonnet-20241022", help="Anthropic model to use")
    parser.add_argument("--frame-interval", type=int, default=2, help="Seconds between frames")
    parser.add_argument("--max-frames", type=int, default=8, help="Max frames to send")
    parser.add_argument("--temp-dir", default=None, help="Temporary directory (default: system temp)")
    
    args = parser.parse_args()
    
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)
    
    # Use temp directory
    if args.temp_dir:
        out_dir = args.temp_dir
        Path(out_dir).mkdir(parents=True, exist_ok=True)
    else:
        out_dir = tempfile.mkdtemp(prefix="claude_video_")
    
    print(f"Working directory: {out_dir}")
    
    try:
        # Process video
        video_path = download_video(args.url, out_dir)
        audio_path = extract_audio(video_path, out_dir)
        frames = extract_frames(video_path, out_dir, args.frame_interval)
        frames = frames[:args.max_frames]
        
        if not frames:
            raise RuntimeError("No frames extracted from video")
        
        transcription = transcribe_audio(audio_path)
        print(f"\n--- Transcription (first 500 chars) ---\n{transcription[:500]}\n")
        
        # Query Claude
        response = query_claude_with_video(api_key, transcription, frames, args.question, args.model)
        
        print("--- Claude's Response ---")
        print(response)
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        print(f"\nWorking files saved in: {out_dir}")


if __name__ == "__main__":
    main()
