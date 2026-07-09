Uso Docker (reproducible container)

CPU image build & run

1) Build (CPU):
   docker build -t claude-video-skill:latest .

2) Run (mount output dir locally and pass API key):
   mkdir -p output
   docker run --rm -v "%cd%\output:/output" -e ANTHROPIC_API_KEY="%ANTHROPIC_API_KEY%" claude-video-skill:latest "https://www.youtube.com/watch?v=..." /output 2

GPU image (optional)

1) Build GPU image (example):
   docker build -f Dockerfile.gpu -t claude-video-skill:gpu .

2) Run GPU image (requires NVIDIA Container Toolkit):
   docker run --gpus all --rm -v "%cd%\output:/output" -e ANTHROPIC_API_KEY="%ANTHROPIC_API_KEY%" claude-video-skill:gpu "https://www.youtube.com/watch?v=..." /output 2

Notas y recomendaciones
- For faster GPU transcription (faster-whisper) install a torch wheel compatible with the CUDA version inside the GPU image. Example (inside Dockerfile.gpu or after build):
    pip install torch --index-url https://download.pytorch.org/whl/cu121
- Ensure ANTHROPIC_API_KEY is set in your environment when running the container (or pass -e ANTHROPIC_API_KEY).
- The container installs yt-dlp and ffmpeg; large models (whisper) will run on CPU unless you install GPU-enabled libraries.
- Respect DRM and copyright when downloading content.

If you want, add a GitHub Actions workflow to build and publish the image.