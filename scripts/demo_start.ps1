Param(
  [string]$Port = "8000"
)

Write-Host "[demo] Building UI (Vite)…"
Push-Location "ui"
try {
  # Ensure Vite builds with base path for FastAPI static mount
  $env:VITE_BASE = '/web/'

  # Install/update deps so react-router-dom is available
  npm install
  if ($LASTEXITCODE -ne 0) { throw "[demo] npm install failed." }

  # Build UI
  npm run build
  if ($LASTEXITCODE -ne 0) { throw "[demo] UI build failed." }
} finally {
  Pop-Location
}

Write-Host "[demo] Copying UI dist → app/web …"
if (-not (Test-Path "app\web")) { New-Item -ItemType Directory -Path "app\web" | Out-Null }
robocopy "ui\dist" "app\web" /MIR /E | Out-Null

Write-Host "[demo] Starting API on http://127.0.0.1:$Port …"
try {
  # Ensure Chocolatey shims are available in this session (common path for ffmpeg.exe)
  $chocoBin = 'C:\ProgramData\chocolatey\bin'
  if (Test-Path $chocoBin) { $env:PATH = "$chocoBin;" + $env:PATH }
} catch {}
try {
  $ff = (Get-Command ffmpeg -ErrorAction SilentlyContinue)
  if (-not $ff) {
    Write-Host "[demo] Warning: ffmpeg not found on PATH. Whisper may fail to decode webm/opus." -ForegroundColor Yellow
  } else {
    Write-Host "[demo] ffmpeg detected at: $($ff.Source)"
  }
} catch {}
Write-Host "[demo] Tip: If streaming doesn’t finalize, press Stop once or raise the silence threshold in Settings."
uvicorn app.main:app --reload --port $Port
