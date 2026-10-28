param([switch]$Seed, [switch]$SkipInfrastructure)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
function Run([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Program failed with exit code $LASTEXITCODE" }
}
foreach ($tool in @("py", "node", "npm")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) { throw "Install $tool first. See docs/WINDOWS_SETUP.md." }
}
if (-not (Test-Path "backend/.env")) { Copy-Item "backend/.env.example" "backend/.env" }
if (-not (Test-Path "frontend/.env")) { Copy-Item "frontend/.env.example" "frontend/.env" }
if (-not $SkipInfrastructure) {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Install and start Docker Desktop, or use -SkipInfrastructure with your own PostgreSQL and Redis." }
    Run "docker" @("compose", "-f", "infrastructure/docker-compose.yml", "up", "-d", "--wait", "db", "redis")
}
if (-not (Test-Path "backend/.venv/Scripts/python.exe")) { Run "py" @("-3.12", "-m", "venv", "backend/.venv") }
$python = Join-Path $PSScriptRoot "backend/.venv/Scripts/python.exe"
Push-Location backend
try {
    Run $python @("-m", "pip", "install", "-r", "requirements-dev.lock", "-e", ".[dev]")
    Run $python @("-m", "alembic", "upgrade", "head")
    if ($Seed) { Run $python @("-m", "app.db.seed") }
} finally { Pop-Location }
Push-Location frontend
try { Run "npm" @("ci") } finally { Pop-Location }
Write-Host "Ready. Run npm run dev from this folder, then open http://localhost:5173"
Write-Host "In another terminal: cd backend; ./.venv/Scripts/python.exe -m app.workers.run"
