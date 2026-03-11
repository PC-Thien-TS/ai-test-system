param()

$ErrorActionPreference = "Stop"

function Get-RepoRoot {
    $scriptDir = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($scriptDir)) {
        $scriptDir = Split-Path -Parent $PSCommandPath
    }
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Get-RequiredEnv {
    param([string]$Name)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Missing required environment variable: $Name"
    }
    return $value
}

function Get-OptionalEnv {
    param(
        [string]$Name,
        [string]$DefaultValue
    )
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $DefaultValue
    }
    return $value
}

function Normalize-ApiPrefix {
    param([string]$Prefix)
    $p = [string]$Prefix
    if ([string]::IsNullOrWhiteSpace($p)) { $p = "/api/v1" }
    if (-not $p.StartsWith("/")) { $p = "/$p" }
    if ($p.Length -gt 1) { $p = $p.TrimEnd("/") }
    return $p
}

function Get-NestedValue {
    param(
        [object]$InputObject,
        [string[]]$PathParts
    )
    $current = $InputObject
    foreach ($part in $PathParts) {
        if ($null -eq $current) { return $null }
        $prop = $current.PSObject.Properties[$part]
        if ($null -eq $prop) { return $null }
        $current = $prop.Value
    }
    return $current
}

function Get-StatusCodeFromError {
    param([System.Management.Automation.ErrorRecord]$ErrorRecord)
    if ($null -eq $ErrorRecord -or $null -eq $ErrorRecord.Exception -or $null -eq $ErrorRecord.Exception.Response) {
        return $null
    }
    try { return [int]$ErrorRecord.Exception.Response.StatusCode } catch { return $null }
}

function Get-BodyFromError {
    param([System.Management.Automation.ErrorRecord]$ErrorRecord)
    if ($null -eq $ErrorRecord) { return "" }
    if ($ErrorRecord.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($ErrorRecord.ErrorDetails.Message)) {
        return $ErrorRecord.ErrorDetails.Message
    }
    if ($null -eq $ErrorRecord.Exception -or $null -eq $ErrorRecord.Exception.Response) { return "" }
    try {
        $reader = New-Object System.IO.StreamReader($ErrorRecord.Exception.Response.GetResponseStream())
        $text = $reader.ReadToEnd()
        $reader.Close()
        return $text
    }
    catch { return "" }
}

function Resolve-SwaggerRef {
    param(
        [object]$SwaggerDoc,
        [string]$Ref
    )
    if ($null -eq $SwaggerDoc -or [string]::IsNullOrWhiteSpace($Ref) -or -not $Ref.StartsWith("#/")) {
        return $null
    }
    $segments = $Ref.Substring(2).Split("/")
    $node = $SwaggerDoc
    foreach ($segment in $segments) {
        if ($null -eq $node) { return $null }
        $prop = $node.PSObject.Properties[$segment]
        if ($null -eq $prop) { return $null }
        $node = $prop.Value
    }
    return $node
}

function Resolve-Schema {
    param(
        [object]$SwaggerDoc,
        [object]$Schema
    )
    if ($null -eq $Schema) { return $null }
    $refProp = $Schema.PSObject.Properties["`$ref"]
    if ($null -ne $refProp -and -not [string]::IsNullOrWhiteSpace([string]$refProp.Value)) {
        return Resolve-SwaggerRef -SwaggerDoc $SwaggerDoc -Ref ([string]$refProp.Value)
    }
    return $Schema
}

function Get-OperationRequestSchema {
    param(
        [object]$SwaggerDoc,
        [object]$Operation
    )
    if ($null -eq $Operation -or $null -eq $Operation.requestBody -or $null -eq $Operation.requestBody.content) {
        return $null
    }
    $content = $Operation.requestBody.content
    $media = $null
    $jsonProp = $content.PSObject.Properties["application/json"]
    if ($null -ne $jsonProp) { $media = $jsonProp.Value }
    elseif ($content.PSObject.Properties.Count -gt 0) { $media = $content.PSObject.Properties[0].Value }
    if ($null -eq $media -or $null -eq $media.schema) { return $null }
    return Resolve-Schema -SwaggerDoc $SwaggerDoc -Schema $media.schema
}

function New-ValueForSchema {
    param(
        [string]$PropertyName,
        [object]$SchemaNode
    )
    $propLower = $PropertyName.ToLowerInvariant()
    if ($propLower -eq "email") { return "qa.full.smoke@example.com" }
    if ($propLower -eq "password") { return "Qa@123456" }
    if ($propLower -eq "deviceid") { return "qa-full-smoke" }
    if ($propLower -eq "languagecode") { return "vi" }
    if ($propLower -eq "searchquery") { return "test" }
    if ($propLower -eq "isanonymous") { return $false }

    if ($null -ne $SchemaNode -and $null -ne $SchemaNode.PSObject.Properties["example"]) { return $SchemaNode.example }
    if ($null -ne $SchemaNode -and $null -ne $SchemaNode.PSObject.Properties["default"]) { return $SchemaNode.default }

    $type = $null
    if ($null -ne $SchemaNode -and $null -ne $SchemaNode.PSObject.Properties["type"]) {
        $type = [string]$SchemaNode.type
    }
    switch ($type) {
        "boolean" { return $false }
        "integer" { return 1 }
        "number" { return 1 }
        "array" { return @() }
        "object" { return @{} }
        default { return "qa-full-smoke" }
    }
}

