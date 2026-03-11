param()

$ErrorActionPreference = "Stop"

function Get-RequiredEnvValue {
    param([string]$Name)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ([string]::IsNullOrWhiteSpace($value)) {
        throw "Missing required environment variable: $Name"
    }
    return $value
}

function Get-RepoRoot {
    $scriptDir = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($scriptDir)) {
        $scriptDir = Split-Path -Parent $PSCommandPath
    }
    return (Resolve-Path (Join-Path $scriptDir "..")).Path
}

function Join-ApiUrl {
    param(
        [string]$BaseUrl,
        [string]$Path
    )
    $base = $BaseUrl.TrimEnd("/")
    if ([string]::IsNullOrWhiteSpace($Path)) {
        return $base
    }
    if ($Path.StartsWith("/")) {
        return "$base$Path"
    }
    return "$base/$Path"
}

function Get-NestedValue {
    param(
        [object]$InputObject,
        [string[]]$PathParts
    )

    $current = $InputObject
    foreach ($part in $PathParts) {
        if ($null -eq $current) {
            return $null
        }

        $prop = $current.PSObject.Properties[$part]
        if ($null -eq $prop) {
            return $null
        }

        $current = $prop.Value
    }
    return $current
}

function Extract-AuthTokens {
    param([object]$JsonBody)

    $accessToken = $null
    $refreshToken = $null
    if ($null -ne $JsonBody) {
        $accessValue = Get-NestedValue -InputObject $JsonBody -PathParts @("login", "data", "token")
        if (($accessValue -isnot [string]) -or [string]::IsNullOrWhiteSpace($accessValue)) {
            $accessValue = Get-NestedValue -InputObject $JsonBody -PathParts @("data", "token")
        }
        if ($accessValue -is [string] -and -not [string]::IsNullOrWhiteSpace($accessValue)) {
            $accessToken = ([string]$accessValue).Trim()
        }

        $refreshValue = Get-NestedValue -InputObject $JsonBody -PathParts @("login", "data", "refreshToken")
        if (($refreshValue -isnot [string]) -or [string]::IsNullOrWhiteSpace($refreshValue)) {
            $refreshValue = Get-NestedValue -InputObject $JsonBody -PathParts @("data", "refreshToken")
        }
        if ($refreshValue -is [string] -and -not [string]::IsNullOrWhiteSpace($refreshValue)) {
            $refreshToken = ([string]$refreshValue).Trim()
        }
    }

    return [pscustomobject]@{
        AccessToken  = $accessToken
        RefreshToken = $refreshToken
    }
}

function Invoke-ApiRequest {
    param(
        [string]$Method,
        [string]$Url,
        [hashtable]$Headers,
        [object]$Body,
        [switch]$ForceJsonContentType
    )

    $effectiveHeaders = @{}
    $effectiveHeaders["Accept"] = "application/json"

    if ($null -ne $Headers -and $Headers.Count -gt 0) {
        foreach ($key in $Headers.Keys) {
            $effectiveHeaders[$key] = $Headers[$key]
        }
    }

    $hasJsonBody = $null -ne $Body
    if ($hasJsonBody -or $ForceJsonContentType) {
        $effectiveHeaders["Content-Type"] = "application/json; charset=utf-8"
    }

    $invokeParams = @{
        Method      = $Method
        Uri         = $Url
        ErrorAction = "Stop"
        Headers     = $effectiveHeaders
        UseBasicParsing = $true
    }

    if ($hasJsonBody) {
        $invokeParams["Body"] = ($Body | ConvertTo-Json -Depth 20)
        $invokeParams["ContentType"] = "application/json; charset=utf-8"
    }

    try {
        $response = Invoke-RestMethod @invokeParams
        $status = 200
        $text = ""
        $json = $null

        if ($null -eq $response) {
            $text = ""
            $json = $null
        }
        elseif ($response -is [string]) {
            $text = [string]$response
            try {
                $json = $text | ConvertFrom-Json -Depth 20
            }
            catch {
                $json = $null
            }
        }
        else {
            $json = $response
            try {
                $text = $response | ConvertTo-Json -Depth 20 -Compress
            }
            catch {
                $text = [string]$response
            }
        }

        return [pscustomobject]@{
            Status    = $status
            BodyText  = $text
            BodyJson  = $json
            ErrorText = $null
        }
    }
    catch {
        $status = $null
        $text = $null
        $json = $null
        $errorText = $_.Exception.Message

        if ($_.Exception.Response) {
            $resp = $_.Exception.Response
            try {
                $status = [int]$resp.StatusCode
            }
            catch {
                $status = $null
            }

            try {
                $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
                $text = $reader.ReadToEnd()
                $reader.Close()
            }
            catch {
                $text = $null
            }
        }
        elseif ($_.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($_.ErrorDetails.Message)) {
            $text = $_.ErrorDetails.Message
        }

        if (-not [string]::IsNullOrWhiteSpace($text)) {
            try {
                $json = $text | ConvertFrom-Json -Depth 20
            }
            catch {
                $json = $null
            }
        }

        return [pscustomobject]@{
            Status    = $status
            BodyText  = $text
            BodyJson  = $json
            ErrorText = $errorText
        }
    }
}

