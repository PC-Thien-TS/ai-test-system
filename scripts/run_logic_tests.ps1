param(
    [string]$BackendPath = "",
    [string]$FrontendPath = "",
    [string]$ArtifactsRoot = "",
    [switch]$UnitOnly
)

$ErrorActionPreference = "Stop"

function Resolve-RepoRoot {
    $scriptDir = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($scriptDir)) {
        $scriptDir = Split-Path -Parent $PSCommandPath
    }
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Get-SourcePathFromEvidence {
    param(
        [string]$EvidenceFile,
        [string]$SourceName
    )

    if (-not (Test-Path $EvidenceFile)) {
        return ""
    }

    $content = Get-Content $EvidenceFile
    $lineIndex = -1

    for ($i = 0; $i -lt $content.Length; $i++) {
        if ($content[$i] -match "^\s*-\s*name:\s*$SourceName\s*$") {
            $lineIndex = $i
            break
        }
    }

    if ($lineIndex -lt 0) {
        return ""
    }

    for ($j = $lineIndex + 1; $j -lt [Math]::Min($lineIndex + 8, $content.Length); $j++) {
        if ($content[$j] -match "^\s*path:\s*(.+)\s*$") {
            $raw = $Matches[1].Trim()
            return $raw -replace "/", "\"
        }
    }

    return ""
}

function Ensure-Command {
    param([string]$Name)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    return $null -ne $cmd
}

function Run-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "=== $Name ==="
    & $Action
}

function Invoke-Native {
    param(
        [scriptblock]$Action,
        [string]$ErrorMessage
    )

    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$ErrorMessage (exit code: $LASTEXITCODE)"
    }
}

$repoRoot = Resolve-RepoRoot
$evidenceFile = Join-Path $repoRoot "evidence_sources.yaml"

if ([string]::IsNullOrWhiteSpace($BackendPath)) {
    $BackendPath = Get-SourcePathFromEvidence -EvidenceFile $evidenceFile -SourceName "backend"
}
if ([string]::IsNullOrWhiteSpace($FrontendPath)) {
    $FrontendPath = Get-SourcePathFromEvidence -EvidenceFile $evidenceFile -SourceName "web_admin"
}
if ([string]::IsNullOrWhiteSpace($ArtifactsRoot)) {
    $ArtifactsRoot = Join-Path $repoRoot "artifacts\test-results"
}

$backendResults = Join-Path $ArtifactsRoot "backend"
$frontendResults = Join-Path $ArtifactsRoot "frontend"

New-Item -Path $backendResults -ItemType Directory -Force | Out-Null
New-Item -Path $frontendResults -ItemType Directory -Force | Out-Null

Write-Host "Repo root:        $repoRoot"
Write-Host "Backend path:     $BackendPath"
Write-Host "Frontend path:    $FrontendPath"
Write-Host "Artifacts root:   $ArtifactsRoot"
if ($UnitOnly) {
    Write-Host "MODE: UNIT_ONLY"
}
else {
    Write-Host "MODE: FULL"
}

if (-not (Test-Path $BackendPath)) {
    throw "Backend path not found: $BackendPath"
}
if (-not (Test-Path $FrontendPath)) {
    throw "Frontend path not found: $FrontendPath"
}

$slnFiles = Get-ChildItem -Path $BackendPath -Filter *.sln -Recurse | Select-Object -ExpandProperty FullName
$csprojFiles = Get-ChildItem -Path $BackendPath -Filter *.csproj -Recurse | Select-Object -ExpandProperty FullName
$frontendPackage = Join-Path $FrontendPath "package.json"

Write-Host ""
Write-Host "Detected backend solutions:"
$slnFiles | ForEach-Object { Write-Host " - $_" }
Write-Host "Detected backend projects:"
$csprojFiles | ForEach-Object { Write-Host " - $_" }
Write-Host "Detected frontend package:"
Write-Host " - $frontendPackage"

$hasFailures = $false
$backendUnitLane = "NOT_RUN"
$backendIntegrationLane = "NOT_RUN"
$frontendLane = "NOT_RUN"