function Build-BodyFromSchema {
    param(
        [object]$SwaggerDoc,
        [object]$SchemaNode
    )
    $resolved = Resolve-Schema -SwaggerDoc $SwaggerDoc -Schema $SchemaNode
    if ($null -eq $resolved -or $null -eq $resolved.properties) { return @{} }
    $required = @()
    if ($null -ne $resolved.required) { $required = @($resolved.required) }
    $body = [ordered]@{}
    foreach ($name in $required) {
        $propSchema = $resolved.properties.PSObject.Properties[$name].Value
        $resolvedProp = Resolve-Schema -SwaggerDoc $SwaggerDoc -Schema $propSchema
        $body[$name] = New-ValueForSchema -PropertyName $name -SchemaNode $resolvedProp
    }
    return $body
}

function Invoke-ApiRequest {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [object]$Body,
        [int]$TimeoutSec
    )
    $effectiveHeaders = @{"Accept" = "application/json" }
    if ($null -ne $Headers) {
        foreach ($k in $Headers.Keys) { $effectiveHeaders[$k] = $Headers[$k] }
    }
    $params = @{
        Method      = $Method
        Uri         = $Url
        Headers     = $effectiveHeaders
        ErrorAction = "Stop"
        TimeoutSec  = $TimeoutSec
    }
    if ($null -ne $Body) {
        $params["ContentType"] = "application/json; charset=utf-8"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }
    try {
        $response = Invoke-RestMethod @params
        $text = ""
        $json = $response
        if ($null -eq $response) {
            $text = ""
        }
        elseif ($response -is [string]) {
            $text = [string]$response
            try { $json = $text | ConvertFrom-Json -Depth 20 } catch { $json = $response }
        }
        else {
            try { $text = $response | ConvertTo-Json -Depth 20 -Compress } catch { $text = [string]$response }
        }
        return [pscustomobject]@{ Ok = $true; Status = 200; BodyJson = $json; BodyText = $text; ErrorText = $null }
    }
    catch {
        $status = Get-StatusCodeFromError -ErrorRecord $_
        $bodyText = Get-BodyFromError -ErrorRecord $_
        return [pscustomobject]@{ Ok = $false; Status = $status; BodyJson = $null; BodyText = $bodyText; ErrorText = $_.Exception.Message }
    }
}

function Get-SkipReason {
    param(
        [string]$Path,
        [string]$Tag
    )
    $text = ("{0} {1}" -f $Tag, $Path).ToLowerInvariant()
    if ($text.Contains("remove-multiple")) { return "remove-multiple is blocked" }
    if ($text.Contains("notification-seed-data") -and ($text.Contains("/all") -or $text.Contains("templates") -or $text.Contains("policies"))) {
        return "notification seed data template/policy endpoints are blocked"
    }
    if ($text.Contains("momo") -or $text.Contains("stripe") -or $text.Contains("webhook") -or $text.Contains("payment")) {
        return "payments/webhooks are blocked"
    }
    return $null
}

function Get-RequiredQueryMap {
    param([object]$Operation)
    $query = @{}
    if ($null -eq $Operation -or $null -eq $Operation.parameters) { return $query }
    foreach ($param in @($Operation.parameters)) {
        if ($null -eq $param -or [string]$param.in -ne "query" -or -not [bool]$param.required) { continue }
        $value = $null
        if ($null -ne $param.PSObject.Properties["example"]) {
            $value = $param.example
        }
        elseif ($null -ne $param.schema -and $null -ne $param.schema.PSObject.Properties["default"]) {
            $value = $param.schema.default
        }
        else {
            $nameLower = ([string]$param.name).ToLowerInvariant()
            if ($nameLower.Contains("page")) { $value = 1 }
            elseif ($nameLower.Contains("size")) { $value = 10 }
            elseif ($nameLower.Contains("keyword") -or $nameLower.Contains("search")) { $value = "test" }
            elseif ($null -ne $param.schema -and [string]$param.schema.type -eq "boolean") { $value = $false }
            elseif ($null -ne $param.schema -and ([string]$param.schema.type -eq "integer" -or [string]$param.schema.type -eq "number")) { $value = 1 }
            else { $value = "test" }
        }
        $query[[string]$param.name] = $value
    }
    return $query
}

function Get-SafeReadOnlyQueryDefault {
    param([string]$ParamName)
    switch ($ParamName) {
        "PageNumber" { return 1 }
        "PageSize" { return 1 }
        "pageNumber" { return 1 }
        "pageSize" { return 1 }
        "Keyword" { return "test" }
        "keyword" { return "test" }
        "LanguageCode" { return "vi" }
        default { return $null }
    }
}

function Resolve-ReadOnlyQueryPlan {
    param([object]$Operation)

    $result = [ordered]@{
        Ok                  = $true
        Query               = @{}
        MissingParamNames   = @()
        RequiresApiKeyQr    = $false
        RequiresApiKeyQrWhy = ""
    }

    if ($null -eq $Operation -or $null -eq $Operation.parameters) {
        return [pscustomobject]$result
    }

    foreach ($param in @($Operation.parameters)) {
        if ($null -eq $param -or [string]::IsNullOrWhiteSpace([string]$param.name)) { continue }

        $paramName = [string]$param.name
        $paramNameLower = $paramName.ToLowerInvariant()
        $paramIn = if ($null -eq $param.in) { "" } else { [string]$param.in }

        if ($paramNameLower -eq "x-api-key" -or $paramNameLower -eq "qrcode" -or $paramNameLower -eq "qrcode") {
            $result.RequiresApiKeyQr = $true
            $result.RequiresApiKeyQrWhy = "requires api key/qrCode"
        }

        if ($paramIn -ne "query") { continue }
        if (-not [bool]$param.required) { continue }

        $value = $null
        if ($null -ne $param.PSObject.Properties["example"]) {
            $value = $param.example
        }
        elseif ($null -ne $param.schema -and $null -ne $param.schema.PSObject.Properties["default"]) {
            $value = $param.schema.default
        }
        else {
            $value = Get-SafeReadOnlyQueryDefault -ParamName $paramName
        }

        if ($null -eq $value -or ([string]$value -eq "")) {
            $result.Ok = $false
            $result.MissingParamNames += $paramName
            continue
        }

        $result.Query[$paramName] = $value
    }

    return [pscustomobject]$result
}

