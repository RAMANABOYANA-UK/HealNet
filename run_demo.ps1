param(
    [ValidateSet('validate','server')]
    [string]$Mode = 'validate'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoRoot

$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw 'Virtual environment not found. Create it first with: python -m venv .venv'
}

switch ($Mode) {
    'validate' {
        Write-Host 'Running HealNet validation...' -ForegroundColor Cyan
        & $python test_tools.py
    }
    'server' {
        Write-Host 'Starting HealNet MCP server in HTTP mode...' -ForegroundColor Cyan
        $env:HEALNET_TRANSPORT = 'http'
        $env:HEALNET_HOST = '127.0.0.1'
        $env:HEALNET_PORT = '9000'
        & $python -m healnet.server
    }
}
