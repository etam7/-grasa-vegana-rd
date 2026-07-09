#!/bin/sh
set -e

if [ "$1" = "--help" ] || [ -z "$1" ]; then
  cat <<'USAGE'
Usage: docker run --rm -v $(pwd)/output:/output -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" IMAGE <url> [out_dir_on_container] [frameIntervalSec]

Example:
  docker build -t claude-video-skill:latest .
  docker run --rm -v "$(pwd)/output:/output" -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" claude-video-skill:latest "https://youtu.be/..." /output 2

Notes:
 - For GPU image: docker build -f Dockerfile.gpu -t claude-video-skill:gpu .
 - Run GPU container with: docker run --gpus all --rm -v ... -e ANTHROPIC_API_KEY=... claude-video-skill:gpu "<url>" /output 2
USAGE
  exit 0
fi

URL="$1"
OUT_DIR=${2:-/output}
FRAME_INTERVAL=${3:-2}

mkdir -p "$OUT_DIR"

echo "Downloading $URL to $OUT_DIR"
yt-dlp -f best -o "$OUT_DIR/video.%(ext)s" "$URL" --no-warnings

VIDEO_PATH=$(ls -t "$OUT_DIR"/video.* 2>/dev/null | head -n1 || true)
if [ -z "$VIDEO_PATH" ]; then
  echo "Error: no video file found in $OUT_DIR" >&2
  exit 2
fi

echo "Video: $VIDEO_PATH"
AUDIO_PATH="$OUT_DIR/audio.wav"

echo "Extracting audio to $AUDIO_PATH"
ffmpeg -hide_banner -loglevel error -y -i "$VIDEO_PATH" -vn -ar 16000 -ac 1 "$AUDIO_PATH"

echo "Extracting frames every ${FRAME_INTERVAL}s"
ffmpeg -hide_banner -loglevel error -y -i "$VIDEO_PATH" -vf "fps=1/$FRAME_INTERVAL" -vsync vfr "$OUT_DIR/frame_%04d.jpg"

echo "Running transcription and Claude call"
python /app/tools/claude_video_skill.py --audio "$AUDIO_PATH" --frames-dir "$OUT_DIR" --video "$VIDEO_PATH"

echo "Done. Output in $OUT_DIR"
