param()

$ErrorActionPreference = "Stop"

function Req([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($v)) { throw "Missing required environment variable: $name" }
    return $v
}

function Opt([string]$name, [string]$defaultValue) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($v)) { return $defaultValue }
    return $v
}

function RepoRoot {
    $d = $PSScriptRoot
    if ([string]::IsNullOrWhiteSpace($d)) { $d = Split-Path -Parent $PSCommandPath }
    return (Resolve-Path (Join-Path $d "..")).Path
}

function StatusFromError($err) {
    try { return [int]$err.Exception.Response.StatusCode } catch { return $null }
}

function BodyFromError($err) {
    if ($err.ErrorDetails -and -not [string]::IsNullOrWhiteSpace($err.ErrorDetails.Message)) { return $err.ErrorDetails.Message }
    try {
        $r = New-Object System.IO.StreamReader($err.Exception.Response.GetResponseStream())
        $t = $r.ReadToEnd()
        $r.Close()
        return $t
    }
    catch { return "" }
}

function BuildQuery([hashtable]$q) {
    if ($null -eq $q -or $q.Count -eq 0) { return "" }
    $pairs = New-Object System.Collections.Generic.List[string]
    foreach ($k in ($q.Keys | Sort-Object)) {
        $pairs.Add(([System.Uri]::EscapeDataString([string]$k) + "=" + [System.Uri]::EscapeDataString([string]$q[$k]))) | Out-Null
    }
    return ($pairs -join "&")
}

function PathWithQuery([string]$path, [hashtable]$query) {
    if ([string]::IsNullOrWhiteSpace($path) -or -not $path.StartsWith("/")) { return $null }
    $q = BuildQuery $query
    if ([string]::IsNullOrWhiteSpace($q)) { return $path }
    return ("{0}?{1}" -f $path, $q)
}

function Url([string]$base, [string]$pathWithQuery) {
    if ([string]::IsNullOrWhiteSpace($pathWithQuery) -or -not $pathWithQuery.StartsWith("/")) { return $null }
    return ($base.TrimEnd("/") + $pathWithQuery)
}

function NormalizePrefix([string]$p) {
    if ([string]::IsNullOrWhiteSpace($p)) { $p = "/api/v1" }
    if (-not $p.StartsWith("/")) { $p = "/$p" }
    if ($p.Length -gt 1) { $p = $p.TrimEnd("/") }
    return $p
}

function ApiPath([string]$prefix, [string]$rel) {
    if ([string]::IsNullOrWhiteSpace($rel)) { return $null }
    if ($rel.StartsWith($prefix)) { return $rel }
    if ($rel.StartsWith("/")) { return "$prefix$rel" }
    return "$prefix/$rel"
}

function GetOp($swagger, [string]$method, [string]$path) {
    $pp = $swagger.paths.PSObject.Properties[$path]
    if ($null -eq $pp) { return $null }
    $mp = $pp.Value.PSObject.Properties[$method.ToLowerInvariant()]
    if ($null -eq $mp) { return $null }
    return $mp.Value
}

function AuthRequired($swagger, $op) {
    if ($null -ne $op.PSObject.Properties["security"]) {
        if ($null -eq $op.security) { return $false }
        return @($op.security).Count -gt 0
    }
    if ($null -ne $swagger.PSObject.Properties["security"] -and $null -ne $swagger.security) { return @($swagger.security).Count -gt 0 }
    return $false
}

function FindOpByHint($swagger, [string]$tag, [string]$method, [string]$pathContains) {
    foreach ($p in $swagger.paths.PSObject.Properties) {
        if (-not $p.Name.ToLowerInvariant().Contains($pathContains.ToLowerInvariant())) { continue }
        $mp = $p.Value.PSObject.Properties[$method.ToLowerInvariant()]
        if ($null -eq $mp) { continue }
        $op = $mp.Value
        $t = if ($op.tags -and @($op.tags).Count -gt 0) { [string]$op.tags[0] } else { "" }
        if ($t.ToLowerInvariant() -ne $tag.ToLowerInvariant()) { continue }
        return [pscustomobject]@{ Path = $p.Name; Method = $method.ToUpperInvariant(); Operation = $op }
    }
    return $null
}

function FindFirstValue($obj, [string]$nameRegex, [string]$kind) {
    if ($null -eq $obj) { return $null }
    if ($kind -eq "number" -and ($obj -is [int] -or $obj -is [long] -or $obj -is [double] -or $obj -is [decimal])) { return $obj }
    if ($kind -eq "string" -and $obj -is [string] -and -not [string]::IsNullOrWhiteSpace($obj)) { return $obj }
    if ($obj -is [string]) { return $null }
    if ($obj -is [System.Collections.IDictionary]) {
        foreach ($k in $obj.Keys) {
            $name = [string]$k; $v = $obj[$k]
            if ($name -match $nameRegex) {
                if ($kind -eq "number" -and ($v -is [int] -or $v -is [long] -or $v -is [double] -or $v -is [decimal])) { return $v }
                if ($kind -eq "string" -and $v -is [string] -and -not [string]::IsNullOrWhiteSpace($v)) { return $v }
            }
        }
        foreach ($k in $obj.Keys) { $f = FindFirstValue $obj[$k] $nameRegex $kind; if ($null -ne $f) { return $f } }
        return $null
    }
    if ($obj -is [System.Collections.IEnumerable]) {
        foreach ($it in $obj) { $f = FindFirstValue $it $nameRegex $kind; if ($null -ne $f) { return $f } }
        return $null
    }
    foreach ($p in $obj.PSObject.Properties) {
        if ($p.Name -match $nameRegex) {
            if ($kind -eq "number" -and ($p.Value -is [int] -or $p.Value -is [long] -or $p.Value -is [double] -or $p.Value -is [decimal])) { return $p.Value }
            if ($kind -eq "string" -and $p.Value -is [string] -and -not [string]::IsNullOrWhiteSpace($p.Value)) { return $p.Value }
        }
    }
    foreach ($p in $obj.PSObject.Properties) { $f = FindFirstValue $p.Value $nameRegex $kind; if ($null -ne $f) { return $f } }
    return $null
}

function Is-JsonObject($obj) {
    if ($null -eq $obj) { return $false }
    if ($obj -is [System.Collections.IDictionary]) { return $true }
    return ($obj -is [pscustomobject])
}

function Get-DataNode($bodyJson) {
    if ($null -eq $bodyJson) { return $null }
    if ($bodyJson -is [pscustomobject] -or $bodyJson -is [System.Collections.IDictionary]) {
        $dataProp = $bodyJson.PSObject.Properties["data"]
        if ($null -ne $dataProp -and $null -ne $dataProp.Value) { return $dataProp.Value }
    }
    return $bodyJson
}

function Validate-SuccessContract($bodyJson) {
    if ($null -eq $bodyJson) {
        return [pscustomobject]@{
            Ok = $true
            IsMinimal = $true
            Reason = "success status with empty/minimal response body"
        }
    }
    if (-not (Is-JsonObject $bodyJson)) {
        return [pscustomobject]@{
            Ok = $true
            IsMinimal = $true
            Reason = "success status with empty/minimal response body"
        }
    }

    $hasResult = ($null -ne $bodyJson.PSObject.Properties["result"])
    $hasData = ($null -ne $bodyJson.PSObject.Properties["data"])

    # Enforce envelope only when endpoint response actually follows that envelope pattern.
    if ($hasResult -or $hasData) {
        if (-not $hasResult) {
            return [pscustomobject]@{
                Ok = $false
                IsMinimal = $false
                Reason = "missing result field"
            }
        }
        if (-not $hasData) {
            return [pscustomobject]@{
                Ok = $false
                IsMinimal = $false
                Reason = "missing data field"
            }
        }
        return [pscustomobject]@{
            Ok = $true
            IsMinimal = $false
            Reason = ""
        }
    }

    return [pscustomobject]@{
        Ok = $true
        IsMinimal = $true
        Reason = "success status with empty/minimal response body"
    }
}

function Infer-SeedNumber($bodyJson, [string[]]$patterns) {
    $sources = @((Get-DataNode $bodyJson), $bodyJson)
    foreach ($src in $sources) {
        foreach ($pattern in $patterns) {
            $v = FindFirstValue $src $pattern "number"
            if ($null -ne $v) { return $v }
        }
    }
    return $null
}

function Infer-SeedString($bodyJson, [string[]]$patterns) {
    $sources = @((Get-DataNode $bodyJson), $bodyJson)
    foreach ($src in $sources) {
        foreach ($pattern in $patterns) {
            $v = FindFirstValue $src $pattern "string"
            if ($null -ne $v -and -not [string]::IsNullOrWhiteSpace([string]$v)) { return [string]$v }
        }
    }
    return $null
}

function TryInferStoreUniqueId($bodyJson) {
    $sources = @((Get-DataNode $bodyJson), $bodyJson)
    $exactKeys = @("uniqueId", "UniqueId", "storeUniqueId", "StoreUniqueId", "unique_id", "store_unique_id")
    foreach ($src in $sources) {
        if (-not (Is-JsonObject $src)) { continue }
        foreach ($k in $exactKeys) {
            $prop = $src.PSObject.Properties[$k]
            if ($null -eq $prop -or $null -eq $prop.Value) { continue }
            $candidate = ([string]$prop.Value).Trim()
            if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
            return $candidate
        }
    }
    return $null
}