function Resolve-SwaggerRef {
    param(
        [object]$SwaggerDoc,
        [string]$Ref
    )

    if ($null -eq $SwaggerDoc -or [string]::IsNullOrWhiteSpace($Ref)) {
        return $null
    }
    if (-not $Ref.StartsWith("#/")) {
        return $null
    }

    $segments = $Ref.Substring(2).Split("/")
    $node = $SwaggerDoc
    foreach ($segment in $segments) {
        if ($null -eq $node) {
            return $null
        }
        $prop = $node.PSObject.Properties[$segment]
        if ($null -eq $prop) {
            return $null
        }
        $node = $prop.Value
    }
    return $node
}

function Resolve-SwaggerSchema {
    param(
        [object]$SwaggerDoc,
        [object]$Schema
    )

    if ($null -eq $Schema) {
        return $null
    }

    $refProp = $Schema.PSObject.Properties["`$ref"]
    if ($null -ne $refProp -and -not [string]::IsNullOrWhiteSpace([string]$refProp.Value)) {
        return Resolve-SwaggerRef -SwaggerDoc $SwaggerDoc -Ref ([string]$refProp.Value)
    }

    return $Schema
}

function Get-SwaggerOperation {
    param(
        [object]$SwaggerDoc,
        [string]$ApiPath,
        [string]$Method
    )

    if ($null -eq $SwaggerDoc -or $null -eq $SwaggerDoc.paths) {
        return $null
    }

    $pathProp = $SwaggerDoc.paths.PSObject.Properties[$ApiPath]
    if ($null -eq $pathProp) {
        return $null
    }

    $methodKey = $Method.ToLowerInvariant()
    $opProp = $pathProp.Value.PSObject.Properties[$methodKey]
    if ($null -eq $opProp) {
        return $null
    }

    return $opProp.Value
}

