# PowerShell wrapper: descarga vídeo, extrae audio y frames, y llama al script Python
# Requisitos (instalar antes):
# - ffmpeg (añadir a PATH)
# - yt-dlp (pip install yt-dlp o instalar binario)
# - Python 3.9+ en PATH
# - pip install -r requirements.txt (ver abajo)

param(
    [Parameter(Mandatory=$true)][string]$url,
    [string]$outDir = "./output",
    [int]$frameIntervalSec = 2
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Crear directorio de salida
$absOut = Resolve-Path -LiteralPath $outDir -ErrorAction SilentlyContinue
if (-not $?) { New-Item -ItemType Directory -Path $outDir | Out-Null }
$outDir = (Resolve-Path -LiteralPath $outDir).Path

Write-Output "Output: $outDir"

# Descargar vídeo con yt-dlp
Write-Output "Descargando vídeo..."
yt-dlp -f best -o "$outDir\video.%(ext)s" $url --no-warnings

# Encontrar fichero de vídeo descargado
$videoFile = Get-ChildItem -Path $outDir -Filter "video.*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $videoFile) { Write-Error "No se encontró el archivo de vídeo descargado."; exit 1 }
$videoPath = $videoFile.FullName
Write-Output "Vídeo: $videoPath"

# Extraer audio a WAV (mono, 16k)
$audioPath = Join-Path $outDir "audio.wav"
Write-Output "Extrayendo audio a $audioPath..."
ffmpeg -hide_banner -loglevel error -y -i "$videoPath" -vn -ar 16000 -ac 1 "$audioPath"

# Extraer frames cada N segundos
Write-Output "Extrayendo frames cada $frameIntervalSec s..."
$framePattern = Join-Path $outDir "frame_%04d.jpg"
ffmpeg -hide_banner -loglevel error -y -i "$videoPath" -vf "fps=1/$frameIntervalSec" -vsync vfr "$framePattern"

# Llamar al script Python para transcribir y enviar a Claude
Write-Output "Llamando al script Python para transcribir y enviar a Claude..."
$scriptPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..\tools\claude_video_skill.py"
$scriptPath = Resolve-Path -LiteralPath $scriptPath -ErrorAction SilentlyContinue
if (-not $scriptPath) { $scriptPath = Join-Path (Split-Path -Parent $PSScriptRoot) "..\tools\claude_video_skill.py" }

python "$scriptPath" --audio "$audioPath" --frames-dir "$outDir" --video "$videoPath"

Write-Output "Hecho. Revisa salida en: $outDir"

# Requisitos Python (ejecutar una vez):
# pip install openai-whisper anthropic requests
# Nota: openai-whisper funciona en CPU; para modelos más rápidos/precisos considerar faster-whisper o un servicio ASR.
