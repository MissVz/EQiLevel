param(
    [string]$ApiBase = "http://127.0.0.1:8000",
    [string]$AdminKey,
    [Nullable[Int64]]$SessionId = $null,
    [string]$Text = "Hi from smoke test",
    [string]$AudioPath,
    [switch]$PickSample
)

function Get-EnvValueFromDotEnv([string]$Key) {
    if (-not (Test-Path -LiteralPath '.env')) { return $null }
    try {
        $line = Get-Content -LiteralPath .env | Where-Object { $_ -match "^$Key=(.*)$" } | Select-Object -First 1
        if ($line) {
            $m = [regex]::Match($line, "^$Key=(.*)$")
            if ($m.Success) { return $m.Groups[1].Value.Trim('"') }
        }
    } catch {}
    return $null
}

Write-Host "=== Smoke Test: $ApiBase ===" -ForegroundColor Cyan

if (-not $AdminKey) {
    $AdminKey = Get-EnvValueFromDotEnv 'ADMIN_API_KEY'
    if ($AdminKey) {
        Write-Host "Loaded ADMIN_API_KEY from .env" -ForegroundColor DarkGray
    } else {
        Write-Host "ADMIN_API_KEY not provided and not found in .env (admin checks will be skipped)." -ForegroundColor Yellow
    }
}

try {
    Write-Host "-- GET /api/v1/health/full" -ForegroundColor Green
    $health = irm "$ApiBase/api/v1/health/full"
    $health | ConvertTo-Json -Depth 8
} catch {
    Write-Error "Health check failed: $($_.Exception.Message)"
    exit 1
}

try {
    if (-not $SessionId) {
        Write-Host "-- POST /session/start" -ForegroundColor Green
        $sidResp = irm "$ApiBase/session/start" -Method Post
        $SessionId = [int64]$sidResp.session_id
        Write-Host "Session started: $SessionId" -ForegroundColor DarkGray
    } else {
        Write-Host "Using provided SessionId: $SessionId" -ForegroundColor DarkGray
    }
} catch {
    Write-Error "Start session failed: $($_.Exception.Message)"
    exit 1
}

try {
    Write-Host "-- POST /session (text turn)" -ForegroundColor Green
    $body = @{ user_text = $Text; session_id = $SessionId } | ConvertTo-Json
    $reply = irm "$ApiBase/session" -Method Post -ContentType 'application/json' -Body $body
    Write-Host "Reply text:" -ForegroundColor DarkGray
    $reply.text
} catch {
    Write-Error "Posting turn failed: $($_.Exception.Message)"
    exit 1
}

try {
    Write-Host "-- GET /api/v1/debug/db" -ForegroundColor Green
    $db = irm "$ApiBase/api/v1/debug/db"
    $db | ConvertTo-Json -Depth 8
} catch {
    Write-Warning "Debug DB check failed: $($_.Exception.Message)"
}

if ($AdminKey) {
    try {
        Write-Host "-- GET /api/v1/admin/turns_raw?limit=5" -ForegroundColor Green
        $turns = irm "$ApiBase/api/v1/admin/turns_raw?limit=5" -Headers @{ 'X-Admin-Key' = $AdminKey }
        $turns | ConvertTo-Json -Depth 8
    } catch {
        Write-Warning "Admin turns_raw failed: $($_.Exception.Message)"
    }
    try {
        Write-Host "-- GET /api/v1/admin/summary" -ForegroundColor Green
        $summary = irm "$ApiBase/api/v1/admin/summary" -Headers @{ 'X-Admin-Key' = $AdminKey }
        $summary | ConvertTo-Json -Depth 8
    } catch {
        Write-Warning "Admin summary failed: $($_.Exception.Message)"
    }
} else {
    Write-Host "Skipping admin endpoints (no ADMIN_API_KEY)." -ForegroundColor Yellow
}

try {
    Write-Host "-- GET /api/v1/metrics" -ForegroundColor Green
    $metrics = irm "$ApiBase/api/v1/metrics"
    $metrics | ConvertTo-Json -Depth 8
} catch {
    Write-Warning "Metrics check failed: $($_.Exception.Message)"
}

# Optional: /transcribe with a sample file
try {
    $audioToUse = $null
    if ($AudioPath) {
        if (Test-Path -LiteralPath $AudioPath) { $audioToUse = (Resolve-Path -LiteralPath $AudioPath).Path }
        else { Write-Warning "AudioPath not found: $AudioPath" }
    } elseif ($PickSample) {
        $patterns = @('*.wav','*.mp3','*.m4a','*.webm','*.ogg')
        foreach ($p in $patterns) {
            $files = Get-ChildItem -LiteralPath 'samples' -File -Filter $p -ErrorAction SilentlyContinue
            if ($files -and $files.Count -gt 0) { $audioToUse = $files[0].FullName; break }
        }
        if (-not $audioToUse) { Write-Warning "No audio files found in samples (supported: wav/mp3/m4a/webm/ogg)." }
    }

    if ($audioToUse) {
        Write-Host "-- POST /transcribe (file: $audioToUse)" -ForegroundColor Green
        # Prefer -Form if available (PowerShell 7+). Fallback to HttpClient for PS5.
        $irmParams = (Get-Command Invoke-RestMethod).Parameters
        if ($irmParams.ContainsKey('Form')) {
            $resp = irm "$ApiBase/transcribe" -Method Post -Form @{ file = (Get-Item -LiteralPath $audioToUse) }
            $resp | ConvertTo-Json -Depth 8
        } else {
            $handler = New-Object System.Net.Http.HttpClientHandler
            $client = New-Object System.Net.Http.HttpClient($handler)
            try {
                $mp = New-Object System.Net.Http.MultipartFormDataContent
                $fileStream = [System.IO.File]::OpenRead($audioToUse)
                $sc = New-Object System.Net.Http.StreamContent($fileStream)
                $fname = [System.IO.Path]::GetFileName($audioToUse)
                $mp.Add($sc, 'file', $fname)
                $respMsg = $client.PostAsync("$ApiBase/transcribe", $mp).GetAwaiter().GetResult()
                $respStr = $respMsg.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                if (-not $respMsg.IsSuccessStatusCode) { throw "HTTP $($respMsg.StatusCode): $respStr" }
                $respObj = $null
                try { $respObj = $respStr | ConvertFrom-Json } catch { $respObj = @{ raw = $respStr } }
                $respObj | ConvertTo-Json -Depth 8
            } finally {
                if ($fileStream) { $fileStream.Dispose() }
                if ($client) { $client.Dispose() }
            }
        }
    } else {
        Write-Host "Skipping /transcribe (no audio file selected). Use -AudioPath or -PickSample." -ForegroundColor Yellow
    }
} catch {
    Write-Warning "Transcribe check failed: $($_.Exception.Message)"
}

Write-Host "=== Smoke Test Completed ===" -ForegroundColor Cyan