function Get-SwaggerRequestBodyInfo {
    param(
        [object]$SwaggerDoc,
        [string]$ApiPath,
        [string]$Method
    )

    $unknown = [pscustomobject]@{
        RequiredFields = @()
        Properties     = @()
        ExamplePayload = @{}
        ExampleText    = "{}"
        BodyRequired   = $false
        IsKnown        = $false
        ResolvedSchema = $null
        PropertySchemas = @{}
    }

    $operation = Get-SwaggerOperation -SwaggerDoc $SwaggerDoc -ApiPath $ApiPath -Method $Method
    if ($null -eq $operation) {
        return $unknown
    }

    $requestBody = $operation.requestBody
    if ($null -eq $requestBody) {
        return $unknown
    }

    $requiredFlag = $false
    if ($null -ne $requestBody.PSObject.Properties["required"]) {
        $requiredFlag = [bool]$requestBody.required
    }

    $content = $requestBody.content
    if ($null -eq $content) {
        return [pscustomobject]@{
            RequiredFields = @()
            Properties     = @()
            ExamplePayload = @{}
            ExampleText    = "{}"
            BodyRequired   = $requiredFlag
            IsKnown        = $true
            ResolvedSchema = $null
            PropertySchemas = @{}
        }
    }

    $media = $null
    $jsonContentProp = $content.PSObject.Properties["application/json"]
    if ($null -ne $jsonContentProp) {
        $media = $jsonContentProp.Value
    }
    elseif ($content.PSObject.Properties.Count -gt 0) {
        $media = $content.PSObject.Properties[0].Value
    }

    if ($null -eq $media) {
        return [pscustomobject]@{
            RequiredFields = @()
            Properties     = @()
            ExamplePayload = @{}
            ExampleText    = "{}"
            BodyRequired   = $requiredFlag
            IsKnown        = $true
            ResolvedSchema = $null
            PropertySchemas = @{}
        }
    }

    $requiredFields = @()
    $properties = @()
    $propertySchemas = @{}
    $schema = $media.schema
    $resolvedSchema = Resolve-SwaggerSchema -SwaggerDoc $SwaggerDoc -Schema $schema
    if ($null -ne $resolvedSchema -and $null -ne $resolvedSchema.required) {
        $requiredFields = @($resolvedSchema.required)
    }
    if ($null -ne $resolvedSchema -and $null -ne $resolvedSchema.properties) {
        $properties = @($resolvedSchema.properties.PSObject.Properties.Name)
        foreach ($propName in $properties) {
            $propSchema = $resolvedSchema.properties.PSObject.Properties[$propName].Value
            $propertySchemas[$propName] = Resolve-SwaggerSchema -SwaggerDoc $SwaggerDoc -Schema $propSchema
        }
    }

    $examplePayload = $null
    if ($null -ne $media.PSObject.Properties["example"]) {
        $examplePayload = $media.example
    }
    elseif ($null -ne $media.PSObject.Properties["examples"] -and $media.examples.PSObject.Properties.Count -gt 0) {
        $exampleNode = $media.examples.PSObject.Properties[0].Value
        if ($null -ne $exampleNode -and $null -ne $exampleNode.PSObject.Properties["value"]) {
            $examplePayload = $exampleNode.value
        }
    }
    elseif ($null -ne $resolvedSchema -and $null -ne $resolvedSchema.PSObject.Properties["example"]) {
        $examplePayload = $resolvedSchema.example
    }

    if ($null -eq $examplePayload) {
        $generatedExample = @{}
        foreach ($propName in $properties) {
            $propSchema = $propertySchemas[$propName]
            if ($null -eq $propSchema) {
                continue
            }

            if ($null -ne $propSchema.PSObject.Properties["example"]) {
                $generatedExample[$propName] = $propSchema.example
                continue
            }

            if ($null -ne $propSchema.PSObject.Properties["default"]) {
                $generatedExample[$propName] = $propSchema.default
            }
        }
        $examplePayload = $generatedExample
    }

    if ($null -eq $examplePayload) {
        $examplePayload = @{}
    }

    $exampleText = "{}"
    try {
        $exampleText = ($examplePayload | ConvertTo-Json -Depth 20 -Compress)
    }
    catch {
        $exampleText = "{}"
    }

    return [pscustomobject]@{
        RequiredFields = $requiredFields
        ExamplePayload = $examplePayload
        ExampleText    = $exampleText
        Properties     = $properties
        BodyRequired   = $requiredFlag
        IsKnown        = $true
        ResolvedSchema = $resolvedSchema
        PropertySchemas = $propertySchemas
    }
}

function Get-PropertyByPreferredNames {
    param(
        [string[]]$AvailableNames,
        [string[]]$PreferredNames
    )

    foreach ($preferred in $PreferredNames) {
        foreach ($available in $AvailableNames) {
            if ($available -ieq $preferred) {
                return $available
            }
        }
    }

    return $null
}

function Get-FirstStringPropertyName {
    param(
        [string[]]$AvailableNames,
        [hashtable]$PropertySchemas,
        [string]$ExcludeName
    )

    foreach ($name in $AvailableNames) {
        if (-not [string]::IsNullOrWhiteSpace($ExcludeName) -and $name -ieq $ExcludeName) {
            continue
        }

        $schema = $PropertySchemas[$name]
        if ($null -eq $schema -or $null -eq $schema.PSObject.Properties["type"] -or [string]::IsNullOrWhiteSpace([string]$schema.type)) {
            return $name
        }
        if ([string]$schema.type -ieq "string") {
            return $name
        }
    }

    return $null
}

