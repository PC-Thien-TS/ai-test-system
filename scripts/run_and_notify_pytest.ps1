$ErrorActionPreference = "Continue"

python scripts/run_pytest_with_report.py $args
$pytestExitCode = $LASTEXITCODE

python scripts/notify_lark_from_pytest.py
$notifyExitCode = $LASTEXITCODE

if ($notifyExitCode -ne 0) {
    Write-Warning "notify_lark_from_pytest.py exited with code $notifyExitCode (non-blocking)."
}

exit $pytestExitCode

