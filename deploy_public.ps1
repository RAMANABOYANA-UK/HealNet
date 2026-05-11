$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

docker compose up --build -d
Write-Host 'HealNet is starting on http://localhost:9000/mcp' -ForegroundColor Green
