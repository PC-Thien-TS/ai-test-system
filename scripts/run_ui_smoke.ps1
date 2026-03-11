param()

$ErrorActionPreference = "Stop"

function RepoRoot {
    $d = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($d)) { $d = Split-Path -Parent $PSCommandPath }
    return (Resolve-Path (Join-Path $d "..")).Path
}

function Req([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($v)) { throw "Missing required environment variable: $name" }
    return $v
}

function Opt([string]$name, [string]$defaultValue = "") {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($v)) { return $defaultValue }
    return $v
}

function HasCommand([string]$name) {
    return $null -ne (Get-Command $name -ErrorAction SilentlyContinue)
}

function Parse-PlaywrightSummary([string]$reportPath) {
    if (-not (Test-Path $reportPath)) {
        return [pscustomobject]@{
            total = 0
            passed = 0
            failed = 1
            skipped = 0
            error = "Playwright JSON report not found."
        }
    }

    $report = Get-Content -Path $reportPath -Raw | ConvertFrom-Json
    $stats = $report.stats
    $passed = 0
    $failed = 0
    $skipped = 0
    $flaky = 0
    if ($stats) {
        if ($null -ne $stats.PSObject.Properties["expected"]) { $passed = [int]$stats.expected }
        if ($null -ne $stats.PSObject.Properties["unexpected"]) { $failed = [int]$stats.unexpected }
        if ($null -ne $stats.PSObject.Properties["skipped"]) { $skipped = [int]$stats.skipped }
        if ($null -ne $stats.PSObject.Properties["flaky"]) { $flaky = [int]$stats.flaky }
    }
    $failed += $flaky
    $total = $passed + $failed + $skipped
    return [pscustomobject]@{
        total = $total
        passed = $passed
        failed = $failed
        skipped = $skipped
        error = $null
    }
}

$root = RepoRoot
$suiteDir = Join-Path $root "tests/ui_smoke"
$outDir = Join-Path $root "artifacts/test-results/ui-smoke"
$logPath = Join-Path $outDir "ui_smoke.log"
$summaryPath = Join-Path $outDir "ui_smoke.summary.json"
$reportPath = Join-Path $outDir "playwright-report.json"
$junitPath = Join-Path $outDir "playwright-junit.xml"

New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$global:LogLines = New-Object System.Collections.Generic.List[string]
$exitCode = 0
$startedAt = (Get-Date).ToString("o")

function Log([string]$m) {
    $line = "[{0}] {1}" -f (Get-Date).ToString("s"), $m
    $global:LogLines.Add($line) | Out-Null
    Write-Host $m
}

try {
    $baseUrl = Req "BASE_URL"
    if (-not (Test-Path $suiteDir)) { throw "UI smoke suite folder not found: $suiteDir" }
    if (-not (HasCommand "node")) { throw "Node.js is required. Install Node.js and ensure 'node' is on PATH." }
    if (-not (HasCommand "npm")) { throw "npm is required. Install Node.js/npm and ensure 'npm' is on PATH." }

    Log "UI smoke start. base_url=$baseUrl"
    Push-Location $suiteDir

    if (-not (Test-Path (Join-Path $suiteDir "node_modules"))) {
        Log "Installing UI smoke dependencies..."
        & npm install --no-audit --no-fund 2>&1 | ForEach-Object { Log ([string]$_) }
        if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
    }

    Log "Ensuring Playwright Chromium browser is installed..."
    & npx playwright install chromium 2>&1 | ForEach-Object { Log ([string]$_) }
    if ($LASTEXITCODE -ne 0) {
        Log "WARN: 'npx playwright install chromium' failed. Continuing in case browser is already installed."
    }

    $env:UI_SMOKE_ARTIFACT_DIR = $outDir
    $env:BASE_URL = $baseUrl
    $env:API_BASE_URL = Opt "API_BASE_URL"
    $env:API_USER = Opt "API_USER"
    $env:API_PASS = Opt "API_PASS"

    Log "Running Playwright UI smoke tests..."
    & npx playwright test 2>&1 | ForEach-Object { Log ([string]$_) }
    $runCode = $LASTEXITCODE

    Pop-Location

    $parsed = Parse-PlaywrightSummary $reportPath
    if ($runCode -ne 0 -and $parsed.failed -eq 0) {
        $parsed.failed = 1
        $parsed.total = [Math]::Max(1, $parsed.total)
    }

    $summary = [ordered]@{
        base_url = $baseUrl
        started_at = $startedAt
        finished_at = (Get-Date).ToString("o")
        total = $parsed.total
        passed = $parsed.passed
        failed = $parsed.failed
        skipped = $parsed.skipped
        report_path = $reportPath
        junit_path = $junitPath
        log_path = $logPath
        notes = if ($parsed.error) { $parsed.error } else { "OK" }
    }
    $summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding UTF8

    if ($runCode -ne 0 -or $parsed.failed -gt 0) { $exitCode = 1 }
    Log ("Summary: total={0}, passed={1}, failed={2}, skipped={3}" -f $summary.total, $summary.passed, $summary.failed, $summary.skipped)
    Log "Summary file: $summaryPath"
}
catch {
    $exitCode = 1
    Log ("FATAL: " + $_.Exception.Message)
    $summary = [ordered]@{
        base_url = Opt "BASE_URL"
        started_at = $startedAt
        finished_at = (Get-Date).ToString("o")
        total = 0
        passed = 0
        failed = 1
        skipped = 0
        report_path = $reportPath
        junit_path = $junitPath
        log_path = $logPath
        notes = ("FATAL: " + $_.Exception.Message)
    }
    $summary | ConvertTo-Json -Depth 10 | Set-Content -Path $summaryPath -Encoding UTF8
}
finally {
    try { Set-Content -Path $logPath -Value $global:LogLines -Encoding UTF8 }
    catch {
        $fallback = Join-Path $outDir ("ui_smoke.{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
        Set-Content -Path $fallback -Value $global:LogLines -Encoding UTF8
        Write-Host "Primary log locked. Fallback log: $fallback"
    }
    if (Get-Location) {
        try { Pop-Location | Out-Null } catch { }
    }
}

exit $exitCode
