$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:PYTHONIOENCODING = "utf-8"
Push-Location $root
try {
    & py "hollow star scripts\hollowstar_host.py" local-check
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