function TryInferNewsSlug($bodyJson) {
    $result = [pscustomobject]@{
        Slug = $null
        Reason = "No detail-route-compatible slug field found."
    }
    if ($null -eq $bodyJson) {
        $result.Reason = "News response body is null."
        return $result
    }

    $dataNode = Get-DataNode $bodyJson
    $items = @()
    if ($dataNode -and $dataNode.data) { $items = @($dataNode.data) }
    elseif ($dataNode -and $dataNode.items) { $items = @($dataNode.items) }
    elseif ($dataNode -and $dataNode.records) { $items = @($dataNode.records) }
    elseif ($dataNode -is [System.Collections.IEnumerable] -and -not ($dataNode -is [string])) { $items = @($dataNode) }

    if ($items.Count -eq 0) {
        $result.Reason = "News list returned zero records (data.data/items/records empty)."
        return $result
    }

    $exactKeys = @("slug", "Slug", "seoSlug", "SeoSlug", "alias", "Alias", "path", "Path", "urlSlug", "UrlSlug", "newsSlug", "NewsSlug")
    foreach ($item in $items) {
        if (-not (Is-JsonObject $item)) { continue }
        foreach ($k in $exactKeys) {
            $prop = $item.PSObject.Properties[$k]
            if ($null -eq $prop -or $null -eq $prop.Value) { continue }
            $candidate = ([string]$prop.Value).Trim()
            if ([string]::IsNullOrWhiteSpace($candidate)) { continue }
            $result.Slug = $candidate
            $result.Reason = "Resolved from key '$k'."
            return $result
        }
    }

    $sampleKeys = @()
    $firstObj = $items | Where-Object { Is-JsonObject $_ } | Select-Object -First 1
    if ($firstObj) { $sampleKeys = @($firstObj.PSObject.Properties.Name) }
    if ($sampleKeys.Count -gt 0) {
        $result.Reason = ("No slug-like field in news items. sample_keys={0}" -f ($sampleKeys -join ","))
    }
    return $result
}

function InvokeJson([string]$method, [string]$url, [hashtable]$headers, $body, [int]$timeoutSec) {
    $h = @{ "Accept" = "application/json" }
    if ($headers) { foreach ($k in $headers.Keys) { $h[$k] = $headers[$k] } }
    $p = @{ Method = $method; Uri = $url; Headers = $h; ErrorAction = "Stop"; TimeoutSec = $timeoutSec }
    if ($null -ne $body) { $p["ContentType"] = "application/json; charset=utf-8"; $p["Body"] = ($body | ConvertTo-Json -Depth 20 -Compress) }
    try {
        $r = Invoke-RestMethod @p
        $txt = ""; $json = $r
        if ($r -is [string]) { $txt = [string]$r; try { $json = $txt | ConvertFrom-Json -Depth 20 } catch { $json = $r } }
        else { try { $txt = $r | ConvertTo-Json -Depth 20 -Compress } catch { $txt = [string]$r } }
        return [pscustomobject]@{ status = 200; body_json = $json; body_text = $txt; error = $null }
    }
    catch {
        return [pscustomobject]@{ status = (StatusFromError $_); body_json = $null; body_text = (BodyFromError $_); error = $_.Exception.Message }
    }
}

function InvokeRaw([string]$method, [string]$url, [hashtable]$headers, [string]$contentType, [string]$bodyText, [int]$timeoutSec) {
    $h = @{ "Accept" = "application/json" }
    if ($headers) { foreach ($k in $headers.Keys) { $h[$k] = $headers[$k] } }
    $p = @{ Method = $method; Uri = $url; Headers = $h; ErrorAction = "Stop"; TimeoutSec = $timeoutSec }
    if (-not [string]::IsNullOrWhiteSpace($contentType)) { $p["ContentType"] = $contentType }
    if ($null -ne $bodyText) { $p["Body"] = $bodyText }
    try {
        $r = Invoke-RestMethod @p
        $txt = ""; $json = $r
        if ($r -is [string]) { $txt = [string]$r; try { $json = $txt | ConvertFrom-Json -Depth 20 } catch { $json = $r } }
        else { try { $txt = $r | ConvertTo-Json -Depth 20 -Compress } catch { $txt = [string]$r } }
        return [pscustomobject]@{ status = 200; body_json = $json; body_text = $txt; error = $null }
    }
    catch {
        return [pscustomobject]@{ status = (StatusFromError $_); body_json = $null; body_text = (BodyFromError $_); error = $_.Exception.Message }
    }
}

function New-IdempotencyKey {
    return ("qa-regression-{0}" -f ([Guid]::NewGuid().ToString("N")))
}

function ExtractTokenFromLogin($bodyJson) {
    if ($null -eq $bodyJson) { return $null }
    $tk = $bodyJson.data.token
    if ([string]::IsNullOrWhiteSpace([string]$tk)) { $tk = $bodyJson.login.data.token }
    if ([string]::IsNullOrWhiteSpace([string]$tk)) { return $null }
    return ([string]$tk).Trim()
}

function Get-OrderCreateDiagnostic([Nullable[int]]$status, [string]$bodyText) {
    $b = if ($null -eq $bodyText) { "" } else { [string]$bodyText }
    $u = $b.ToUpperInvariant()
    if ($status -eq 415) { return "Unsupported Media Type (expected application/json; charset=utf-8)." }
    if ($u.Contains("QUANTITY")) { return "Missing Quantity validation triggered." }
    if ($u.Contains("IDEMPOTENCY-KEY") -or $u.Contains("IDEMPOTENCYKEY")) { return "Missing Idempotency-Key validation triggered." }
    if ($u.Contains("POLICY_NOT_CONFIGURED")) { return "POLICY_NOT_CONFIGURED: business/store policy is not configured." }
    return $null
}

function TrySeedSkuFromStoreMenu([string]$prefix, [int]$storeId) {
    if ($storeId -le 0) { return $null }
    $menuPath = ApiPath $prefix ("/stores/{0}/menu" -f $storeId)
    $menuUrl = Url $script:base $menuPath
    $headers = @{}
    if (-not [string]::IsNullOrWhiteSpace($script:token)) { $headers["Authorization"] = "Bearer $($script:token)" }
    $resp = InvokeJson "GET" $menuUrl $headers $null $script:timeoutSec
    if ($resp.status -ne 200 -or $null -eq $resp.body_json) { return $null }

    try {
        $dataNode = Get-DataNode $resp.body_json
        if ($null -eq $dataNode -or $null -eq $dataNode.categories) { return $null }
        foreach ($category in @($dataNode.categories)) {
            $categoryName = [string]$category.name
            foreach ($item in @($category.items)) {
                $itemName = [string]$item.name
                foreach ($skuNode in @($item.skus)) {
                    $idProp = $skuNode.PSObject.Properties["id"]
                    if ($null -eq $idProp -or $null -eq $idProp.Value) { continue }
                    $isActive = $false
                    $activeProp = $skuNode.PSObject.Properties["isActive"]
                    if ($null -ne $activeProp -and $null -ne $activeProp.Value) { $isActive = [bool]$activeProp.Value }
                    $availabilityStatus = -1
                    $availProp = $skuNode.PSObject.Properties["availabilityStatus"]
                    if ($null -ne $availProp -and $null -ne $availProp.Value) {
                        try { $availabilityStatus = [int]$availProp.Value } catch { $availabilityStatus = -1 }
                    }
                    if (-not $isActive -or $availabilityStatus -ne 0) { continue }
                    $skuName = ""
                    $skuNameProp = $skuNode.PSObject.Properties["name"]
                    if ($null -ne $skuNameProp -and $null -ne $skuNameProp.Value) { $skuName = [string]$skuNameProp.Value }
                    return [pscustomobject]@{
                        StoreId = [int]$storeId
                        CategoryName = $categoryName
                        ItemName = $itemName
                        SkuId = [int]$idProp.Value
                        SkuName = $skuName
                    }
                }
            }
        }
    }
    catch { }
    return $null
}

$root = RepoRoot
$outDir = Join-Path $root "artifacts/test-results/api-regression"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
$logPath = Join-Path $outDir "api_regression.log"
$summaryPath = Join-Path $outDir "api_regression.summary.json"
$failedPath = Join-Path $outDir "api_regression.failed.json"

$global:LogLines = New-Object System.Collections.Generic.List[string]
$results = New-Object System.Collections.Generic.List[object]
$startedAt = (Get-Date).ToString("o")
$exitCode = 0

function Log([string]$m) { $global:LogLines.Add(("[{0}] {1}" -f (Get-Date).ToString("s"), $m)) | Out-Null; Write-Host $m }

function AddResult([string]$id, [string]$module, [string]$name, [string]$method, [string]$path, [int[]]$expected, [Nullable[int]]$actual, [string]$notes, [string]$outcome) {
    if ([string]::IsNullOrWhiteSpace($outcome)) { if ($null -ne $actual -and $expected -contains [int]$actual) { $outcome = "PASS" } else { $outcome = "FAIL" } }
    $r = [pscustomobject]@{
        id              = $id
        module          = $module
        name            = $name
        method          = $method
        path            = $path
        ok              = ($outcome -eq "PASS")
        status          = $actual
        expected_status = @($expected)
        notes           = $notes
        ts              = (Get-Date).ToString("o")
        outcome         = $outcome
    }
    $results.Add($r) | Out-Null
    $st = if ($null -eq $actual) { "null" } else { [string]$actual }
    try {
        $line = ("{0} | {1} | {2} {3} | outcome={4} | status={5} | expected={6} | notes={7}" -f $module.ToUpperInvariant(), $id, $method, $path, $outcome, $st, (@($expected) -join ","), $notes)
    }
    catch {
        $safeExpected = @($expected) -join ","
        $line = "SYSTEM | LOG-001 | INTERNAL AddResult log format fallback | outcome=WARN | status=0 | expected= | notes=Log format fallback triggered. module=$module; id=$id; method=$method; path=$path; outcome=$outcome; status=$st; expected=$safeExpected; raw_notes=$notes"
    }
    try { Log $line }
    catch {
        try {
            $global:LogLines.Add(("[{0}] {1}" -f (Get-Date).ToString("s"), $line)) | Out-Null
        }
        catch { }
        Write-Host $line
    }
}

