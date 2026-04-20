$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    python scripts/run_pytest_with_report.py @args
    $pytestExitCode = $LASTEXITCODE

    python scripts/notify_lark_from_pytest.py
    $notifyExitCode = $LASTEXITCODE
    if ($notifyExitCode -ne 0) {
        Write-Host "[run-and-notify] notify script returned non-zero: $notifyExitCode (ignored)"
    }

    exit $pytestExitCode
}
finally {
    Pop-Location
}