function Build-QueryString {
    param([hashtable]$Query)
    if ($null -eq $Query -or $Query.Count -eq 0) { return "" }
    $pairs = New-Object System.Collections.Generic.List[string]
    foreach ($key in ($Query.Keys | Sort-Object)) {
        $pairs.Add(([System.Uri]::EscapeDataString([string]$key) + "=" + [System.Uri]::EscapeDataString([string]$Query[$key]))) | Out-Null
    }
    return ($pairs -join "&")
}

function Build-PathWithQuery {
    param(
        [string]$Path,
        [hashtable]$Query
    )
    if ([string]::IsNullOrWhiteSpace($Path) -or -not $Path.StartsWith("/")) {
        return $null
    }
    $queryString = Build-QueryString -Query $Query
    if ([string]::IsNullOrWhiteSpace($queryString)) { return $Path }
    return ("{0}?{1}" -f $Path, $queryString)
}

function Build-Url {
    param(
        [string]$BaseUrl,
        [string]$PathWithQuery
    )
    if ([string]::IsNullOrWhiteSpace($PathWithQuery)) { return $null }
    if ($PathWithQuery.StartsWith("http")) { return $PathWithQuery }
    if ($PathWithQuery.StartsWith("/")) { return "$BaseUrl$PathWithQuery" }
    return $null
}

function Is-AdminAuthzEndpoint {
    param([object]$Endpoint)
    $pathLower = if ($null -eq $Endpoint.Path) { "" } else { ([string]$Endpoint.Path).ToLowerInvariant() }
    $tagLower = if ($null -eq $Endpoint.Tag) { "" } else { ([string]$Endpoint.Tag).ToLowerInvariant() }
    if ($pathLower.Contains("/admin") -or $tagLower.Contains("-admin")) { return $true }
    if ($tagLower -eq "dashboard" -or $tagLower -eq "member" -or $tagLower -eq "admin") { return $true }
    if ($pathLower.Contains("/dashboard") -or $pathLower.Contains("/member")) { return $true }
    return $false
}

function Is-MissingRequiredParamsFailure {
    param([string]$BodyText)
    if ([string]::IsNullOrWhiteSpace($BodyText)) { return $false }
    $lower = $BodyText.ToLowerInvariant()
    return ($lower.Contains("field is required") -or $lower.Contains("missing required") -or $lower.Contains("required properties"))
}

function Is-AuthRequired {
    param(
        [object]$Operation,
        [object]$SwaggerDoc
    )
    if ($null -ne $Operation.PSObject.Properties["security"]) {
        if ($null -eq $Operation.security) { return $false }
        return @($Operation.security).Count -gt 0
    }
    if ($null -ne $SwaggerDoc.PSObject.Properties["security"] -and $null -ne $SwaggerDoc.security) {
        return @($SwaggerDoc.security).Count -gt 0
    }
    return $false
}

function Get-PathPlaceholders {
    param([string]$Path)
    $matches = [regex]::Matches($Path, "{([^}]+)}")
    $names = New-Object System.Collections.Generic.List[string]
    foreach ($m in $matches) { $names.Add($m.Groups[1].Value) | Out-Null }
    return $names.ToArray()
}

function Replace-PathPlaceholders {
    param(
        [string]$Path,
        [hashtable]$Values
    )
    $resolved = $Path
    foreach ($key in $Values.Keys) {
        $resolved = $resolved -replace "\{$([regex]::Escape($key))\}", [System.Uri]::EscapeDataString([string]$Values[$key])
    }
    return $resolved
}

function Get-EndpointInventory {
    param([object]$SwaggerDoc)
    $ops = New-Object System.Collections.Generic.List[object]
    foreach ($pathProp in $SwaggerDoc.paths.PSObject.Properties) {
        $path = [string]$pathProp.Name
        $pathNode = $pathProp.Value
        foreach ($method in @("get", "post", "put", "patch", "delete")) {
            $opProp = $pathNode.PSObject.Properties[$method]
            if ($null -eq $opProp) { continue }
            $operation = $opProp.Value
            $tag = "untagged"
            if ($null -ne $operation.tags -and @($operation.tags).Count -gt 0) {
                $tag = [string]$operation.tags[0]
            }
            $ops.Add([pscustomobject]@{
                Path         = $path
                Method       = $method.ToUpperInvariant()
                Tag          = $tag
                Operation    = $operation
                PathParams   = Get-PathPlaceholders -Path $path
                AuthRequired = Is-AuthRequired -Operation $operation -SwaggerDoc $SwaggerDoc
            }) | Out-Null
        }
    }
    return $ops.ToArray()
}

function Get-SwaggerPathCount {
    param([object]$SwaggerPaths)
    if ($null -eq $SwaggerPaths) { return 0 }
    if ($SwaggerPaths -is [System.Collections.IDictionary]) {
        return $SwaggerPaths.Keys.Count
    }
    if ($null -ne $SwaggerPaths.PSObject -and $null -ne $SwaggerPaths.PSObject.Properties) {
        return @($SwaggerPaths.PSObject.Properties).Count
    }
    return 0
}

