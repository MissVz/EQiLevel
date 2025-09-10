[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

# Prefer the repo-local venv's Python if present, otherwise fall back to PATH
$repoRoot = (Resolve-Path "$PSScriptRoot/..\").Path
$venvPython = Join-Path $repoRoot ".venv/Scripts/python.exe"
$py = if (Test-Path $venvPython) { $venvPython } else { 'python' }

$scriptPath = Join-Path $PSScriptRoot 'verify_cuda.py'

& $py "$scriptPath"
exit $LASTEXITCODE