function Build-LoginBodyFromSwagger {
    param(
        [object]$SwaggerDoc,
        [string]$ApiUser,
        [string]$ApiPass
    )

    $bodyInfo = Get-SwaggerRequestBodyInfo -SwaggerDoc $SwaggerDoc -ApiPath "/api/v1/auth/login" -Method "post"
    $propertyNames = @($bodyInfo.Properties)

    $passwordField = $null
    foreach ($name in $propertyNames) {
        if ($name -match "(?i)pass") {
            $passwordField = $name
            break
        }
    }

    $preferredUserNames = @("email", "userName", "username", "phone", "account", "login")
    $userField = Get-PropertyByPreferredNames -AvailableNames $propertyNames -PreferredNames $preferredUserNames
    $userMappingUnknown = $false
    if ([string]::IsNullOrWhiteSpace($userField)) {
        $userField = Get-FirstStringPropertyName -AvailableNames $propertyNames -PropertySchemas $bodyInfo.PropertySchemas -ExcludeName $passwordField
        if (-not [string]::IsNullOrWhiteSpace($userField)) {
            $userMappingUnknown = $true
        }
    }

    $bodyTable = @{}
    if ($bodyInfo.ExamplePayload -is [hashtable]) {
        foreach ($k in $bodyInfo.ExamplePayload.Keys) {
            $bodyTable[$k] = $bodyInfo.ExamplePayload[$k]
        }
    }
    elseif ($bodyInfo.ExamplePayload -is [pscustomobject]) {
        foreach ($p in $bodyInfo.ExamplePayload.PSObject.Properties) {
            $bodyTable[$p.Name] = $p.Value
        }
    }

    if (-not [string]::IsNullOrWhiteSpace($userField)) {
        $bodyTable[$userField] = $ApiUser
    }
    if (-not [string]::IsNullOrWhiteSpace($passwordField)) {
        $bodyTable[$passwordField] = $ApiPass
    }

    return [pscustomobject]@{
        Body               = $bodyTable
        BodyInfo           = $bodyInfo
        UserField          = $userField
        PasswordField      = $passwordField
        UserMappingUnknown = $userMappingUnknown
    }
}

function Get-SwaggerDocument {
    param([string]$BaseUrl)

    $url = "$BaseUrl/swagger/v1/swagger.json"
    $response = Invoke-ApiRequest -Method "GET" -Url $url -Headers @{} -Body $null
    return [pscustomobject]@{
        Url      = $url
        Response = $response
        Document = $response.BodyJson
    }
}

$repoRoot = Get-RepoRoot
$artifactDir = Join-Path $repoRoot "artifacts\test-results\api"
New-Item -Path $artifactDir -ItemType Directory -Force | Out-Null

$logPath = Join-Path $artifactDir "api_smoke.log"
$summaryPath = Join-Path $artifactDir "api_smoke.summary.json"
$global:LogLines = New-Object System.Collections.Generic.List[string]

function Write-Log {
    param([string]$Message)
    $line = "{0} {1}" -f (Get-Date).ToString("o"), $Message
    $null = $global:LogLines.Add($line)
    Write-Host $Message
}

function Flush-LogBuffer {
    param(
        [string]$PrimaryPath
    )

    $targetDir = Split-Path -Parent $PrimaryPath
    if (-not (Test-Path $targetDir)) {
        New-Item -Path $targetDir -ItemType Directory -Force | Out-Null
    }

    try {
        Set-Content -Path $PrimaryPath -Value $global:LogLines -Encoding UTF8
        return $PrimaryPath
    }
    catch {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $fallbackPath = Join-Path $targetDir "api_smoke.$timestamp.log"
        Set-Content -Path $fallbackPath -Value $global:LogLines -Encoding UTF8
        Write-Host "Primary log file is locked. Wrote fallback log: $fallbackPath"
        return $fallbackPath
    }
}

function Build-FailureNote {
    param(
        [string]$Prefix,
        [object]$Response
    )

    $statusText = if ($null -eq $Response.Status) { "UNKNOWN" } else { [string]$Response.Status }
    $errorText = if ([string]::IsNullOrWhiteSpace($Response.ErrorText)) { "<none>" } else { $Response.ErrorText }
    $bodyText = if ([string]::IsNullOrWhiteSpace($Response.BodyText)) { "<empty>" } else { $Response.BodyText }
    return "$Prefix status=$statusText; error=$errorText; body=$bodyText"
}

function Get-ExceptionStatusCode {
    param([System.Management.Automation.ErrorRecord]$ExceptionRecord)

    if ($null -eq $ExceptionRecord -or $null -eq $ExceptionRecord.Exception -or $null -eq $ExceptionRecord.Exception.Response) {
        return $null
    }

    try {
        return [int]$ExceptionRecord.Exception.Response.StatusCode
    }
    catch {
        return $null
    }
}

