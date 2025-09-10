[CmdletBinding()]
param(
  [string]$DistPath = "ui/dist",
  [string]$WebPath = "app/web"
)

$ErrorActionPreference = 'Stop'
if (!(Test-Path $DistPath)) { throw "Build output not found: $DistPath. Run 'npm run build' in ui/." }
New-Item -ItemType Directory -Path $WebPath -Force | Out-Null
robocopy $DistPath $WebPath /E | Out-Null
Write-Host "Copied UI from '$DistPath' to '$WebPath'. Open http://127.0.0.1:8000/"

