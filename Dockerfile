# Dockerfile (CPU) for Claude video skill
FROM python:3.10-slim
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ffmpeg \
        git \
        curl \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python deps (yt-dlp included)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt yt-dlp

# Copy scripts and tools
COPY scripts/ scripts/
COPY tools/ tools/

# Entrypoint
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["--help"]
