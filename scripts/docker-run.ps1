# PowerShell helper: build Docker image and run container for video processing
# Usage: .\scripts\docker-run.ps1 -url "<instagram_or_youtube_url>"
#   or:  .\scripts\docker-run.ps1 -url "..." -outDir "./output2" -frameInterval 3

param(
    [Parameter(Mandatory=$true)][string]$url,
    [string]$outDir = "./output",
    [int]$frameInterval = 2,
    [string]$tag = "claude-video-skill:latest"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Output "Claude Video Skill Docker Helper"
Write-Output "=================================="

# Verify Docker is available
Write-Output "Checking Docker availability..."
docker --version | Out-Null
if (-not $?) {
    Write-Error "Docker is not installed or not in PATH. Please install Docker Desktop."
    exit 1
}

# Verify ANTHROPIC_API_KEY is set
$apiKey = $env:ANTHROPIC_API_KEY
if (-not $apiKey) {
    Write-Error "ANTHROPIC_API_KEY environment variable is not set. Please configure it first:"
    Write-Output "  [System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'your-key-here', 'User')"
    exit 1
}

# Create output directory
Write-Output "Creating output directory: $outDir"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

# Get absolute path for volume mount
$absOutDir = (Resolve-Path -LiteralPath $outDir).Path
Write-Output "Output directory (absolute): $absOutDir"

# Build image (uses cache on subsequent runs)
Write-Output "Building Docker image (may take 3-5 min on first run)..."
$dockerfilePath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\Dockerfile"
if (-not (Test-Path $dockerfilePath)) {
    Write-Error "Dockerfile not found at $dockerfilePath"
    exit 1
}

docker build -f "$dockerfilePath" -t $tag (Split-Path -Parent $dockerfilePath)
if (-not $?) {
    Write-Error "Docker build failed."
    exit 1
}

Write-Output "Running container..."
docker run --rm `
    -v "$absOutDir`:/output" `
    -e ANTHROPIC_API_KEY="$apiKey" `
    $tag "$url" /output $frameInterval

if ($?) {
    Write-Output ""
    Write-Output "Success! Results in: $absOutDir"
    Write-Output "  - video.* (downloaded)"
    Write-Output "  - audio.wav (extracted)"
    Write-Output "  - frame_*.jpg (keyframes)"
} else {
    Write-Error "Container execution failed."
    exit 1
}