function Try-ResolvePathParams {
    param(
        [object]$Endpoint,
        [hashtable]$SeedIds
    )
    $values = @{}
    foreach ($paramName in $Endpoint.PathParams) {
        $paramText = [string]$paramName
        if ([string]::IsNullOrWhiteSpace($paramText)) {
            return [pscustomobject]@{ Ok = $false; Values = @{}; Reason = "Missing seed id" }
        }
        if ($paramText.ToLowerInvariant().Contains("id")) {
            if ($SeedIds.ContainsKey($Endpoint.Tag) -and $null -ne $SeedIds[$Endpoint.Tag]) {
                $values[$paramText] = $SeedIds[$Endpoint.Tag]
            }
            else {
                return [pscustomobject]@{ Ok = $false; Values = @{}; Reason = "Missing seed id" }
            }
        }
        else {
            return [pscustomobject]@{ Ok = $false; Values = @{}; Reason = "Missing seed id" }
        }
    }
    return [pscustomobject]@{ Ok = $true; Values = $values; Reason = "" }
}

function Find-FirstIdValue {
    param([object]$InputObject)
    if ($null -eq $InputObject) { return $null }
    if ($InputObject -is [string]) { return $null }

    if ($InputObject -is [System.Collections.IDictionary]) {
        foreach ($key in $InputObject.Keys) {
            if ([string]$key -match "(?i)^id$|id$") {
                $value = $InputObject[$key]
                if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) { return $value }
            }
        }
        foreach ($key in $InputObject.Keys) {
            $candidate = Find-FirstIdValue -InputObject $InputObject[$key]
            if ($null -ne $candidate) { return $candidate }
        }
        return $null
    }

    if ($InputObject -is [System.Collections.IEnumerable]) {
        foreach ($item in $InputObject) {
            $candidate = Find-FirstIdValue -InputObject $item
            if ($null -ne $candidate) { return $candidate }
        }
        return $null
    }

    foreach ($prop in $InputObject.PSObject.Properties) {
        if ($prop.Name -match "(?i)^id$|id$") {
            if ($null -ne $prop.Value -and -not [string]::IsNullOrWhiteSpace([string]$prop.Value)) { return $prop.Value }
        }
    }
    foreach ($prop in $InputObject.PSObject.Properties) {
        $candidate = Find-FirstIdValue -InputObject $prop.Value
        if ($null -ne $candidate) { return $candidate }
    }
    return $null
}

function Get-ResourceKey {
    param([string]$Path)
    $segments = $Path.Trim("/").Split("/")
    $filtered = New-Object System.Collections.Generic.List[string]
    foreach ($seg in $segments) {
        if ([string]::IsNullOrWhiteSpace($seg)) { continue }
        if ($seg -ieq "api" -or $seg -ieq "v1") { continue }
        if ($seg.StartsWith("{")) { continue }
        $filtered.Add($seg.ToLowerInvariant()) | Out-Null
    }
    if ($filtered.Count -eq 0) { return "" }
    return $filtered[0]
}

function Get-RollbackOperation {
    param(
        [object]$CreateEndpoint,
        [object[]]$Inventory
    )
    $createKey = Get-ResourceKey -Path $CreateEndpoint.Path
    $candidates = $Inventory | Where-Object {
        $_.Tag -eq $CreateEndpoint.Tag -and
        @("DELETE", "POST", "PUT", "PATCH") -contains $_.Method -and
        $_.Path.ToLowerInvariant() -match "delete|remove"
    } | Sort-Object Path, Method

    foreach ($candidate in $candidates) {
        $skipReason = Get-SkipReason -Path $candidate.Path -Tag $candidate.Tag
        if (-not [string]::IsNullOrWhiteSpace($skipReason)) { continue }
        if ((Get-ResourceKey -Path $candidate.Path) -eq $createKey) {
            return $candidate
        }
    }
    return $null
}

function Get-IdPropertyName {
    param([object]$Schema)
    if ($null -eq $Schema -or $null -eq $Schema.properties) { return $null }
    foreach ($name in $Schema.properties.PSObject.Properties.Name) {
        if ([string]$name -match "(?i)^id$|id$") {
            return [string]$name
        }
    }
    return $null
}

$repoRoot = Get-RepoRoot
$artifactDir = Join-Path $repoRoot "artifacts\test-results\api"
New-Item -Path $artifactDir -ItemType Directory -Force | Out-Null
$logPath = Join-Path $artifactDir "api_full_smoke.log"
$summaryPath = Join-Path $artifactDir "api_full_smoke.summary.json"
$failedPath = Join-Path $artifactDir "api_full_smoke.failed.json"

$global:LogLines = New-Object System.Collections.Generic.List[string]
$results = New-Object System.Collections.Generic.List[object]
$script:checkSeq = 0
$scriptExitCode = 0
$startedAt = (Get-Date).ToString("o")
$mode = "READ_ONLY"
$baseUrl = ""
$apiPrefix = "/api/v1"

function Write-Log {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date).ToString("o"), $Message
    $null = $global:LogLines.Add($line)
    Write-Host $Message
}

function Flush-Logs {
    param([string]$PrimaryPath)
    $dir = Split-Path -Parent $PrimaryPath
    if (-not (Test-Path $dir)) { New-Item -Path $dir -ItemType Directory -Force | Out-Null }
    try {
        Set-Content -Path $PrimaryPath -Value $global:LogLines -Encoding UTF8
        return $PrimaryPath
    }
    catch {
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $fallback = Join-Path $dir "api_full_smoke.$stamp.log"
        Set-Content -Path $fallback -Value $global:LogLines -Encoding UTF8
        Write-Host "Primary log locked. Fallback log: $fallback"
        return $fallback
    }
}

function Next-CheckId {
    param([string]$Prefix)
    $script:checkSeq++
    return "{0}-{1:D3}" -f $Prefix, $script:checkSeq
}