if (-not (Ensure-Command -Name "dotnet")) {
    Write-Host ""
    Write-Host "ERROR: dotnet SDK not found in PATH. Install .NET SDK (8.x recommended)."
    $hasFailures = $true
    $backendUnitLane = "FAILED: dotnet not found"
    if ($UnitOnly) {
        $backendIntegrationLane = "SKIPPED: Backend.IntegrationTests (known compile issue: Moq ReturnsAsync mismatch)"
    }
    else {
        $backendIntegrationLane = "FAILED: dotnet not found"
    }
}
else {
    $backendSln = Join-Path $BackendPath "CoreV2.sln"
    if (-not (Test-Path $backendSln)) {
        Write-Host "ERROR: backend solution not found at $backendSln"
        $hasFailures = $true
        $backendUnitLane = "FAILED: solution missing"
        if ($UnitOnly) {
            $backendIntegrationLane = "SKIPPED: Backend.IntegrationTests (known compile issue: Moq ReturnsAsync mismatch)"
        }
        else {
            $backendIntegrationLane = "FAILED: solution missing"
        }
    }
    else {
        try {
            Run-Step "Backend restore" {
                Push-Location $BackendPath
                Invoke-Native -ErrorMessage "dotnet restore failed" -Action {
                    dotnet restore CoreV2.sln
                }
                Pop-Location
            }

            if ($UnitOnly) {
                $backendUnitProj = Join-Path $BackendPath "tests\Backend.UnitTests\Backend.UnitTests.csproj"
                if (-not (Test-Path $backendUnitProj)) {
                    throw "Backend unit test project not found: $backendUnitProj"
                }

                Run-Step "Backend unit tests only (.trx + .junit.xml)" {
                    Push-Location $BackendPath
                    Invoke-Native -ErrorMessage "backend unit tests failed" -Action {
                        dotnet test $backendUnitProj `
                            --configuration Release `
                            --results-directory "$backendResults" `
                            --logger "trx;LogFileName=backend_tests.trx" `
                            --logger "junit;LogFilePath=$backendResults\backend_tests.junit.xml"
                    }
                    Pop-Location
                }

                $backendUnitLane = "RAN: PASS"
                $backendIntegrationLane = "SKIPPED: Backend.IntegrationTests (known compile issue: Moq ReturnsAsync mismatch)"
            }
            else {
                Run-Step "Backend tests (.trx + .junit.xml)" {
                    Push-Location $BackendPath
                    Invoke-Native -ErrorMessage "backend tests failed" -Action {
                        dotnet test CoreV2.sln `
                            --configuration Release `
                            --results-directory "$backendResults" `
                            --logger "trx;LogFileName=backend_tests.trx" `
                            --logger "junit;LogFilePath=$backendResults\backend_tests.junit.xml"
                    }
                    Pop-Location
                }

                $backendUnitLane = "RAN: included in full backend lane"
                $backendIntegrationLane = "RAN: included in full backend lane"
            }
        }
        catch {
            Write-Host "ERROR: backend tests failed."
            Write-Host $_
            $hasFailures = $true
            if ($backendUnitLane -eq "NOT_RUN") {
                $backendUnitLane = "FAILED"
            }
            if ($backendIntegrationLane -eq "NOT_RUN") {
                if ($UnitOnly) {
                    $backendIntegrationLane = "SKIPPED: Backend.IntegrationTests (known compile issue: Moq ReturnsAsync mismatch)"
                }
                else {
                    $backendIntegrationLane = "FAILED"
                }
            }
        }
    }
}

if (-not (Ensure-Command -Name "npm")) {
    Write-Host ""
    Write-Host "ERROR: npm not found in PATH. Install Node.js 18+."
    $hasFailures = $true
    $frontendLane = "FAILED: npm not found"
}
else {
    try {
        Run-Step "Frontend install" {
            Push-Location $FrontendPath
            if (-not (Test-Path (Join-Path $FrontendPath "node_modules"))) {
                Invoke-Native -ErrorMessage "npm install failed" -Action {
                    npm install
                }
            }
            Pop-Location
        }

        Run-Step "Frontend unit tests (.junit.xml)" {
            Push-Location $FrontendPath
            Invoke-Native -ErrorMessage "frontend tests failed" -Action {
                npm test -- --reporter=default --reporter=junit --outputFile="$frontendResults\frontend_tests.junit.xml"
            }
            Pop-Location
        }

        $frontendLane = "RAN: PASS"
    }
    catch {
        Write-Host "ERROR: frontend tests failed."
        Write-Host $_
        $hasFailures = $true
        if ($frontendLane -eq "NOT_RUN") {
            $frontendLane = "FAILED"
        }
    }
}

Write-Host ""
Write-Host "=== Summary ==="
if ($UnitOnly) {
    Write-Host "MODE: UNIT_ONLY"
}
else {
    Write-Host "MODE: FULL"
}
Write-Host "Backend.UnitTests: $backendUnitLane"
Write-Host "Backend.IntegrationTests: $backendIntegrationLane"
Write-Host "Frontend.UnitTests: $frontendLane"
if ($UnitOnly) {
    Write-Host "SKIPPED: Backend.IntegrationTests (known compile issue: Moq ReturnsAsync mismatch)"
}
if ($hasFailures) {
    Write-Host "Logic test run completed with failures."
    Write-Host "Reports location: $ArtifactsRoot"
    exit 1
}
else {
    Write-Host "Logic test run succeeded."
    Write-Host "Reports location: $ArtifactsRoot"
    exit 0
}