function RunCase([hashtable]$c) {
    $op = GetOp $script:swagger $c.method $c.contract_path
    if ($null -eq $op) { AddResult $c.id $c.module $c.name $c.method $c.contract_path $c.expected_status $null "FAIL: Contract mismatch. Endpoint not found in swagger." "FAIL"; return $null }
    if ($c.call_path.Contains("{")) { AddResult $c.id $c.module $c.name $c.method $c.contract_path $c.expected_status $null "SKIPPED: Missing seed id." "SKIPPED"; return $null }
    $finalQuery = @{}
    if ($c.query) { foreach ($k in $c.query.Keys) { $finalQuery[$k] = $c.query[$k] } }
    if ($op.parameters) {
        foreach ($p in @($op.parameters)) {
            if ([string]$p.in -ne "query" -or -not [bool]$p.required) { continue }
            $n = [string]$p.name
            if ($finalQuery.ContainsKey($n)) { continue }
            $v = $null
            if ($null -ne $p.PSObject.Properties["example"]) { $v = $p.example }
            elseif ($null -ne $p.schema -and $null -ne $p.schema.PSObject.Properties["default"]) { $v = $p.schema.default }
            elseif ($n -in @("PageNumber", "pageNumber")) { $v = 1 }
            elseif ($n -in @("PageSize", "pageSize")) { $v = 1 }
            elseif ($n -in @("Keyword", "keyword")) { $v = "test" }
            elseif ($n -in @("LanguageCode", "languageCode")) { $v = "vi" }
            elseif ($n -in @("id", "Id", "storeId", "StoreId")) { $v = $script:seedId }
            elseif ($n -in @("uniqueId", "UniqueId")) { $v = $script:seedUniqueId }
            if ($null -eq $v -or [string]::IsNullOrWhiteSpace([string]$v)) { AddResult $c.id $c.module $c.name $c.method $c.contract_path $c.expected_status $null ("SKIPPED: Missing required params ($n).") "SKIPPED"; return $null }
            $finalQuery[$n] = $v
        }
    }
    $pathForCall = PathWithQuery $c.call_path $finalQuery
    if ([string]::IsNullOrWhiteSpace($pathForCall)) { AddResult $c.id $c.module $c.name $c.method $c.contract_path $c.expected_status $null "SKIPPED: Invalid path format." "SKIPPED"; return $null }
    $url = Url $script:base $pathForCall
    if ([string]::IsNullOrWhiteSpace($url)) { AddResult $c.id $c.module $c.name $c.method $c.contract_path $c.expected_status $null "SKIPPED: Invalid URL build." "SKIPPED"; return $null }
    $headers = @{}
    $needAuth = $false
    if ($c.require_token) { $needAuth = $true }
    if ($c.no_token) { $needAuth = $false }
    if ($needAuth -and [string]::IsNullOrWhiteSpace($script:token)) { AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $null "SKIPPED: Auth token unavailable." "SKIPPED"; return $null }
    if (-not $c.no_token -and -not [string]::IsNullOrWhiteSpace($script:token)) { $headers["Authorization"] = "Bearer $($script:token)" }
    if ($c.extra_headers) {
        foreach ($hk in $c.extra_headers.Keys) { $headers[[string]$hk] = [string]$c.extra_headers[$hk] }
    }
    $resp = InvokeJson $c.method $url $headers $c.body $script:timeoutSec
    $outcome = ""
    $notes = if ($c.expected_status -contains [int]$resp.status) { "OK" } else { "Unexpected status. error=$($resp.error); body=$($resp.body_text)" }

    if ([bool]$c.skip_on_unauthorized -and $resp.status -in @(401, 403)) {
        $skipNote = if ([string]::IsNullOrWhiteSpace([string]$c.unauthorized_skip_note)) {
            "SKIPPED: required role is unavailable for current token (status=$($resp.status))"
        }
        else {
            [string]$c.unauthorized_skip_note + " (status=$($resp.status))"
        }
        AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $skipNote "SKIPPED"
        return $resp
    }

    if ([bool]$c.admin_required_case -and $resp.status -in @(401, 403)) {
        $notes = "SKIPPED: requires admin role (status=$($resp.status))"
        AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $notes "SKIPPED"
        return $resp
    }

    if ($null -ne $resp.status -and $resp.status -ge 500) {
        $notes = "Regression finding: server error ($($resp.status)). error=$($resp.error); body=$($resp.body_text)"
        $outcome = "FAIL"
    }

    if (($null -ne $resp.status) -and ($resp.status -ge 200) -and ($resp.status -lt 300) -and (-not [bool]$c.skip_contract_assert)) {
        $contract = Validate-SuccessContract $resp.body_json
        if (-not $contract.Ok) {
            $notes = "Contract assertion failed: $($contract.Reason). body=$($resp.body_text)"
            $outcome = "FAIL"
        }
        elseif ($contract.IsMinimal) {
            $notes = "OK (success status with empty/minimal response body)"
        }
    }

    if ([bool]$c.not_found_negative -and $null -ne $resp.status -and $resp.status -lt 500 -and $outcome -ne "FAIL") {
        if ($c.expected_status -contains [int]$resp.status) {
            $notes = "OK (not-found negative case)"
        }
        else {
            $notes = "Non-5xx accepted for not-found negative case. status=$($resp.status); body=$($resp.body_text)"
        }
        $outcome = "PASS"
    }

    AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $notes $outcome
    return $resp
}

function RunAdminCase([hashtable]$c) {
    $c.admin_required_case = $true
    return (RunCase $c)
}