function Get-ExceptionBodyText {
    param([System.Management.Automation.ErrorRecord]$ExceptionRecord)

    if ($null -eq $ExceptionRecord) {
        return "<empty>"
    }

    if ($ExceptionRecord.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($ExceptionRecord.ErrorDetails.Message)) {
        return $ExceptionRecord.ErrorDetails.Message
    }

    if ($null -eq $ExceptionRecord.Exception -or $null -eq $ExceptionRecord.Exception.Response) {
        return "<empty>"
    }

    try {
        $reader = New-Object System.IO.StreamReader($ExceptionRecord.Exception.Response.GetResponseStream())
        $text = $reader.ReadToEnd()
        $reader.Close()
        if ([string]::IsNullOrWhiteSpace($text)) {
            return "<empty>"
        }
        return $text
    }
    catch {
        return "<empty>"
    }
}

function Build-StepExceptionNote {
    param(
        [string]$Prefix,
        [System.Management.Automation.ErrorRecord]$ExceptionRecord
    )

    $status = Get-ExceptionStatusCode -ExceptionRecord $ExceptionRecord
    $statusText = if ($null -eq $status) { "UNKNOWN" } else { [string]$status }
    $errorText = if ($null -eq $ExceptionRecord) { "<none>" } else { $ExceptionRecord.Exception.Message }
    $bodyText = Get-ExceptionBodyText -ExceptionRecord $ExceptionRecord
    return "$Prefix status=$statusText; error=$errorText; body=$bodyText"
}

$results = New-Object System.Collections.Generic.List[object]
$scriptExitCode = 0
$skipMain = $false

function Add-Result {
    param(
        [string]$Id,
        [string]$Name,
        [bool]$Ok,
        [Nullable[int]]$Status,
        [string]$Notes
    )

    $result = [pscustomobject]@{
        id    = $Id
        name  = $Name
        ok    = $Ok
        status = $Status
        notes = $Notes
        ts    = (Get-Date).ToString("o")
    }

    $results.Add($result) | Out-Null
    $statusText = if ($null -eq $Status) { "null" } else { [string]$Status }
    Write-Log ("{0} | {1} | ok={2} | status={3} | {4}" -f $Id, $Name, $Ok, $statusText, $Notes)
}

