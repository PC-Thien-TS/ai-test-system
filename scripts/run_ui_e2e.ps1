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
$packageDir = Join-Path $root "tests/ui_smoke"
$configPath = Join-Path $root "tests/ui_e2e/playwright.config.js"
$outDir = Join-Path $root "artifacts/test-results/ui-e2e"
$logPath = Join-Path $outDir "ui_e2e.log"
$summaryPath = Join-Path $outDir "ui_e2e.summary.json"
$reportPath = Join-Path $outDir "playwright-report.json"
$junitPath = Join-Path $outDir "playwright-junit.xml"
$startedAt = (Get-Date).ToString("o")
$global:LogLines = New-Object System.Collections.Generic.List[string]
$exitCode = 0
$npmCmd = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$npxCmd = if ($env:OS -eq "Windows_NT") { "npx.cmd" } else { "npx" }

function Log([string]$m) {
    $line = "[{0}] {1}" -f (Get-Date).ToString("s"), $m
    $global:LogLines.Add($line) | Out-Null
    Write-Host $m
}

New-Item -ItemType Directory -Path $outDir -Force | Out-Null

try {
    $baseUrl = Opt "BASE_URL" "http://192.168.1.7:19068"
    $apiUser = Req "API_USER"
    $apiPass = Req "API_PASS"

    if (-not (Test-Path $packageDir)) { throw "Playwright package folder not found: $packageDir" }
    if (-not (Test-Path $configPath)) { throw "Playwright config not found: $configPath" }
    if (-not (HasCommand "node")) { throw "Node.js is required. Install Node.js and ensure 'node' is on PATH." }
    if (-not (HasCommand $npmCmd)) { throw "npm is required. Install Node.js/npm and ensure 'npm' is on PATH." }
    if (-not (HasCommand $npxCmd)) { throw "npx is required. Install Node.js/npm and ensure 'npx' is on PATH." }

    Log "UI E2E start. base_url=$baseUrl"
    Push-Location $packageDir

    if (-not (Test-Path (Join-Path $packageDir "node_modules"))) {
        Log "Installing Playwright dependencies..."
        & $npmCmd install --no-audit --no-fund 2>&1 | ForEach-Object { Log ([string]$_) }
        if ($LASTEXITCODE -ne 0) { throw "npm install failed with exit code $LASTEXITCODE" }
    }

    Log "Ensuring Playwright Chromium browser is installed..."
    & $npxCmd playwright install chromium 2>&1 | ForEach-Object { Log ([string]$_) }
    if ($LASTEXITCODE -ne 0) {
        Log "WARN: 'npx playwright install chromium' failed. Continuing in case Chromium is already installed."
    }

    $env:UI_E2E_ARTIFACT_DIR = $outDir
    $env:BASE_URL = $baseUrl
    $env:API_USER = $apiUser
    $env:API_PASS = $apiPass
    $env:UI_LOGIN_PATH = Opt "UI_LOGIN_PATH" "/en/login"

    Log "Running Playwright admin E2E suite..."
    & $npxCmd playwright test --config $configPath 2>&1 | ForEach-Object { Log ([string]$_) }
    $runCode = $LASTEXITCODE

    Pop-Location

    $parsed = Parse-PlaywrightSummary $reportPath
    if ($runCode -ne 0 -and $parsed.failed -eq 0) {
        $parsed.failed = 1
        $parsed.total = [Math]::Max(1, $parsed.total)
    }

    $summary = [ordered]@{
        base_url = $baseUrl
        login_path = $env:UI_LOGIN_PATH
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
        base_url = Opt "BASE_URL" "http://192.168.1.7:19068"
        login_path = Opt "UI_LOGIN_PATH" "/en/login"
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
    try {
        Set-Content -Path $logPath -Value $global:LogLines -Encoding UTF8
    }
    catch {
        $fallback = Join-Path $outDir ("ui_e2e.{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
        Set-Content -Path $fallback -Value $global:LogLines -Encoding UTF8
        Write-Host "Primary log locked. Fallback log: $fallback"
    }
    if (Get-Location) {
        try { Pop-Location | Out-Null } catch { }
    }
}

exit $exitCode
