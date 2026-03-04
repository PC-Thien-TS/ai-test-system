.\.venv\Scripts\Activate.ps1

python scripts/run_domain_manual.py `
    --domain didaunao_release_audit `
    --run-id didaunao_weekly_release

python scripts/validate_outputs.py `
    outputs/didaunao_release_audit/didaunao_weekly_release

python scripts/export_release_audit_report.py `
    outputs/didaunao_release_audit/didaunao_weekly_release

Write-Host "Release audit report generated."