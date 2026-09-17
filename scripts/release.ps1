$ErrorActionPreference = 'Stop'

Set-Location (Split-Path -Parent $PSScriptRoot) | Out-Null

python -m pytest -q

New-Item -ItemType Directory -Force dist | Out-Null
$name = "api-platform-{0:yyyyMMdd-HHmmss}" -f (Get-Date)
$out = Join-Path dist "$name.zip"

$items = @(
    "main.py",
    "admin",
    "apis",
    "core",
    "static",
    "tests",
    "deploy",
    "Dockerfile",
    "docker-compose.yml",
    "DEPLOY.md",
    "README.md",
    "requirements.txt",
    "config.json.example"
)

if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path $items -DestinationPath $out
Write-Host "release: $out"