function Add-Result {
    param(
        [string]$Id,
        [string]$Name,
        [string]$Method,
        [string]$Path,
        [bool]$Ok,
        [Nullable[int]]$Status,
        [string]$Notes,
        [string]$Tag
    )
    $result = [pscustomobject]@{
        id     = $Id
        name   = $Name
        method = $Method
        path   = $Path
        ok     = $Ok
        status = $Status
        mode   = $mode
        notes  = $Notes
        ts     = (Get-Date).ToString("o")
        tag    = $Tag
    }
    $results.Add($result) | Out-Null
    $statusText = if ($null -eq $Status) { "null" } else { [string]$Status }
    $tagText = if ([string]::IsNullOrWhiteSpace($Tag)) { "untagged" } else { $Tag }
    Write-Log ("{0} | {1} | {2} {3} | ok={4} | status={5} | notes={6}" -f $tagText, $Id, $Method, $Path, $Ok, $statusText, $Notes)
}

try {
    $baseUrl = (Get-RequiredEnv -Name "API_BASE_URL").TrimEnd("/")
    $apiUser = Get-RequiredEnv -Name "API_USER"
    $apiPass = Get-RequiredEnv -Name "API_PASS"
    $apiPrefix = Normalize-ApiPrefix -Prefix (Get-OptionalEnv -Name "API_PREFIX" -DefaultValue "/api/v1")
    $mode = (Get-OptionalEnv -Name "API_MODE" -DefaultValue "READ_ONLY").ToUpperInvariant()
    if ($mode -ne "READ_ONLY" -and $mode -ne "WRITE") {
        throw "Invalid API_MODE: $mode. Allowed: READ_ONLY or WRITE."
    }
    $timeoutSec = 30
    try { $timeoutSec = [int](Get-OptionalEnv -Name "API_TIMEOUT_SEC" -DefaultValue "30") } catch { $timeoutSec = 30 }
    if ($timeoutSec -le 0) { $timeoutSec = 30 }

    Write-Log "Full smoke start. base_url=$baseUrl api_prefix=$apiPrefix mode=$mode timeout_sec=$timeoutSec"

    # SYS-001: non-fatal base root check (do not block swagger-driven scan)
    $rootStatus = $null
    $rootError = $null
    $rootBody = ""
    try {
        $null = Invoke-RestMethod -Method Get -Uri "$baseUrl/" -TimeoutSec ([int]$timeoutSec) -ErrorAction Stop
        $rootStatus = 200
    }
    catch {
        $rootStatus = Get-StatusCodeFromError -ErrorRecord $_
        $rootError = $_.Exception.Message
        $rootBody = Get-BodyFromError -ErrorRecord $_
    }
    $rootOk = ($rootStatus -eq 200 -or $rootStatus -eq 404)
    $rootNote = if ($rootOk) {
        "Base root check status=$rootStatus. Non-fatal base root check; swagger is the primary signal."
    }
    else {
        "Base root check failed. status=$rootStatus; error=$rootError; body=$rootBody. Non-fatal base root check; swagger is the primary signal."
    }
    Add-Result -Id "SYS-001" -Name "Base root reachability" -Method "GET" -Path "/" -Ok $rootOk -Status $rootStatus -Notes $rootNote -Tag "system"

    $swaggerUrl = "$baseUrl/swagger/v1/swagger.json"
    $sw = Invoke-ApiRequest -Method "GET" -Url $swaggerUrl -Headers @{} -Body $null -TimeoutSec $timeoutSec
    $swOk = $sw.Ok -and $sw.Status -ge 200 -and $sw.Status -lt 300
    $swNote = if ($swOk) { "Swagger reachable." } else { "Swagger fetch failed. status=$($sw.Status); error=$($sw.ErrorText); body=$($sw.BodyText)" }
    Add-Result -Id "API-00" -Name "Fetch swagger" -Method "GET" -Path "/swagger/v1/swagger.json" -Ok $swOk -Status $sw.Status -Notes $swNote -Tag "system"
    if (-not $swOk -or $null -eq $sw.BodyJson) { throw "Cannot continue without swagger." }
    $swagger = $sw.BodyJson

    $loginPayload = [ordered]@{
        email    = $apiUser
        password = $apiPass
        deviceID = "qa-full-smoke"
    }
    $loginUrl = "$baseUrl$apiPrefix/auth/login"
    $login = Invoke-ApiRequest -Method "POST" -Url $loginUrl -Headers @{} -Body $loginPayload -TimeoutSec $timeoutSec
    $loginOk = $login.Ok -and $login.Status -ge 200 -and $login.Status -lt 300
    $loginNote = if ($loginOk) { "Login succeeded." } else { "Login failed. status=$($login.Status); error=$($login.ErrorText); body=$($login.BodyText)" }
    Add-Result -Id "API-01" -Name "Login" -Method "POST" -Path "$apiPrefix/auth/login" -Ok $loginOk -Status $login.Status -Notes $loginNote -Tag "auth"

    $tokenValue = Get-NestedValue -InputObject $login.BodyJson -PathParts @("login", "data", "token")
    if (($tokenValue -isnot [string]) -or [string]::IsNullOrWhiteSpace($tokenValue)) {
        $tokenValue = Get-NestedValue -InputObject $login.BodyJson -PathParts @("data", "token")
    }
    $token = $null
    if ($tokenValue -is [string] -and -not [string]::IsNullOrWhiteSpace($tokenValue)) {
        $token = $tokenValue.Trim()
    }
    $tokenOk = -not [string]::IsNullOrWhiteSpace($token)
    $tokenNote = if ($tokenOk) { "Token extracted and trimmed." } else { "Token missing at login.data.token." }
    Add-Result -Id "API-01A" -Name "Extract auth token" -Method "PARSE" -Path "login.data.token" -Ok $tokenOk -Status $login.Status -Notes $tokenNote -Tag "auth"

    $inventory = Get-EndpointInventory -SwaggerDoc $swagger
    $groupLines = $inventory | Group-Object Tag | Sort-Object Name | ForEach-Object { "$($_.Name):$($_.Count)" }
    Write-Log ("Endpoint inventory by tag: " + ($groupLines -join ", "))

    $scanExecuted = 0
    $scanSkipped = 0
    Write-Log ("SWAGGER_SCAN_START paths={0}" -f (Get-SwaggerPathCount -SwaggerPaths $swagger.paths))

    if ($mode -eq "READ_ONLY") {
        $seedIds = @{}
        $getNoParam = $inventory | Where-Object { $_.Method -eq "GET" -and $_.PathParams.Count -eq 0 } | Sort-Object Tag, Path
        $getWithParam = $inventory | Where-Object { $_.Method -eq "GET" -and $_.PathParams.Count -gt 0 } | Sort-Object Tag, Path

        foreach ($ep in $getNoParam) {
            $skipReason = Get-SkipReason -Path $ep.Path -Tag $ep.Tag
            $id = Next-CheckId -Prefix "RO"
            if (-not [string]::IsNullOrWhiteSpace($skipReason)) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $ep.Path -Ok $true -Status $null -Notes "SKIPPED: $skipReason" -Tag $ep.Tag
                continue
            }

            $queryPlan = Resolve-ReadOnlyQueryPlan -Operation $ep.Operation
            if ($queryPlan.RequiresApiKeyQr) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $ep.Path -Ok $true -Status $null -Notes "SKIPPED: $($queryPlan.RequiresApiKeyQrWhy)" -Tag $ep.Tag
                continue
            }
            if (-not $queryPlan.Ok) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $ep.Path -Ok $true -Status $null -Notes ("SKIPPED: Missing required params (" + ($queryPlan.MissingParamNames -join ", ") + ")") -Tag $ep.Tag
                continue
            }

            $fullPathForLog = Build-PathWithQuery -Path $ep.Path -Query $queryPlan.Query
            if ([string]::IsNullOrWhiteSpace($fullPathForLog) -or -not $fullPathForLog.StartsWith("/")) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $ep.Path -Ok $true -Status $null -Notes "SKIPPED: Invalid path format" -Tag $ep.Tag
                continue
            }

            $url = Build-Url -BaseUrl $baseUrl -PathWithQuery $fullPathForLog
            if ([string]::IsNullOrWhiteSpace($url)) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $fullPathForLog -Ok $true -Status $null -Notes "SKIPPED: Invalid URL build" -Tag $ep.Tag
                continue
            }
            $headers = @{}
            if ($ep.AuthRequired -and -not [string]::IsNullOrWhiteSpace($token)) {
                $headers["Authorization"] = "Bearer $token"
            }

            $resp = Invoke-ApiRequest -Method "GET" -Url $url -Headers $headers -Body $null -TimeoutSec $timeoutSec
            $scanExecuted++

            $ok = $resp.Ok -and $resp.Status -ge 200 -and $resp.Status -lt 300
            $note = if ($ok) { "OK" } else { "HTTP failure. status=$($resp.Status); error=$($resp.ErrorText); body=$($resp.BodyText)" }
            if ($resp.Status -ge 500) {
                $ok = $false
                $note = "HTTP failure (5xx). status=$($resp.Status); error=$($resp.ErrorText); body=$($resp.BodyText)"
            }
            elseif (($resp.Status -eq 401 -or $resp.Status -eq 403) -and (Is-AdminAuthzEndpoint -Endpoint $ep)) {
                $ok = $true
                $scanSkipped++
                $note = "SKIPPED: requires admin role (status=$($resp.Status))"
            }
            elseif ($resp.Status -eq 400 -and (Is-MissingRequiredParamsFailure -BodyText $resp.BodyText)) {
                $ok = $true
                $scanSkipped++
                $note = "SKIPPED: Missing required params"
            }
            elseif ($ep.AuthRequired -and [string]::IsNullOrWhiteSpace($token)) {
                $note = "$note Missing auth token."
            }
            Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $fullPathForLog -Ok $ok -Status $resp.Status -Notes $note -Tag $ep.Tag

            if ($ok -and -not $seedIds.ContainsKey($ep.Tag)) {
                $seed = Find-FirstIdValue -InputObject $resp.BodyJson
                if ($null -ne $seed) { $seedIds[$ep.Tag] = $seed }
            }
        }

        foreach ($ep in $getWithParam) {
            $skipReason = Get-SkipReason -Path $ep.Path -Tag $ep.Tag
            $id = Next-CheckId -Prefix "RO"
            if (-not [string]::IsNullOrWhiteSpace($skipReason)) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $ep.Path -Ok $true -Status $null -Notes "SKIPPED: $skipReason" -Tag $ep.Tag
                continue
            }

            $resolve = Try-ResolvePathParams -Endpoint $ep -SeedIds $seedIds
            if (-not $resolve.Ok) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $ep.Path -Ok $true -Status $null -Notes "SKIPPED: $($resolve.Reason)" -Tag $ep.Tag
                continue
            }

            $resolvedPath = Replace-PathPlaceholders -Path $ep.Path -Values $resolve.Values
            $queryPlan = Resolve-ReadOnlyQueryPlan -Operation $ep.Operation
            if ($queryPlan.RequiresApiKeyQr) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $resolvedPath -Ok $true -Status $null -Notes "SKIPPED: $($queryPlan.RequiresApiKeyQrWhy)" -Tag $ep.Tag
                continue
            }
            if (-not $queryPlan.Ok) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $resolvedPath -Ok $true -Status $null -Notes ("SKIPPED: Missing required params (" + ($queryPlan.MissingParamNames -join ", ") + ")") -Tag $ep.Tag
                continue
            }

            $fullPathForLog = Build-PathWithQuery -Path $resolvedPath -Query $queryPlan.Query
            if ([string]::IsNullOrWhiteSpace($fullPathForLog) -or -not $fullPathForLog.StartsWith("/")) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $resolvedPath -Ok $true -Status $null -Notes "SKIPPED: Invalid path format" -Tag $ep.Tag
                continue
            }

            $url = Build-Url -BaseUrl $baseUrl -PathWithQuery $fullPathForLog
            if ([string]::IsNullOrWhiteSpace($url)) {
                $scanSkipped++
                Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $fullPathForLog -Ok $true -Status $null -Notes "SKIPPED: Invalid URL build" -Tag $ep.Tag
                continue
            }
            $headers = @{}
            if ($ep.AuthRequired -and -not [string]::IsNullOrWhiteSpace($token)) {
                $headers["Authorization"] = "Bearer $token"
            }

            $resp = Invoke-ApiRequest -Method "GET" -Url $url -Headers $headers -Body $null -TimeoutSec $timeoutSec
            $scanExecuted++
            $ok = $resp.Ok -and $resp.Status -ge 200 -and $resp.Status -lt 300
            $note = if ($ok) { "OK" } else { "HTTP failure. status=$($resp.Status); error=$($resp.ErrorText); body=$($resp.BodyText)" }
            if ($resp.Status -ge 500) {
                $ok = $false
                $note = "HTTP failure (5xx). status=$($resp.Status); error=$($resp.ErrorText); body=$($resp.BodyText)"
            }
            elseif (($resp.Status -eq 401 -or $resp.Status -eq 403) -and (Is-AdminAuthzEndpoint -Endpoint $ep)) {
                $ok = $true
                $scanSkipped++
                $note = "SKIPPED: requires admin role (status=$($resp.Status))"
            }
            elseif ($resp.Status -eq 400 -and (Is-MissingRequiredParamsFailure -BodyText $resp.BodyText)) {
                $ok = $true
                $scanSkipped++
                $note = "SKIPPED: Missing required params"
            }
            elseif ($ep.AuthRequired -and [string]::IsNullOrWhiteSpace($token)) {
                $note = "$note Missing auth token."
            }
            Add-Result -Id $id -Name "READ_ONLY GET" -Method $ep.Method -Path $fullPathForLog -Ok $ok -Status $resp.Status -Notes $note -Tag $ep.Tag
        }
    }

    Write-Log ("SWAGGER_SCAN_DONE executed={0} skipped={1}" -f $scanExecuted, $scanSkipped)

    if ($mode -eq "WRITE") {
        $createOps = $inventory | Where-Object {
            @("POST", "PUT", "PATCH") -contains $_.Method -and
            $_.Path.ToLowerInvariant() -match "create|add|insert" -and
            $_.Path.ToLowerInvariant() -notmatch "/auth/login"
        } | Sort-Object Tag, Path

        foreach ($createEp in $createOps) {
            $pairId = Next-CheckId -Prefix "WR"
            $skipReason = Get-SkipReason -Path $createEp.Path -Tag $createEp.Tag
            if (-not [string]::IsNullOrWhiteSpace($skipReason)) {
                Add-Result -Id $pairId -Name "WRITE create+rollback" -Method $createEp.Method -Path $createEp.Path -Ok $true -Status $null -Notes "SKIPPED: $skipReason" -Tag $createEp.Tag
                continue
            }

            $rollbackEp = Get-RollbackOperation -CreateEndpoint $createEp -Inventory $inventory
            if ($null -eq $rollbackEp) {
                Add-Result -Id $pairId -Name "WRITE create+rollback" -Method $createEp.Method -Path $createEp.Path -Ok $true -Status $null -Notes "SKIPPED: rollback endpoint not found" -Tag $createEp.Tag
                continue
            }

            $createSchema = Get-OperationRequestSchema -SwaggerDoc $swagger -Operation $createEp.Operation
            if ($null -eq $createSchema) {
                Add-Result -Id $pairId -Name "WRITE create+rollback" -Method $createEp.Method -Path $createEp.Path -Ok $true -Status $null -Notes "SKIPPED: create schema missing" -Tag $createEp.Tag
                continue
            }

            $createBody = Build-BodyFromSchema -SwaggerDoc $swagger -SchemaNode $createSchema
            if ($createBody.Count -eq 0) {
                Add-Result -Id $pairId -Name "WRITE create+rollback" -Method $createEp.Method -Path $createEp.Path -Ok $true -Status $null -Notes "SKIPPED: create body cannot be built safely" -Tag $createEp.Tag
                continue
            }

            $createHeaders = @{}
            if ($createEp.AuthRequired -and -not [string]::IsNullOrWhiteSpace($token)) { $createHeaders["Authorization"] = "Bearer $token" }
            $createResp = Invoke-ApiRequest -Method $createEp.Method -Url (Build-Url -BaseUrl $baseUrl -PathWithQuery $createEp.Path) -Headers $createHeaders -Body $createBody -TimeoutSec $timeoutSec
            $createOk = $createResp.Ok -and $createResp.Status -ge 200 -and $createResp.Status -lt 300
            $createNote = if ($createOk) { "Create succeeded." } else { "Create failed. status=$($createResp.Status); error=$($createResp.ErrorText); body=$($createResp.BodyText)" }
            Add-Result -Id "$pairId-C" -Name "WRITE create" -Method $createEp.Method -Path $createEp.Path -Ok $createOk -Status $createResp.Status -Notes $createNote -Tag $createEp.Tag
            if (-not $createOk) { continue }

            $createdId = Find-FirstIdValue -InputObject $createResp.BodyJson
            $rollbackPath = $rollbackEp.Path
            if ($rollbackEp.PathParams.Count -gt 0) {
                if ($null -eq $createdId) {
                    Add-Result -Id "$pairId-R" -Name "WRITE rollback" -Method $rollbackEp.Method -Path $rollbackEp.Path -Ok $false -Status $null -Notes "Rollback failed: missing created id" -Tag $rollbackEp.Tag
                    continue
                }
                $values = @{}
                foreach ($placeholder in $rollbackEp.PathParams) { $values[$placeholder] = $createdId }
                $rollbackPath = Replace-PathPlaceholders -Path $rollbackPath -Values $values
            }

            $rollbackSchema = Get-OperationRequestSchema -SwaggerDoc $swagger -Operation $rollbackEp.Operation
            $rollbackBody = @{}
            if ($null -ne $rollbackSchema) {
                $rollbackBody = Build-BodyFromSchema -SwaggerDoc $swagger -SchemaNode $rollbackSchema
                $idProp = Get-IdPropertyName -Schema $rollbackSchema
                if (-not [string]::IsNullOrWhiteSpace($idProp) -and $null -ne $createdId) { $rollbackBody[$idProp] = $createdId }
                if ($rollbackBody.Contains("isAll")) { $rollbackBody["isAll"] = $false }
                if ($rollbackBody.Contains("deviceId")) { $rollbackBody["deviceId"] = "qa-full-smoke" }
                if ($rollbackBody.Contains("isAnonymous")) { $rollbackBody["isAnonymous"] = $false }
            }

            $rollbackHeaders = @{}
            if ($rollbackEp.AuthRequired -and -not [string]::IsNullOrWhiteSpace($token)) { $rollbackHeaders["Authorization"] = "Bearer $token" }
            $rbBody = if ($rollbackBody.Count -gt 0) { $rollbackBody } else { $null }
            $rollbackResp = Invoke-ApiRequest -Method $rollbackEp.Method -Url (Build-Url -BaseUrl $baseUrl -PathWithQuery $rollbackPath) -Headers $rollbackHeaders -Body $rbBody -TimeoutSec $timeoutSec
            $rollbackOk = $rollbackResp.Ok -and $rollbackResp.Status -ge 200 -and $rollbackResp.Status -lt 300
            $rollbackNote = if ($rollbackOk) { "Rollback succeeded." } else { "Rollback failed. status=$($rollbackResp.Status); error=$($rollbackResp.ErrorText); body=$($rollbackResp.BodyText)" }
            Add-Result -Id "$pairId-R" -Name "WRITE rollback" -Method $rollbackEp.Method -Path $rollbackPath -Ok $rollbackOk -Status $rollbackResp.Status -Notes $rollbackNote -Tag $rollbackEp.Tag
        }
    }
}
catch {
    $scriptExitCode = 1
    $status = Get-StatusCodeFromError -ErrorRecord $_
    $body = Get-BodyFromError -ErrorRecord $_
    $pos = if ($_.InvocationInfo -and -not [string]::IsNullOrWhiteSpace($_.InvocationInfo.PositionMessage)) { $_.InvocationInfo.PositionMessage } else { "<unknown>" }
    $stack = if (-not [string]::IsNullOrWhiteSpace($_.ScriptStackTrace)) { $_.ScriptStackTrace } else { "<none>" }
    Add-Result -Id "SYS-999" -Name "Fatal runner error" -Method "SYSTEM" -Path "/" -Ok $false -Status $status -Notes "Fatal error. status=$status; error=$($_.Exception.Message); body=$body; pos=$pos; stack=$stack" -Tag "system"
}
finally {
    $finishedAt = (Get-Date).ToString("o")
    $skipped = @($results | Where-Object { $_.notes -like "SKIPPED:*" }).Count
    $failed = @($results | Where-Object { (-not $_.ok) -and ($_.notes -notlike "SKIPPED:*") }).Count
    $passed = @($results | Where-Object { $_.ok -and ($_.notes -notlike "SKIPPED:*") }).Count
    $total = $results.Count

    $summary = [ordered]@{
        base_url    = $baseUrl
        api_prefix  = $apiPrefix
        mode        = $mode
        started_at  = $startedAt
        finished_at = $finishedAt
        total       = $total
        passed      = $passed
        failed      = $failed
        skipped     = $skipped
        results     = $results
    }
    $summary | ConvertTo-Json -Depth 30 | Set-Content -Path $summaryPath -Encoding UTF8

    if ($failed -gt 0) {
        ($results | Where-Object { (-not $_.ok) -and ($_.notes -notlike "SKIPPED:*") }) | ConvertTo-Json -Depth 30 | Set-Content -Path $failedPath -Encoding UTF8
        $scriptExitCode = 1
    }
    else {
        if (Test-Path $failedPath) { Remove-Item -Path $failedPath -Force }
        if ($scriptExitCode -ne 1) { $scriptExitCode = 0 }
    }

    Write-Log ("Summary: total={0}, passed={1}, failed={2}, skipped={3}" -f $total, $passed, $failed, $skipped)
    Write-Log "Summary file: $summaryPath"
    $actualLogPath = Flush-Logs -PrimaryPath $logPath
    if ($actualLogPath -ne $logPath) { Write-Host "Log file used: $actualLogPath" }
}

exit $scriptExitCode