try {
    try {
        $apiBaseUrl = Get-RequiredEnvValue -Name "API_BASE_URL"
        $apiUser = Get-RequiredEnvValue -Name "API_USER"
        $apiPass = Get-RequiredEnvValue -Name "API_PASS"
    }
    catch {
        $message = $_.Exception.Message
        Add-Result -Id "API-ENV" -Name "Environment validation" -Ok $false -Status $null -Notes $message

        $summary = [ordered]@{
            generated_at  = (Get-Date).ToString("o")
            api_base_url  = [Environment]::GetEnvironmentVariable("API_BASE_URL")
            total         = $results.Count
            passed        = 0
            failed        = $results.Count
            results       = $results
        }
        $summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding UTF8
        Write-Log "Summary: FAILED (environment validation)"
        $scriptExitCode = 1
        $skipMain = $true
    }

    if (-not $skipMain) {
        $token = $null
        $refreshToken = $null
        $loginResponse = $null

        $Base = $env:API_BASE_URL.TrimEnd('/')
        $ApiPrefix = "$Base/api/v1"

        Write-Log "API smoke start. Base URL: $Base"
        Write-Log "API prefix: $ApiPrefix"

# API-00: GET /swagger/v1/swagger.json
try {
    $swaggerFetch = Get-SwaggerDocument -BaseUrl $Base
    $api00 = $swaggerFetch.Response
    $swaggerDoc = $swaggerFetch.Document
    $api00Ok = $null -ne $api00.Status -and $api00.Status -eq 200
    $api00Note = if ($api00Ok) {
        "Swagger reachable."
    }
    else {
        Build-FailureNote -Prefix "Swagger check failed. Check API_BASE_URL host/port." -Response $api00
    }
    Add-Result -Id "API-00" -Name "GET /swagger/v1/swagger.json (base reachability)" -Ok $api00Ok -Status $api00.Status -Notes $api00Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-00 failed." -ExceptionRecord $_
    Add-Result -Id "API-00" -Name "GET /swagger/v1/swagger.json (base reachability)" -Ok $false -Status $status -Notes $notes
    $swaggerDoc = $null
}

# API-01: POST /auth/login
try {
    $loginBody = [ordered]@{
        email    = $apiUser
        password = $apiPass
        deviceID = "qa-smoke"
    }
    $api01 = Invoke-ApiRequest -Method "POST" -Url "$ApiPrefix/auth/login" -Headers @{} -Body $loginBody
    $api01Ok = $null -ne $api01.Status -and $api01.Status -ge 200 -and $api01.Status -lt 300
    $api01Note = if ($api01Ok) { "Login request succeeded." } else { Build-FailureNote -Prefix "Login failed." -Response $api01 }
    Add-Result -Id "API-01" -Name "POST /auth/login (valid credentials)" -Ok $api01Ok -Status $api01.Status -Notes $api01Note
    $loginResponse = $api01

    if (-not $api01Ok) {
        $responseBodyLog = if ([string]::IsNullOrWhiteSpace($api01.BodyText)) { "<empty>" } else { $api01.BodyText }
        Write-Log "API-01 response body: $responseBodyLog"
    }
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-01 failed." -ExceptionRecord $_
    Add-Result -Id "API-01" -Name "POST /auth/login (valid credentials)" -Ok $false -Status $status -Notes $notes
    $loginResponse = [pscustomobject]@{
        Status    = $status
        BodyText  = ""
        BodyJson  = $null
        ErrorText = $_.Exception.Message
    }
}

# API-01A: extract token
try {
    $authTokens = Extract-AuthTokens -JsonBody $loginResponse.BodyJson
    $token = if ([string]::IsNullOrWhiteSpace($authTokens.AccessToken)) { $null } else { $authTokens.AccessToken.Trim() }
    $refreshToken = if ([string]::IsNullOrWhiteSpace($authTokens.RefreshToken)) { $null } else { $authTokens.RefreshToken.Trim() }
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $tokenNote = "Access token extracted from login.data.token and trimmed."
        if (-not [string]::IsNullOrWhiteSpace($refreshToken)) {
            $tokenNote = "$tokenNote Refresh token extracted from login.data.refreshToken."
        }
        else {
            $tokenNote = "$tokenNote Refresh token missing at login.data.refreshToken."
        }
        Add-Result -Id "API-01A" -Name "Extract access token from login response" -Ok $true -Status $loginResponse.Status -Notes $tokenNote
    }
    else {
        Add-Result -Id "API-01A" -Name "Extract access token from login response" -Ok $false -Status $loginResponse.Status -Notes "Failed to parse access token at login.data.token."
    }
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-01A failed." -ExceptionRecord $_
    Add-Result -Id "API-01A" -Name "Extract access token from login response" -Ok $false -Status $status -Notes $notes
}

# API-02: GET /account/get-info
try {
    $api02Headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $api02Headers["Authorization"] = "Bearer $token"
    }
    $api02 = Invoke-ApiRequest -Method "GET" -Url "$ApiPrefix/account/get-info" -Headers $api02Headers -Body $null
    $api02Ok = $null -ne $api02.Status -and $api02.Status -ge 200 -and $api02.Status -lt 300 -and -not [string]::IsNullOrWhiteSpace($token)
    $api02Note = if ([string]::IsNullOrWhiteSpace($token)) {
        "Token missing from API-01A."
    }
    elseif ($api02Ok) {
        "Account info request succeeded."
    }
    else {
        Build-FailureNote -Prefix "Account info request failed." -Response $api02
    }
    Add-Result -Id "API-02" -Name "GET /account/get-info (authorized)" -Ok $api02Ok -Status $api02.Status -Notes $api02Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-02 failed." -ExceptionRecord $_
    Add-Result -Id "API-02" -Name "GET /account/get-info (authorized)" -Ok $false -Status $status -Notes $notes
}

# API-03: negative login with wrong password
try {
    $negativeLoginBody = @{
        email    = $apiUser
        password = "$apiPass-wrong"
        deviceID = "qa-smoke"
    }
    $api03 = Invoke-ApiRequest -Method "POST" -Url "$ApiPrefix/auth/login" -Headers @{} -Body $negativeLoginBody
    $api03Ok = $false
    $api03Note = "Negative login returned unexpected status."
    if ($null -eq $api03.Status) {
        $api03Ok = $false
        $api03Note = Build-FailureNote -Prefix "Negative login request failed." -Response $api03
    }
    elseif ($api03.Status -eq 404) {
        $api03Ok = $false
        $api03Note = Build-FailureNote -Prefix "route mismatch." -Response $api03
    }
    elseif ($api03.Status -in @(400, 401, 403)) {
        $api03Ok = $true
        $api03Note = "Negative login rejected as expected."
    }
    elseif ($api03.Status -ne 200) {
        $api03Ok = $true
        $api03Note = "Negative login returned non-200 (accepted): $($api03.Status)"
    }
    Add-Result -Id "API-03" -Name "POST /auth/login (wrong password)" -Ok $api03Ok -Status $api03.Status -Notes $api03Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-03 failed." -ExceptionRecord $_
    Add-Result -Id "API-03" -Name "POST /auth/login (wrong password)" -Ok $false -Status $status -Notes $notes
}