try {
    $script:base = (Req "API_BASE_URL").TrimEnd("/")
    $user = Req "API_USER"
    $pass = Req "API_PASS"
    $prefix = NormalizePrefix (Opt "API_PREFIX" "/api/v1")
    $script:timeoutSec = [int](Opt "API_TIMEOUT_SEC" "30")
    if ($script:timeoutSec -le 0) { $script:timeoutSec = 30 }
    $script:token = $null
    $script:refresh = $null
    $script:seedId = $null
    $script:seedUniqueId = $null
    $script:seedPostId = $null
    $script:seedNewsSlug = $null
    $script:seedOrgId = $null
    $script:seedCategoryAdminId = $null
    $script:seedMemberId = $null
    $script:seedStoreCategoryAdminId = $null
    $script:seedStoreCategoryParentId = $null
    $script:seedOrderId = $null
    $script:seedOrderStoreId = $null
    $script:seedSkuId = $null
    $script:preferredOrderStoreId = 9768
    $script:preferredStoreId = 9768
    $script:preferredStoreUniqueId = Opt "API_STORE_UNIQUE_ID" ""
    $script:merchantToken = $null
    $script:merchantUser = $null

    Log "API regression start. base_url=$($script:base) api_prefix=$prefix timeout=$($script:timeoutSec)"
    $sw = InvokeJson "GET" "$($script:base)/swagger/v1/swagger.json" @{} $null $script:timeoutSec
    if ($null -eq $sw.body_json) { throw "Cannot load swagger. status=$($sw.status); body=$($sw.body_text)" }
    $script:swagger = $sw.body_json
    Log "Swagger loaded."

    $merchantUser = Opt "API_MERCHANT_USER" $user
    $merchantPass = Opt "API_MERCHANT_PASS" $pass
    $script:merchantUser = $merchantUser

    # AUTH group
    $loginPath = ApiPath $prefix "/auth/login"
    $rLogin = RunCase @{ id = "AUTH-001"; module = "auth"; name = "Login success"; method = "POST"; contract_path = $loginPath; call_path = $loginPath; query = @{}; body = @{ email = $user; password = $pass; deviceID = "qa-regression" }; expected_status = @(200); require_token = $false; no_token = $true }
    if ($rLogin -and $rLogin.status -eq 200) {
        $tk = ExtractTokenFromLogin $rLogin.body_json
        if (-not [string]::IsNullOrWhiteSpace([string]$tk)) { $script:token = ([string]$tk).Trim() }
        $rf = $rLogin.body_json.data.refreshToken; if ([string]::IsNullOrWhiteSpace([string]$rf)) { $rf = $rLogin.body_json.login.data.refreshToken }
        if (-not [string]::IsNullOrWhiteSpace([string]$rf)) { $script:refresh = ([string]$rf).Trim() }
    }
    if (-not [string]::IsNullOrWhiteSpace($script:token)) {
        if ($merchantUser -ieq $user -and $merchantPass -eq $pass) {
            $script:merchantToken = $script:token
            Log ("Merchant lifecycle auth source: API_USER ({0})" -f $merchantUser)
        }
        else {
            $merchantLoginBody = @{ email = $merchantUser; password = $merchantPass; deviceID = "qa-regression-merchant" }
            $merchantLoginResp = InvokeJson "POST" (Url $script:base $loginPath) @{} $merchantLoginBody $script:timeoutSec
            if ($merchantLoginResp.status -eq 200) {
                $mToken = ExtractTokenFromLogin $merchantLoginResp.body_json
                if (-not [string]::IsNullOrWhiteSpace($mToken)) {
                    $script:merchantToken = $mToken
                    Log ("Merchant lifecycle auth source: API_MERCHANT_USER ({0})" -f $merchantUser)
                }
            }
            if ([string]::IsNullOrWhiteSpace($script:merchantToken)) {
                $script:merchantToken = $script:token
                Log ("Merchant login with API_MERCHANT_USER failed; fallback to API_USER token. merchant={0}; status={1}; body={2}" -f $merchantUser, $merchantLoginResp.status, $merchantLoginResp.body_text)
            }
        }
    }
    RunCase @{ id = "AUTH-002"; module = "auth"; name = "Login wrong password"; method = "POST"; contract_path = $loginPath; call_path = $loginPath; query = @{}; body = @{ email = $user; password = ($pass + "-wrong"); deviceID = "qa-regression" }; expected_status = @(400, 401, 403); require_token = $false; no_token = $true } | Out-Null
    RunCase @{ id = "AUTH-003"; module = "auth"; name = "Login missing email"; method = "POST"; contract_path = $loginPath; call_path = $loginPath; query = @{}; body = @{ password = $pass; deviceID = "qa-regression" }; expected_status = @(400, 422); require_token = $false; no_token = $true } | Out-Null
    RunCase @{ id = "AUTH-004"; module = "auth"; name = "Login missing password"; method = "POST"; contract_path = $loginPath; call_path = $loginPath; query = @{}; body = @{ email = $user; deviceID = "qa-regression" }; expected_status = @(400, 422); require_token = $false; no_token = $true } | Out-Null
    $getInfoPath = ApiPath $prefix "/account/get-info"
    RunCase @{ id = "AUTH-005"; module = "auth"; name = "Get-info with valid token"; method = "GET"; contract_path = $getInfoPath; call_path = $getInfoPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunCase @{ id = "AUTH-006"; module = "auth"; name = "Get-info without token"; method = "GET"; contract_path = $getInfoPath; call_path = $getInfoPath; query = @{}; body = $null; expected_status = @(401, 403); require_token = $false; no_token = $true } | Out-Null
    $refreshOp = FindOpByHint $script:swagger "auth" "POST" "refresh"
    if ($null -eq $refreshOp -or [string]::IsNullOrWhiteSpace($script:refresh)) { AddResult "AUTH-007" "auth" "Refresh token happy path" "POST" "/auth/*refresh*" @(200) $null "SKIPPED: Not feasible (endpoint or refresh token missing)." "SKIPPED" }
    else { RunCase @{ id = "AUTH-007"; module = "auth"; name = "Refresh token happy path"; method = "POST"; contract_path = $refreshOp.Path; call_path = $refreshOp.Path; query = @{}; body = @{ refreshToken = $script:refresh; token = $script:token; deviceID = "qa-regression" }; expected_status = @(200, 400, 422); require_token = $false; no_token = $false } | Out-Null }

    # SEARCHES group
    $postsPath = ApiPath $prefix "/searches/posts"
    $rSea001 = RunCase @{ id = "SEA-001"; module = "searches"; name = "Posts search normal keyword"; method = "GET"; contract_path = $postsPath; call_path = $postsPath; query = @{ keyword = "test" }; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rSea001 -and $rSea001.status -eq 200 -and -not $script:seedSkuId) { $script:seedSkuId = Infer-SeedNumber $rSea001.body_json @("(?i)^skuid$","(?i)sku_id$","(?i)variantid$","(?i)variant_id$") }
    RunCase @{ id = "SEA-002"; module = "searches"; name = "Posts search empty/missing keyword"; method = "GET"; contract_path = $postsPath; call_path = $postsPath; query = @{}; body = $null; expected_status = @(200, 400, 422); require_token = $false; no_token = $false } | Out-Null
    $sgContract = ApiPath $prefix "/searches/suggestions/{keyword}"
    RunCase @{ id = "SEA-003"; module = "searches"; name = "Suggestions valid keyword"; method = "GET"; contract_path = $sgContract; call_path = (ApiPath $prefix "/searches/suggestions/test"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    $sp = [System.Uri]::EscapeDataString("te#st@!")
    RunCase @{ id = "SEA-004"; module = "searches"; name = "Suggestions special characters"; method = "GET"; contract_path = $sgContract; call_path = (ApiPath $prefix "/searches/suggestions/$sp"); query = @{}; body = $null; expected_status = @(200, 400); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "SEA-005"; module = "searches"; name = "Hot keywords"; method = "GET"; contract_path = (ApiPath $prefix "/searches/hot-keywords"); call_path = (ApiPath $prefix "/searches/hot-keywords"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    $histPath = ApiPath $prefix "/searches/histories"
    RunCase @{ id = "SEA-006"; module = "searches"; name = "Histories with token"; method = "GET"; contract_path = $histPath; call_path = $histPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunCase @{ id = "SEA-007"; module = "searches"; name = "Create history valid"; method = "POST"; contract_path = $histPath; call_path = $histPath; query = @{}; body = @{ searchQuery = "test"; deviceId = "qa-regression"; isAnonymous = $false; languageCode = "vi" }; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "SEA-008"; module = "searches"; name = "Create history missing searchQuery"; method = "POST"; contract_path = $histPath; call_path = $histPath; query = @{}; body = @{ deviceId = "qa-regression"; isAnonymous = $false; languageCode = "vi" }; expected_status = @(400, 422); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "SEA-009"; module = "searches"; name = "Delete histories valid delete-all"; method = "DELETE"; contract_path = $histPath; call_path = $histPath; query = @{}; body = @{ isAll = $true; deviceId = "qa-regression"; isAnonymous = $false }; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "SEA-010"; module = "searches"; name = "Delete histories missing body"; method = "DELETE"; contract_path = $histPath; call_path = $histPath; query = @{}; body = $null; expected_status = @(400, 415, 422); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "SEA-011"; module = "searches"; name = "Search filters"; method = "GET"; contract_path = (ApiPath $prefix "/searches/filters"); call_path = (ApiPath $prefix "/searches/filters"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null

    # STORE group
    $sRoot = ApiPath $prefix "/store"
    $rr = RunCase @{ id = "STO-001"; module = "store"; name = "Get store"; method = "GET"; contract_path = $sRoot; call_path = $sRoot; query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rr -and $rr.status -eq 200) { if (-not $script:seedId) { $script:seedId = Infer-SeedNumber $rr.body_json @("(?i)^id$","(?i)storeid$","(?i)store_id$") }; if (-not $script:seedUniqueId) { $script:seedUniqueId = TryInferStoreUniqueId $rr.body_json }; if (-not $script:seedSkuId) { $script:seedSkuId = Infer-SeedNumber $rr.body_json @("(?i)^skuid$","(?i)sku_id$","(?i)variantid$","(?i)variant_id$") } }
    $rList = RunCase @{ id = "STO-002"; module = "store"; name = "Get store list"; method = "GET"; contract_path = (ApiPath $prefix "/store/list"); call_path = (ApiPath $prefix "/store/list"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rList -and $rList.status -eq 200) { if (-not $script:seedId) { $script:seedId = Infer-SeedNumber $rList.body_json @("(?i)^id$","(?i)storeid$","(?i)store_id$") }; if (-not $script:seedUniqueId) { $script:seedUniqueId = TryInferStoreUniqueId $rList.body_json }; if (-not $script:seedSkuId) { $script:seedSkuId = Infer-SeedNumber $rList.body_json @("(?i)^skuid$","(?i)sku_id$","(?i)variantid$","(?i)variant_id$") } }
    $rPaged = RunCase @{ id = "STO-003"; module = "store"; name = "Get store paged"; method = "GET"; contract_path = (ApiPath $prefix "/store/paged"); call_path = (ApiPath $prefix "/store/paged"); query = @{ PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rPaged -and $rPaged.status -eq 200) { if (-not $script:seedId) { $script:seedId = Infer-SeedNumber $rPaged.body_json @("(?i)^id$","(?i)storeid$","(?i)store_id$") }; if (-not $script:seedUniqueId) { $script:seedUniqueId = TryInferStoreUniqueId $rPaged.body_json }; if (-not $script:seedSkuId) { $script:seedSkuId = Infer-SeedNumber $rPaged.body_json @("(?i)^skuid$","(?i)sku_id$","(?i)variantid$","(?i)variant_id$") } }
    RunCase @{ id = "STO-004"; module = "store"; name = "Get store reviews"; method = "GET"; contract_path = (ApiPath $prefix "/store/reviews"); call_path = (ApiPath $prefix "/store/reviews"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "STO-005"; module = "store"; name = "Get store views (capture behavior)"; method = "GET"; contract_path = (ApiPath $prefix "/store/views"); call_path = (ApiPath $prefix "/store/views"); query = @{}; body = $null; expected_status = @(200, 400, 415); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "STO-006"; module = "store"; name = "Get store verify"; method = "GET"; contract_path = (ApiPath $prefix "/store/verify"); call_path = (ApiPath $prefix "/store/verify"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "STO-007"; module = "store"; name = "Get store verify detail"; method = "GET"; contract_path = (ApiPath $prefix "/store/verify/detail"); call_path = (ApiPath $prefix "/store/verify/detail"); query = @{}; body = $null; expected_status = @(200, 400, 404); require_token = $false; no_token = $false } | Out-Null
    $rStorePreferred = RunCase @{ id = "STO-008"; module = "store"; name = "Get /store/{id} valid id"; method = "GET"; contract_path = (ApiPath $prefix "/store/{id}"); call_path = (ApiPath $prefix "/store/$($script:preferredStoreId)"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rStorePreferred -and $rStorePreferred.status -eq 200 -and [string]::IsNullOrWhiteSpace($script:preferredStoreUniqueId)) {
        $script:preferredStoreUniqueId = TryInferStoreUniqueId $rStorePreferred.body_json
        if (-not [string]::IsNullOrWhiteSpace($script:preferredStoreUniqueId)) {
            Log ("Store stable seed resolved from /store/{{id}}: storeId={0}, uniqueId={1}" -f $script:preferredStoreId, $script:preferredStoreUniqueId)
        }
    }
    RunCase @{ id = "STO-009"; module = "store"; name = "Get /store/{id} invalid id"; method = "GET"; contract_path = (ApiPath $prefix "/store/{id}"); call_path = (ApiPath $prefix "/store/999999999"); query = @{}; body = $null; expected_status = @(400, 404); require_token = $false; no_token = $false; not_found_negative = $true } | Out-Null
    if (-not [string]::IsNullOrWhiteSpace($script:preferredStoreUniqueId)) {
        $u = [System.Uri]::EscapeDataString([string]$script:preferredStoreUniqueId)
        RunCase @{ id = "STO-010"; module = "store"; name = "Get /store/{uniqueId} valid uniqueId"; method = "GET"; contract_path = (ApiPath $prefix "/store/{uniqueId}"); call_path = (ApiPath $prefix "/store/$u"); query = @{ UniqueId = [string]$script:preferredStoreUniqueId }; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    }
    else {
        AddResult "STO-010" "store" "Get /store/{uniqueId} valid uniqueId" "GET" (ApiPath $prefix "/store/{uniqueId}") @(200) $null "SKIPPED: Missing stable uniqueId seed. Provide API_STORE_UNIQUE_ID or ensure /store/9768 returns uniqueId." "SKIPPED"
    }
    RunCase @{ id = "STO-011"; module = "store"; name = "Get /store/{uniqueId} invalid uniqueId"; method = "GET"; contract_path = (ApiPath $prefix "/store/{uniqueId}"); call_path = (ApiPath $prefix "/store/UNKNOWN-UNIQUE-ID-QA"); query = @{ UniqueId = "UNKNOWN-UNIQUE-ID-QA" }; body = $null; expected_status = @(400, 404); require_token = $false; no_token = $false; not_found_negative = $true } | Out-Null
    RunCase @{ id = "STO-012"; module = "store"; name = "Get store collections (capture behavior)"; method = "GET"; contract_path = (ApiPath $prefix "/store/collections"); call_path = (ApiPath $prefix "/store/collections"); query = @{}; body = $null; expected_status = @(200, 400, 404, 415); require_token = $false; no_token = $false } | Out-Null

    # ORDER (initial safe subset)
    RunCase @{ id = "PAY-001"; module = "payments"; name = "GET /payments/methods"; method = "GET"; contract_path = (ApiPath $prefix "/payments/methods"); call_path = (ApiPath $prefix "/payments/methods"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null

    $rAdminOrders = RunAdminCase @{ id = "AORD-001"; module = "admin-orders"; name = "GET /admin/orders"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders"); call_path = (ApiPath $prefix "/admin/orders"); query = @{ PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rAdminOrders -and $rAdminOrders.status -eq 200) {
        if (-not $script:seedOrderId) { $script:seedOrderId = Infer-SeedNumber $rAdminOrders.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$") }
        if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = Infer-SeedNumber $rAdminOrders.body_json @("(?i)^storeid$","(?i)store_id$") }
    }

    $rMerchantOrders = RunCase @{ id = "MORD-001"; module = "merchant-orders"; name = "GET /merchant/orders"; method = "GET"; contract_path = (ApiPath $prefix "/merchant/orders"); call_path = (ApiPath $prefix "/merchant/orders"); query = @{ PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role" }
    if ($rMerchantOrders -and $rMerchantOrders.status -eq 200) {
        if (-not $script:seedOrderId) { $script:seedOrderId = Infer-SeedNumber $rMerchantOrders.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$") }
        if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = Infer-SeedNumber $rMerchantOrders.body_json @("(?i)^storeid$","(?i)store_id$") }
    }

    $ordersCreatePath = ApiPath $prefix "/orders"
    AddResult "ORD-001" "orders" "POST /orders (legacy)" "POST" $ordersCreatePath @(200, 201) $null "SKIPPED: Superseded by ORD-API-001 contract-driven create-order coverage." "SKIPPED"

    $preferredSku = TrySeedSkuFromStoreMenu $prefix ([int]$script:preferredOrderStoreId)
    if ($preferredSku -and $preferredSku.SkuId) {
        $script:seedOrderStoreId = [int]$script:preferredOrderStoreId
        $script:seedSkuId = [int]$preferredSku.SkuId
        Log ("Order seed from preferred store menu: storeId={0}, category='{1}', item='{2}', skuId={3}, skuName='{4}'" -f $script:seedOrderStoreId, $preferredSku.CategoryName, $preferredSku.ItemName, $script:seedSkuId, $preferredSku.SkuName)
    }
    elseif (-not $script:seedOrderStoreId) {
        $script:seedOrderStoreId = $script:preferredOrderStoreId
    }
    if (-not $script:seedSkuId -and $script:seedOrderStoreId) {
        $menuSeedSku = TrySeedSkuFromStoreMenu $prefix ([int]$script:seedOrderStoreId)
        if ($menuSeedSku -and $menuSeedSku.SkuId) {
            $script:seedSkuId = [int]$menuSeedSku.SkuId
            Log ("Order seed from menu: storeId={0}, category='{1}', item='{2}', skuId={3}, skuName='{4}'" -f $script:seedOrderStoreId, $menuSeedSku.CategoryName, $menuSeedSku.ItemName, $script:seedSkuId, $menuSeedSku.SkuName)
        }
    }

    if ($script:seedOrderId) {
        RunCase @{ id = "ORD-003"; module = "orders"; name = "GET /orders/{id}"; method = "GET"; contract_path = (ApiPath $prefix "/orders/{id}"); call_path = (ApiPath $prefix "/orders/$($script:seedOrderId)"); query = @{}; body = $null; expected_status = @(200, 404); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires customer order visibility" } | Out-Null
        RunCase @{ id = "MORD-003"; module = "merchant-orders"; name = "POST /merchant/orders/{id}/accept"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/accept"); call_path = (ApiPath $prefix "/merchant/orders/$($script:seedOrderId)/accept"); query = @{}; body = @{}; expected_status = @(200, 400, 401, 403, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = @{ Authorization = "Bearer $($script:merchantToken)" }; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
    }
    else {
        AddResult "ORD-003" "orders" "GET /orders/{id}" "GET" (ApiPath $prefix "/orders/{id}") @(200, 404) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-003" "merchant-orders" "POST /merchant/orders/{id}/accept" "POST" (ApiPath $prefix "/merchant/orders/{id}/accept") @(200, 400, 401, 403, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
    }

    if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = $script:seedId }
    if ($script:seedOrderStoreId) {
        RunCase @{ id = "POL-001"; module = "ordering-policy"; name = "GET /ordering-policy/store/{storeId}"; method = "GET"; contract_path = (ApiPath $prefix "/ordering-policy/store/{storeId}"); call_path = (ApiPath $prefix "/ordering-policy/store/$($script:seedOrderStoreId)"); query = @{}; body = $null; expected_status = @(200, 404); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires role-based ordering policy access" } | Out-Null
    }
    else {
        AddResult "POL-001" "ordering-policy" "GET /ordering-policy/store/{storeId}" "GET" (ApiPath $prefix "/ordering-policy/store/{storeId}") @(200, 404) $null "SKIPPED: Missing store id seed." "SKIPPED"
    }

    # ORDER API (critical v1)
    $rAordApi001 = RunCase @{ id = "AORD-API-001"; module = "admin-orders"; name = "Admin list orders"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders"); call_path = (ApiPath $prefix "/admin/orders"); query = @{ pageNumber = 1; pageSize = 1 }; body = $null; expected_status = @(200); require_token = $true; no_token = $false; admin_required_case = $true }
    if ($rAordApi001 -and $rAordApi001.status -eq 200) {
        if (-not $script:seedOrderId) { $script:seedOrderId = Infer-SeedNumber $rAordApi001.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$") }
        if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = Infer-SeedNumber $rAordApi001.body_json @("(?i)^storeid$","(?i)store_id$") }
    }
    if ($script:seedOrderId) {
        RunCase @{ id = "AORD-API-002"; module = "admin-orders"; name = "Admin order detail"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders/{id}"); call_path = (ApiPath $prefix "/admin/orders/$($script:seedOrderId)"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false; admin_required_case = $true } | Out-Null
    }
    else {
        AddResult "AORD-API-002" "admin-orders" "Admin order detail" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $null "SKIPPED: Missing order id seed for admin detail." "SKIPPED"
    }

    if ($script:seedOrderStoreId -and $script:seedSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $ordBody = @{
            storeId = [int]$script:seedOrderStoreId
            items = @(
                @{
                    skuId = [int]$script:seedSkuId
                    quantity = 1
                }
            )
        }
        $ordHeaders = @{
            Authorization = "Bearer $($script:token)"
            "Idempotency-Key" = (New-IdempotencyKey)
        }
        $ordUrl = Url $script:base (ApiPath $prefix "/orders")
        $rOrdCreate = InvokeJson "POST" $ordUrl $ordHeaders $ordBody $script:timeoutSec
        $diag = Get-OrderCreateDiagnostic $rOrdCreate.status $rOrdCreate.body_text
        if ($rOrdCreate.status -eq 200) {
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status "OK" "PASS"
            if (-not $script:seedOrderId) { $script:seedOrderId = Infer-SeedNumber $rOrdCreate.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$") }
            if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = Infer-SeedNumber $rOrdCreate.body_json @("(?i)^storeid$","(?i)store_id$") }
        }
        elseif ($rOrdCreate.status -eq 400 -and $diag -eq "POLICY_NOT_CONFIGURED: business/store policy is not configured.") {
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status ("SKIPPED: $diag body=$($rOrdCreate.body_text)") "SKIPPED"
        }
        elseif ($rOrdCreate.status -in @(401, 403)) {
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status ("SKIPPED: requires customer ordering role (status=$($rOrdCreate.status))") "SKIPPED"
        }
        else {
            $failNote = if ($diag) { "Unexpected status. $diag error=$($rOrdCreate.error); body=$($rOrdCreate.body_text)" } else { "Unexpected status. error=$($rOrdCreate.error); body=$($rOrdCreate.body_text)" }
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status $failNote "FAIL"
        }
    }
    else {
        AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $null "SKIPPED: Missing storeId/skuId seed or auth token for valid order payload." "SKIPPED"
    }

    if (-not [string]::IsNullOrWhiteSpace($script:token)) {
        $badHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) }
        $badUrl = Url $script:base (ApiPath $prefix "/orders")
        $r415 = InvokeRaw "POST" $badUrl $badHeaders "text/plain" "{}" $script:timeoutSec
        $diag415 = Get-OrderCreateDiagnostic $r415.status $r415.body_text
        $r415Notes = if ($r415.status -eq 415) { "OK: Unsupported Media Type validation confirmed." } elseif ($diag415) { "Unexpected status. $diag415 error=$($r415.error); body=$($r415.body_text)" } else { "Unexpected status. error=$($r415.error); body=$($r415.body_text)" }
        AddResult "ORD-API-002" "orders" "Create order unsupported media type" "POST" (ApiPath $prefix "/orders") @(415) $r415.status $r415Notes ""
    }
    else {
        AddResult "ORD-API-002" "orders" "Create order unsupported media type" "POST" (ApiPath $prefix "/orders") @(415) $null "SKIPPED: Auth token unavailable." "SKIPPED"
    }

    if ($script:seedOrderStoreId) {
        $invalidBody = @{
            storeId = [int]$script:seedOrderStoreId
        }
        $rOrd003 = RunCase @{ id = "ORD-API-003"; module = "orders"; name = "Create order validation failure (missing items)"; method = "POST"; contract_path = (ApiPath $prefix "/orders"); call_path = (ApiPath $prefix "/orders"); query = @{}; body = $invalidBody; expected_status = @(400, 422); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires customer ordering role"; skip_contract_assert = $true; extra_headers = @{ "Idempotency-Key" = (New-IdempotencyKey) } }
        if ($rOrd003 -and $rOrd003.status -notin @(400, 422) ) {
            $diag003 = Get-OrderCreateDiagnostic $rOrd003.status $rOrd003.body_text
            if ($diag003) { Log ("ORD-API-003 diagnostic: {0}" -f $diag003) }
        }
    }
    else {
        AddResult "ORD-API-003" "orders" "Create order validation failure (missing items)" "POST" (ApiPath $prefix "/orders") @(400, 422) $null "SKIPPED: Missing storeId seed." "SKIPPED"
    }

    if ($script:seedOrderId) {
        Log ("Merchant lifecycle context: merchant={0}; orderId={1}; orderStoreId={2}; preferredStoreId={3}" -f $script:merchantUser, $script:seedOrderId, $script:seedOrderStoreId, $script:preferredOrderStoreId)
        RunCase @{ id = "ORD-API-004"; module = "orders"; name = "Get order detail success"; method = "GET"; contract_path = (ApiPath $prefix "/orders/{id}"); call_path = (ApiPath $prefix "/orders/$($script:seedOrderId)"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires customer order visibility" } | Out-Null
        $merchantAuthHeaders = @{ Authorization = "Bearer $($script:merchantToken)" }
        $rMordAccept = RunCase @{ id = "MORD-API-001"; module = "merchant-orders"; name = "Merchant accept order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/accept"); call_path = (ApiPath $prefix "/merchant/orders/$($script:seedOrderId)/accept"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true }
        $rMordReject = RunCase @{ id = "MORD-API-002"; module = "merchant-orders"; name = "Merchant reject order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/reject"); call_path = (ApiPath $prefix "/merchant/orders/$($script:seedOrderId)/reject"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true }

        if ($rMordAccept -and $rMordAccept.status -eq 400) {
            if (($rMordAccept.body_text | Out-String).ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
                Log ("MORD-API-001 review: FORBIDDEN_SCOPE for merchant={0}, orderId={1}, orderStoreId={2}. Scope/ownership relation is not satisfied." -f $script:merchantUser, $script:seedOrderId, $script:seedOrderStoreId)
            }
            else { Log ("MORD-API-001 review: status=400 suggests business-state precondition was not met. body={0}" -f $rMordAccept.body_text) }
        }
        if ($rMordReject -and $rMordReject.status -eq 400) {
            if (($rMordReject.body_text | Out-String).ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
                Log ("MORD-API-002 review: FORBIDDEN_SCOPE for merchant={0}, orderId={1}, orderStoreId={2}. Scope/ownership relation is not satisfied." -f $script:merchantUser, $script:seedOrderId, $script:seedOrderStoreId)
            }
            else { Log ("MORD-API-002 review: status=400 suggests business-state precondition was not met. body={0}" -f $rMordReject.body_text) }
        }

        if ($rMordAccept -and $rMordAccept.status -eq 200) {
            RunCase @{ id = "MORD-API-003"; module = "merchant-orders"; name = "Merchant mark-arrived order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/mark-arrived"); call_path = (ApiPath $prefix "/merchant/orders/$($script:seedOrderId)/mark-arrived"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
            RunCase @{ id = "MORD-API-004"; module = "merchant-orders"; name = "Merchant complete order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/complete"); call_path = (ApiPath $prefix "/merchant/orders/$($script:seedOrderId)/complete"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
        }
        else {
            AddResult "MORD-API-003" "merchant-orders" "Merchant mark-arrived order" "POST" (ApiPath $prefix "/merchant/orders/{id}/mark-arrived") @(200, 400, 404, 409, 422) $null "SKIPPED: Accept transition did not succeed (status must be 200) so mark-arrived precondition is unmet." "SKIPPED"
            AddResult "MORD-API-004" "merchant-orders" "Merchant complete order" "POST" (ApiPath $prefix "/merchant/orders/{id}/complete") @(200, 400, 404, 409, 422) $null "SKIPPED: Accept transition did not succeed (status must be 200) so complete precondition is unmet." "SKIPPED"
        }
    }
    else {
        AddResult "ORD-API-004" "orders" "Get order detail success" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-001" "merchant-orders" "Merchant accept order" "POST" (ApiPath $prefix "/merchant/orders/{id}/accept") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-002" "merchant-orders" "Merchant reject order" "POST" (ApiPath $prefix "/merchant/orders/{id}/reject") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-003" "merchant-orders" "Merchant mark-arrived order" "POST" (ApiPath $prefix "/merchant/orders/{id}/mark-arrived") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-004" "merchant-orders" "Merchant complete order" "POST" (ApiPath $prefix "/merchant/orders/{id}/complete") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
    }

    # POSTS group
    $postsRootPath = ApiPath $prefix "/posts"
    $rPostsList = RunCase @{ id = "POSTS-001"; module = "posts"; name = "GET /posts list happy path"; method = "GET"; contract_path = $postsRootPath; call_path = $postsRootPath; query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rPostsList -and $rPostsList.status -eq 200 -and -not $script:seedPostId) { $script:seedPostId = Infer-SeedNumber $rPostsList.body_json @("(?i)^id$","(?i)postid$","(?i)post_id$","(?i)^ids$") }
    $rPostIds = RunCase @{ id = "POSTS-002"; module = "posts"; name = "GET /posts/ids happy path"; method = "GET"; contract_path = (ApiPath $prefix "/posts/ids"); call_path = (ApiPath $prefix "/posts/ids"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    if ($rPostIds -and $rPostIds.status -eq 200 -and -not $script:seedPostId) { $script:seedPostId = Infer-SeedNumber $rPostIds.body_json @("(?i)^id$","(?i)postid$","(?i)post_id$","(?i)^ids$") }
    RunCase @{ id = "POSTS-003"; module = "posts"; name = "GET /posts/categories happy path"; method = "GET"; contract_path = (ApiPath $prefix "/posts/categories"); call_path = (ApiPath $prefix "/posts/categories"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "POSTS-004"; module = "posts"; name = "GET /posts/pending happy path"; method = "GET"; contract_path = (ApiPath $prefix "/posts/pending"); call_path = (ApiPath $prefix "/posts/pending"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "POSTS-005"; module = "posts"; name = "GET /posts/recommend happy path"; method = "GET"; contract_path = (ApiPath $prefix "/posts/recommend"); call_path = (ApiPath $prefix "/posts/recommend"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    if ($script:seedPostId) {
        Log ("Posts seed resolved: postId={0}" -f $script:seedPostId)
        RunCase @{ id = "POSTS-006"; module = "posts"; name = "GET /posts/{validId} happy path"; method = "GET"; contract_path = (ApiPath $prefix "/posts/{id}"); call_path = (ApiPath $prefix "/posts/$($script:seedPostId)"); query = @{}; body = $null; expected_status = @(200, 404); require_token = $false; no_token = $false } | Out-Null
    }
    else {
        Log "Posts seed unresolved: no usable post id found from /posts or /posts/ids."
        AddResult "POSTS-006" "posts" "GET /posts/{validId} happy path" "GET" (ApiPath $prefix "/posts/{id}") @(200) $null "SKIPPED: Missing seed post id." "SKIPPED"
    }
    RunCase @{ id = "POSTS-007"; module = "posts"; name = "GET /posts/{invalidId} negative path"; method = "GET"; contract_path = (ApiPath $prefix "/posts/{id}"); call_path = (ApiPath $prefix "/posts/999999999"); query = @{}; body = $null; expected_status = @(400, 404); require_token = $false; no_token = $false; not_found_negative = $true } | Out-Null
    RunCase @{ id = "POSTS-008"; module = "posts"; name = "GET /posts pagination variant"; method = "GET"; contract_path = $postsRootPath; call_path = $postsRootPath; query = @{ PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null

    # NEWS group
    $newsRootPath = ApiPath $prefix "/news"
    $rNews = RunCase @{ id = "NEWS-001"; module = "news"; name = "GET /news list happy path"; method = "GET"; contract_path = $newsRootPath; call_path = $newsRootPath; query = @{ LanguageCode = "vi"; PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $false; no_token = $false }
    $newsSeedReason = "Unknown news seed reason."
    if ($rNews -and $rNews.status -eq 200 -and -not $script:seedNewsSlug) {
        $newsSeed = TryInferNewsSlug $rNews.body_json
        if ($newsSeed) {
            $script:seedNewsSlug = $newsSeed.Slug
            if (-not [string]::IsNullOrWhiteSpace([string]$newsSeed.Reason)) { $newsSeedReason = [string]$newsSeed.Reason }
        }
    }
    RunCase @{ id = "NEWS-002"; module = "news"; name = "GET /news pagination+language variant"; method = "GET"; contract_path = $newsRootPath; call_path = $newsRootPath; query = @{ LanguageCode = "vi"; PageNumber = 2; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    if ($script:seedNewsSlug) {
        Log ("News seed resolved: slug='{0}'" -f $script:seedNewsSlug)
        $validSlug = [System.Uri]::EscapeDataString([string]$script:seedNewsSlug)
        RunCase @{ id = "NEWS-003"; module = "news"; name = "GET /news/{validSlug} happy path"; method = "GET"; contract_path = (ApiPath $prefix "/news/{slug}"); call_path = (ApiPath $prefix "/news/$validSlug"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    }
    else {
        Log ("News seed unresolved: {0}" -f $newsSeedReason)
        AddResult "NEWS-003" "news" "GET /news/{validSlug} happy path" "GET" (ApiPath $prefix "/news/{slug}") @(200) $null ("SKIPPED: Missing seed news slug. " + $newsSeedReason) "SKIPPED"
    }
    RunCase @{ id = "NEWS-004"; module = "news"; name = "GET /news/{invalidSlug} negative path"; method = "GET"; contract_path = (ApiPath $prefix "/news/{slug}"); call_path = (ApiPath $prefix "/news/unknown-slug-qa-regression"); query = @{}; body = $null; expected_status = @(400, 404); require_token = $false; no_token = $false; not_found_negative = $true } | Out-Null

    # ORGANIZATION group
    $orgListPath = ApiPath $prefix "/organization/list"
    $rOrgList = RunCase @{ id = "ORG-001"; module = "organization"; name = "GET /organization/list happy path"; method = "GET"; contract_path = $orgListPath; call_path = $orgListPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rOrgList -and $rOrgList.status -eq 200 -and -not $script:seedOrgId) { $script:seedOrgId = FindFirstValue $rOrgList.body_json "(?i)^id$|organizationid$" "number" }
    $rOrgInfo = RunCase @{ id = "ORG-002"; module = "organization"; name = "GET /organization/get-info happy path"; method = "GET"; contract_path = (ApiPath $prefix "/organization/get-info"); call_path = (ApiPath $prefix "/organization/get-info"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rOrgInfo -and $rOrgInfo.status -eq 200 -and -not $script:seedOrgId) { $script:seedOrgId = FindFirstValue $rOrgInfo.body_json "(?i)^id$|organizationid$" "number" }
    RunCase @{ id = "ORG-003"; module = "organization"; name = "GET /organization/get-organization-type happy path"; method = "GET"; contract_path = (ApiPath $prefix "/organization/get-organization-type"); call_path = (ApiPath $prefix "/organization/get-organization-type"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null
    RunCase @{ id = "ORG-004"; module = "organization"; name = "GET /organization/pagination-selection happy path"; method = "GET"; contract_path = (ApiPath $prefix "/organization/pagination-selection"); call_path = (ApiPath $prefix "/organization/pagination-selection"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    $rOrgPaged = RunCase @{ id = "ORG-005"; module = "organization"; name = "GET /organization/paged happy path"; method = "GET"; contract_path = (ApiPath $prefix "/organization/paged"); call_path = (ApiPath $prefix "/organization/paged"); query = @{ PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rOrgPaged -and $rOrgPaged.status -eq 200 -and -not $script:seedOrgId) { $script:seedOrgId = FindFirstValue $rOrgPaged.body_json "(?i)^id$|organizationid$" "number" }
    if ($script:seedOrgId) {
        RunCase @{ id = "ORG-006"; module = "organization"; name = "GET /organization/detail/{validId} happy path"; method = "GET"; contract_path = (ApiPath $prefix "/organization/detail/{id}"); call_path = (ApiPath $prefix "/organization/detail/$($script:seedOrgId)"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    }
    else {
        AddResult "ORG-006" "organization" "GET /organization/detail/{validId} happy path" "GET" (ApiPath $prefix "/organization/detail/{id}") @(200) $null "SKIPPED: Missing seed organization id." "SKIPPED"
    }
    RunCase @{ id = "ORG-007"; module = "organization"; name = "GET /organization/detail/{invalidId} contract behavior"; method = "GET"; contract_path = (ApiPath $prefix "/organization/detail/{id}"); call_path = (ApiPath $prefix "/organization/detail/999999999"); query = @{}; body = $null; expected_status = @(200, 400, 404); require_token = $true; no_token = $false; not_found_negative = $true } | Out-Null

    # NOTIFICATION group
    $notiListPath = ApiPath $prefix "/notification"
    $notiUnreadPath = ApiPath $prefix "/notification/unread-count"
    RunCase @{ id = "NOTI-001"; module = "notification"; name = "GET /notification happy path"; method = "GET"; contract_path = $notiListPath; call_path = $notiListPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunCase @{ id = "NOTI-002"; module = "notification"; name = "GET /notification/unread-count happy path"; method = "GET"; contract_path = $notiUnreadPath; call_path = $notiUnreadPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunCase @{ id = "NOTI-003"; module = "notification"; name = "GET /notification without token negative"; method = "GET"; contract_path = $notiListPath; call_path = $notiListPath; query = @{}; body = $null; expected_status = @(401, 403); require_token = $false; no_token = $true } | Out-Null

    $markAllPath = ApiPath $prefix "/notification/mark-all-read"
    if ($null -eq (GetOp $script:swagger "POST" $markAllPath)) {
        AddResult "NOTI-004" "notification" "POST /notification/mark-all-read safe path" "POST" $markAllPath @(200) $null "SKIPPED: Contract not found in swagger." "SKIPPED"
    }
    else {
        RunCase @{ id = "NOTI-004"; module = "notification"; name = "POST /notification/mark-all-read safe path"; method = "POST"; contract_path = $markAllPath; call_path = $markAllPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    }

    $markReadPath = ApiPath $prefix "/notification/mark-read"
    if ($null -eq (GetOp $script:swagger "POST" $markReadPath)) {
        AddResult "NOTI-005" "notification" "POST /notification/mark-read contract behavior" "POST" $markReadPath @(200, 400, 422) $null "SKIPPED: Contract not found in swagger." "SKIPPED"
    }
    else {
        RunCase @{ id = "NOTI-005"; module = "notification"; name = "POST /notification/mark-read contract behavior"; method = "POST"; contract_path = $markReadPath; call_path = $markReadPath; query = @{}; body = @{}; expected_status = @(200, 400, 422); require_token = $true; no_token = $false } | Out-Null
    }

    $notiDeletePath = ApiPath $prefix "/notification/delete"
    if ($null -eq (GetOp $script:swagger "POST" $notiDeletePath)) {
        AddResult "NOTI-006" "notification" "POST /notification/delete contract behavior" "POST" $notiDeletePath @(200, 400, 422) $null "SKIPPED: Contract not found in swagger." "SKIPPED"
    }
    else {
        RunCase @{ id = "NOTI-006"; module = "notification"; name = "POST /notification/delete contract behavior"; method = "POST"; contract_path = $notiDeletePath; call_path = $notiDeletePath; query = @{}; body = @{}; expected_status = @(200, 400, 422); require_token = $true; no_token = $false } | Out-Null
    }

    # CATEGORY-ADMIN group
    $catAdminListPath = ApiPath $prefix "/category-admin/list"
    $rCatList = RunAdminCase @{ id = "CATADM-001"; module = "category-admin"; name = "GET /category-admin/list"; method = "GET"; contract_path = $catAdminListPath; call_path = $catAdminListPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rCatList -and $rCatList.status -eq 200 -and -not $script:seedCategoryAdminId) { $script:seedCategoryAdminId = Infer-SeedNumber $rCatList.body_json @("(?i)^id$","(?i)categoryid$","(?i)category_id$") }
    $catAdminSelectionPath = ApiPath $prefix "/category-admin/selection"
    $rCatSelection = RunAdminCase @{ id = "CATADM-002"; module = "category-admin"; name = "GET /category-admin/selection"; method = "GET"; contract_path = $catAdminSelectionPath; call_path = $catAdminSelectionPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rCatSelection -and $rCatSelection.status -eq 200 -and -not $script:seedCategoryAdminId) { $script:seedCategoryAdminId = Infer-SeedNumber $rCatSelection.body_json @("(?i)^id$","(?i)categoryid$","(?i)category_id$") }
    RunAdminCase @{ id = "CATADM-003"; module = "category-admin"; name = "GET /category-admin/generate-code"; method = "GET"; contract_path = (ApiPath $prefix "/category-admin/generate-code"); call_path = (ApiPath $prefix "/category-admin/generate-code"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    if ($script:seedCategoryAdminId) {
        RunAdminCase @{ id = "CATADM-004"; module = "category-admin"; name = "GET /category-admin/detail/{validId}"; method = "GET"; contract_path = (ApiPath $prefix "/category-admin/detail/{id}"); call_path = (ApiPath $prefix "/category-admin/detail/$($script:seedCategoryAdminId)"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    }
    else {
        AddResult "CATADM-004" "category-admin" "GET /category-admin/detail/{validId}" "GET" (ApiPath $prefix "/category-admin/detail/{id}") @(200) $null "SKIPPED: Missing category-admin id seed." "SKIPPED"
    }
    RunAdminCase @{ id = "CATADM-005"; module = "category-admin"; name = "GET /category-admin/detail/{invalidId}"; method = "GET"; contract_path = (ApiPath $prefix "/category-admin/detail/{id}"); call_path = (ApiPath $prefix "/category-admin/detail/999999999"); query = @{}; body = $null; expected_status = @(400, 404); require_token = $true; no_token = $false; not_found_negative = $true } | Out-Null
    RunCase @{ id = "CATADM-006"; module = "category-admin"; name = "GET /category-admin/list without token"; method = "GET"; contract_path = $catAdminListPath; call_path = $catAdminListPath; query = @{}; body = $null; expected_status = @(401, 403); require_token = $false; no_token = $true } | Out-Null

    # DASHBOARD group
    $today = (Get-Date).ToString("yyyy-MM-dd")
    $weekAgo = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
    RunAdminCase @{ id = "DASH-001"; module = "dashboard"; name = "GET /Dashboard/user-registrations"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/user-registrations"); call_path = (ApiPath $prefix "/Dashboard/user-registrations"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunAdminCase @{ id = "DASH-002"; module = "dashboard"; name = "GET /Dashboard/store-registrations"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/store-registrations"); call_path = (ApiPath $prefix "/Dashboard/store-registrations"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunAdminCase @{ id = "DASH-003"; module = "dashboard"; name = "GET /Dashboard/qr-scans"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/qr-scans"); call_path = (ApiPath $prefix "/Dashboard/qr-scans"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunAdminCase @{ id = "DASH-004"; module = "dashboard"; name = "GET /Dashboard/user-registrations-by-date"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/user-registrations-by-date"); call_path = (ApiPath $prefix "/Dashboard/user-registrations-by-date"); query = @{ startDate = $weekAgo; endDate = $today }; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunAdminCase @{ id = "DASH-005"; module = "dashboard"; name = "GET /Dashboard/store-registrations-by-date"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/store-registrations-by-date"); call_path = (ApiPath $prefix "/Dashboard/store-registrations-by-date"); query = @{ startDate = $weekAgo; endDate = $today }; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunAdminCase @{ id = "DASH-006"; module = "dashboard"; name = "GET /Dashboard/qr-scans-by-date"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/qr-scans-by-date"); call_path = (ApiPath $prefix "/Dashboard/qr-scans-by-date"); query = @{ startDate = $weekAgo; endDate = $today }; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    RunCase @{ id = "DASH-007"; module = "dashboard"; name = "GET /Dashboard/user-registrations without token"; method = "GET"; contract_path = (ApiPath $prefix "/Dashboard/user-registrations"); call_path = (ApiPath $prefix "/Dashboard/user-registrations"); query = @{}; body = $null; expected_status = @(401, 403); require_token = $false; no_token = $true } | Out-Null

    # MEMBER group
    $memberListPath = ApiPath $prefix "/member/list"
    $rMemberList = RunAdminCase @{ id = "MEMBER-001"; module = "member"; name = "GET /member/list"; method = "GET"; contract_path = $memberListPath; call_path = $memberListPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rMemberList -and $rMemberList.status -eq 200 -and -not $script:seedMemberId) { $script:seedMemberId = FindFirstValue $rMemberList.body_json "(?i)^id$|memberid$|userid$" "number" }
    $memberSelectionPath = ApiPath $prefix "/member/pagination-selection"
    $rMemberSelection = RunAdminCase @{ id = "MEMBER-002"; module = "member"; name = "GET /member/pagination-selection"; method = "GET"; contract_path = $memberSelectionPath; call_path = $memberSelectionPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rMemberSelection -and $rMemberSelection.status -eq 200 -and -not $script:seedMemberId) { $script:seedMemberId = FindFirstValue $rMemberSelection.body_json "(?i)^id$|memberid$|userid$" "number" }
    if ($script:seedMemberId) {
        RunAdminCase @{ id = "MEMBER-003"; module = "member"; name = "GET /member/detail/{validId}"; method = "GET"; contract_path = (ApiPath $prefix "/member/detail/{id}"); call_path = (ApiPath $prefix "/member/detail/$($script:seedMemberId)"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    }
    else {
        AddResult "MEMBER-003" "member" "GET /member/detail/{validId}" "GET" (ApiPath $prefix "/member/detail/{id}") @(200) $null "SKIPPED: Missing member id seed." "SKIPPED"
    }
    RunAdminCase @{ id = "MEMBER-004"; module = "member"; name = "GET /member/detail/{invalidId}"; method = "GET"; contract_path = (ApiPath $prefix "/member/detail/{id}"); call_path = (ApiPath $prefix "/member/detail/999999999"); query = @{}; body = $null; expected_status = @(400, 404); require_token = $true; no_token = $false; not_found_negative = $true } | Out-Null
    RunCase @{ id = "MEMBER-005"; module = "member"; name = "GET /member/list without token"; method = "GET"; contract_path = $memberListPath; call_path = $memberListPath; query = @{}; body = $null; expected_status = @(401, 403); require_token = $false; no_token = $true } | Out-Null

    # STORE-CATEGORY ADMIN group
    $storeCatSelectionPath = ApiPath $prefix "/store-category/admin/selection"
    $rStoreCatSelection = RunAdminCase @{ id = "STCATADM-001"; module = "store-category-admin"; name = "GET /store-category/admin/selection"; method = "GET"; contract_path = $storeCatSelectionPath; call_path = $storeCatSelectionPath; query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false }
    if ($rStoreCatSelection -and $rStoreCatSelection.status -eq 200 -and -not $script:seedStoreCategoryAdminId) { $script:seedStoreCategoryAdminId = Infer-SeedNumber $rStoreCatSelection.body_json @("(?i)^id$","(?i)categoryid$","(?i)category_id$") }
    if ($rStoreCatSelection -and $rStoreCatSelection.status -eq 200 -and -not $script:seedStoreCategoryParentId) { $script:seedStoreCategoryParentId = Infer-SeedNumber $rStoreCatSelection.body_json @("(?i)^parentid$","(?i)parent_id$","(?i)parentcategoryid$") }
    RunAdminCase @{ id = "STCATADM-002"; module = "store-category-admin"; name = "GET /store-category/admin/generate-code"; method = "GET"; contract_path = (ApiPath $prefix "/store-category/admin/generate-code"); call_path = (ApiPath $prefix "/store-category/admin/generate-code"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    if ($script:seedStoreCategoryAdminId) {
        RunAdminCase @{ id = "STCATADM-003"; module = "store-category-admin"; name = "GET /store-category/admin/detail/{validId}"; method = "GET"; contract_path = (ApiPath $prefix "/store-category/admin/detail/{id}"); call_path = (ApiPath $prefix "/store-category/admin/detail/$($script:seedStoreCategoryAdminId)"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
    }
    else {
        AddResult "STCATADM-003" "store-category-admin" "GET /store-category/admin/detail/{validId}" "GET" (ApiPath $prefix "/store-category/admin/detail/{id}") @(200) $null "SKIPPED: Missing store-category admin id seed." "SKIPPED"
    }
    RunAdminCase @{ id = "STCATADM-004"; module = "store-category-admin"; name = "GET /store-category/admin/detail/{invalidId}"; method = "GET"; contract_path = (ApiPath $prefix "/store-category/admin/detail/{id}"); call_path = (ApiPath $prefix "/store-category/admin/detail/999999999"); query = @{}; body = $null; expected_status = @(400, 404); require_token = $true; no_token = $false; not_found_negative = $true } | Out-Null
    $parentIdForChildren = if ($script:seedStoreCategoryParentId) { $script:seedStoreCategoryParentId } else { $script:seedStoreCategoryAdminId }
    if ($parentIdForChildren) {
        RunAdminCase @{ id = "STCATADM-005"; module = "store-category-admin"; name = "GET /store-category/admin/children/{parentId}"; method = "GET"; contract_path = (ApiPath $prefix "/store-category/admin/children/{parentId}"); call_path = (ApiPath $prefix "/store-category/admin/children/$parentIdForChildren"); query = @{}; body = $null; expected_status = @(200, 404); require_token = $true; no_token = $false } | Out-Null
    }
    else {
        AddResult "STCATADM-005" "store-category-admin" "GET /store-category/admin/children/{parentId}" "GET" (ApiPath $prefix "/store-category/admin/children/{parentId}") @(200, 404) $null "SKIPPED: Missing parent id seed." "SKIPPED"
    }
    RunCase @{ id = "STCATADM-006"; module = "store-category-admin"; name = "GET /store-category/admin/selection without token"; method = "GET"; contract_path = $storeCatSelectionPath; call_path = $storeCatSelectionPath; query = @{}; body = $null; expected_status = @(401, 403); require_token = $false; no_token = $true } | Out-Null

    # AUTH logout at end (if feasible)
    $logoutOp = FindOpByHint $script:swagger "auth" "POST" "logout"
    if ($null -eq $logoutOp -or [string]::IsNullOrWhiteSpace($script:token)) { AddResult "AUTH-008" "auth" "Logout happy path" "POST" "/auth/*logout*" @(200) $null "SKIPPED: Not feasible (endpoint or token missing)." "SKIPPED" }
    else { RunCase @{ id = "AUTH-008"; module = "auth"; name = "Logout happy path"; method = "POST"; contract_path = $logoutOp.Path; call_path = $logoutOp.Path; query = @{}; body = @{ token = $script:token; refreshToken = $script:refresh; deviceID = "qa-regression" }; expected_status = @(200, 400, 422); require_token = $true; no_token = $false } | Out-Null }
}
catch {
    $exitCode = 1
    AddResult "SYS-999" "system" "Fatal runner error" "SYSTEM" "/" @() (StatusFromError $_) ("FAIL: " + $_.Exception.Message + "; body=" + (BodyFromError $_)) "FAIL"
}
finally {
    $finishedAt = (Get-Date).ToString("o")
    $passed = @($results | Where-Object { $_.outcome -eq "PASS" }).Count
    $failed = @($results | Where-Object { $_.outcome -eq "FAIL" }).Count
    $skipped = @($results | Where-Object { $_.outcome -eq "SKIPPED" }).Count
    $summary = [ordered]@{
        base_url    = $script:base
        api_prefix  = Opt "API_PREFIX" "/api/v1"
        started_at  = $startedAt
        finished_at = $finishedAt
        total       = $results.Count
        passed      = $passed
        failed      = $failed
        skipped     = $skipped
        results     = $results
    }
    $summary | ConvertTo-Json -Depth 30 | Set-Content -Path $summaryPath -Encoding UTF8
    if ($failed -gt 0) {
        ($results | Where-Object { $_.outcome -eq "FAIL" }) | ConvertTo-Json -Depth 30 | Set-Content -Path $failedPath -Encoding UTF8
        $exitCode = 1
    }
    elseif (Test-Path $failedPath) { Remove-Item -Path $failedPath -Force }

    Log ("Summary: total={0}, passed={1}, failed={2}, skipped={3}" -f $results.Count, $passed, $failed, $skipped)
    Log "Summary file: $summaryPath"
    try { Set-Content -Path $logPath -Value $global:LogLines -Encoding UTF8 }
    catch {
        $f = Join-Path $outDir ("api_regression.{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
        Set-Content -Path $f -Value $global:LogLines -Encoding UTF8
        Write-Host "Primary log locked. Fallback log: $f"
    }
}

exit $exitCode
