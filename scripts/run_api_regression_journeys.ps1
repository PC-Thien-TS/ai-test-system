param()

$scriptPath = Join-Path $PSScriptRoot "run_api_regression.ps1"
& $scriptPath -Mode JOURNEYS
exit $LASTEXITCODE