# API-04: GET /searches/posts?keyword=test
try {
    $api04Headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $api04Headers["Authorization"] = "Bearer $token"
    }
    $api04 = Invoke-ApiRequest -Method "GET" -Url "$ApiPrefix/searches/posts?keyword=test" -Headers $api04Headers -Body $null
    $api04Ok = $null -ne $api04.Status -and $api04.Status -ge 200 -and $api04.Status -lt 300
    $api04Note = if ($api04Ok) { "Search posts succeeded." } else { Build-FailureNote -Prefix "Search posts failed." -Response $api04 }
    if ([string]::IsNullOrWhiteSpace($token)) {
        $api04Note = "$api04Note Token missing; request sent without Authorization."
    }
    Add-Result -Id "API-04" -Name "GET /searches/posts?keyword=test" -Ok $api04Ok -Status $api04.Status -Notes $api04Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-04 failed." -ExceptionRecord $_
    Add-Result -Id "API-04" -Name "GET /searches/posts?keyword=test" -Ok $false -Status $status -Notes $notes
}

# API-05: GET /searches/suggestions/test
try {
    $keyword = "test"
    $api05 = Invoke-ApiRequest -Method "GET" -Url "$ApiPrefix/searches/suggestions/$keyword" -Headers @{} -Body $null
    $api05Ok = $null -ne $api05.Status -and $api05.Status -ge 200 -and $api05.Status -lt 300
    $api05Note = if ($api05Ok) { "Suggestions request succeeded." } else { Build-FailureNote -Prefix "Suggestions request failed." -Response $api05 }
    Add-Result -Id "API-05" -Name "GET /searches/suggestions/test" -Ok $api05Ok -Status $api05.Status -Notes $api05Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-05 failed." -ExceptionRecord $_
    Add-Result -Id "API-05" -Name "GET /searches/suggestions/test" -Ok $false -Status $status -Notes $notes
}

# API-06: POST /searches/histories
try {
    $api06Headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $api06Headers["Authorization"] = "Bearer $token"
    }
    $api06Body = [ordered]@{
        searchQuery       = "test"
        deviceId          = "qa-smoke"
        isAnonymous       = $false
        languageCode      = "vi"
    }
    $api06 = Invoke-ApiRequest -Method "POST" -Url "$ApiPrefix/searches/histories" -Headers $api06Headers -Body $api06Body
    $api06Ok = $null -ne $api06.Status -and $api06.Status -ge 200 -and $api06.Status -lt 300
    $api06BodyJson = $api06Body | ConvertTo-Json -Depth 20 -Compress
    $api06Curl = if (-not [string]::IsNullOrWhiteSpace($token)) {
        "curl -X POST `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -H `"Authorization: Bearer <token>`" -d '$api06BodyJson'"
    }
    else {
        "curl -X POST `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -d '$api06BodyJson'"
    }
    $api06Note = if ($api06Ok) { "Create search history succeeded." } else { Build-FailureNote -Prefix "Create search history failed." -Response $api06 }
    if ([string]::IsNullOrWhiteSpace($token)) {
        $api06Note = "$api06Note Token missing; request sent without Authorization."
    }
    $api06Note = "$api06Note curl=$api06Curl"
    Add-Result -Id "API-06" -Name "POST /searches/histories {searchQuery:test}" -Ok $api06Ok -Status $api06.Status -Notes $api06Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $api06Body = [ordered]@{
        searchQuery       = "test"
        deviceId          = "qa-smoke"
        isAnonymous       = $false
        languageCode      = "vi"
    }
    $api06BodyJson = $api06Body | ConvertTo-Json -Depth 20 -Compress
    $api06Curl = if (-not [string]::IsNullOrWhiteSpace($token)) {
        "curl -X POST `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -H `"Authorization: Bearer <token>`" -d '$api06BodyJson'"
    }
    else {
        "curl -X POST `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -d '$api06BodyJson'"
    }
    $notes = "$(Build-StepExceptionNote -Prefix "API-06 failed." -ExceptionRecord $_) curl=$api06Curl"
    Add-Result -Id "API-06" -Name "POST /searches/histories {searchQuery:test}" -Ok $false -Status $status -Notes $notes
}

