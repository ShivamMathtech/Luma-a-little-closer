$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
& npm run dev
exit $LASTEXITCODE