# API-07: GET /searches/histories
try {
    $api07Headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $api07Headers["Authorization"] = "Bearer $token"
    }
    $api07 = Invoke-ApiRequest -Method "GET" -Url "$ApiPrefix/searches/histories" -Headers $api07Headers -Body $null
    $api07Ok = $null -ne $api07.Status -and $api07.Status -ge 200 -and $api07.Status -lt 300
    $api07Note = if ($api07Ok) { "Get search histories succeeded." } else { Build-FailureNote -Prefix "Get search histories failed." -Response $api07 }
    if ([string]::IsNullOrWhiteSpace($token)) {
        $api07Note = "$api07Note Token missing; request sent without Authorization."
    }
    Add-Result -Id "API-07" -Name "GET /searches/histories" -Ok $api07Ok -Status $api07.Status -Notes $api07Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $notes = Build-StepExceptionNote -Prefix "API-07 failed." -ExceptionRecord $_
    Add-Result -Id "API-07" -Name "GET /searches/histories" -Ok $false -Status $status -Notes $notes
}

# API-08: DELETE /searches/histories
try {
    $api08Headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($token)) {
        $api08Headers["Authorization"] = "Bearer $token"
    }
    $api08Body = [ordered]@{
        isAll       = $true
        deviceId    = "qa-smoke"
        isAnonymous = $false
    }
    $api08 = Invoke-ApiRequest -Method "DELETE" -Url "$ApiPrefix/searches/histories" -Headers $api08Headers -Body $api08Body -ForceJsonContentType
    $api08Ok = $null -ne $api08.Status -and $api08.Status -ge 200 -and $api08.Status -lt 300
    $api08BodyJson = $api08Body | ConvertTo-Json -Depth 20 -Compress
    $api08Curl = if (-not [string]::IsNullOrWhiteSpace($token)) {
        "curl -X DELETE `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -H `"Authorization: Bearer <token>`" -d '$api08BodyJson'"
    }
    else {
        "curl -X DELETE `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -d '$api08BodyJson'"
    }
    $api08Note = if ($api08Ok) { "Delete search histories succeeded." } else { Build-FailureNote -Prefix "Delete search histories failed." -Response $api08 }
    if ([string]::IsNullOrWhiteSpace($token)) {
        $api08Note = "$api08Note Token missing; request sent without Authorization."
    }
    $api08Note = "$api08Note curl=$api08Curl"
    Add-Result -Id "API-08" -Name "DELETE /searches/histories" -Ok $api08Ok -Status $api08.Status -Notes $api08Note
}
catch {
    $status = Get-ExceptionStatusCode -ExceptionRecord $_
    $api08Body = [ordered]@{
        isAll       = $true
        deviceId    = "qa-smoke"
        isAnonymous = $false
    }
    $api08BodyJson = $api08Body | ConvertTo-Json -Depth 20 -Compress
    $api08Curl = if (-not [string]::IsNullOrWhiteSpace($token)) {
        "curl -X DELETE `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -H `"Authorization: Bearer <token>`" -d '$api08BodyJson'"
    }
    else {
        "curl -X DELETE `"$ApiPrefix/searches/histories`" -H `"Accept: application/json`" -H `"Content-Type: application/json; charset=utf-8`" -d '$api08BodyJson'"
    }
    $notes = "$(Build-StepExceptionNote -Prefix "API-08 failed." -ExceptionRecord $_) curl=$api08Curl"
Add-Result -Id "API-08" -Name "DELETE /searches/histories" -Ok $false -Status $status -Notes $notes
}

$failed = @($results | Where-Object { -not $_.ok }).Count
$passed = $results.Count - $failed

$summary = [ordered]@{
    generated_at = (Get-Date).ToString("o")
    api_base_url = $apiBaseUrl
    total        = $results.Count
    passed       = $passed
    failed       = $failed
    results      = $results
}

$summary | ConvertTo-Json -Depth 20 | Set-Content -Path $summaryPath -Encoding UTF8

Write-Log ("Summary: total={0}, passed={1}, failed={2}" -f $results.Count, $passed, $failed)
Write-Log "Log file: $logPath"
Write-Log "Summary file: $summaryPath"

        if ($failed -gt 0) {
            $scriptExitCode = 1
        }
        else {
            $scriptExitCode = 0
        }
    }
}
finally {
    $writtenLogPath = Flush-LogBuffer -PrimaryPath $logPath
    if ($writtenLogPath -ne $logPath) {
        Write-Host "Log file used: $writtenLogPath"
    }
}

exit $scriptExitCode
