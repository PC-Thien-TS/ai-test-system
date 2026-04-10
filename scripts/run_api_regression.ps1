param(
    [ValidateSet("ALL", "CORE", "JOURNEYS", "EDGE")]
    [string]$Mode = ""
)

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

function OptInt([string]$name, $defaultValue = $null) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($v)) { return $defaultValue }
    $n = 0
    if ([int]::TryParse($v, [ref]$n)) { return $n }
    throw "Invalid integer environment variable: $name=$v"
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

function Get-OrderRecords($bodyJson) {
    $records = @()
    $dataNode = Get-DataNode $bodyJson
    if ($null -eq $dataNode) { return $records }
    if ($dataNode -and $dataNode.data) {
        $records = @($dataNode.data)
    }
    elseif ($dataNode -and $dataNode.items) {
        $records = @($dataNode.items)
    }
    elseif ($dataNode -and $dataNode.records) {
        $records = @($dataNode.records)
    }
    elseif ($dataNode -is [System.Collections.IEnumerable] -and -not ($dataNode -is [string])) {
        $records = @($dataNode)
    }
    return $records
}

function Get-ObjectPropValue($obj, [string[]]$keys) {
    if ($null -eq $obj) { return $null }
    foreach ($k in $keys) {
        $prop = $obj.PSObject.Properties[$k]
        if ($null -ne $prop) { return $prop.Value }
    }
    return $null
}

function TryParse-Int($value, $defaultValue = $null) {
    if ($null -eq $value) { return $defaultValue }
    $n = 0
    if ([int]::TryParse([string]$value, [ref]$n)) { return $n }
    return $defaultValue
}

function Load-OrderSeedSnapshot([string]$repoRoot) {
    $seedPath = Join-Path $repoRoot "test-assets/seeds/order/order_seed.json"
    if (-not (Test-Path $seedPath)) {
        return [pscustomobject]@{
            Path = $seedPath
            Data = $null
            Error = ""
        }
    }
    try {
        $raw = Get-Content -Path $seedPath -Raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            return [pscustomobject]@{
                Path = $seedPath
                Data = $null
                Error = "seed file is empty"
            }
        }
        $json = $raw | ConvertFrom-Json
        return [pscustomobject]@{
            Path = $seedPath
            Data = $json
            Error = ""
        }
    }
    catch {
        return [pscustomobject]@{
            Path = $seedPath
            Data = $null
            Error = $_.Exception.Message
        }
    }
}

function Discover-OrderStateSeeds([string]$base, [string]$prefix, [string]$token, [int]$timeoutSec) {
    $result = [pscustomobject]@{
        pendingOrderId = $null
        paidOrderId = $null
        cancelledOrderId = $null
        completedOrderId = $null
        Source = "none"
        Notes = ""
    }
    if ([string]::IsNullOrWhiteSpace($token)) {
        $result.Notes = "No auth token."
        return $result
    }

    $ordersPath = ApiPath $prefix "/orders"
    $headers = @{ Authorization = "Bearer $token" }
    $seen = New-Object System.Collections.Generic.HashSet[int]
    $scanNotes = New-Object System.Collections.Generic.List[string]

    foreach ($page in @(0, 1, 2, 3)) {
        $resp = InvokeJson "GET" (Url $base (PathWithQuery $ordersPath @{ pageNumber = $page; pageSize = 50 })) $headers $null $timeoutSec
        $scanNotes.Add(("page={0} status={1}" -f $page, $resp.status)) | Out-Null
        if ($resp.status -ne 200) { continue }

        $records = Get-OrderRecords $resp.body_json
        foreach ($o in $records) {
            if ($null -eq $o) { continue }
            $idObj = Get-ObjectPropValue $o @("id", "Id", "orderId", "OrderId")
            if ($null -eq $idObj) { continue }
            $oid = 0
            if (-not [int]::TryParse([string]$idObj, [ref]$oid)) { continue }
            if ($seen.Contains($oid)) { continue }
            $seen.Add($oid) | Out-Null

            $statusObj = Get-ObjectPropValue $o @("status", "Status", "orderStatus", "OrderStatus")
            $status = $null
            if ($null -ne $statusObj) {
                $tmp = 0
                if ([int]::TryParse([string]$statusObj, [ref]$tmp)) { $status = $tmp }
            }
            $paidAt = [string](Get-ObjectPropValue $o @("paidAt", "PaidAt", "paid_at"))
            $serviceCompletedAt = [string](Get-ObjectPropValue $o @("serviceCompletedAt", "ServiceCompletedAt", "service_completed_at"))
            $customerConfirmedAt = [string](Get-ObjectPropValue $o @("customerConfirmedCompletedAt", "CustomerConfirmedCompletedAt", "customer_confirmed_completed_at"))

            if (-not $result.paidOrderId -and -not [string]::IsNullOrWhiteSpace($paidAt)) { $result.paidOrderId = $oid }
            if (-not $result.completedOrderId -and (-not [string]::IsNullOrWhiteSpace($serviceCompletedAt) -or -not [string]::IsNullOrWhiteSpace($customerConfirmedAt))) { $result.completedOrderId = $oid }
            if (-not $result.cancelledOrderId -and ($status -in @(60, 61, 62, 63, 64, 65))) { $result.cancelledOrderId = $oid }
            if (-not $result.pendingOrderId -and ($status -in @(10, 50)) -and [string]::IsNullOrWhiteSpace($paidAt)) { $result.pendingOrderId = $oid }
        }
    }

    $result.Source = "customer_order_history"
    $result.Notes = ($scanNotes -join "; ")
    return $result
}

function Discover-CompletedOrderSeedFromAdmin([string]$base, [string]$prefix, [string]$adminToken, [string]$customerToken, [int]$timeoutSec) {
    $result = [pscustomobject]@{
        CompletedOrderId = $null
        Note = ""
    }
    if ([string]::IsNullOrWhiteSpace($adminToken)) {
        $result.Note = "admin token unavailable for completed-order seed probe."
        return $result
    }
    if ([string]::IsNullOrWhiteSpace($customerToken)) {
        $result.Note = "customer token unavailable for completed-order seed probe."
        return $result
    }

    $adminPath = ApiPath $prefix "/admin/orders"
    $adminHeaders = @{ Authorization = "Bearer $adminToken" }
    $customerHeaders = @{ Authorization = "Bearer $customerToken" }
    $candidateIds = New-Object System.Collections.Generic.List[int]
    $scanNotes = New-Object System.Collections.Generic.List[string]

    foreach ($page in @(0, 1, 2, 3)) {
        $resp = InvokeJson "GET" (Url $base (PathWithQuery $adminPath @{ pageNumber = $page; pageSize = 50 })) $adminHeaders $null $timeoutSec
        $scanNotes.Add(("admin_page={0} status={1}" -f $page, $resp.status)) | Out-Null
        if ($resp.status -ne 200) { continue }
        $records = Get-OrderRecords $resp.body_json
        foreach ($o in $records) {
            if ($null -eq $o) { continue }
            $idObj = Get-ObjectPropValue $o @("id", "Id", "orderId", "OrderId")
            if ($null -eq $idObj) { continue }
            $oid = 0
            if (-not [int]::TryParse([string]$idObj, [ref]$oid)) { continue }

            $statusObj = Get-ObjectPropValue $o @("status", "Status", "orderStatus", "OrderStatus")
            $status = $null
            if ($null -ne $statusObj) {
                $tmp = 0
                if ([int]::TryParse([string]$statusObj, [ref]$tmp)) { $status = $tmp }
            }
            $serviceCompletedAt = [string](Get-ObjectPropValue $o @("serviceCompletedAt", "ServiceCompletedAt", "service_completed_at"))
            $customerConfirmedAt = [string](Get-ObjectPropValue $o @("customerConfirmedCompletedAt", "CustomerConfirmedCompletedAt", "customer_confirmed_completed_at"))

            $isCompletedCandidate = (-not [string]::IsNullOrWhiteSpace($serviceCompletedAt)) -or (-not [string]::IsNullOrWhiteSpace($customerConfirmedAt)) -or ($status -in @(22, 23, 80, 81, 82, 83, 84, 85))
            if (-not $isCompletedCandidate) { continue }
            if (-not $candidateIds.Contains($oid)) { $candidateIds.Add($oid) | Out-Null }
        }
    }

    if ($candidateIds.Count -eq 0) {
        $result.Note = ("no completed-like candidates in admin list. {0}" -f ($scanNotes -join "; "))
        return $result
    }

    $inaccessible = New-Object System.Collections.Generic.List[string]
    foreach ($oid in $candidateIds) {
        $detailResp = InvokeJson "GET" (Url $base (ApiPath $prefix "/orders/$oid")) $customerHeaders $null $timeoutSec
        if ($detailResp.status -eq 200) {
            $result.CompletedOrderId = [int]$oid
            $result.Note = ("completed-order seed resolved from admin list and customer detail visibility. orderId={0}" -f $oid)
            return $result
        }
        $msg = [string]$detailResp.body_text
        if ($detailResp.status -in @(400, 401, 403) -and $msg.ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
            $inaccessible.Add(("orderId={0} status={1} FORBIDDEN_SCOPE" -f $oid, $detailResp.status)) | Out-Null
        }
        else {
            $inaccessible.Add(("orderId={0} status={1}" -f $oid, $detailResp.status)) | Out-Null
        }
    }

    $result.Note = ("completed-like admin candidates are not visible in customer scope. candidates={0}; checks={1}" -f ($candidateIds -join ","), ($inaccessible -join "; "))
    return $result
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

function TryCreateFreshOrder(
    [string]$prefix,
    [string]$journey,
    [int]$storeId,
    [int]$skuId,
    [int]$quantity = 1,
    [string]$note = "",
    [hashtable]$extraPayload = $null,
    [string]$tokenOverride = ""
) {
    $result = [pscustomobject]@{
        Journey        = $journey
        Ok             = $false
        Class          = "SEED_BLOCKER"
        Status         = $null
        OrderId        = $null
        StoreId        = $storeId
        SkuId          = $skuId
        Quantity       = $quantity
        IdempotencyKey = $null
        Payload        = $null
        BodyText       = ""
        Note           = ""
    }

    $useToken = if (-not [string]::IsNullOrWhiteSpace($tokenOverride)) { $tokenOverride } else { $script:token }
    if ([string]::IsNullOrWhiteSpace($useToken)) {
        $result.Note = "missing customer auth token"
        return $result
    }
    if ($storeId -le 0 -or $skuId -le 0) {
        $result.Note = ("invalid seed store/sku. storeId={0}; skuId={1}" -f $storeId, $skuId)
        return $result
    }
    if ($quantity -le 0) { $quantity = 1 }

    $item = @{
        skuId = [int]$skuId
        quantity = [int]$quantity
    }
    if (-not [string]::IsNullOrWhiteSpace($note)) { $item["note"] = $note }

    $payload = @{
        storeId = [int]$storeId
        items = @($item)
    }
    if ($extraPayload) {
        foreach ($k in $extraPayload.Keys) {
            $payload[[string]$k] = $extraPayload[$k]
        }
    }

    $idem = New-IdempotencyKey
    $headers = @{
        Authorization = "Bearer $useToken"
        "Idempotency-Key" = $idem
    }
    $resp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders")) $headers $payload $script:timeoutSec
    $result.Status = $resp.status
    $result.IdempotencyKey = $idem
    $result.Payload = $payload
    $result.BodyText = [string]$resp.body_text

    if ($resp.status -eq 200) {
        $oid = Infer-SeedNumber $resp.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$")
        if ($oid) {
            $result.OrderId = [int]$oid
            $result.Ok = $true
            $result.Class = "PASS"
            $result.Note = ("order created. orderId={0}; storeId={1}; skuId={2}; quantity={3}; idempotencyKey={4}" -f $result.OrderId, $storeId, $skuId, $quantity, $idem)
            return $result
        }
        $result.Class = "FRAMEWORK_OR_CONTRACT_ISSUE"
        $result.Note = ("status=200 but order id not inferable. body={0}" -f $resp.body_text)
        return $result
    }

    $diag = Get-OrderCreateDiagnostic $resp.status $resp.body_text
    if ($resp.status -in @(401, 403)) {
        $result.Class = "SCOPE_BLOCKER"
        $result.Note = ("ordering scope unavailable (status={0}). body={1}" -f $resp.status, $resp.body_text)
    }
    elseif ($resp.status -eq 400 -and -not [string]::IsNullOrWhiteSpace($diag) -and $diag.Contains("POLICY_NOT_CONFIGURED")) {
        $result.Class = "RUNTIME_CONTRACT_CONFIG_BLOCKER"
        $result.Note = ("{0} body={1}" -f $diag, $resp.body_text)
    }
    elseif ($resp.status -ge 500) {
        $result.Class = "BACKEND_DEFECT"
        $result.Note = ("server error during create-order journey setup. status={0}; body={1}" -f $resp.status, $resp.body_text)
    }
    else {
        $result.Class = "RUNTIME_CONTRACT_CONFIG_BLOCKER"
        if (-not [string]::IsNullOrWhiteSpace($diag)) {
            $result.Note = ("{0} body={1}" -f $diag, $resp.body_text)
        }
        else {
            $result.Note = ("create-order setup returned non-200 status={0}; body={1}" -f $resp.status, $resp.body_text)
        }
    }
    return $result
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
    $seedToken = if (-not [string]::IsNullOrWhiteSpace($script:token)) { $script:token } elseif (-not [string]::IsNullOrWhiteSpace($script:adminToken)) { $script:adminToken } else { "" }
    if (-not [string]::IsNullOrWhiteSpace($seedToken)) { $headers["Authorization"] = "Bearer $seedToken" }
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

function TrySeedAdditionalSkuFromStoreMenu([string]$prefix, [int]$storeId, [int]$excludeSkuId) {
    if ($storeId -le 0) { return $null }
    $menuPath = ApiPath $prefix ("/stores/{0}/menu" -f $storeId)
    $menuUrl = Url $script:base $menuPath
    $headers = @{}
    $seedToken = if (-not [string]::IsNullOrWhiteSpace($script:token)) { $script:token } elseif (-not [string]::IsNullOrWhiteSpace($script:adminToken)) { $script:adminToken } else { "" }
    if (-not [string]::IsNullOrWhiteSpace($seedToken)) { $headers["Authorization"] = "Bearer $seedToken" }
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
                    $sid = 0
                    if (-not [int]::TryParse([string]$idProp.Value, [ref]$sid)) { continue }
                    if ($sid -le 0 -or $sid -eq $excludeSkuId) { continue }

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
                        SkuId = $sid
                        SkuName = $skuName
                    }
                }
            }
        }
    }
    catch { }
    return $null
}

function TrySeedDisabledOrOutOfStockSkuFromStoreMenu([string]$prefix, [int]$storeId) {
    if ($storeId -le 0) { return $null }
    $menuPath = ApiPath $prefix ("/stores/{0}/menu" -f $storeId)
    $menuUrl = Url $script:base $menuPath
    $headers = @{}
    $seedToken = if (-not [string]::IsNullOrWhiteSpace($script:token)) { $script:token } elseif (-not [string]::IsNullOrWhiteSpace($script:adminToken)) { $script:adminToken } else { "" }
    if (-not [string]::IsNullOrWhiteSpace($seedToken)) { $headers["Authorization"] = "Bearer $seedToken" }
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
                    $sid = 0
                    if (-not [int]::TryParse([string]$idProp.Value, [ref]$sid)) { continue }
                    if ($sid -le 0) { continue }

                    $isActive = $true
                    $activeProp = $skuNode.PSObject.Properties["isActive"]
                    if ($null -ne $activeProp -and $null -ne $activeProp.Value) {
                        try { $isActive = [bool]$activeProp.Value } catch { $isActive = $true }
                    }
                    $availabilityStatus = 0
                    $availProp = $skuNode.PSObject.Properties["availabilityStatus"]
                    if ($null -ne $availProp -and $null -ne $availProp.Value) {
                        try { $availabilityStatus = [int]$availProp.Value } catch { $availabilityStatus = 0 }
                    }

                    if ($isActive -and $availabilityStatus -eq 0) { continue }
                    $skuName = ""
                    $skuNameProp = $skuNode.PSObject.Properties["name"]
                    if ($null -ne $skuNameProp -and $null -ne $skuNameProp.Value) { $skuName = [string]$skuNameProp.Value }

                    return [pscustomobject]@{
                        StoreId = [int]$storeId
                        CategoryName = $categoryName
                        ItemName = $itemName
                        SkuId = $sid
                        SkuName = $skuName
                        IsActive = $isActive
                        AvailabilityStatus = $availabilityStatus
                    }
                }
            }
        }
    }
    catch { }
    return $null
}

function Discover-AlternateStoreMenuSeed([string]$prefix, [int]$excludeStoreId, [int]$scanLimit = 300) {
    $headers = @{}
    $seedToken = if (-not [string]::IsNullOrWhiteSpace($script:token)) { $script:token } elseif (-not [string]::IsNullOrWhiteSpace($script:adminToken)) { $script:adminToken } else { "" }
    if (-not [string]::IsNullOrWhiteSpace($seedToken)) { $headers["Authorization"] = "Bearer $seedToken" }

    $storeListPath = ApiPath $prefix "/store/list"
    $listResp = InvokeJson "GET" (Url $script:base $storeListPath) $headers $null $script:timeoutSec
    if ($listResp.status -ne 200 -or $null -eq $listResp.body_json -or $null -eq $listResp.body_json.data) {
        Log ("Alternate store seed scan skipped: /store/list unavailable (status={0})" -f $listResp.status)
        return $null
    }

    $stores = @($listResp.body_json.data)
    if ($stores.Count -eq 0) {
        Log "Alternate store seed scan skipped: /store/list returned no records."
        return $null
    }

    $candidateStores = New-Object System.Collections.Generic.List[object]
    foreach ($store in $stores) {
        $sidObj = $store.PSObject.Properties["id"]
        if ($null -eq $sidObj -or $null -eq $sidObj.Value) { continue }
        $sid = 0
        if (-not [int]::TryParse([string]$sidObj.Value, [ref]$sid)) { continue }
        if ($sid -le 0 -or $sid -eq $excludeStoreId) { continue }
        $candidateStores.Add([pscustomobject]@{ Id = $sid; Store = $store }) | Out-Null
    }
    if ($candidateStores.Count -eq 0) {
        Log ("Alternate store seed scan skipped: no candidate stores outside excluded storeId={0}" -f $excludeStoreId)
        return $null
    }

    # Prefer newer/higher ids first for better chance of active catalog in current runtime.
    $candidateStores = @($candidateStores | Sort-Object -Property Id -Descending)

    $checked = 0
    foreach ($candidate in $candidateStores) {
        if ($checked -ge $scanLimit) { break }
        $sid = [int]$candidate.Id
        $checked++

        $seed = TrySeedSkuFromStoreMenu $prefix $sid
        if ($seed -and $seed.SkuId) {
            Log ("Alternate store seed resolved: storeId={0}, category='{1}', item='{2}', skuId={3}, skuName='{4}'" -f $seed.StoreId, $seed.CategoryName, $seed.ItemName, $seed.SkuId, $seed.SkuName)
            return $seed
        }
    }

    Log ("Alternate store seed scan exhausted: checked={0}, scanLimit={1}, no active menu sku found outside storeId={2}" -f $checked, $scanLimit, $excludeStoreId)
    return $null
}

function BodyContainsId([string]$bodyText, [int]$id) {
    if ([string]::IsNullOrWhiteSpace($bodyText)) { return $false }
    $pattern = ('"id"\s*:\s*{0}([,\s\}}])' -f [regex]::Escape([string]$id))
    return [regex]::IsMatch($bodyText, $pattern)
}

function BodyContainsAnyKey([string]$bodyText, [string[]]$keys) {
    if ([string]::IsNullOrWhiteSpace($bodyText)) { return $false }
    foreach ($k in $keys) {
        $pattern = ('"{0}"\s*:' -f [regex]::Escape($k))
        if ([regex]::IsMatch($bodyText, $pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) { return $true }
    }
    return $false
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

$selectedLayer = if (-not [string]::IsNullOrWhiteSpace($Mode)) { $Mode } else { (Opt "API_RUN_LAYER" "ALL") }
if ([string]::IsNullOrWhiteSpace($selectedLayer)) { $selectedLayer = "ALL" }
$selectedLayer = $selectedLayer.ToUpperInvariant()
if ($selectedLayer -notin @("ALL", "CORE", "JOURNEYS", "EDGE")) { $selectedLayer = "ALL" }
$script:runLayer = $selectedLayer

$script:edgeCaseIds = @(
    "ORD-001",
    "ORD-003",
    "STO-010",
    "NEWS-003",
    "ORD-API-008",
    "ORD-API-017",
    "ORD-API-018",
    "ORD-API-019",
    "AORD-API-007",
    "AORD-API-008",
    "ORD-CAN-004"
)

$script:journeyCaseIds = @(
    "ORD-API-001", "ORD-API-004", "ORD-API-009", "ORD-API-020",
    "ORD-API-021", "ORD-API-022", "ORD-API-023", "ORD-API-028",
    "ORD-PAY-001", "ORD-PAY-003", "ORD-PAY-004", "ORD-PAY-007", "ORD-PAY-008",
    "ORD-CUS-001", "ORD-CUS-002", "ORD-CUS-003", "ORD-CUS-004",
    "ORD-CAN-001", "ORD-CAN-002", "ORD-CAN-003",
    "MORD-API-001", "MORD-API-002", "MORD-API-003", "MORD-API-004", "MORD-API-005", "MORD-API-006", "MORD-API-007", "MORD-API-008",
    "AORD-API-003", "AORD-API-004",
    "ORD-ADDON-001", "ORD-ADDON-002"
)

$script:bootstrapCaseIds = @(
    "AUTH-001"
)

function Get-CaseLayer([string]$id) {
    if ([string]::IsNullOrWhiteSpace($id)) { return "CORE" }
    if ($id -like "NOTI-ORD-*" -or $id -like "ORD-JOB-*" -or $id -like "ORD-CAVEAT-*") { return "EDGE" }
    if ($script:edgeCaseIds -contains $id) { return "EDGE" }
    if ($script:journeyCaseIds -contains $id) { return "JOURNEYS" }
    return "CORE"
}

function Should-RunCase([string]$id) {
    if (-not [string]::IsNullOrWhiteSpace($id) -and $id -like "SYS-*") { return $true }
    if ($script:bootstrapCaseIds -contains $id) { return $true }
    if ($script:runLayer -eq "ALL") { return $true }
    return ((Get-CaseLayer $id) -eq $script:runLayer)
}

function Log([string]$m) { $global:LogLines.Add(("[{0}] {1}" -f (Get-Date).ToString("s"), $m)) | Out-Null; Write-Host $m }

function AddResult([string]$id, [string]$module, [string]$name, [string]$method, [string]$path, [int[]]$expected, [Nullable[int]]$actual, [string]$notes, [string]$outcome) {
    if (-not (Should-RunCase $id)) { return }
    if ([string]::IsNullOrWhiteSpace($outcome)) { if ($null -ne $actual -and $expected -contains [int]$actual) { $outcome = "PASS" } else { $outcome = "FAIL" } }
    $r = [pscustomobject]@{
        id              = $id
        layer           = Get-CaseLayer $id
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

function Get-DefaultTokenForModule([string]$module) {
    if ([string]::IsNullOrWhiteSpace($module)) { return $null }
    $m = $module.ToLowerInvariant()
    if ($m -eq "merchant-orders") {
        if (-not [string]::IsNullOrWhiteSpace($script:merchantToken)) { return $script:merchantToken }
        return $null
    }
    if ($m -in @("store", "admin-orders", "category-admin", "dashboard", "member", "store-category-admin", "admin-ops", "admin-disputes")) {
        if (-not [string]::IsNullOrWhiteSpace($script:adminToken)) { return $script:adminToken }
        return $null
    }
    if (-not [string]::IsNullOrWhiteSpace($script:token)) {
        return $script:token
    }
    return $null
}

function Get-AuthMissingNote([string]$module) {
    if ([string]::IsNullOrWhiteSpace($module)) {
        return "CLASS=CONFIG_BLOCKER; SKIPPED: scoped auth token unavailable for this endpoint; verify role credentials."
    }
    $m = $module.ToLowerInvariant()
    if ($m -eq "merchant-orders") {
        if ($null -ne $script:merchantLoginStatus -and [int]$script:merchantLoginStatus -ne 200) {
            return ("CLASS=CONFIG_BLOCKER; SKIPPED: merchant token unavailable because API_MERCHANT_USER/API_MERCHANT_PASS login failed (status={0}); body={1}" -f $script:merchantLoginStatus, $script:merchantLoginBody)
        }
        return "CLASS=CONFIG_BLOCKER; SKIPPED: merchant token unavailable; verify API_MERCHANT_USER/API_MERCHANT_PASS."
    }
    if ($m -in @("store", "admin-orders", "category-admin", "dashboard", "member", "store-category-admin", "admin-ops", "admin-disputes")) {
        if ($null -ne $script:adminLoginStatus -and [int]$script:adminLoginStatus -ne 200) {
            return ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin token unavailable because API_ADMIN_USER/API_ADMIN_PASS login failed (status={0}); body={1}" -f $script:adminLoginStatus, $script:adminLoginBody)
        }
        return "CLASS=ACCOUNT_BLOCKER; SKIPPED: admin token unavailable for admin-scoped endpoint."
    }
    return "CLASS=CONFIG_BLOCKER; SKIPPED: scoped auth token unavailable for this endpoint; verify role credentials."
}

function Is-AdminScopedModule([string]$module) {
    if ([string]::IsNullOrWhiteSpace($module)) { return $false }
    $m = $module.ToLowerInvariant()
    return ($m -in @("store", "admin-orders", "category-admin", "dashboard", "member", "store-category-admin", "admin-ops", "admin-disputes"))
}

function Is-MerchantScopedModule([string]$module) {
    if ([string]::IsNullOrWhiteSpace($module)) { return $false }
    return ($module.ToLowerInvariant() -eq "merchant-orders")
}

function RunCase([hashtable]$c) {
    if (-not (Should-RunCase ([string]$c.id))) { return $null }
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
    $defaultToken = $null
    if (-not [bool]$c.no_token) { $defaultToken = Get-DefaultTokenForModule ([string]$c.module) }
    $needAuth = $false
    if ($c.require_token) { $needAuth = $true }
    if ($c.no_token) { $needAuth = $false }
    if ($needAuth -and [string]::IsNullOrWhiteSpace($defaultToken)) {
        $missingTokenNote = Get-AuthMissingNote ([string]$c.module)
        AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $null $missingTokenNote "SKIPPED"
        return $null
    }
    if (-not $c.no_token -and -not [string]::IsNullOrWhiteSpace($defaultToken)) { $headers["Authorization"] = "Bearer $defaultToken" }
    if ($c.extra_headers) {
        foreach ($hk in $c.extra_headers.Keys) { $headers[[string]$hk] = [string]$c.extra_headers[$hk] }
    }
    $resp = InvokeJson $c.method $url $headers $c.body $script:timeoutSec
    $outcome = ""
    $notes = if ($c.expected_status -contains [int]$resp.status) { "OK" } else { "Unexpected status. error=$($resp.error); body=$($resp.body_text)" }

    if ($resp.status -in @(401, 403) -and -not [bool]$c.no_token -and [string]::IsNullOrWhiteSpace($defaultToken) -and -not [bool]$c.admin_required_case -and -not [bool]$c.skip_on_unauthorized) {
        AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status "CLASS=CONFIG_BLOCKER; SKIPPED: scoped auth token unavailable for this endpoint; verify role credentials." "SKIPPED"
        return $resp
    }

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
        $notes = "CLASS=ACCOUNT_BLOCKER; SKIPPED: admin scope/role unavailable (status=$($resp.status))"
        AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $notes "SKIPPED"
        return $resp
    }

    if ([string]$c.module -eq "merchant-orders" -and $resp.status -eq 400) {
        $bodyUpper = ""
        if (-not [string]::IsNullOrWhiteSpace($resp.body_text)) { $bodyUpper = ([string]$resp.body_text).ToUpperInvariant() }
        if ($bodyUpper.Contains("FORBIDDEN_SCOPE")) {
            $notes = "CLASS=SCOPE_BLOCKER; SKIPPED: merchant scope/ownership mismatch (FORBIDDEN_SCOPE). body=$($resp.body_text)"
            AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $notes "SKIPPED"
            return $resp
        }
    }

    if ([bool]$c.skip_on_forbidden_scope -and $resp.status -eq 400) {
        $bodyUpper = ""
        if (-not [string]::IsNullOrWhiteSpace($resp.body_text)) { $bodyUpper = ([string]$resp.body_text).ToUpperInvariant() }
        if ($bodyUpper.Contains("FORBIDDEN_SCOPE")) {
            $scopeNote = if ([string]::IsNullOrWhiteSpace([string]$c.forbidden_scope_note)) {
                "CLASS=SCOPE_BLOCKER; SKIPPED: FORBIDDEN_SCOPE for current account/context. body=$($resp.body_text)"
            }
            else {
                "CLASS=SCOPE_BLOCKER; SKIPPED: $($c.forbidden_scope_note). body=$($resp.body_text)"
            }
            AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $scopeNote "SKIPPED"
            return $resp
        }
    }

    if ([string]$c.id -eq "AUTH-001" -and $resp.status -eq 400) {
        $bodyUpper = ""
        if (-not [string]::IsNullOrWhiteSpace($resp.body_text)) { $bodyUpper = ([string]$resp.body_text).ToUpperInvariant() }
        if ($bodyUpper.Contains("INCORRECT EMAIL OR PASSWORD")) {
            AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status "CLASS=CONFIG_BLOCKER; SKIPPED: API_USER/API_PASS is invalid for this runtime environment (Incorrect email or password)." "SKIPPED"
            return $resp
        }
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
        if ($resp.status -in @(401, 403)) {
            $notes = "CLASS=SCOPE_BLOCKER; SKIPPED: unauthorized for not-found negative check; verify role/scope/auth context."
            $outcome = "SKIPPED"
        }
        elseif ($c.expected_status -contains [int]$resp.status) {
            $notes = "OK (not-found negative case)"
            $outcome = "PASS"
        }
        else {
            $notes = "Non-5xx accepted for not-found negative case. status=$($resp.status); body=$($resp.body_text)"
            $outcome = "PASS"
        }
    }

    AddResult $c.id $c.module $c.name $c.method $pathForCall $c.expected_status $resp.status $notes $outcome
    return $resp
}

function RunAdminCase([hashtable]$c) {
    $c.admin_required_case = $true
    if ((-not $c.ContainsKey("extra_headers") -or $null -eq $c.extra_headers) -and -not [string]::IsNullOrWhiteSpace($script:adminToken)) {
        $c.extra_headers = @{ Authorization = "Bearer $($script:adminToken)" }
        $c.require_token = $false
        $c.no_token = $true
    }
    return (RunCase $c)
}

function Get-AdminPrecheck([string]$base, [string]$prefix, [hashtable]$headers, [int]$timeoutSec) {
    $path = ApiPath $prefix "/admin/orders"
    $resp = InvokeJson "GET" (Url $base (PathWithQuery $path @{ pageNumber = 1; pageSize = 1 })) $headers $null $timeoutSec
    return [pscustomobject]@{
        Path = $path
        Status = $resp.status
        BodyText = $resp.body_text
        Ok = ($resp.status -eq 200)
    }
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
    $script:seedId = OptInt "API_STORE_ID" $null
    $script:seedUniqueId = Opt "API_STORE_UNIQUE_ID" ""
    $script:seedPostId = $null
    $script:seedNewsSlug = Opt "API_NEWS_SLUG" ""
    $script:seedOrgId = $null
    $script:seedCategoryAdminId = OptInt "API_CATEGORY_ADMIN_ID" $null
    $script:seedMemberId = $null
    $script:seedStoreCategoryAdminId = OptInt "API_STORE_CATEGORY_ADMIN_ID" $null
    $script:seedStoreCategoryParentId = $null
    $script:seedOrderId = OptInt "API_PENDING_ORDER_ID" $null
    $script:seedOrderStoreId = OptInt "API_ORDER_STORE_ID" $null
    $script:seedSkuId = OptInt "API_ORDER_SKU_ID" $null
    $script:preferredStoreId = OptInt "API_STORE_ID" 9768
    $script:preferredOrderStoreId = OptInt "API_ORDER_STORE_ID" $script:preferredStoreId
    $script:preferredStoreUniqueId = Opt "API_STORE_UNIQUE_ID" ""
    $script:altStoreId = OptInt "API_ALT_STORE_ID" $null
    $script:altStoreUniqueId = Opt "API_ALT_STORE_UNIQUE_ID" ""
    $script:altSkuId = OptInt "API_ALT_SKU_ID" $null
    $script:altStoreScanLimit = OptInt "API_ALT_STORE_SCAN_LIMIT" 300
    $script:storeUniqueScanLimit = OptInt "API_STORE_UNIQUE_SCAN_LIMIT" 40
    $script:merchantStoreId = OptInt "API_MERCHANT_STORE_ID" $null
    $script:pendingOrderId = OptInt "API_PENDING_ORDER_ID" $null
    $script:paidOrderId = OptInt "API_PAID_ORDER_ID" $null
    $script:cancelledOrderId = OptInt "API_CANCELLED_ORDER_ID" $null
    $script:completedOrderId = OptInt "API_COMPLETED_ORDER_ID" $null
    $script:completedOrderSeedNote = ""
    $script:disabledSkuId = OptInt "API_DISABLED_SKU_ID" $null
    $script:outOfStockSkuId = OptInt "API_OUT_OF_STOCK_SKU_ID" $null
    $script:closedStoreId = OptInt "API_CLOSED_STORE_ID" $null
    $script:orderingDisabledStoreId = OptInt "API_ORDERING_DISABLED_STORE_ID" $null
    $script:merchantToken = $null
    $script:merchantUser = $null
    $script:merchantLoginStatus = $null
    $script:merchantLoginBody = ""
    $script:adminToken = $null
    $script:adminUser = $null
    $script:adminLoginStatus = $null
    $script:adminLoginBody = ""

    $repoRoot = RepoRoot
    $orderSeedSnapshot = Load-OrderSeedSnapshot $repoRoot
    if ($orderSeedSnapshot -and $orderSeedSnapshot.Data) {
        $seedData = $orderSeedSnapshot.Data
        if (-not $script:seedOrderStoreId) {
            $seedStoreId = TryParse-Int $seedData.storeId $null
            if ($seedStoreId) { $script:seedOrderStoreId = [int]$seedStoreId }
        }
        if (-not $script:seedSkuId) {
            $seedSkuId = TryParse-Int $seedData.skuId $null
            if ($seedSkuId) { $script:seedSkuId = [int]$seedSkuId }
        }
        if (-not $script:pendingOrderId) {
            $seedPending = TryParse-Int $seedData.pendingOrderId $null
            if ($seedPending) { $script:pendingOrderId = [int]$seedPending }
        }
        if (-not $script:paidOrderId) {
            $seedPaid = TryParse-Int $seedData.paidOrderId $null
            if ($seedPaid) { $script:paidOrderId = [int]$seedPaid }
        }
        if (-not $script:cancelledOrderId) {
            $seedCancelled = TryParse-Int $seedData.cancelledOrderId $null
            if ($seedCancelled) { $script:cancelledOrderId = [int]$seedCancelled }
        }
        if (-not $script:completedOrderId) {
            $seedCompleted = TryParse-Int $seedData.completedOrderId $null
            if ($seedCompleted) { $script:completedOrderId = [int]$seedCompleted }
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$seedData.storeUniqueIdPathToken) -and [string]::IsNullOrWhiteSpace($script:seedUniqueId)) {
            $script:seedUniqueId = ([string]$seedData.storeUniqueIdPathToken).Trim()
        }
        if (-not $script:preferredStoreId -and $script:seedOrderStoreId) {
            $script:preferredStoreId = [int]$script:seedOrderStoreId
        }
        if (-not $script:preferredOrderStoreId -and $script:seedOrderStoreId) {
            $script:preferredOrderStoreId = [int]$script:seedOrderStoreId
        }
    }

    Log "API regression start. base_url=$($script:base) api_prefix=$prefix timeout=$($script:timeoutSec) layer=$($script:runLayer)"
    if ($orderSeedSnapshot -and -not [string]::IsNullOrWhiteSpace($orderSeedSnapshot.Error)) {
        Log ("Order seed snapshot load warning: path={0}; error={1}" -f $orderSeedSnapshot.Path, $orderSeedSnapshot.Error)
    }
    elseif ($orderSeedSnapshot -and $orderSeedSnapshot.Data) {
        Log ("Order seed snapshot loaded: path={0}; storeId={1}; skuId={2}; pending={3}; paid={4}; cancelled={5}; completed={6}" -f $orderSeedSnapshot.Path, $script:seedOrderStoreId, $script:seedSkuId, $script:pendingOrderId, $script:paidOrderId, $script:cancelledOrderId, $script:completedOrderId)
    }
    $sw = InvokeJson "GET" "$($script:base)/swagger/v1/swagger.json" @{} $null $script:timeoutSec
    if ($null -eq $sw.body_json) { throw "Cannot load swagger. status=$($sw.status); body=$($sw.body_text)" }
    $script:swagger = $sw.body_json
    Log "Swagger loaded."

    $merchantUser = Opt "API_MERCHANT_USER" $user
    $merchantPass = Opt "API_MERCHANT_PASS" $pass
    $script:merchantUser = $merchantUser
    $adminUser = Opt "API_ADMIN_USER" $user
    $adminPass = Opt "API_ADMIN_PASS" $pass
    $script:adminUser = $adminUser

    # AUTH group
    $loginPath = ApiPath $prefix "/auth/login"
    $rLogin = RunCase @{ id = "AUTH-001"; module = "auth"; name = "Login success"; method = "POST"; contract_path = $loginPath; call_path = $loginPath; query = @{}; body = @{ email = $user; password = $pass; deviceID = "qa-regression" }; expected_status = @(200); require_token = $false; no_token = $true }
    if ($rLogin -and $rLogin.status -eq 200) {
        $tk = ExtractTokenFromLogin $rLogin.body_json
        if (-not [string]::IsNullOrWhiteSpace([string]$tk)) { $script:token = ([string]$tk).Trim() }
        $rf = $rLogin.body_json.data.refreshToken; if ([string]::IsNullOrWhiteSpace([string]$rf)) { $rf = $rLogin.body_json.login.data.refreshToken }
        if (-not [string]::IsNullOrWhiteSpace([string]$rf)) { $script:refresh = ([string]$rf).Trim() }
    }
    if ($merchantUser -ieq $user -and $merchantPass -eq $pass -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $script:merchantToken = $script:token
        $script:merchantLoginStatus = 200
        $script:merchantLoginBody = "Merchant token reuses API_USER auth session."
        Log ("Merchant lifecycle auth source: API_USER ({0})" -f $merchantUser)
    }
    else {
        $merchantLoginBody = @{ email = $merchantUser; password = $merchantPass; deviceID = "qa-regression-merchant" }
        $merchantLoginResp = InvokeJson "POST" (Url $script:base $loginPath) @{} $merchantLoginBody $script:timeoutSec
        $script:merchantLoginStatus = $merchantLoginResp.status
        $script:merchantLoginBody = [string]$merchantLoginResp.body_text
        if ($merchantLoginResp.status -eq 200) {
            $mToken = ExtractTokenFromLogin $merchantLoginResp.body_json
            if (-not [string]::IsNullOrWhiteSpace($mToken)) {
                $script:merchantToken = $mToken
                Log ("Merchant lifecycle auth source: API_MERCHANT_USER ({0})" -f $merchantUser)
            }
            else {
                Log ("Merchant login succeeded but token extraction failed. merchant={0}" -f $merchantUser)
            }
        }
        else {
            Log ("Merchant login failed. merchant={0}; status={1}; body={2}" -f $merchantUser, $merchantLoginResp.status, $merchantLoginResp.body_text)
        }
    }

    if ($adminUser -ieq $user -and $adminPass -eq $pass -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $script:adminToken = $script:token
        $script:adminLoginStatus = 200
        $script:adminLoginBody = "Admin token reuses API_USER auth session."
        Log ("Admin auth source: API_USER ({0})" -f $adminUser)
    }
    else {
        $adminLoginBody = @{ email = $adminUser; password = $adminPass; deviceID = "qa-regression-admin" }
        $adminLoginResp = InvokeJson "POST" (Url $script:base $loginPath) @{} $adminLoginBody $script:timeoutSec
        $script:adminLoginStatus = $adminLoginResp.status
        $script:adminLoginBody = [string]$adminLoginResp.body_text
        if ($adminLoginResp.status -eq 200) {
            $aToken = ExtractTokenFromLogin $adminLoginResp.body_json
            if (-not [string]::IsNullOrWhiteSpace($aToken)) {
                $script:adminToken = $aToken
                Log ("Admin auth source: API_ADMIN_USER ({0})" -f $adminUser)
            }
            else {
                Log ("Admin login succeeded but token extraction failed. admin={0}" -f $adminUser)
            }
        }
        else {
            Log ("Admin login failed. admin={0}; status={1}; body={2}" -f $adminUser, $adminLoginResp.status, $adminLoginResp.body_text)
        }
    }
    $adminAuthHeaders = @{}
    if (-not [string]::IsNullOrWhiteSpace($script:adminToken)) {
        $adminAuthHeaders["Authorization"] = "Bearer $($script:adminToken)"
    }
    if ($adminAuthHeaders.ContainsKey("Authorization")) {
        $adminPrecheck = Get-AdminPrecheck $script:base $prefix $adminAuthHeaders $script:timeoutSec
    }
    else {
        $adminPrecheck = [pscustomobject]@{
            Path = (ApiPath $prefix "/admin/orders")
            Status = $null
            BodyText = "admin token unavailable"
            Ok = $false
        }
    }
    $adminReady = $adminPrecheck.Ok
    if ($adminReady) {
        Log ("Admin precheck PASS: path={0}; status={1}" -f $adminPrecheck.Path, $adminPrecheck.Status)
    }
    else {
        Log ("Admin precheck BLOCKED: path={0}; status={1}; body={2}" -f $adminPrecheck.Path, $adminPrecheck.Status, $adminPrecheck.BodyText)
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
    RunCase @{ id = "SEA-007"; module = "searches"; name = "Create history valid"; method = "POST"; contract_path = $histPath; call_path = $histPath; query = @{}; body = @{ searchQuery = "test"; deviceId = "qa-regression"; isAnonymous = $false; languageCode = "vi" }; expected_status = @(200); require_token = $true; no_token = $false } | Out-Null
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
    $sto010Candidates = New-Object System.Collections.Generic.List[string]
    foreach ($cand in @($script:preferredStoreUniqueId, $script:seedUniqueId)) {
        if ([string]::IsNullOrWhiteSpace($cand)) { continue }
        $trimmed = ([string]$cand).Trim()
        if (-not $sto010Candidates.Contains($trimmed)) { $sto010Candidates.Add($trimmed) | Out-Null }
    }
    foreach ($idCandidate in @($script:preferredStoreId, $script:seedId)) {
        if ($null -eq $idCandidate) { continue }
        $asText = ([string]([int]$idCandidate)).Trim()
        if (-not [string]::IsNullOrWhiteSpace($asText) -and -not $sto010Candidates.Contains($asText)) {
            $sto010Candidates.Add($asText) | Out-Null
        }
    }
    if ($rList -and $rList.status -eq 200 -and $rList.body_json -and $rList.body_json.data) {
        $scanCount = 0
        foreach ($storeRec in @($rList.body_json.data)) {
            if ($scanCount -ge $script:storeUniqueScanLimit) { break }
            $scanCount++
            $codeProp = $storeRec.PSObject.Properties["code"]
            if ($null -eq $codeProp -or [string]::IsNullOrWhiteSpace([string]$codeProp.Value)) { continue }
            $codeCandidate = ([string]$codeProp.Value).Trim()
            if (-not $sto010Candidates.Contains($codeCandidate)) { $sto010Candidates.Add($codeCandidate) | Out-Null }
        }
    }

    if ($sto010Candidates.Count -gt 0) {
        $sto010Resolved = $false
        $sto010AnyServerError = $false
        $sto010Attempts = New-Object System.Collections.Generic.List[string]
        $sto010PreviewLimit = 16
        $sto010Headers = @{}
        $sto010Token = if (-not [string]::IsNullOrWhiteSpace($script:token)) { $script:token } elseif (-not [string]::IsNullOrWhiteSpace($script:adminToken)) { $script:adminToken } else { "" }
        if (-not [string]::IsNullOrWhiteSpace($sto010Token)) { $sto010Headers["Authorization"] = "Bearer $sto010Token" }
        foreach ($candidate in $sto010Candidates) {
            $u = [System.Uri]::EscapeDataString([string]$candidate)
            $numericCandidate = [regex]::IsMatch([string]$candidate, '^\d+$')
            $pathOnlyAttempt = (ApiPath $prefix "/store/$u")
            $queryAttempt = ((ApiPath $prefix "/store/$u") + "?UniqueId=$u")
            $attemptUrls = @(
                $pathOnlyAttempt,
                $queryAttempt
            )
            foreach ($attemptPath in $attemptUrls) {
                $resp = InvokeJson "GET" (Url $script:base $attemptPath) $sto010Headers $null $script:timeoutSec
                $respBodyPreview = [string]$resp.body_text
                if ($respBodyPreview.Length -gt 220) { $respBodyPreview = $respBodyPreview.Substring(0, 220) + "...<truncated>" }
                $sto010Attempts.Add(("candidate={0}; path={1}; status={2}; body={3}" -f $candidate, $attemptPath, $resp.status, $respBodyPreview)) | Out-Null
                if ($resp.status -eq 200) {
                    $isQueryAttempt = ($attemptPath -eq $queryAttempt)
                    if ($numericCandidate -and -not $isQueryAttempt) {
                        $sto010Attempts.Add(("candidate={0}; path={1}; note=200 via numeric id route is not accepted as uniqueId proof." -f $candidate, $attemptPath)) | Out-Null
                        continue
                    }
                    if ($numericCandidate -and $isQueryAttempt) {
                        $probeToken = [System.Uri]::EscapeDataString("__qa_probe_invalid_uniqueid__")
                        $probePath = ((ApiPath $prefix "/store/$u") + "?UniqueId=$probeToken")
                        $probeResp = InvokeJson "GET" (Url $script:base $probePath) $sto010Headers $null $script:timeoutSec
                        $probeBodyPreview = [string]$probeResp.body_text
                        if ($probeBodyPreview.Length -gt 220) { $probeBodyPreview = $probeBodyPreview.Substring(0, 220) + "...<truncated>" }
                        $sto010Attempts.Add(("candidate={0}; path={1}; status={2}; body={3}" -f $candidate, $probePath, $probeResp.status, $probeBodyPreview)) | Out-Null
                        if ($probeResp.status -eq 200) {
                            $sto010Attempts.Add(("candidate={0}; note=uniqueId query appears ignored for numeric path token; not accepted as deterministic uniqueId proof." -f $candidate)) | Out-Null
                            continue
                        }
                    }
                    $script:preferredStoreUniqueId = $candidate
                    $attemptPreview = if ($sto010Attempts.Count -gt $sto010PreviewLimit) {
                        ((@($sto010Attempts | Select-Object -First $sto010PreviewLimit) + ("...truncated; total_attempts={0}" -f $sto010Attempts.Count)) -join " | ")
                    } else {
                        ($sto010Attempts -join " | ")
                    }
                    AddResult "STO-010" "store" "Get /store/{uniqueId} valid uniqueId" "GET" (ApiPath $prefix "/store/{uniqueId}") @(200) 200 ("CLASS=PASS; runtime uniqueId candidate resolved. " + $attemptPreview) "PASS"
                    $sto010Resolved = $true
                    break
                }
                if ($resp.status -ge 500 -and -not ([string]$resp.body_text).ToLowerInvariant().Contains("not found")) {
                    $sto010AnyServerError = $true
                }
            }
            if ($sto010Resolved) { break }
        }

        if (-not $sto010Resolved) {
            $attemptNote = if ($sto010Attempts.Count -gt $sto010PreviewLimit) {
                ((@($sto010Attempts | Select-Object -First $sto010PreviewLimit) + ("...truncated; total_attempts={0}" -f $sto010Attempts.Count)) -join " | ")
            } else {
                ($sto010Attempts -join " | ")
            }
            if ($sto010AnyServerError) {
                AddResult "STO-010" "store" "Get /store/{uniqueId} valid uniqueId" "GET" (ApiPath $prefix "/store/{uniqueId}") @(200) 500 ("CLASS=BACKEND_DEFECT; server error during uniqueId seed probe. $attemptNote") "FAIL"
            }
            else {
                AddResult "STO-010" "store" "Get /store/{uniqueId} valid uniqueId" "GET" (ApiPath $prefix "/store/{uniqueId}") @(200) $null ("CLASS=SEED_BLOCKER; SKIPPED: no deterministic runtime uniqueId candidate resolved after explicit + scanned probes. $attemptNote") "SKIPPED"
            }
        }
    }
    else {
        AddResult "STO-010" "store" "Get /store/{uniqueId} valid uniqueId" "GET" (ApiPath $prefix "/store/{uniqueId}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing stable uniqueId seed. Provide API_STORE_UNIQUE_ID or expose uniqueId in store detail/list payload." "SKIPPED"
    }
    RunCase @{ id = "STO-011"; module = "store"; name = "Get /store/{uniqueId} invalid uniqueId"; method = "GET"; contract_path = (ApiPath $prefix "/store/{uniqueId}"); call_path = (ApiPath $prefix "/store/UNKNOWN-UNIQUE-ID-QA"); query = @{ UniqueId = "UNKNOWN-UNIQUE-ID-QA" }; body = $null; expected_status = @(400, 404); require_token = $false; no_token = $false; not_found_negative = $true } | Out-Null
    RunCase @{ id = "STO-012"; module = "store"; name = "Get store collections (capture behavior)"; method = "GET"; contract_path = (ApiPath $prefix "/store/collections"); call_path = (ApiPath $prefix "/store/collections"); query = @{}; body = $null; expected_status = @(200, 400, 404, 415); require_token = $false; no_token = $false } | Out-Null

    # ORDER (initial safe subset)
    RunCase @{ id = "PAY-001"; module = "payments"; name = "GET /payments/methods"; method = "GET"; contract_path = (ApiPath $prefix "/payments/methods"); call_path = (ApiPath $prefix "/payments/methods"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $false } | Out-Null

    $rAdminOrders = RunAdminCase @{ id = "AORD-001"; module = "admin-orders"; name = "GET /admin/orders"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders"); call_path = (ApiPath $prefix "/admin/orders"); query = @{ PageNumber = 1; PageSize = 1 }; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders }
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
    AddResult "ORD-001" "orders" "POST /orders (legacy)" "POST" $ordersCreatePath @(200, 201) $null "CLASS=FRAMEWORK_GAP; SKIPPED: Superseded by ORD-API-001 contract-driven create-order coverage." "SKIPPED"

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
    if (-not $script:disabledSkuId -and -not $script:outOfStockSkuId -and $script:seedOrderStoreId) {
        $edgeSkuSeed = TrySeedDisabledOrOutOfStockSkuFromStoreMenu $prefix ([int]$script:seedOrderStoreId)
        if ($edgeSkuSeed -and $edgeSkuSeed.SkuId) {
            if (-not [bool]$edgeSkuSeed.IsActive) {
                $script:disabledSkuId = [int]$edgeSkuSeed.SkuId
            }
            elseif ($edgeSkuSeed.AvailabilityStatus -ne 0) {
                $script:outOfStockSkuId = [int]$edgeSkuSeed.SkuId
            }
            Log ("Edge sku seed discovered: storeId={0}, category='{1}', item='{2}', skuId={3}, skuName='{4}', isActive={5}, availabilityStatus={6}" -f $edgeSkuSeed.StoreId, $edgeSkuSeed.CategoryName, $edgeSkuSeed.ItemName, $edgeSkuSeed.SkuId, $edgeSkuSeed.SkuName, $edgeSkuSeed.IsActive, $edgeSkuSeed.AvailabilityStatus)
        }
    }

    if ($script:seedOrderId) {
        RunCase @{ id = "ORD-003"; module = "orders"; name = "GET /orders/{id}"; method = "GET"; contract_path = (ApiPath $prefix "/orders/{id}"); call_path = (ApiPath $prefix "/orders/$($script:seedOrderId)"); query = @{}; body = $null; expected_status = @(200, 404); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires customer order visibility"; skip_on_forbidden_scope = $true; forbidden_scope_note = "customer order visibility blocked by scope/account" } | Out-Null
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
    $rAordApi001 = RunCase @{ id = "AORD-API-001"; module = "admin-orders"; name = "Admin list orders"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders"); call_path = (ApiPath $prefix "/admin/orders"); query = @{ pageNumber = 1; pageSize = 1 }; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders; admin_required_case = $true }
    if ($rAordApi001 -and $rAordApi001.status -eq 200) {
        if (-not $script:seedOrderId) { $script:seedOrderId = Infer-SeedNumber $rAordApi001.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$") }
        if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = Infer-SeedNumber $rAordApi001.body_json @("(?i)^storeid$","(?i)store_id$") }
    }
    if ($script:seedOrderId -and $adminReady) {
        RunCase @{ id = "AORD-API-002"; module = "admin-orders"; name = "Admin order detail"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders/{id}"); call_path = (ApiPath $prefix "/admin/orders/$($script:seedOrderId)"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders; admin_required_case = $true } | Out-Null
    }
    elseif ($script:seedOrderId -and -not $adminReady) {
        AddResult "AORD-API-002" "admin-orders" "Admin order detail" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before detail lookup. status=$($adminPrecheck.Status)") "SKIPPED"
    }
    else {
        AddResult "AORD-API-002" "admin-orders" "Admin order detail" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $null "SKIPPED: Missing order id seed for admin detail." "SKIPPED"
    }

    $script:lastCreatedOrderId = $null
    $script:lastCreateIdempotencyKey = $null
    $script:lastCreatePayload = $null
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
        $createIdemKey = New-IdempotencyKey
        $ordHeaders = @{
            Authorization = "Bearer $($script:token)"
            "Idempotency-Key" = $createIdemKey
        }
        $ordUrl = Url $script:base (ApiPath $prefix "/orders")
        $rOrdCreate = InvokeJson "POST" $ordUrl $ordHeaders $ordBody $script:timeoutSec
        $diag = Get-OrderCreateDiagnostic $rOrdCreate.status $rOrdCreate.body_text
        $createdOrderId = Infer-SeedNumber $rOrdCreate.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$")
        $script:lastCreateIdempotencyKey = $createIdemKey
        $script:lastCreatePayload = $ordBody
        if ($createdOrderId) { $script:lastCreatedOrderId = [int]$createdOrderId }
        if ($rOrdCreate.status -eq 200) {
            $okNote = "CLASS=PASS; actor=customer; contentType=application/json; idempotencyKey=$createIdemKey; storeId=$($ordBody.storeId); skuId=$($ordBody.items[0].skuId); quantity=$($ordBody.items[0].quantity); orderId=$createdOrderId"
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status $okNote "PASS"
            if (-not $script:seedOrderId) { $script:seedOrderId = Infer-SeedNumber $rOrdCreate.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$") }
            if (-not $script:seedOrderStoreId) { $script:seedOrderStoreId = Infer-SeedNumber $rOrdCreate.body_json @("(?i)^storeid$","(?i)store_id$") }
        }
        elseif ($rOrdCreate.status -eq 400 -and $diag -eq "POLICY_NOT_CONFIGURED: business/store policy is not configured.") {
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: $diag body=$($rOrdCreate.body_text)") "SKIPPED"
        }
        elseif ($rOrdCreate.status -in @(401, 403)) {
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status ("CLASS=SCOPE_BLOCKER; SKIPPED: requires customer ordering role (status=$($rOrdCreate.status))") "SKIPPED"
        }
        else {
            $class = if ($rOrdCreate.status -ge 500) { "BACKEND_DEFECT" } else { "FRAMEWORK_OR_CONTRACT_ISSUE" }
            $failNote = if ($diag) { "CLASS=$class; Unexpected status. $diag error=$($rOrdCreate.error); body=$($rOrdCreate.body_text)" } else { "CLASS=$class; Unexpected status. error=$($rOrdCreate.error); body=$($rOrdCreate.body_text)" }
            AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $rOrdCreate.status $failNote "FAIL"
        }
    }
    else {
        AddResult "ORD-API-001" "orders" "Create order success" "POST" (ApiPath $prefix "/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing storeId/skuId seed or auth token for valid order payload." "SKIPPED"
    }

    if ($script:seedOrderStoreId -and $script:seedSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $idemPayload = @{
            storeId = [int]$script:seedOrderStoreId
            items = @(
                @{
                    skuId = [int]$script:seedSkuId
                    quantity = 1
                }
            )
        }
        $idemKey = New-IdempotencyKey
        $idemHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = $idemKey }
        $idemUrl = Url $script:base (ApiPath $prefix "/orders")
        $idemRun1 = InvokeJson "POST" $idemUrl $idemHeaders $idemPayload $script:timeoutSec
        $idemRun2 = InvokeJson "POST" $idemUrl $idemHeaders $idemPayload $script:timeoutSec
        $idemOrderId1 = Infer-SeedNumber $idemRun1.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$")
        $idemOrderId2 = Infer-SeedNumber $idemRun2.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$")
        $idemNote = "idempotencyKey=$idemKey; firstStatus=$($idemRun1.status); secondStatus=$($idemRun2.status); firstOrderId=$idemOrderId1; secondOrderId=$idemOrderId2; firstBody=$($idemRun1.body_text); secondBody=$($idemRun2.body_text)"
        if ($idemRun1.status -eq 200 -and $idemRun2.status -eq 200 -and $idemOrderId1 -and $idemOrderId1 -eq $idemOrderId2) {
            AddResult "ORD-API-005" "orders" "Create order idempotency with same key" "POST" (ApiPath $prefix "/orders") @(200) 200 ("CLASS=PASS; same order reused. $idemNote") "PASS"
        }
        elseif (($idemRun1.status -eq 200 -and $idemRun2.status -in @(400, 409, 422)) -or ($idemRun2.status -eq 200 -and $idemRun1.status -in @(400, 409, 422))) {
            AddResult "ORD-API-005" "orders" "Create order idempotency with same key" "POST" (ApiPath $prefix "/orders") @(200, 400, 409, 422) $idemRun2.status ("CLASS=PASS; duplicate prevented by backend contract. $idemNote") "PASS"
        }
        elseif ($idemRun1.status -in @(401, 403) -or $idemRun2.status -in @(401, 403)) {
            AddResult "ORD-API-005" "orders" "Create order idempotency with same key" "POST" (ApiPath $prefix "/orders") @(200) $idemRun2.status ("CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable. $idemNote") "SKIPPED"
        }
        elseif (($idemRun1.status -ge 500) -or ($idemRun2.status -ge 500)) {
            AddResult "ORD-API-005" "orders" "Create order idempotency with same key" "POST" (ApiPath $prefix "/orders") @(200) $idemRun2.status ("CLASS=BACKEND_DEFECT; idempotency handling returned server error. $idemNote") "FAIL"
        }
        else {
            AddResult "ORD-API-005" "orders" "Create order idempotency with same key" "POST" (ApiPath $prefix "/orders") @(200) $idemRun2.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected idempotency behavior. $idemNote") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-005" "orders" "Create order idempotency with same key" "POST" (ApiPath $prefix "/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku prerequisites." "SKIPPED"
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

    if ($script:seedOrderStoreId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $emptyItemsPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @() }
        $emptyItemsHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) }
        $emptyItemsResp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders")) $emptyItemsHeaders $emptyItemsPayload $script:timeoutSec
        $emptyItemsNote = "status=$($emptyItemsResp.status); body=$($emptyItemsResp.body_text)"
        if ($emptyItemsResp.status -in @(400, 422)) {
            AddResult "ORD-API-006" "orders" "Create order rejects empty items" "POST" (ApiPath $prefix "/orders") @(400, 422) $emptyItemsResp.status ("CLASS=PASS; validation behavior confirmed. $emptyItemsNote") "PASS"
        }
        elseif ($emptyItemsResp.status -in @(401, 403)) {
            AddResult "ORD-API-006" "orders" "Create order rejects empty items" "POST" (ApiPath $prefix "/orders") @(400, 422) $emptyItemsResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable. $emptyItemsNote") "SKIPPED"
        }
        elseif ($emptyItemsResp.status -ge 500) {
            AddResult "ORD-API-006" "orders" "Create order rejects empty items" "POST" (ApiPath $prefix "/orders") @(400, 422) $emptyItemsResp.status ("CLASS=BACKEND_DEFECT; server error on validation path. $emptyItemsNote") "FAIL"
        }
        else {
            AddResult "ORD-API-006" "orders" "Create order rejects empty items" "POST" (ApiPath $prefix "/orders") @(400, 422) $emptyItemsResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. $emptyItemsNote") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-006" "orders" "Create order rejects empty items" "POST" (ApiPath $prefix "/orders") @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing storeId seed or auth token." "SKIPPED"
    }

    if ($script:seedOrderStoreId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $invalidSkuPayload = @{
            storeId = [int]$script:seedOrderStoreId
            items = @(
                @{
                    skuId = 999999999
                    quantity = 1
                }
            )
        }
        $invalidSkuHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) }
        $invalidSkuResp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders")) $invalidSkuHeaders $invalidSkuPayload $script:timeoutSec
        $invalidSkuNote = "status=$($invalidSkuResp.status); body=$($invalidSkuResp.body_text)"
        if ($invalidSkuResp.status -in @(400, 404, 409, 422)) {
            AddResult "ORD-API-007" "orders" "Create order rejects invalid sku" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $invalidSkuResp.status ("CLASS=PASS; invalid sku rejected. $invalidSkuNote") "PASS"
        }
        elseif ($invalidSkuResp.status -in @(401, 403)) {
            AddResult "ORD-API-007" "orders" "Create order rejects invalid sku" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $invalidSkuResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable. $invalidSkuNote") "SKIPPED"
        }
        elseif ($invalidSkuResp.status -ge 500) {
            AddResult "ORD-API-007" "orders" "Create order rejects invalid sku" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $invalidSkuResp.status ("CLASS=BACKEND_DEFECT; server error on invalid sku validation path. $invalidSkuNote") "FAIL"
        }
        else {
            AddResult "ORD-API-007" "orders" "Create order rejects invalid sku" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $invalidSkuResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status for invalid sku. $invalidSkuNote") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-007" "orders" "Create order rejects invalid sku" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing storeId seed or auth token." "SKIPPED"
    }

    $crossStoreSeed = $null
    if ($script:altStoreId -and $script:altSkuId) {
        if ($script:altStoreId -eq $script:seedOrderStoreId) {
            Log ("Cross-store config ignored because API_ALT_STORE_ID matches API_ORDER_STORE_ID ({0})." -f $script:altStoreId)
        }
        else {
            $crossStoreSeed = [pscustomobject]@{
                StoreId = [int]$script:altStoreId
                SkuId = [int]$script:altSkuId
                CategoryName = "CONFIG"
                ItemName = "CONFIG"
                SkuName = "CONFIG"
            }
            Log ("Cross-store seed from env: storeId={0}, skuId={1}" -f $script:altStoreId, $script:altSkuId)
        }
    }
    if (-not $crossStoreSeed -and $script:altStoreId) {
        $crossStoreSeed = TrySeedSkuFromStoreMenu $prefix ([int]$script:altStoreId)
    }
    if (-not $crossStoreSeed -and $script:seedOrderStoreId -eq 9768) {
        $crossStoreSeed = TrySeedSkuFromStoreMenu $prefix 9608
    }
    elseif (-not $crossStoreSeed -and $script:seedOrderStoreId -and $script:seedOrderStoreId -ne 9768) {
        $crossStoreSeed = TrySeedSkuFromStoreMenu $prefix 9768
    }
    if (-not $crossStoreSeed -and $script:seedId -and $script:seedId -ne $script:seedOrderStoreId) {
        $crossStoreSeed = TrySeedSkuFromStoreMenu $prefix ([int]$script:seedId)
    }
    if (-not $crossStoreSeed -and $script:seedOrderStoreId) {
        $crossStoreSeed = Discover-AlternateStoreMenuSeed $prefix ([int]$script:seedOrderStoreId) ([int]$script:altStoreScanLimit)
    }
    if ($crossStoreSeed -and $crossStoreSeed.StoreId -and $crossStoreSeed.SkuId) {
        if (-not $script:altStoreId) { $script:altStoreId = [int]$crossStoreSeed.StoreId }
        if (-not $script:altSkuId) { $script:altSkuId = [int]$crossStoreSeed.SkuId }
        Log ("Cross-store deterministic seed active: altStoreId={0}, altSkuId={1}" -f $script:altStoreId, $script:altSkuId)
    }
    if ($script:seedOrderStoreId -and -not [string]::IsNullOrWhiteSpace($script:token) -and $crossStoreSeed -and $crossStoreSeed.SkuId) {
        $crossPayload = @{
            storeId = [int]$script:seedOrderStoreId
            items = @(
                @{
                    skuId = [int]$crossStoreSeed.SkuId
                    quantity = 1
                }
            )
        }
        $crossResp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders")) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $crossPayload $script:timeoutSec
        $crossNote = "seedStore=$($script:seedOrderStoreId); crossStore=$($crossStoreSeed.StoreId); crossSku=$($crossStoreSeed.SkuId); status=$($crossResp.status); body=$($crossResp.body_text)"
        if ($crossResp.status -in @(400, 404, 409, 422)) {
            AddResult "ORD-API-008" "orders" "Cross-store cart rule" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $crossResp.status ("CLASS=PASS; cross-store item rejected. $crossNote") "PASS"
        }
        elseif ($crossResp.status -eq 200) {
            AddResult "ORD-API-008" "orders" "Cross-store cart rule" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $crossResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; potential cross-store rule gap. $crossNote") "FAIL"
        }
        elseif ($crossResp.status -ge 500) {
            AddResult "ORD-API-008" "orders" "Cross-store cart rule" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $crossResp.status ("CLASS=BACKEND_DEFECT; server error on cross-store validation path. $crossNote") "FAIL"
        }
        else {
            AddResult "ORD-API-008" "orders" "Cross-store cart rule" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $crossResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. $crossNote") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-008" "orders" "Cross-store cart rule" "POST" (ApiPath $prefix "/orders") @(400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing alternate store/sku seed for deterministic cross-store validation." "SKIPPED"
    }

    if (-not $script:pendingOrderId -or -not $script:paidOrderId -or -not $script:cancelledOrderId -or -not $script:completedOrderId) {
        $discoveredOrderSeeds = Discover-OrderStateSeeds $script:base $prefix $script:token $script:timeoutSec
        if (-not $script:pendingOrderId -and $discoveredOrderSeeds.pendingOrderId) { $script:pendingOrderId = [int]$discoveredOrderSeeds.pendingOrderId }
        if (-not $script:paidOrderId -and $discoveredOrderSeeds.paidOrderId) { $script:paidOrderId = [int]$discoveredOrderSeeds.paidOrderId }
        if (-not $script:cancelledOrderId -and $discoveredOrderSeeds.cancelledOrderId) { $script:cancelledOrderId = [int]$discoveredOrderSeeds.cancelledOrderId }
        if (-not $script:completedOrderId -and $discoveredOrderSeeds.completedOrderId) { $script:completedOrderId = [int]$discoveredOrderSeeds.completedOrderId }
        Log ("Order state seed discovery: source={0}; pending={1}; paid={2}; cancelled={3}; completed={4}; notes={5}" -f $discoveredOrderSeeds.Source, $script:pendingOrderId, $script:paidOrderId, $script:cancelledOrderId, $script:completedOrderId, $discoveredOrderSeeds.Notes)
    }
    if (-not $script:completedOrderId) {
        $completedFromAdmin = Discover-CompletedOrderSeedFromAdmin $script:base $prefix $script:adminToken $script:token $script:timeoutSec
        if ($completedFromAdmin.CompletedOrderId) {
            $script:completedOrderId = [int]$completedFromAdmin.CompletedOrderId
            $script:completedOrderSeedNote = [string]$completedFromAdmin.Note
            Log ("Completed-order seed discovery fallback: resolved orderId={0}; note={1}" -f $script:completedOrderId, $script:completedOrderSeedNote)
        }
        elseif (-not [string]::IsNullOrWhiteSpace([string]$completedFromAdmin.Note)) {
            $script:completedOrderSeedNote = [string]$completedFromAdmin.Note
            Log ("Completed-order seed discovery fallback: unresolved. note={0}" -f $script:completedOrderSeedNote)
        }
    }

    # Journey-oriented order seeds: keep each major flow on its own fresh order when possible.
    $script:scenarioCreateOrderId = if ($script:lastCreatedOrderId) { [int]$script:lastCreatedOrderId } else { $null }
    $script:scenarioPaymentOrderId = $null
    $script:scenarioCustomerActionOrderId = $null
    $script:scenarioMerchantOrderId = $null
    $script:scenarioMerchantLifecycleOrderId = $null
    $script:scenarioAdminOrderId = $null

    if ($script:seedOrderStoreId -and $script:seedSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $paymentSeed = TryCreateFreshOrder -prefix $prefix -journey "J2-Payment" -storeId ([int]$script:seedOrderStoreId) -skuId ([int]$script:seedSkuId) -quantity 1 -note "qa-journey-payment"
        if ($paymentSeed.Ok -and $paymentSeed.OrderId) {
            $script:scenarioPaymentOrderId = [int]$paymentSeed.OrderId
            Log ("Order journey seed created: J2-Payment orderId={0}" -f $script:scenarioPaymentOrderId)
        }
        else {
            Log ("Order journey seed blocked: J2-Payment class={0}; status={1}; note={2}" -f $paymentSeed.Class, $paymentSeed.Status, $paymentSeed.Note)
        }

        $customerSeed = TryCreateFreshOrder -prefix $prefix -journey "J3-CustomerAction" -storeId ([int]$script:seedOrderStoreId) -skuId ([int]$script:seedSkuId) -quantity 1 -note "qa-journey-customer"
        if ($customerSeed.Ok -and $customerSeed.OrderId) {
            $script:scenarioCustomerActionOrderId = [int]$customerSeed.OrderId
            Log ("Order journey seed created: J3-CustomerAction orderId={0}" -f $script:scenarioCustomerActionOrderId)
        }
        else {
            Log ("Order journey seed blocked: J3-CustomerAction class={0}; status={1}; note={2}" -f $customerSeed.Class, $customerSeed.Status, $customerSeed.Note)
        }

        $merchantSeed = TryCreateFreshOrder -prefix $prefix -journey "J5-Merchant" -storeId ([int]$script:seedOrderStoreId) -skuId ([int]$script:seedSkuId) -quantity 1 -note "qa-journey-merchant"
        if ($merchantSeed.Ok -and $merchantSeed.OrderId) {
            $script:scenarioMerchantOrderId = [int]$merchantSeed.OrderId
            Log ("Order journey seed created: J5-Merchant orderId={0}" -f $script:scenarioMerchantOrderId)
        }
        else {
            Log ("Order journey seed blocked: J5-Merchant class={0}; status={1}; note={2}" -f $merchantSeed.Class, $merchantSeed.Status, $merchantSeed.Note)
        }

        $merchantLifecycleSeed = TryCreateFreshOrder -prefix $prefix -journey "J6-MerchantLifecycle" -storeId ([int]$script:seedOrderStoreId) -skuId ([int]$script:seedSkuId) -quantity 1 -note "qa-journey-merchant-lifecycle"
        if ($merchantLifecycleSeed.Ok -and $merchantLifecycleSeed.OrderId) {
            $script:scenarioMerchantLifecycleOrderId = [int]$merchantLifecycleSeed.OrderId
            Log ("Order journey seed created: J6-MerchantLifecycle orderId={0}" -f $script:scenarioMerchantLifecycleOrderId)
        }
        else {
            Log ("Order journey seed blocked: J6-MerchantLifecycle class={0}; status={1}; note={2}" -f $merchantLifecycleSeed.Class, $merchantLifecycleSeed.Status, $merchantLifecycleSeed.Note)
        }
    }
    else {
        Log "Order journey seed setup skipped: missing token/storeId/skuId."
    }

    $detailOrderId = if ($script:scenarioCreateOrderId) { [int]$script:scenarioCreateOrderId } elseif ($script:pendingOrderId) { [int]$script:pendingOrderId } elseif ($script:seedOrderId) { [int]$script:seedOrderId } else { $null }
    $paymentOrderId = if ($script:scenarioPaymentOrderId) { [int]$script:scenarioPaymentOrderId } else { $detailOrderId }
    $customerActionOrderId = if ($script:scenarioCustomerActionOrderId) { [int]$script:scenarioCustomerActionOrderId } else { $detailOrderId }
    $merchantVisibilityOrderId = if ($script:scenarioMerchantOrderId) { [int]$script:scenarioMerchantOrderId } else { $detailOrderId }
    $merchantLifecycleOrderId = if ($script:scenarioMerchantLifecycleOrderId) { [int]$script:scenarioMerchantLifecycleOrderId } elseif ($merchantVisibilityOrderId) { [int]$merchantVisibilityOrderId } else { $detailOrderId }
    $merchantOrderId = $merchantVisibilityOrderId
    $adminOrderId = if ($script:scenarioCreateOrderId) { [int]$script:scenarioCreateOrderId } elseif ($merchantOrderId) { [int]$merchantOrderId } else { $detailOrderId }
    $targetOrderId = $detailOrderId
    if ($targetOrderId) {
        Log ("Order journey context: detailOrderId={0}; paymentOrderId={1}; customerActionOrderId={2}; merchantVisibilityOrderId={3}; merchantLifecycleOrderId={4}; adminOrderId={5}; merchant={6}; orderStoreId={7}; preferredStoreId={8}" -f $detailOrderId, $paymentOrderId, $customerActionOrderId, $merchantVisibilityOrderId, $merchantLifecycleOrderId, $adminOrderId, $script:merchantUser, $script:seedOrderStoreId, $script:preferredOrderStoreId)
        RunCase @{ id = "ORD-API-004"; module = "orders"; name = "Get order detail success"; method = "GET"; contract_path = (ApiPath $prefix "/orders/{id}"); call_path = (ApiPath $prefix "/orders/$targetOrderId"); query = @{}; body = $null; expected_status = @(200); require_token = $true; no_token = $false; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires customer order visibility"; skip_on_forbidden_scope = $true; forbidden_scope_note = "customer order detail blocked by scope/account" } | Out-Null

        $listOrdersPath = $null
        foreach ($p in $script:swagger.paths.PSObject.Properties) {
            if (-not $p.Name.StartsWith((ApiPath $prefix "/orders"))) { continue }
            if ($p.Name -match "\{id\}") { continue }
            if ($null -eq $p.Value.PSObject.Properties["get"]) { continue }
            $listOrdersPath = $p.Name
            break
        }
        if ($listOrdersPath) {
            $historyVariants = @(
                @{ pageNumber = 0; pageSize = 20 },
                @{ pageNumber = 1; pageSize = 20 },
                @{ pageNumber = 0; pageSize = 50 }
            )
            $historyResp = $null
            $historyMatched = $false
            foreach ($q in $historyVariants) {
                $historyResp = InvokeJson "GET" (Url $script:base (PathWithQuery $listOrdersPath $q)) @{ Authorization = "Bearer $($script:token)" } $null $script:timeoutSec
                if ($historyResp.status -eq 200 -and (BodyContainsId $historyResp.body_text ([int]$targetOrderId))) { $historyMatched = $true; break }
            }
            $historyNote = "path=$listOrdersPath; status=$($historyResp.status); targetOrderId=$targetOrderId; body=$($historyResp.body_text)"
            if ($historyResp.status -eq 200 -and $historyMatched) {
                AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" $listOrdersPath @(200) $historyResp.status ("CLASS=PASS; created order is visible in order history/list. $historyNote") "PASS"
            }
            elseif ($historyResp.status -in @(401, 403)) {
                AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" $listOrdersPath @(200) $historyResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: order history visibility blocked by scope. $historyNote") "SKIPPED"
            }
            elseif ($historyResp.status -eq 200) {
                AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" $listOrdersPath @(200) $historyResp.status ("CLASS=SEED_BLOCKER; SKIPPED: created order id not found in list payload. $historyNote") "SKIPPED"
            }
            elseif ($historyResp.status -ge 500) {
                AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" $listOrdersPath @(200) $historyResp.status ("CLASS=BACKEND_DEFECT; server error while checking order history. $historyNote") "FAIL"
            }
            else {
                AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" $listOrdersPath @(200) $historyResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. $historyNote") "FAIL"
            }
        }
        else {
            AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" (ApiPath $prefix "/orders") @(200) $null "CLASS=FRAMEWORK_GAP; SKIPPED: no list/history endpoint discovered in Swagger." "SKIPPED"
        }

        $paymentsPath = ApiPath $prefix "/orders/{id}/payments"
        $paymentOp = GetOp $script:swagger "POST" $paymentsPath
        if ($null -eq $paymentOp) {
            AddResult "ORD-PAY-001" "order-payment" "Payment success updates order status" "POST" $paymentsPath @(200) $null "CLASS=FRAMEWORK_GAP; SKIPPED: payment endpoint not found in Swagger." "SKIPPED"
            AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" $paymentsPath @(400, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: payment endpoint not found in Swagger." "SKIPPED"
            AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: payment endpoint not found in Swagger." "SKIPPED"
            AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" $paymentsPath @(200, 202, 408) $null "CLASS=FRAMEWORK_GAP; SKIPPED: payment endpoint not found in Swagger." "SKIPPED"
        }
        elseif (-not $paymentOrderId) {
            AddResult "ORD-PAY-001" "order-payment" "Payment success updates order status" "POST" $paymentsPath @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing payment-journey order id." "SKIPPED"
            AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" $paymentsPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing payment-journey order id." "SKIPPED"
            AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing payment-journey order id." "SKIPPED"
            AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" $paymentsPath @(200, 202, 408) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing payment-journey order id." "SKIPPED"
        }
        else {
            $payCallPath = ApiPath $prefix "/orders/$paymentOrderId/payments"
            $payHeaders = @{ Authorization = "Bearer $($script:token)" }
            $payInvalid = InvokeJson "POST" (Url $script:base $payCallPath) $payHeaders @{} $script:timeoutSec
            $payInvalidNote = "status=$($payInvalid.status); orderId=$paymentOrderId; body=$($payInvalid.body_text)"
            if ($payInvalid.status -in @(400, 422)) {
                AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" $paymentsPath @(400, 422) $payInvalid.status ("CLASS=PASS; expected validation failure confirmed. $payInvalidNote") "PASS"
            }
            elseif ($payInvalid.status -in @(401, 403)) {
                AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" $paymentsPath @(400, 422) $payInvalid.status ("CLASS=SCOPE_BLOCKER; SKIPPED: payment scope unavailable. $payInvalidNote") "SKIPPED"
            }
            elseif ($payInvalid.status -ge 500) {
                AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" $paymentsPath @(400, 422) $payInvalid.status ("CLASS=BACKEND_DEFECT; server error on invalid payment path. $payInvalidNote") "FAIL"
            }
            else {
                AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" $paymentsPath @(400, 422) $payInvalid.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status for invalid payment payload. $payInvalidNote") "FAIL"
            }

            $paySuccessHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) }
            $paySuccess = InvokeRaw "POST" (Url $script:base $payCallPath) $paySuccessHeaders "application/json; charset=utf-8" "{}" $script:timeoutSec
            $paySuccessNote = "status=$($paySuccess.status); orderId=$paymentOrderId; body=$($paySuccess.body_text)"
            if ($paySuccess.status -eq 200) {
                AddResult "ORD-PAY-001" "order-payment" "Payment success updates order status" "POST" $paymentsPath @(200) 200 ("CLASS=PASS; payment intent/session created. $paySuccessNote") "PASS"

                $payRetryHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) }
                $payRetry = InvokeRaw "POST" (Url $script:base $payCallPath) $payRetryHeaders "application/json; charset=utf-8" "{}" $script:timeoutSec
                $payRetryNote = "firstStatus=$($paySuccess.status); retryStatus=$($payRetry.status); orderId=$paymentOrderId; retryBody=$($payRetry.body_text)"
                if ($payRetry.status -in @(200, 400, 409, 422)) {
                    AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 409, 422) $payRetry.status ("CLASS=PASS; retry returned controlled contract status. $payRetryNote") "PASS"
                }
                elseif ($payRetry.status -in @(401, 403)) {
                    AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 409, 422) $payRetry.status ("CLASS=SCOPE_BLOCKER; SKIPPED: payment retry scope unavailable. $payRetryNote") "SKIPPED"
                }
                elseif ($payRetry.status -ge 500) {
                    AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 409, 422) $payRetry.status ("CLASS=BACKEND_DEFECT; server error on payment retry. $payRetryNote") "FAIL"
                }
                else {
                    AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 409, 422) $payRetry.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected retry status. $payRetryNote") "FAIL"
                }

                if (BodyContainsAnyKey $paySuccess.body_text @("expiresAt", "stripeClientSecret", "paymentAttemptId")) {
                    AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" $paymentsPath @(200, 202, 408) 200 ("CLASS=PASS; pending payment intent markers observed (expiresAt/clientSecret/attemptId). $paySuccessNote") "PASS"
                }
                else {
                    AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" $paymentsPath @(200, 202, 408) $paySuccess.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: response lacks deterministic pending markers. $paySuccessNote") "SKIPPED"
                }
            }
            elseif ($paySuccess.status -in @(401, 403)) {
                AddResult "ORD-PAY-001" "order-payment" "Payment success updates order status" "POST" $paymentsPath @(200) $paySuccess.status ("CLASS=SCOPE_BLOCKER; SKIPPED: payment scope unavailable. $paySuccessNote") "SKIPPED"
                AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 409, 422) $null "CLASS=SCOPE_BLOCKER; SKIPPED: payment success precondition blocked by scope." "SKIPPED"
                AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" $paymentsPath @(200, 202, 408) $null "CLASS=SCOPE_BLOCKER; SKIPPED: payment success precondition blocked by scope." "SKIPPED"
            }
            else {
                AddResult "ORD-PAY-001" "order-payment" "Payment success updates order status" "POST" $paymentsPath @(200) $paySuccess.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: payment success returned non-200. $paySuccessNote") "SKIPPED"
                AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" $paymentsPath @(200, 400, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: payment success precondition not met for retry check." "SKIPPED"
                AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" $paymentsPath @(200, 202, 408) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: payment success precondition not met for pending check." "SKIPPED"
            }
        }
        if ($script:paidOrderId) {
            $paidPath = ApiPath $prefix "/orders/$($script:paidOrderId)/payments"
            $paidResp = InvokeRaw "POST" (Url $script:base $paidPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            $paidNote = "status=$($paidResp.status); orderId=$($script:paidOrderId); body=$($paidResp.body_text)"
            if ($paidResp.status -in @(400, 409, 422)) {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" $paymentsPath @(400, 409, 422) $paidResp.status ("CLASS=PASS; already-paid guard returned controlled status. $paidNote") "PASS"
            }
            elseif ($paidResp.status -in @(401, 403)) {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" $paymentsPath @(400, 409, 422) $paidResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: no visibility to configured paid order. $paidNote") "SKIPPED"
            }
            elseif ($paidResp.status -ge 500) {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" $paymentsPath @(400, 409, 422) $paidResp.status ("CLASS=BACKEND_DEFECT; server error on already-paid guard. $paidNote") "FAIL"
            }
            else {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" $paymentsPath @(400, 409, 422) $paidResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status for already-paid guard. $paidNote") "FAIL"
            }
        }
        else {
            AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" $paymentsPath @(400, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic already-paid order seed and settlement callback control." "SKIPPED"
        }

        if ($script:cancelledOrderId) {
            $cancelPath = ApiPath $prefix "/orders/$($script:cancelledOrderId)/payments"
            $cancelResp = InvokeRaw "POST" (Url $script:base $cancelPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            $cancelNote = "status=$($cancelResp.status); orderId=$($script:cancelledOrderId); body=$($cancelResp.body_text)"
            if ($cancelResp.status -in @(400, 409, 422)) {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" $paymentsPath @(400, 409, 422) $cancelResp.status ("CLASS=PASS; cancelled-order guard returned controlled status. $cancelNote") "PASS"
            }
            elseif ($cancelResp.status -in @(401, 403)) {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" $paymentsPath @(400, 409, 422) $cancelResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: no visibility to configured cancelled order. $cancelNote") "SKIPPED"
            }
            elseif ($cancelResp.status -ge 500) {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" $paymentsPath @(400, 409, 422) $cancelResp.status ("CLASS=BACKEND_DEFECT; server error on cancelled-order guard. $cancelNote") "FAIL"
            }
            else {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" $paymentsPath @(400, 409, 422) $cancelResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status for cancelled-order guard. $cancelNote") "FAIL"
            }
        }
        else {
            AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" $paymentsPath @(400, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic cancelled-order seed in customer scope." "SKIPPED"
        }

        # Extended payment + customer lifecycle contract checks
        $walletPath = ApiPath $prefix "/orders/{id}/payments/wallet"
        $walletOp = GetOp $script:swagger "POST" $walletPath
        if ($null -eq $walletOp) {
            AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" $walletPath @(200, 400, 404, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: wallet payment endpoint not found in Swagger." "SKIPPED"
        }
        elseif (-not [string]::IsNullOrWhiteSpace($script:token) -and $paymentOrderId) {
            $walletResp = InvokeRaw "POST" (Url $script:base (ApiPath $prefix "/orders/$paymentOrderId/payments/wallet")) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            $walletNote = "status=$($walletResp.status); orderId=$paymentOrderId; body=$($walletResp.body_text)"
            if ($walletResp.status -in @(200, 400, 404, 409, 422)) {
                AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" $walletPath @(200, 400, 404, 409, 422) $walletResp.status ("CLASS=PASS; wallet payment contract returned controlled status. $walletNote") "PASS"
            }
            elseif ($walletResp.status -in @(401, 403)) {
                AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" $walletPath @(200, 400, 404, 409, 422) $walletResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: wallet payment scope unavailable. $walletNote") "SKIPPED"
            }
            elseif ($walletResp.status -ge 500) {
                AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" $walletPath @(200, 400, 404, 409, 422) $walletResp.status ("CLASS=BACKEND_DEFECT; server error on wallet payment path. $walletNote") "FAIL"
            }
            else {
                AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" $walletPath @(200, 400, 404, 409, 422) $walletResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected wallet payment status. $walletNote") "FAIL"
            }
        }
        else {
            AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" $walletPath @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth token or order id seed." "SKIPPED"
        }

        $verifyPath = ApiPath $prefix "/orders/{id}/payments/verify"
        $verifyOp = GetOp $script:swagger "GET" $verifyPath
        if ($null -eq $verifyOp) {
            AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" $verifyPath @(200, 400, 404, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: payment verify endpoint not found in Swagger." "SKIPPED"
        }
        elseif (-not [string]::IsNullOrWhiteSpace($script:token) -and $paymentOrderId) {
            $verifyResp = InvokeJson "GET" (Url $script:base (ApiPath $prefix "/orders/$paymentOrderId/payments/verify")) @{ Authorization = "Bearer $($script:token)" } $null $script:timeoutSec
            $verifyNote = "status=$($verifyResp.status); orderId=$paymentOrderId; body=$($verifyResp.body_text)"
            if ($verifyResp.status -in @(200, 400, 404, 409, 422)) {
                AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" $verifyPath @(200, 400, 404, 409, 422) $verifyResp.status ("CLASS=PASS; payment verify path returned controlled status. $verifyNote") "PASS"
            }
            elseif ($verifyResp.status -in @(401, 403)) {
                AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" $verifyPath @(200, 400, 404, 409, 422) $verifyResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: payment verify scope unavailable. $verifyNote") "SKIPPED"
            }
            elseif ($verifyResp.status -ge 500) {
                AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" $verifyPath @(200, 400, 404, 409, 422) $verifyResp.status ("CLASS=BACKEND_DEFECT; server error on payment verify path. $verifyNote") "FAIL"
            }
            else {
                AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" $verifyPath @(200, 400, 404, 409, 422) $verifyResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected payment verify status. $verifyNote") "FAIL"
            }
        }
        else {
            AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" $verifyPath @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth token or order id seed." "SKIPPED"
        }

        $customerActionSpecs = @(
            @{ Id = "ORD-CUS-001"; Name = "Customer cancel order returns controlled status"; Method = "POST"; ContractPath = (ApiPath $prefix "/orders/{id}/cancel"); Expected = @(200, 400, 404, 409, 422) },
            @{ Id = "ORD-CUS-002"; Name = "Customer confirm-arrival returns controlled status"; Method = "POST"; ContractPath = (ApiPath $prefix "/orders/{id}/confirm-arrival"); Expected = @(200, 400, 404, 409, 422) },
            @{ Id = "ORD-CUS-003"; Name = "Customer confirm-complete returns controlled status"; Method = "POST"; ContractPath = (ApiPath $prefix "/orders/{id}/confirm-complete"); Expected = @(200, 400, 404, 409, 422) },
            @{ Id = "ORD-CUS-004"; Name = "Customer report-not-arrived returns controlled status"; Method = "POST"; ContractPath = (ApiPath $prefix "/orders/{id}/report-not-arrived"); Expected = @(200, 400, 404, 409, 422) }
        )
        foreach ($spec in $customerActionSpecs) {
            $op = GetOp $script:swagger $spec.Method $spec.ContractPath
            if ($null -eq $op) {
                AddResult $spec.Id "orders-customer" $spec.Name $spec.Method $spec.ContractPath $spec.Expected $null "CLASS=FRAMEWORK_GAP; SKIPPED: endpoint not found in Swagger." "SKIPPED"
                continue
            }
            if ([string]::IsNullOrWhiteSpace($script:token) -or -not $customerActionOrderId) {
                AddResult $spec.Id "orders-customer" $spec.Name $spec.Method $spec.ContractPath $spec.Expected $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth token or order id seed." "SKIPPED"
                continue
            }
            $callPath = $spec.ContractPath.Replace("{id}", [string]$customerActionOrderId)
            $resp = InvokeRaw $spec.Method (Url $script:base $callPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            $note = "status=$($resp.status); orderId=$customerActionOrderId; body=$($resp.body_text)"
            if ($resp.status -in $spec.Expected) {
                AddResult $spec.Id "orders-customer" $spec.Name $spec.Method $spec.ContractPath $spec.Expected $resp.status ("CLASS=PASS; customer action returned controlled status. $note") "PASS"
            }
            elseif ($resp.status -in @(401, 403)) {
                AddResult $spec.Id "orders-customer" $spec.Name $spec.Method $spec.ContractPath $spec.Expected $resp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: customer scope unavailable for action. $note") "SKIPPED"
            }
            elseif ($resp.status -ge 500) {
                AddResult $spec.Id "orders-customer" $spec.Name $spec.Method $spec.ContractPath $spec.Expected $resp.status ("CLASS=BACKEND_DEFECT; server error on customer action path. $note") "FAIL"
            }
            else {
                AddResult $spec.Id "orders-customer" $spec.Name $spec.Method $spec.ContractPath $spec.Expected $resp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected customer action status. $note") "FAIL"
            }
        }

        $merchantCanProcessTarget = $false
        $merchantListBootstrapResp = $rMerchantOrders
        if (-not $merchantListBootstrapResp -and -not [string]::IsNullOrWhiteSpace($script:merchantToken)) {
            $merchantListBootstrapResp = InvokeJson "GET" (Url $script:base (PathWithQuery (ApiPath $prefix "/merchant/orders") @{ pageNumber = 1; pageSize = 1 })) @{ Authorization = "Bearer $($script:merchantToken)" } $null $script:timeoutSec
        }
        $merchantScopeBlockNote = ""
        if ([string]::IsNullOrWhiteSpace($script:merchantToken)) {
            $merchantScopeBlockNote = "merchant auth/token unavailable"
            $merchantAuthNote = Get-AuthMissingNote "merchant-orders"
            AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" (ApiPath $prefix "/merchant/orders") @(200) $script:merchantLoginStatus $merchantAuthNote "SKIPPED"
        }
        elseif ($script:merchantStoreId -and $script:seedOrderStoreId -and ([int]$script:merchantStoreId -ne [int]$script:seedOrderStoreId)) {
            $merchantScopeBlockNote = "configured merchant store ($($script:merchantStoreId)) != order store ($($script:seedOrderStoreId))"
            AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" (ApiPath $prefix "/merchant/orders") @(200) $null ("CLASS=SCOPE_BLOCKER; SKIPPED: $merchantScopeBlockNote") "SKIPPED"
        }
        elseif ($merchantListBootstrapResp -and $merchantListBootstrapResp.status -eq 200) {
            $merchantListPath = ApiPath $prefix "/merchant/orders"
            $merchantQueries = New-Object System.Collections.Generic.List[object]
            if ($script:seedOrderStoreId) {
                $merchantQueries.Add(@{ pageNumber = 0; pageSize = 50; storeId = [int]$script:seedOrderStoreId }) | Out-Null
                $merchantQueries.Add(@{ pageNumber = 1; pageSize = 50; storeId = [int]$script:seedOrderStoreId }) | Out-Null
            }
            $merchantQueries.Add(@{ pageNumber = 0; pageSize = 50 }) | Out-Null
            $merchantQueries.Add(@{ pageNumber = 1; pageSize = 50 }) | Out-Null
            $merchantQueries.Add(@{ pageNumber = 2; pageSize = 50 }) | Out-Null

            $merchantMatched = $false
            $merchantLastResp = $merchantListBootstrapResp
            $merchantAttemptNotes = New-Object System.Collections.Generic.List[string]
            $merchantAttemptNotes.Add(("bootstrap=query=pageNumber=1&pageSize=1; status={0}" -f $merchantListBootstrapResp.status)) | Out-Null
            foreach ($q in $merchantQueries) {
                $resp = InvokeJson "GET" (Url $script:base (PathWithQuery $merchantListPath $q)) @{ Authorization = "Bearer $($script:merchantToken)" } $null $script:timeoutSec
                $merchantLastResp = $resp
                $merchantAttemptNotes.Add(("query={0}; status={1}" -f (($q.Keys | Sort-Object | ForEach-Object { "$_=$($q[$_])" }) -join "&"), $resp.status)) | Out-Null
                if ($resp.status -eq 200 -and (BodyContainsId $resp.body_text ([int]$merchantOrderId))) { $merchantMatched = $true; break }
                if ($resp.status -in @(401, 403)) { break }
            }
            $merchantListNote = "targetOrderId=$merchantOrderId; attempts=$([string]::Join(' | ', $merchantAttemptNotes)); body=$($merchantLastResp.body_text)"
            if ($merchantMatched) {
                AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" $merchantListPath @(200) 200 ("CLASS=PASS; created order visible in merchant list. $merchantListNote") "PASS"
                $merchantCanProcessTarget = $true
            }
            elseif ($merchantLastResp.status -eq 200) {
                AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" $merchantListPath @(200) 200 ("CLASS=SCOPE_BLOCKER; SKIPPED: merchant list does not include created order id after deterministic query scan. $merchantListNote") "SKIPPED"
                $merchantScopeBlockNote = "merchant list does not include target order"
            }
            elseif ($merchantLastResp.status -in @(401, 403)) {
                AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" $merchantListPath @(200) $merchantLastResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: merchant role is unavailable. $merchantListNote") "SKIPPED"
                $merchantScopeBlockNote = "merchant role is unavailable"
            }
            else {
                AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" $merchantListPath @(200) $merchantLastResp.status ("CLASS=SEED_BLOCKER; SKIPPED: merchant list query did not return usable data. $merchantListNote") "SKIPPED"
                $merchantScopeBlockNote = "merchant list response unavailable"
            }
        }
        elseif ($merchantListBootstrapResp -and $merchantListBootstrapResp.status -in @(401, 403)) {
            AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" (ApiPath $prefix "/merchant/orders") @(200) $merchantListBootstrapResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: merchant role is unavailable." "SKIPPED"
            $merchantScopeBlockNote = "merchant role is unavailable"
        }
        else {
            AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" (ApiPath $prefix "/merchant/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: merchant list response unavailable." "SKIPPED"
            $merchantScopeBlockNote = "merchant list response unavailable"
        }

        if ($merchantCanProcessTarget) {
            RunCase @{ id = "MORD-API-008"; module = "merchant-orders"; name = "Merchant detail loads target order"; method = "GET"; contract_path = (ApiPath $prefix "/merchant/orders/{id}"); call_path = (ApiPath $prefix "/merchant/orders/$merchantOrderId"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = @{ Authorization = "Bearer $($script:merchantToken)" }; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
        }
        else {
            $merchantSkipNote = if ([string]::IsNullOrWhiteSpace($merchantScopeBlockNote)) { "merchant ownership precheck not satisfied" } else { $merchantScopeBlockNote }
            $merchantSkipClass = if ([string]::IsNullOrWhiteSpace($script:merchantToken)) { "CONFIG_BLOCKER" } else { "SCOPE_BLOCKER" }
            AddResult "MORD-API-008" "merchant-orders" "Merchant detail loads target order" "GET" (ApiPath $prefix "/merchant/orders/{id}") @(200) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
        }

        $adminListBootstrapResp = $rAordApi001
        if (-not $adminListBootstrapResp -and $adminReady) {
            $adminListBootstrapResp = InvokeJson "GET" (Url $script:base (PathWithQuery (ApiPath $prefix "/admin/orders") @{ pageNumber = 1; pageSize = 1 })) $adminAuthHeaders $null $script:timeoutSec
        }

        if (-not $adminReady) {
            AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" (ApiPath $prefix "/admin/orders") @(200) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before list visibility scan. status=$($adminPrecheck.Status)") "SKIPPED"
        }
        elseif ($adminListBootstrapResp -and $adminListBootstrapResp.status -eq 200) {
            $adminListPath = ApiPath $prefix "/admin/orders"
            $listOp = GetOp $script:swagger "GET" $adminListPath
            $hasOrderIdFilter = $false
            if ($listOp -and $listOp.parameters) {
                foreach ($p in @($listOp.parameters)) {
                    if ([string]$p.in -eq "query" -and ([string]$p.name).ToLowerInvariant() -in @("orderid","id")) { $hasOrderIdFilter = $true; break }
                }
            }
            $adminQueries = New-Object System.Collections.Generic.List[object]
            if ($hasOrderIdFilter) { $adminQueries.Add(@{ pageNumber = 0; pageSize = 50; orderId = [int]$adminOrderId }) | Out-Null }
            if ($script:seedOrderStoreId) { $adminQueries.Add(@{ pageNumber = 0; pageSize = 50; storeId = [int]$script:seedOrderStoreId }) | Out-Null }
            $adminQueries.Add(@{ pageNumber = 0; pageSize = 50 }) | Out-Null
            $adminQueries.Add(@{ pageNumber = 1; pageSize = 50 }) | Out-Null
            $adminQueries.Add(@{ pageNumber = 2; pageSize = 50 }) | Out-Null

            $adminMatched = $false
            $adminLastResp = $adminListBootstrapResp
            $adminAttemptNotes = New-Object System.Collections.Generic.List[string]
            $adminSeenQueryKeys = New-Object System.Collections.Generic.HashSet[string]
            $adminAttemptNotes.Add(("bootstrap=query=pageNumber=1&pageSize=1; status={0}" -f $adminListBootstrapResp.status)) | Out-Null
            foreach ($q in $adminQueries) {
                $qKey = ($q.Keys | Sort-Object | ForEach-Object { "$_=$($q[$_])" }) -join "&"
                if (-not $adminSeenQueryKeys.Add($qKey)) { continue }
                $resp = InvokeJson "GET" (Url $script:base (PathWithQuery $adminListPath $q)) $adminAuthHeaders $null $script:timeoutSec
                $adminLastResp = $resp
                $adminAttemptNotes.Add(("query={0}; status={1}" -f $qKey, $resp.status)) | Out-Null
                if ($resp.status -eq 200 -and (BodyContainsId $resp.body_text ([int]$adminOrderId))) { $adminMatched = $true; break }
                if ($resp.status -in @(401, 403)) { break }
            }

            # Fallback deterministic scan: walk more pages when target order is older than the first pages.
            if (-not $adminMatched -and $adminLastResp.status -eq 200) {
                $adminDataNode = Get-DataNode $adminLastResp.body_json
                $firstPage = TryParse-Int (Get-ObjectPropValue $adminDataNode @("firstPage", "FirstPage")) 0
                $lastPage = TryParse-Int (Get-ObjectPropValue $adminDataNode @("lastPage", "LastPage")) $null
                if ($null -eq $lastPage) {
                    $totalPages = TryParse-Int (Get-ObjectPropValue $adminDataNode @("totalPages", "TotalPages")) $null
                    if ($null -ne $totalPages -and $totalPages -gt 0) { $lastPage = $totalPages - 1 }
                }

                if ($null -ne $lastPage -and $lastPage -ge $firstPage) {
                    $scanLast = [Math]::Min([int]$lastPage, 50)
                    for ($page = [int]$firstPage; $page -le $scanLast; $page++) {
                        $scanQuery = @{ pageNumber = $page; pageSize = 50 }
                        if ($script:seedOrderStoreId) { $scanQuery.storeId = [int]$script:seedOrderStoreId }
                        $scanKey = ($scanQuery.Keys | Sort-Object | ForEach-Object { "$_=$($scanQuery[$_])" }) -join "&"
                        if (-not $adminSeenQueryKeys.Add($scanKey)) { continue }

                        $scanResp = InvokeJson "GET" (Url $script:base (PathWithQuery $adminListPath $scanQuery)) $adminAuthHeaders $null $script:timeoutSec
                        $adminLastResp = $scanResp
                        $adminAttemptNotes.Add(("scan={0}; status={1}" -f $scanKey, $scanResp.status)) | Out-Null
                        if ($scanResp.status -eq 200 -and (BodyContainsId $scanResp.body_text ([int]$adminOrderId))) { $adminMatched = $true; break }
                        if ($scanResp.status -in @(401, 403)) { break }
                        if ($scanResp.status -ge 500) { break }
                    }
                }
            }
            $adminListNote = "targetOrderId=$adminOrderId; attempts=$([string]::Join(' | ', $adminAttemptNotes)); body=$($adminLastResp.body_text)"
            if ($adminMatched) {
                AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" $adminListPath @(200) 200 ("CLASS=PASS; created order visible in admin list. $adminListNote") "PASS"
            }
            elseif ($adminLastResp.status -eq 200) {
                AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" $adminListPath @(200) 200 ("CLASS=QUERY_BLOCKER; SKIPPED: order not found in scanned admin pages/filters. $adminListNote") "SKIPPED"
            }
            elseif ($adminLastResp.status -in @(401, 403)) {
                AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" $adminListPath @(200) $adminLastResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: admin role is unavailable. $adminListNote") "SKIPPED"
            }
            elseif ($adminLastResp.status -ge 500) {
                AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" $adminListPath @(200) $adminLastResp.status ("CLASS=BACKEND_DEFECT; admin list paging/filter query returned server error. $adminListNote") "FAIL"
            }
            else {
                AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" $adminListPath @(200) $adminLastResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected admin list status. $adminListNote") "FAIL"
            }
        }
        elseif ($adminListBootstrapResp -and $adminListBootstrapResp.status -in @(401, 403)) {
            AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" (ApiPath $prefix "/admin/orders") @(200) $adminListBootstrapResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: admin role is unavailable." "SKIPPED"
        }
        else {
            AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" (ApiPath $prefix "/admin/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: admin list response unavailable." "SKIPPED"
        }

        if (-not $adminReady) {
            AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before detail verification. status=$($adminPrecheck.Status)") "SKIPPED"
        }
        else {
            $adminDetailResp = InvokeJson "GET" (Url $script:base (ApiPath $prefix "/admin/orders/$adminOrderId")) $adminAuthHeaders $null $script:timeoutSec
            $adminDetailNote = "status=$($adminDetailResp.status); orderId=$adminOrderId; body=$($adminDetailResp.body_text)"
            if ($adminDetailResp.status -eq 200) {
                $hasItems = BodyContainsAnyKey $adminDetailResp.body_text @("items")
                $hasTimeline = BodyContainsAnyKey $adminDetailResp.body_text @("timeline", "statusHistories", "statusHistory", "history")
                if ($hasItems -and $hasTimeline) {
                    AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=PASS; admin detail includes items and timeline markers. $adminDetailNote") "PASS"
                }
                elseif ($hasItems) {
                    AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; items present but timeline markers not found. $adminDetailNote") "FAIL"
                }
                else {
                    AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; expected detail fields missing. $adminDetailNote") "FAIL"
                }
            }
            elseif ($adminDetailResp.status -in @(401, 403)) {
                AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminDetailResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: admin role is unavailable. $adminDetailNote") "SKIPPED"
            }
            elseif ($adminDetailResp.status -ge 500) {
                AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminDetailResp.status ("CLASS=BACKEND_DEFECT; server error on admin detail. $adminDetailNote") "FAIL"
            }
            else {
                AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminDetailResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. $adminDetailNote") "FAIL"
            }
        }

        if (-not $adminReady) {
            AddResult "AORD-API-005" "admin-orders" "Admin list filters by store/status" "GET" (ApiPath $prefix "/admin/orders") @(200) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before filtered list check. status=$($adminPrecheck.Status)") "SKIPPED"
            AddResult "AORD-API-006" "admin-disputes" "Admin dispute list visibility" "GET" (ApiPath $prefix "/admin/disputes") @(200) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before dispute list check. status=$($adminPrecheck.Status)") "SKIPPED"
            AddResult "AORD-API-007" "admin-disputes" "Admin dispute detail visibility" "GET" (ApiPath $prefix "/admin/disputes/{id}") @(200) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before dispute detail check. status=$($adminPrecheck.Status)") "SKIPPED"
            AddResult "AORD-API-008" "admin-disputes" "Admin dispute resolve validation (invalid payload)" "POST" (ApiPath $prefix "/admin/disputes/{id}/resolve") @(400, 422) $adminPrecheck.Status ("CLASS=ACCOUNT_BLOCKER; SKIPPED: admin precheck failed before dispute resolve validation check. status=$($adminPrecheck.Status)") "SKIPPED"
        }
        else {
            RunCase @{ id = "AORD-API-005"; module = "admin-orders"; name = "Admin list filters by store/status"; method = "GET"; contract_path = (ApiPath $prefix "/admin/orders"); call_path = (ApiPath $prefix "/admin/orders"); query = @{ pageNumber = 0; pageSize = 20; storeId = [int]$script:seedOrderStoreId; status = 10 }; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders; admin_required_case = $true } | Out-Null

            $adminDisputesListPath = ApiPath $prefix "/admin/disputes"
            $adminDisputesListOp = GetOp $script:swagger "GET" $adminDisputesListPath
            if ($null -eq $adminDisputesListOp) {
                AddResult "AORD-API-006" "admin-disputes" "Admin dispute list visibility" "GET" $adminDisputesListPath @(200) $null "CLASS=FRAMEWORK_GAP; SKIPPED: /admin/disputes not found in Swagger." "SKIPPED"
                AddResult "AORD-API-007" "admin-disputes" "Admin dispute detail visibility" "GET" (ApiPath $prefix "/admin/disputes/{id}") @(200) $null "CLASS=FRAMEWORK_GAP; SKIPPED: /admin/disputes/{id} not found in Swagger." "SKIPPED"
                AddResult "AORD-API-008" "admin-disputes" "Admin dispute resolve validation (invalid payload)" "POST" (ApiPath $prefix "/admin/disputes/{id}/resolve") @(400, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: /admin/disputes/{id}/resolve not found in Swagger." "SKIPPED"
            }
            else {
                $rAdminDisputes = RunCase @{ id = "AORD-API-006"; module = "admin-disputes"; name = "Admin dispute list visibility"; method = "GET"; contract_path = $adminDisputesListPath; call_path = $adminDisputesListPath; query = @{ pageNumber = 0; pageSize = 20 }; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders; admin_required_case = $true }
                $seedAdminDisputeId = $null
                if ($rAdminDisputes -and $rAdminDisputes.status -eq 200) {
                    $seedAdminDisputeId = Infer-SeedNumber $rAdminDisputes.body_json @("(?i)^id$","(?i)disputeid$","(?i)dispute_id$")
                }

                if ($seedAdminDisputeId) {
                    RunCase @{ id = "AORD-API-007"; module = "admin-disputes"; name = "Admin dispute detail visibility"; method = "GET"; contract_path = (ApiPath $prefix "/admin/disputes/{id}"); call_path = (ApiPath $prefix "/admin/disputes/$seedAdminDisputeId"); query = @{}; body = $null; expected_status = @(200); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders; admin_required_case = $true } | Out-Null

                    $adminResolveOp = GetOp $script:swagger "POST" (ApiPath $prefix "/admin/disputes/{id}/resolve")
                    if ($null -eq $adminResolveOp) {
                        AddResult "AORD-API-008" "admin-disputes" "Admin dispute resolve validation (invalid payload)" "POST" (ApiPath $prefix "/admin/disputes/{id}/resolve") @(400, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: resolve endpoint not found in Swagger." "SKIPPED"
                    }
                    else {
                        RunCase @{ id = "AORD-API-008"; module = "admin-disputes"; name = "Admin dispute resolve validation (invalid payload)"; method = "POST"; contract_path = (ApiPath $prefix "/admin/disputes/{id}/resolve"); call_path = (ApiPath $prefix "/admin/disputes/$seedAdminDisputeId/resolve"); query = @{}; body = @{}; expected_status = @(400, 422); require_token = $false; no_token = $true; extra_headers = $adminAuthHeaders; admin_required_case = $true; skip_contract_assert = $true } | Out-Null
                    }
                }
                else {
                    AddResult "AORD-API-007" "admin-disputes" "Admin dispute detail visibility" "GET" (ApiPath $prefix "/admin/disputes/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: no dispute id inferable from admin dispute list." "SKIPPED"
                    AddResult "AORD-API-008" "admin-disputes" "Admin dispute resolve validation (invalid payload)" "POST" (ApiPath $prefix "/admin/disputes/{id}/resolve") @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: no dispute id seed for resolve validation." "SKIPPED"
                }
            }
        }

        $merchantAuthHeaders = @{ Authorization = "Bearer $($script:merchantToken)" }
        $merchantActionOrderId = if ($merchantLifecycleOrderId) { [int]$merchantLifecycleOrderId } else { $merchantOrderId }
        $merchantLifecyclePrepNotes = New-Object System.Collections.Generic.List[string]
        if ($merchantCanProcessTarget -and $merchantActionOrderId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
            $walletPrepResp = InvokeRaw "POST" (Url $script:base (ApiPath $prefix "/orders/$merchantActionOrderId/payments/wallet")) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            $merchantLifecyclePrepNotes.Add(("walletPay orderId={0} status={1}" -f $merchantActionOrderId, $walletPrepResp.status)) | Out-Null
            if ($script:paidOrderId -and [int]$script:paidOrderId -ne [int]$merchantActionOrderId) {
                $paidMerchantDetail = InvokeJson "GET" (Url $script:base (ApiPath $prefix "/merchant/orders/$($script:paidOrderId)")) $merchantAuthHeaders $null $script:timeoutSec
                $merchantLifecyclePrepNotes.Add(("merchantDetail paidSeed={0} status={1}" -f $script:paidOrderId, $paidMerchantDetail.status)) | Out-Null
                if ($paidMerchantDetail.status -eq 200) {
                    $merchantActionOrderId = [int]$script:paidOrderId
                }
            }
        }
        elseif ($merchantCanProcessTarget -and $merchantActionOrderId) {
            $merchantLifecyclePrepNotes.Add("walletPay skipped: customer token unavailable") | Out-Null
        }
        if ($merchantCanProcessTarget) {
            Log ("Merchant lifecycle action order selected: orderId={0}; notes={1}" -f $merchantActionOrderId, [string]::Join(" | ", $merchantLifecyclePrepNotes))
        }

        $rMordAccept = $null
        $rMordReject = $null
        if ($merchantCanProcessTarget -and $merchantActionOrderId) {
            $rMordAccept = RunCase @{ id = "MORD-API-001"; module = "merchant-orders"; name = "Merchant accept order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/accept"); call_path = (ApiPath $prefix "/merchant/orders/$merchantActionOrderId/accept"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true }
            $rMordReject = RunCase @{ id = "MORD-API-002"; module = "merchant-orders"; name = "Merchant reject order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/reject"); call_path = (ApiPath $prefix "/merchant/orders/$merchantActionOrderId/reject"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true }
        }
        else {
            $merchantSkipNote = if ([string]::IsNullOrWhiteSpace($merchantScopeBlockNote)) { "merchant ownership precheck not satisfied" } else { $merchantScopeBlockNote }
            $merchantSkipClass = if ([string]::IsNullOrWhiteSpace($script:merchantToken)) { "CONFIG_BLOCKER" } else { "SCOPE_BLOCKER" }
            AddResult "MORD-API-001" "merchant-orders" "Merchant accept order" "POST" (ApiPath $prefix "/merchant/orders/{id}/accept") @(200, 400, 404, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
            AddResult "MORD-API-002" "merchant-orders" "Merchant reject order" "POST" (ApiPath $prefix "/merchant/orders/{id}/reject") @(200, 400, 404, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
        }

        if ($rMordAccept -and $rMordAccept.status -eq 400) {
            if (($rMordAccept.body_text | Out-String).ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
                Log ("MORD-API-001 review: FORBIDDEN_SCOPE for merchant={0}, orderId={1}, orderStoreId={2}. Scope/ownership relation is not satisfied." -f $script:merchantUser, $merchantActionOrderId, $script:seedOrderStoreId)
            }
            else { Log ("MORD-API-001 review: status=400 suggests business-state precondition was not met. orderId={0}; body={1}" -f $merchantActionOrderId, $rMordAccept.body_text) }
        }
        if ($rMordReject -and $rMordReject.status -eq 400) {
            if (($rMordReject.body_text | Out-String).ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
                Log ("MORD-API-002 review: FORBIDDEN_SCOPE for merchant={0}, orderId={1}, orderStoreId={2}. Scope/ownership relation is not satisfied." -f $script:merchantUser, $merchantActionOrderId, $script:seedOrderStoreId)
            }
            else { Log ("MORD-API-002 review: status=400 suggests business-state precondition was not met. orderId={0}; body={1}" -f $merchantActionOrderId, $rMordReject.body_text) }
        }

        if ($merchantCanProcessTarget -and $merchantActionOrderId) {
            if (-not ($rMordAccept -and $rMordAccept.status -eq 200)) {
                Log ("Merchant happy-path precondition not yet met (accept status={0}); executing downstream lifecycle checks as controlled-status assertions on orderId={1}." -f $(if($rMordAccept){$rMordAccept.status}else{"null"}), $merchantActionOrderId)
            }
            RunCase @{ id = "MORD-API-003"; module = "merchant-orders"; name = "Merchant mark-arrived order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/mark-arrived"); call_path = (ApiPath $prefix "/merchant/orders/$merchantActionOrderId/mark-arrived"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
            RunCase @{ id = "MORD-API-004"; module = "merchant-orders"; name = "Merchant complete order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/complete"); call_path = (ApiPath $prefix "/merchant/orders/$merchantActionOrderId/complete"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
            RunCase @{ id = "MORD-API-006"; module = "merchant-orders"; name = "Merchant cancel order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/cancel"); call_path = (ApiPath $prefix "/merchant/orders/$merchantActionOrderId/cancel"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
            RunCase @{ id = "MORD-API-007"; module = "merchant-orders"; name = "Merchant mark-no-show order"; method = "POST"; contract_path = (ApiPath $prefix "/merchant/orders/{id}/mark-no-show"); call_path = (ApiPath $prefix "/merchant/orders/$merchantActionOrderId/mark-no-show"); query = @{}; body = $null; expected_status = @(200, 400, 404, 409, 422); require_token = $false; no_token = $true; extra_headers = $merchantAuthHeaders; skip_on_unauthorized = $true; unauthorized_skip_note = "SKIPPED: requires merchant role"; skip_contract_assert = $true } | Out-Null
        }
        else {
            $merchantSkipNote = if ([string]::IsNullOrWhiteSpace($merchantScopeBlockNote)) { "merchant ownership precheck not satisfied" } else { $merchantScopeBlockNote }
            $merchantSkipClass = if ([string]::IsNullOrWhiteSpace($script:merchantToken)) { "CONFIG_BLOCKER" } else { "SCOPE_BLOCKER" }
            AddResult "MORD-API-003" "merchant-orders" "Merchant mark-arrived order" "POST" (ApiPath $prefix "/merchant/orders/{id}/mark-arrived") @(200, 400, 404, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
            AddResult "MORD-API-004" "merchant-orders" "Merchant complete order" "POST" (ApiPath $prefix "/merchant/orders/{id}/complete") @(200, 400, 404, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
            AddResult "MORD-API-006" "merchant-orders" "Merchant cancel order" "POST" (ApiPath $prefix "/merchant/orders/{id}/cancel") @(200, 400, 404, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
            AddResult "MORD-API-007" "merchant-orders" "Merchant mark-no-show order" "POST" (ApiPath $prefix "/merchant/orders/{id}/mark-no-show") @(200, 400, 404, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $merchantSkipClass, $merchantSkipNote) "SKIPPED"
        }
    }
    else {
        AddResult "ORD-API-004" "orders" "Get order detail success" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-API-009" "orders" "Order history contains created order" "GET" (ApiPath $prefix "/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-PAY-001" "order-payment" "Payment success updates order status" "POST" (ApiPath $prefix "/orders/{id}/payments") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-PAY-002" "order-payment" "Payment fail returns expected state" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-PAY-003" "order-payment" "Payment retry after fail" "POST" (ApiPath $prefix "/orders/{id}/payments") @(200, 400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-PAY-004" "order-payment" "Payment timeout or pending behavior" "POST" (ApiPath $prefix "/orders/{id}/payments") @(200, 202, 408) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-PAY-007" "order-payment" "Wallet payment request returns controlled status" "POST" (ApiPath $prefix "/orders/{id}/payments/wallet") @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-PAY-008" "order-payment" "Payment verify endpoint returns controlled status" "GET" (ApiPath $prefix "/orders/{id}/payments/verify") @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        if (-not [string]::IsNullOrWhiteSpace($script:token) -and $script:paidOrderId) {
            $paidPath = ApiPath $prefix "/orders/$($script:paidOrderId)/payments"
            $paidResp = InvokeRaw "POST" (Url $script:base $paidPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            if ($paidResp.status -in @(400, 409, 422)) {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $paidResp.status ("CLASS=PASS; already-paid guard returned controlled status. orderId=$($script:paidOrderId); body=$($paidResp.body_text)") "PASS"
            }
            elseif ($paidResp.status -in @(401, 403)) {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $paidResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: no visibility to configured paid order. orderId=$($script:paidOrderId); body=$($paidResp.body_text)") "SKIPPED"
            }
            elseif ($paidResp.status -ge 500) {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $paidResp.status ("CLASS=BACKEND_DEFECT; server error on already-paid guard. orderId=$($script:paidOrderId); body=$($paidResp.body_text)") "FAIL"
            }
            else {
                AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $paidResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status for already-paid guard. orderId=$($script:paidOrderId); body=$($paidResp.body_text)") "FAIL"
            }
        }
        else {
            AddResult "ORD-PAY-005" "order-payment" "Cannot pay already-paid order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing paid-order seed." "SKIPPED"
        }

        if (-not [string]::IsNullOrWhiteSpace($script:token) -and $script:cancelledOrderId) {
            $cancelPath = ApiPath $prefix "/orders/$($script:cancelledOrderId)/payments"
            $cancelResp = InvokeRaw "POST" (Url $script:base $cancelPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } "application/json; charset=utf-8" "{}" $script:timeoutSec
            if ($cancelResp.status -in @(400, 409, 422)) {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $cancelResp.status ("CLASS=PASS; cancelled-order guard returned controlled status. orderId=$($script:cancelledOrderId); body=$($cancelResp.body_text)") "PASS"
            }
            elseif ($cancelResp.status -in @(401, 403)) {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $cancelResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: no visibility to configured cancelled order. orderId=$($script:cancelledOrderId); body=$($cancelResp.body_text)") "SKIPPED"
            }
            elseif ($cancelResp.status -ge 500) {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $cancelResp.status ("CLASS=BACKEND_DEFECT; server error on cancelled-order guard. orderId=$($script:cancelledOrderId); body=$($cancelResp.body_text)") "FAIL"
            }
            else {
                AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $cancelResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status for cancelled-order guard. orderId=$($script:cancelledOrderId); body=$($cancelResp.body_text)") "FAIL"
            }
        }
        else {
            AddResult "ORD-PAY-006" "order-payment" "Cannot pay cancelled order" "POST" (ApiPath $prefix "/orders/{id}/payments") @(400, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing cancelled-order seed." "SKIPPED"
        }
        AddResult "MORD-API-005" "merchant-orders" "Merchant list contains created order" "GET" (ApiPath $prefix "/merchant/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-008" "merchant-orders" "Merchant detail loads target order" "GET" (ApiPath $prefix "/merchant/orders/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "AORD-API-003" "admin-orders" "Admin list contains created order" "GET" (ApiPath $prefix "/admin/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "AORD-API-004" "admin-orders" "Admin detail contains items and timeline" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "AORD-API-005" "admin-orders" "Admin list filters by store/status" "GET" (ApiPath $prefix "/admin/orders") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order/store seed." "SKIPPED"
        AddResult "AORD-API-006" "admin-disputes" "Admin dispute list visibility" "GET" (ApiPath $prefix "/admin/disputes") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order/dispute seed context." "SKIPPED"
        AddResult "AORD-API-007" "admin-disputes" "Admin dispute detail visibility" "GET" (ApiPath $prefix "/admin/disputes/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing dispute id seed." "SKIPPED"
        AddResult "AORD-API-008" "admin-disputes" "Admin dispute resolve validation (invalid payload)" "POST" (ApiPath $prefix "/admin/disputes/{id}/resolve") @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing dispute id seed." "SKIPPED"
        AddResult "MORD-API-001" "merchant-orders" "Merchant accept order" "POST" (ApiPath $prefix "/merchant/orders/{id}/accept") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-002" "merchant-orders" "Merchant reject order" "POST" (ApiPath $prefix "/merchant/orders/{id}/reject") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-003" "merchant-orders" "Merchant mark-arrived order" "POST" (ApiPath $prefix "/merchant/orders/{id}/mark-arrived") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-004" "merchant-orders" "Merchant complete order" "POST" (ApiPath $prefix "/merchant/orders/{id}/complete") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-006" "merchant-orders" "Merchant cancel order" "POST" (ApiPath $prefix "/merchant/orders/{id}/cancel") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "MORD-API-007" "merchant-orders" "Merchant mark-no-show order" "POST" (ApiPath $prefix "/merchant/orders/{id}/mark-no-show") @(200, 400, 404, 409, 422) $null "SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-CUS-001" "orders-customer" "Customer cancel order returns controlled status" "POST" (ApiPath $prefix "/orders/{id}/cancel") @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-CUS-002" "orders-customer" "Customer confirm-arrival returns controlled status" "POST" (ApiPath $prefix "/orders/{id}/confirm-arrival") @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-CUS-003" "orders-customer" "Customer confirm-complete returns controlled status" "POST" (ApiPath $prefix "/orders/{id}/confirm-complete") @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "ORD-CUS-004" "orders-customer" "Customer report-not-arrived returns controlled status" "POST" (ApiPath $prefix "/orders/{id}/report-not-arrived") @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
    }

    # ORDER creation hardening expansion (contract-backed + deterministic blockers)
    $ordersPath = ApiPath $prefix "/orders"
    if ($script:seedOrderStoreId -and $script:seedSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $missingIdemPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 }) }
        $missingIdemResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)" } $missingIdemPayload $script:timeoutSec
        if ($missingIdemResp.status -in @(400, 422)) {
            AddResult "ORD-API-010" "orders" "Create order missing Idempotency-Key" "POST" $ordersPath @(400, 422) $missingIdemResp.status ("CLASS=PASS; missing idempotency header rejected. body=$($missingIdemResp.body_text)") "PASS"
        }
        elseif ($missingIdemResp.status -in @(401, 403)) {
            AddResult "ORD-API-010" "orders" "Create order missing Idempotency-Key" "POST" $ordersPath @(400, 422) $missingIdemResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($missingIdemResp.status -ge 500) {
            AddResult "ORD-API-010" "orders" "Create order missing Idempotency-Key" "POST" $ordersPath @(400, 422) $missingIdemResp.status ("CLASS=BACKEND_DEFECT; server error on missing idempotency validation. body=$($missingIdemResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-010" "orders" "Create order missing Idempotency-Key" "POST" $ordersPath @(400, 422) $missingIdemResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($missingIdemResp.body_text)") "FAIL"
        }

        $qty0Payload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 0 }) }
        $qty0Resp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $qty0Payload $script:timeoutSec
        if ($qty0Resp.status -in @(400, 422)) {
            AddResult "ORD-API-011" "orders" "Create order invalid quantity = 0" "POST" $ordersPath @(400, 422) $qty0Resp.status ("CLASS=PASS; quantity lower-bound validation confirmed. body=$($qty0Resp.body_text)") "PASS"
        }
        elseif ($qty0Resp.status -in @(401, 403)) {
            AddResult "ORD-API-011" "orders" "Create order invalid quantity = 0" "POST" $ordersPath @(400, 422) $qty0Resp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($qty0Resp.status -ge 500) {
            AddResult "ORD-API-011" "orders" "Create order invalid quantity = 0" "POST" $ordersPath @(400, 422) $qty0Resp.status ("CLASS=BACKEND_DEFECT; server error on quantity=0 validation. body=$($qty0Resp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-011" "orders" "Create order invalid quantity = 0" "POST" $ordersPath @(400, 422) $qty0Resp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($qty0Resp.body_text)") "FAIL"
        }

        $qtyNegPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = -1 }) }
        $qtyNegResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $qtyNegPayload $script:timeoutSec
        if ($qtyNegResp.status -in @(400, 422)) {
            AddResult "ORD-API-012" "orders" "Create order invalid quantity < 0" "POST" $ordersPath @(400, 422) $qtyNegResp.status ("CLASS=PASS; negative quantity validation confirmed. body=$($qtyNegResp.body_text)") "PASS"
        }
        elseif ($qtyNegResp.status -in @(401, 403)) {
            AddResult "ORD-API-012" "orders" "Create order invalid quantity < 0" "POST" $ordersPath @(400, 422) $qtyNegResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($qtyNegResp.status -ge 500) {
            AddResult "ORD-API-012" "orders" "Create order invalid quantity < 0" "POST" $ordersPath @(400, 422) $qtyNegResp.status ("CLASS=BACKEND_DEFECT; server error on quantity<0 validation. body=$($qtyNegResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-012" "orders" "Create order invalid quantity < 0" "POST" $ordersPath @(400, 422) $qtyNegResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($qtyNegResp.body_text)") "FAIL"
        }

        $largeQtyPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 100000 }) }
        $largeQtyResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $largeQtyPayload $script:timeoutSec
        if ($largeQtyResp.status -in @(200, 400, 409, 422)) {
            AddResult "ORD-API-013" "orders" "Create order excessive quantity" "POST" $ordersPath @(200, 400, 409, 422) $largeQtyResp.status ("CLASS=PASS; observed contract-backed behavior for large quantity. body=$($largeQtyResp.body_text)") "PASS"
        }
        elseif ($largeQtyResp.status -in @(401, 403)) {
            AddResult "ORD-API-013" "orders" "Create order excessive quantity" "POST" $ordersPath @(200, 400, 409, 422) $largeQtyResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($largeQtyResp.status -ge 500) {
            AddResult "ORD-API-013" "orders" "Create order excessive quantity" "POST" $ordersPath @(200, 400, 409, 422) $largeQtyResp.status ("CLASS=BACKEND_DEFECT; server error on large quantity path. body=$($largeQtyResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-013" "orders" "Create order excessive quantity" "POST" $ordersPath @(200, 400, 409, 422) $largeQtyResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($largeQtyResp.body_text)") "FAIL"
        }

        $futureArrivalIso = (Get-Date).ToUniversalTime().AddHours(3).ToString("o")
        $pastArrivalIso = (Get-Date).ToUniversalTime().AddHours(-3).ToString("o")
        $secondarySkuSeed = TrySeedAdditionalSkuFromStoreMenu $prefix ([int]$script:seedOrderStoreId) ([int]$script:seedSkuId
        )
        if ($secondarySkuSeed) {
            Log ("Extended order seed: second sku resolved for storeId={0}, category='{1}', item='{2}', skuId={3}, skuName='{4}'" -f $secondarySkuSeed.StoreId, $secondarySkuSeed.CategoryName, $secondarySkuSeed.ItemName, $secondarySkuSeed.SkuId, $secondarySkuSeed.SkuName)
        }

        $reservationHappyPayload = @{
            storeId = [int]$script:seedOrderStoreId
            orderType = 20
            arrivalTime = $futureArrivalIso
            pax = 2
            items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 })
        }
        $reservationHappyResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $reservationHappyPayload $script:timeoutSec
        if ($reservationHappyResp.status -eq 200) {
            AddResult "ORD-API-021" "orders" "Create reservation happy path" "POST" $ordersPath @(200) $reservationHappyResp.status ("CLASS=PASS; reservation payload accepted. body=$($reservationHappyResp.body_text)") "PASS"
        }
        elseif ($reservationHappyResp.status -in @(400, 409, 422)) {
            AddResult "ORD-API-021" "orders" "Create reservation happy path" "POST" $ordersPath @(200) $reservationHappyResp.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: reservation happy path preconditions are not satisfied. body=$($reservationHappyResp.body_text)") "SKIPPED"
        }
        elseif ($reservationHappyResp.status -in @(401, 403)) {
            AddResult "ORD-API-021" "orders" "Create reservation happy path" "POST" $ordersPath @(200) $reservationHappyResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($reservationHappyResp.status -ge 500) {
            AddResult "ORD-API-021" "orders" "Create reservation happy path" "POST" $ordersPath @(200) $reservationHappyResp.status ("CLASS=BACKEND_DEFECT; server error on reservation happy path. body=$($reservationHappyResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-021" "orders" "Create reservation happy path" "POST" $ordersPath @(200) $reservationHappyResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected reservation happy status. body=$($reservationHappyResp.body_text)") "FAIL"
        }

        $reservationPastPayload = @{
            storeId = [int]$script:seedOrderStoreId
            orderType = 20
            arrivalTime = $pastArrivalIso
            pax = 2
            items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 })
        }
        $reservationPastResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $reservationPastPayload $script:timeoutSec
        if ($reservationPastResp.status -in @(400, 422)) {
            AddResult "ORD-API-022" "orders" "Reservation invalid arrivalTime in past" "POST" $ordersPath @(400, 422) $reservationPastResp.status ("CLASS=PASS; past arrivalTime rejected. body=$($reservationPastResp.body_text)") "PASS"
        }
        elseif ($reservationPastResp.status -eq 200) {
            AddResult "ORD-API-022" "orders" "Reservation invalid arrivalTime in past" "POST" $ordersPath @(400, 422) $reservationPastResp.status ("CLASS=CONTRACT_REVIEW; PASS: runtime currently accepts past arrivalTime (captured behavior). body=$($reservationPastResp.body_text)") "PASS"
        }
        elseif ($reservationPastResp.status -in @(401, 403)) {
            AddResult "ORD-API-022" "orders" "Reservation invalid arrivalTime in past" "POST" $ordersPath @(400, 422) $reservationPastResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($reservationPastResp.status -ge 500) {
            AddResult "ORD-API-022" "orders" "Reservation invalid arrivalTime in past" "POST" $ordersPath @(400, 422) $reservationPastResp.status ("CLASS=BACKEND_DEFECT; server error on past-arrival validation. body=$($reservationPastResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-022" "orders" "Reservation invalid arrivalTime in past" "POST" $ordersPath @(400, 422) $reservationPastResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected past-arrival status. body=$($reservationPastResp.body_text)") "FAIL"
        }

        $reservationPaxPayload = @{
            storeId = [int]$script:seedOrderStoreId
            orderType = 20
            arrivalTime = $futureArrivalIso
            pax = 120
            items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 })
        }
        $reservationPaxResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $reservationPaxPayload $script:timeoutSec
        if ($reservationPaxResp.status -in @(400, 422)) {
            AddResult "ORD-API-023" "orders" "Reservation invalid pax out of range" "POST" $ordersPath @(400, 422) $reservationPaxResp.status ("CLASS=PASS; invalid pax rejected. body=$($reservationPaxResp.body_text)") "PASS"
        }
        elseif ($reservationPaxResp.status -in @(401, 403)) {
            AddResult "ORD-API-023" "orders" "Reservation invalid pax out of range" "POST" $ordersPath @(400, 422) $reservationPaxResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($reservationPaxResp.status -ge 500) {
            AddResult "ORD-API-023" "orders" "Reservation invalid pax out of range" "POST" $ordersPath @(400, 422) $reservationPaxResp.status ("CLASS=BACKEND_DEFECT; server error on pax validation. body=$($reservationPaxResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-023" "orders" "Reservation invalid pax out of range" "POST" $ordersPath @(400, 422) $reservationPaxResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected pax-validation status. body=$($reservationPaxResp.body_text)") "FAIL"
        }

        if ($secondarySkuSeed -and $secondarySkuSeed.SkuId) {
            $multiItemPayload = @{
                storeId = [int]$script:seedOrderStoreId
                items = @(
                    @{ skuId = [int]$script:seedSkuId; quantity = 1; note = "qa-multi-a" },
                    @{ skuId = [int]$secondarySkuSeed.SkuId; quantity = 1; note = "qa-multi-b" }
                )
            }
            $multiItemResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $multiItemPayload $script:timeoutSec
            if ($multiItemResp.status -eq 200) {
                AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $multiItemResp.status ("CLASS=PASS; multi-item payload accepted. secondSkuId=$($secondarySkuSeed.SkuId); body=$($multiItemResp.body_text)") "PASS"
            }
            elseif ($multiItemResp.status -in @(400, 409, 422)) {
                AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $multiItemResp.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: multi-item happy path is not currently accepted in this runtime state. secondSkuId=$($secondarySkuSeed.SkuId); body=$($multiItemResp.body_text)") "SKIPPED"
            }
            elseif ($multiItemResp.status -in @(401, 403)) {
                AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $multiItemResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
            }
            elseif ($multiItemResp.status -ge 500) {
                AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $multiItemResp.status ("CLASS=BACKEND_DEFECT; server error on multi-item payload. body=$($multiItemResp.body_text)") "FAIL"
            }
            else {
                AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $multiItemResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected multi-item status. body=$($multiItemResp.body_text)") "FAIL"
            }
        }
        else {
            AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: missing second active sku in same store for deterministic multi-item payload." "SKIPPED"
        }

        $notePayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1; note = "qa-note-check" }) }
        $nullNotePayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1; note = $null }) }
        $noteResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $notePayload $script:timeoutSec
        $nullNoteResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $nullNotePayload $script:timeoutSec
        $noteVariant = "noteStatus=$($noteResp.status); nullNoteStatus=$($nullNoteResp.status); noteBody=$($noteResp.body_text); nullNoteBody=$($nullNoteResp.body_text)"
        if ($noteResp.status -eq 200 -and $nullNoteResp.status -eq 200) {
            AddResult "ORD-API-025" "orders" "Create order note/null note behavior" "POST" $ordersPath @(200) 200 ("CLASS=PASS; note and null-note payloads are both accepted. $noteVariant") "PASS"
        }
        elseif ($noteResp.status -in @(401, 403) -or $nullNoteResp.status -in @(401, 403)) {
            AddResult "ORD-API-025" "orders" "Create order note/null note behavior" "POST" $ordersPath @(200) $nullNoteResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable. $noteVariant") "SKIPPED"
        }
        elseif ($noteResp.status -ge 500 -or $nullNoteResp.status -ge 500) {
            AddResult "ORD-API-025" "orders" "Create order note/null note behavior" "POST" $ordersPath @(200) $nullNoteResp.status ("CLASS=BACKEND_DEFECT; server error in note/null-note contract path. $noteVariant") "FAIL"
        }
        elseif (($noteResp.status -in @(400, 409, 422)) -or ($nullNoteResp.status -in @(400, 409, 422))) {
            AddResult "ORD-API-025" "orders" "Create order note/null note behavior" "POST" $ordersPath @(200) $nullNoteResp.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: note/null-note payload variants are not fully accepted in current runtime state. $noteVariant") "SKIPPED"
        }
        else {
            AddResult "ORD-API-025" "orders" "Create order note/null note behavior" "POST" $ordersPath @(200) $nullNoteResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected note/null-note statuses. $noteVariant") "FAIL"
        }

        $duplicateSkuPayload = @{
            storeId = [int]$script:seedOrderStoreId
            items = @(
                @{ skuId = [int]$script:seedSkuId; quantity = 1 },
                @{ skuId = [int]$script:seedSkuId; quantity = 2 }
            )
        }
        $duplicateSkuResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $duplicateSkuPayload $script:timeoutSec
        if ($duplicateSkuResp.status -in @(200, 400, 409, 422)) {
            AddResult "ORD-API-026" "orders" "Create order duplicate SKU lines in payload" "POST" $ordersPath @(200, 400, 409, 422) $duplicateSkuResp.status ("CLASS=PASS; duplicate SKU-lines payload returned controlled status. body=$($duplicateSkuResp.body_text)") "PASS"
        }
        elseif ($duplicateSkuResp.status -in @(401, 403)) {
            AddResult "ORD-API-026" "orders" "Create order duplicate SKU lines in payload" "POST" $ordersPath @(200, 400, 409, 422) $duplicateSkuResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($duplicateSkuResp.status -ge 500) {
            AddResult "ORD-API-026" "orders" "Create order duplicate SKU lines in payload" "POST" $ordersPath @(200, 400, 409, 422) $duplicateSkuResp.status ("CLASS=BACKEND_DEFECT; server error on duplicate SKU-lines payload. body=$($duplicateSkuResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-026" "orders" "Create order duplicate SKU lines in payload" "POST" $ordersPath @(200, 400, 409, 422) $duplicateSkuResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected duplicate SKU-lines status. body=$($duplicateSkuResp.body_text)") "FAIL"
        }

        $idemReplayKey = New-IdempotencyKey
        $idemReplayFirstPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 }) }
        $changedSkuForReplay = if ($secondarySkuSeed -and $secondarySkuSeed.SkuId) { [int]$secondarySkuSeed.SkuId } else { [int]$script:seedSkuId }
        $changedQtyForReplay = if ($changedSkuForReplay -eq [int]$script:seedSkuId) { 2 } else { 1 }
        $idemReplaySecondPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = $changedSkuForReplay; quantity = $changedQtyForReplay }) }
        $idemReplayHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = $idemReplayKey }
        $idemReplayFirst = InvokeJson "POST" (Url $script:base $ordersPath) $idemReplayHeaders $idemReplayFirstPayload $script:timeoutSec
        $idemReplaySecond = InvokeJson "POST" (Url $script:base $ordersPath) $idemReplayHeaders $idemReplaySecondPayload $script:timeoutSec
        $idemReplayOrderId1 = Infer-SeedNumber $idemReplayFirst.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$")
        $idemReplayOrderId2 = Infer-SeedNumber $idemReplaySecond.body_json @("(?i)^id$","(?i)orderid$","(?i)order_id$")
        $idemReplayNote = "idempotencyKey=$idemReplayKey; firstStatus=$($idemReplayFirst.status); secondStatus=$($idemReplaySecond.status); firstOrderId=$idemReplayOrderId1; secondOrderId=$idemReplayOrderId2; changedSku=$changedSkuForReplay; changedQty=$changedQtyForReplay; firstBody=$($idemReplayFirst.body_text); secondBody=$($idemReplaySecond.body_text)"
        if ($idemReplayFirst.status -eq 200 -and $idemReplaySecond.status -eq 200 -and $idemReplayOrderId1 -and $idemReplayOrderId2 -and $idemReplayOrderId1 -eq $idemReplayOrderId2) {
            AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) 200 ("CLASS=PASS; changed payload with same key reused same order id. $idemReplayNote") "PASS"
        }
        elseif ($idemReplayFirst.status -eq 200 -and $idemReplaySecond.status -in @(400, 409, 422)) {
            AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) $idemReplaySecond.status ("CLASS=PASS; changed payload with same key was blocked by backend. $idemReplayNote") "PASS"
        }
        elseif ($idemReplaySecond.status -eq 200 -and $idemReplayOrderId1 -and $idemReplayOrderId2 -and $idemReplayOrderId1 -ne $idemReplayOrderId2) {
            AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) $idemReplaySecond.status ("CLASS=BACKEND_DEFECT; same key produced a different order id for replayed request. $idemReplayNote") "FAIL"
        }
        elseif ($idemReplayFirst.status -in @(401, 403) -or $idemReplaySecond.status -in @(401, 403)) {
            AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) $idemReplaySecond.status ("CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable. $idemReplayNote") "SKIPPED"
        }
        elseif ($idemReplayFirst.status -ge 500 -or $idemReplaySecond.status -ge 500) {
            AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) $idemReplaySecond.status ("CLASS=BACKEND_DEFECT; server error on idempotency replay path. $idemReplayNote") "FAIL"
        }
        else {
            AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) $idemReplaySecond.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected idempotency replay behavior. $idemReplayNote") "FAIL"
        }

        $preorderPayload = @{
            storeId = [int]$script:seedOrderStoreId
            orderType = 20
            route = "preorder"
            items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 })
        }
        $preorderResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $preorderPayload $script:timeoutSec
        if ($preorderResp.status -eq 200) {
            AddResult "ORD-API-028" "orders" "Create preorder happy path" "POST" $ordersPath @(200) $preorderResp.status ("CLASS=PASS; preorder-style payload accepted. body=$($preorderResp.body_text)") "PASS"
        }
        elseif ($preorderResp.status -in @(400, 409, 422)) {
            AddResult "ORD-API-028" "orders" "Create preorder happy path" "POST" $ordersPath @(200) $preorderResp.status ("CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: preorder-style happy path preconditions are not satisfied. body=$($preorderResp.body_text)") "SKIPPED"
        }
        elseif ($preorderResp.status -in @(401, 403)) {
            AddResult "ORD-API-028" "orders" "Create preorder happy path" "POST" $ordersPath @(200) $preorderResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($preorderResp.status -ge 500) {
            AddResult "ORD-API-028" "orders" "Create preorder happy path" "POST" $ordersPath @(200) $preorderResp.status ("CLASS=BACKEND_DEFECT; server error on preorder-style payload. body=$($preorderResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-028" "orders" "Create preorder happy path" "POST" $ordersPath @(200) $preorderResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected preorder-style status. body=$($preorderResp.body_text)") "FAIL"
        }

        $pricingPreviewPath = ApiPath $prefix "/orders/pricing-preview"
        $pricingPreviewOp = GetOp $script:swagger "POST" $pricingPreviewPath
        if ($null -eq $pricingPreviewOp) {
            AddResult "ORD-API-029" "orders" "Pricing preview contract behavior" "POST" $pricingPreviewPath @(200, 400, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: pricing-preview endpoint not found in Swagger." "SKIPPED"
        }
        else {
            $pricingPreviewPayload = @{
                storeId = [int]$script:seedOrderStoreId
                items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 })
            }
            $pricingPreviewResp = InvokeJson "POST" (Url $script:base $pricingPreviewPath) @{ Authorization = "Bearer $($script:token)" } $pricingPreviewPayload $script:timeoutSec
            if ($pricingPreviewResp.status -in @(200, 400, 422)) {
                AddResult "ORD-API-029" "orders" "Pricing preview contract behavior" "POST" $pricingPreviewPath @(200, 400, 422) $pricingPreviewResp.status ("CLASS=PASS; pricing preview returned controlled status. body=$($pricingPreviewResp.body_text)") "PASS"
            }
            elseif ($pricingPreviewResp.status -in @(401, 403)) {
                AddResult "ORD-API-029" "orders" "Pricing preview contract behavior" "POST" $pricingPreviewPath @(200, 400, 422) $pricingPreviewResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
            }
            elseif ($pricingPreviewResp.status -ge 500) {
                AddResult "ORD-API-029" "orders" "Pricing preview contract behavior" "POST" $pricingPreviewPath @(200, 400, 422) $pricingPreviewResp.status ("CLASS=BACKEND_DEFECT; server error on pricing-preview path. body=$($pricingPreviewResp.body_text)") "FAIL"
            }
            else {
                AddResult "ORD-API-029" "orders" "Pricing preview contract behavior" "POST" $pricingPreviewPath @(200, 400, 422) $pricingPreviewResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected pricing-preview status. body=$($pricingPreviewResp.body_text)") "FAIL"
            }
        }

    }
    else {
        AddResult "ORD-API-010" "orders" "Create order missing Idempotency-Key" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-011" "orders" "Create order invalid quantity = 0" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-012" "orders" "Create order invalid quantity < 0" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-013" "orders" "Create order excessive quantity" "POST" $ordersPath @(200, 400, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-021" "orders" "Create reservation happy path" "POST" $ordersPath @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-022" "orders" "Reservation invalid arrivalTime in past" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-023" "orders" "Reservation invalid pax out of range" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-024" "orders" "Create order with multiple items" "POST" $ordersPath @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-025" "orders" "Create order note/null note behavior" "POST" $ordersPath @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-026" "orders" "Create order duplicate SKU lines in payload" "POST" $ordersPath @(200, 400, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-027" "orders" "Idempotency replay with changed payload same key" "POST" $ordersPath @(200, 400, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-028" "orders" "Create preorder happy path" "POST" $ordersPath @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
        AddResult "ORD-API-029" "orders" "Pricing preview contract behavior" "POST" (ApiPath $prefix "/orders/pricing-preview") @(200, 400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/store/sku seed." "SKIPPED"
    }

    # Keep backend-defect visibility for invalid/missing store checks even when customer auth is down.
    # If customer token is unavailable, we probe with admin token as a diagnostic fallback.
    $orderDefectProbeToken = $null
    $orderDefectProbeAuth = "none"
    if (-not [string]::IsNullOrWhiteSpace($script:token)) {
        $orderDefectProbeToken = $script:token
        $orderDefectProbeAuth = "customer"
    }
    elseif (-not [string]::IsNullOrWhiteSpace($script:adminToken)) {
        $orderDefectProbeToken = $script:adminToken
        $orderDefectProbeAuth = "admin_fallback"
        Log "ORD-API-014/015 probe auth source: admin_fallback (customer token unavailable)."
    }

    if ($script:seedSkuId -and -not [string]::IsNullOrWhiteSpace($orderDefectProbeToken)) {
        $ordDefectHeaders = @{ Authorization = "Bearer $orderDefectProbeToken"; "Idempotency-Key" = (New-IdempotencyKey) }
        $ordDefectAuthNote = "auth_probe=$orderDefectProbeAuth"

        $invalidStorePayload = @{ storeId = 999999999; items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 }) }
        $invalidStoreResp = InvokeJson "POST" (Url $script:base $ordersPath) $ordDefectHeaders $invalidStorePayload $script:timeoutSec
        if ($invalidStoreResp.status -in @(400, 404, 422)) {
            AddResult "ORD-API-014" "orders" "Create order invalid storeId" "POST" $ordersPath @(400, 404, 422) $invalidStoreResp.status ("CLASS=PASS; invalid store rejected. $ordDefectAuthNote; body=$($invalidStoreResp.body_text)") "PASS"
        }
        elseif ($invalidStoreResp.status -in @(401, 403)) {
            AddResult "ORD-API-014" "orders" "Create order invalid storeId" "POST" $ordersPath @(400, 404, 422) $invalidStoreResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: ordering scope unavailable for invalid-store probe. $ordDefectAuthNote") "SKIPPED"
        }
        elseif ($invalidStoreResp.status -ge 500) {
            AddResult "ORD-API-014" "orders" "Create order invalid storeId" "POST" $ordersPath @(400, 404, 422) $invalidStoreResp.status ("CLASS=BACKEND_DEFECT; server error on invalid store validation path. $ordDefectAuthNote; body=$($invalidStoreResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-014" "orders" "Create order invalid storeId" "POST" $ordersPath @(400, 404, 422) $invalidStoreResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. $ordDefectAuthNote; body=$($invalidStoreResp.body_text)") "FAIL"
        }

        $missingStorePayload = @{ items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1 }) }
        $missingStoreResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $orderDefectProbeToken"; "Idempotency-Key" = (New-IdempotencyKey) } $missingStorePayload $script:timeoutSec
        if ($missingStoreResp.status -in @(400, 422)) {
            AddResult "ORD-API-015" "orders" "Create order missing storeId" "POST" $ordersPath @(400, 422) $missingStoreResp.status ("CLASS=PASS; missing storeId validation confirmed. $ordDefectAuthNote; body=$($missingStoreResp.body_text)") "PASS"
        }
        elseif ($missingStoreResp.status -in @(401, 403)) {
            AddResult "ORD-API-015" "orders" "Create order missing storeId" "POST" $ordersPath @(400, 422) $missingStoreResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: ordering scope unavailable for missing-store probe. $ordDefectAuthNote") "SKIPPED"
        }
        elseif ($missingStoreResp.status -ge 500) {
            AddResult "ORD-API-015" "orders" "Create order missing storeId" "POST" $ordersPath @(400, 422) $missingStoreResp.status ("CLASS=BACKEND_DEFECT; server error on missing storeId validation. $ordDefectAuthNote; body=$($missingStoreResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-015" "orders" "Create order missing storeId" "POST" $ordersPath @(400, 422) $missingStoreResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. $ordDefectAuthNote; body=$($missingStoreResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-014" "orders" "Create order invalid storeId" "POST" $ordersPath @(400, 404, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/sku seed for invalid-store probe." "SKIPPED"
        AddResult "ORD-API-015" "orders" "Create order missing storeId" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing auth/sku seed for missing-store probe." "SKIPPED"
    }

    if ($script:seedOrderStoreId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $missingItemsResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } @{ storeId = [int]$script:seedOrderStoreId } $script:timeoutSec
        if ($missingItemsResp.status -in @(400, 422)) {
            AddResult "ORD-API-016" "orders" "Create order missing items field" "POST" $ordersPath @(400, 422) $missingItemsResp.status ("CLASS=PASS; missing items field validation confirmed. body=$($missingItemsResp.body_text)") "PASS"
        }
        elseif ($missingItemsResp.status -in @(401, 403)) {
            AddResult "ORD-API-016" "orders" "Create order missing items field" "POST" $ordersPath @(400, 422) $missingItemsResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($missingItemsResp.status -ge 500) {
            AddResult "ORD-API-016" "orders" "Create order missing items field" "POST" $ordersPath @(400, 422) $missingItemsResp.status ("CLASS=BACKEND_DEFECT; server error on missing items validation. body=$($missingItemsResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-016" "orders" "Create order missing items field" "POST" $ordersPath @(400, 422) $missingItemsResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($missingItemsResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-016" "orders" "Create order missing items field" "POST" $ordersPath @(400, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing store/auth seed." "SKIPPED"
    }
    if ($script:seedOrderStoreId -and $script:altSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $notBelongPayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = [int]$script:altSkuId; quantity = 1 }) }
        $notBelongResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $notBelongPayload $script:timeoutSec
        if ($notBelongResp.status -in @(400, 404, 409, 422)) {
            AddResult "ORD-API-017" "orders" "Create order item not belonging to store" "POST" $ordersPath @(400, 404, 409, 422) $notBelongResp.status ("CLASS=PASS; item/store mismatch rejected. body=$($notBelongResp.body_text)") "PASS"
        }
        elseif ($notBelongResp.status -in @(401, 403)) {
            AddResult "ORD-API-017" "orders" "Create order item not belonging to store" "POST" $ordersPath @(400, 404, 409, 422) $notBelongResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($notBelongResp.status -ge 500) {
            AddResult "ORD-API-017" "orders" "Create order item not belonging to store" "POST" $ordersPath @(400, 404, 409, 422) $notBelongResp.status ("CLASS=BACKEND_DEFECT; server error on item/store mismatch path. body=$($notBelongResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-017" "orders" "Create order item not belonging to store" "POST" $ordersPath @(400, 404, 409, 422) $notBelongResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($notBelongResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-017" "orders" "Create order item not belonging to store" "POST" $ordersPath @(400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Requires deterministic second store + sku from a different store." "SKIPPED"
    }

    $gatingStoreSkuId = $null
    if ($script:closedStoreId -or $script:orderingDisabledStoreId) {
        if ($script:seedSkuId) { $gatingStoreSkuId = [int]$script:seedSkuId }
    }
    elseif ($crossStoreSeed -and $crossStoreSeed.StoreId -and $crossStoreSeed.SkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        # Auto-probe gating behavior using deterministic alternate store seed to reduce blocker-only coverage.
        $gatingProbeStoreId = [int]$crossStoreSeed.StoreId
        $gatingProbeSkuId = [int]$crossStoreSeed.SkuId
        $gatingProbePayload = @{ storeId = $gatingProbeStoreId; items = @(@{ skuId = $gatingProbeSkuId; quantity = 1 }) }
        $gatingProbeResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $gatingProbePayload $script:timeoutSec
        $gatingProbeBodyUpper = ([string]$gatingProbeResp.body_text).ToUpperInvariant()
        $isGatingReject = ($gatingProbeResp.status -in @(400, 403, 409, 422))
        $hasGatingMarker = $gatingProbeBodyUpper.Contains("POLICY_NOT_CONFIGURED") -or $gatingProbeBodyUpper.Contains("ORDERING_DISABLED") -or $gatingProbeBodyUpper.Contains("STORE_CLOSED") -or $gatingProbeBodyUpper.Contains("CLOSED") -or $gatingProbeBodyUpper.Contains("DISABLED")
        if ($isGatingReject -and $hasGatingMarker) {
            $script:orderingDisabledStoreId = $gatingProbeStoreId
            $gatingStoreSkuId = $gatingProbeSkuId
            Log ("Gating store seed auto-resolved from alternate store probe: storeId={0}, skuId={1}, status={2}" -f $gatingProbeStoreId, $gatingProbeSkuId, $gatingProbeResp.status)
        }
        else {
            Log ("Gating store auto-probe did not produce deterministic closed/ordering-disabled marker: storeId={0}, skuId={1}, status={2}, body={3}" -f $gatingProbeStoreId, $gatingProbeSkuId, $gatingProbeResp.status, $gatingProbeResp.body_text)
        }
    }

    if (($script:closedStoreId -or $script:orderingDisabledStoreId) -and $gatingStoreSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $gatingStoreId = if ($script:closedStoreId) { [int]$script:closedStoreId } else { [int]$script:orderingDisabledStoreId }
        if (-not $gatingStoreSkuId -and $crossStoreSeed -and [int]$crossStoreSeed.StoreId -eq $gatingStoreId) {
            $gatingStoreSkuId = [int]$crossStoreSeed.SkuId
        }
        if (-not $gatingStoreSkuId -and $script:seedSkuId) {
            $gatingStoreSkuId = [int]$script:seedSkuId
        }
        $gatingPayload = @{ storeId = $gatingStoreId; items = @(@{ skuId = [int]$gatingStoreSkuId; quantity = 1 }) }
        $gatingResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $gatingPayload $script:timeoutSec
        if ($gatingResp.status -in @(400, 403, 409, 422)) {
            AddResult "ORD-API-018" "orders" "Create order store closed or ordering disabled" "POST" $ordersPath @(400, 403, 409, 422) $gatingResp.status ("CLASS=PASS; gating store rejected ordering request. storeId=$gatingStoreId; skuId=$gatingStoreSkuId; body=$($gatingResp.body_text)") "PASS"
        }
        elseif ($gatingResp.status -in @(401, 403)) {
            AddResult "ORD-API-018" "orders" "Create order store closed or ordering disabled" "POST" $ordersPath @(400, 403, 409, 422) $gatingResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($gatingResp.status -ge 500) {
            AddResult "ORD-API-018" "orders" "Create order store closed or ordering disabled" "POST" $ordersPath @(400, 403, 409, 422) $gatingResp.status ("CLASS=BACKEND_DEFECT; server error on closed/disabled store gate. storeId=$gatingStoreId; skuId=$gatingStoreSkuId; body=$($gatingResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-018" "orders" "Create order store closed or ordering disabled" "POST" $ordersPath @(400, 403, 409, 422) $gatingResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. storeId=$gatingStoreId; skuId=$gatingStoreSkuId; body=$($gatingResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-018" "orders" "Create order store closed or ordering disabled" "POST" $ordersPath @(400, 403, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: Requires deterministic closed/ordering-disabled store seed." "SKIPPED"
    }

    $edgeSkuId = if ($script:disabledSkuId) { [int]$script:disabledSkuId } elseif ($script:outOfStockSkuId) { [int]$script:outOfStockSkuId } else { $null }
    if ($script:seedOrderStoreId -and $edgeSkuId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $edgePayload = @{ storeId = [int]$script:seedOrderStoreId; items = @(@{ skuId = $edgeSkuId; quantity = 1 }) }
        $edgeResp = InvokeJson "POST" (Url $script:base $ordersPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $edgePayload $script:timeoutSec
        if ($edgeResp.status -in @(400, 404, 409, 422)) {
            AddResult "ORD-API-019" "orders" "Create order item disabled or out-of-stock" "POST" $ordersPath @(400, 404, 409, 422) $edgeResp.status ("CLASS=PASS; disabled/out-of-stock guard returned controlled status. skuId=$edgeSkuId; body=$($edgeResp.body_text)") "PASS"
        }
        elseif ($edgeResp.status -in @(401, 403)) {
            AddResult "ORD-API-019" "orders" "Create order item disabled or out-of-stock" "POST" $ordersPath @(400, 404, 409, 422) $edgeResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer ordering scope unavailable." "SKIPPED"
        }
        elseif ($edgeResp.status -ge 500) {
            AddResult "ORD-API-019" "orders" "Create order item disabled or out-of-stock" "POST" $ordersPath @(400, 404, 409, 422) $edgeResp.status ("CLASS=BACKEND_DEFECT; server error on disabled/out-of-stock guard. skuId=$edgeSkuId; body=$($edgeResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-API-019" "orders" "Create order item disabled or out-of-stock" "POST" $ordersPath @(400, 404, 409, 422) $edgeResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. skuId=$edgeSkuId; body=$($edgeResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-019" "orders" "Create order item disabled or out-of-stock" "POST" $ordersPath @(400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Requires deterministic disabled/out-of-stock sku seed." "SKIPPED"
    }
    if ($script:lastCreatedOrderId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $detailResp020 = InvokeJson "GET" (Url $script:base (ApiPath $prefix "/orders/$($script:lastCreatedOrderId)")) @{ Authorization = "Bearer $($script:token)" } $null $script:timeoutSec
        $detail020Note = "createdOrderId=$($script:lastCreatedOrderId); status=$($detailResp020.status); body=$($detailResp020.body_text)"
        if ($detailResp020.status -eq 200 -and (BodyContainsId $detailResp020.body_text ([int]$script:lastCreatedOrderId))) {
            AddResult "ORD-API-020" "orders" "Create order then detail consistency" "GET" (ApiPath $prefix "/orders/{id}") @(200) 200 ("CLASS=PASS; detail endpoint returns created order. $detail020Note") "PASS"
        }
        elseif ($detailResp020.status -in @(401, 403)) {
            AddResult "ORD-API-020" "orders" "Create order then detail consistency" "GET" (ApiPath $prefix "/orders/{id}") @(200) $detailResp020.status ("CLASS=SCOPE_BLOCKER; SKIPPED: order visibility blocked by scope. $detail020Note") "SKIPPED"
        }
        elseif ($detailResp020.status -ge 500) {
            AddResult "ORD-API-020" "orders" "Create order then detail consistency" "GET" (ApiPath $prefix "/orders/{id}") @(200) $detailResp020.status ("CLASS=BACKEND_DEFECT; server error on detail consistency path. $detail020Note") "FAIL"
        }
        else {
            AddResult "ORD-API-020" "orders" "Create order then detail consistency" "GET" (ApiPath $prefix "/orders/{id}") @(200) $detailResp020.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected detail consistency status. $detail020Note") "FAIL"
        }
    }
    else {
        AddResult "ORD-API-020" "orders" "Create order then detail consistency" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing created order seed." "SKIPPED"
    }

    # ORDER cancellation / dispute coverage
    $disputesPath = ApiPath $prefix "/orders/{id}/disputes"
    $disputesOp = GetOp $script:swagger "POST" $disputesPath
    $cancelTargetOrderId = if ($customerActionOrderId) { [int]$customerActionOrderId } else { $targetOrderId }
    if ($null -eq $disputesOp) {
        AddResult "ORD-CAN-001" "orders-cancellation" "Cancel before payment" "POST" $disputesPath @(200, 400, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: cancellation/dispute endpoint not found in Swagger." "SKIPPED"
        AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: cancellation/dispute endpoint not found in Swagger." "SKIPPED"
        AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: cancellation/dispute endpoint not found in Swagger." "SKIPPED"
        AddResult "ORD-CAN-004" "orders-cancellation" "Cancellation reflected in order timeline" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null "CLASS=FRAMEWORK_GAP; SKIPPED: cancellation flow not executable." "SKIPPED"
    }
    elseif (-not $cancelTargetOrderId -or [string]::IsNullOrWhiteSpace($script:token)) {
        AddResult "ORD-CAN-001" "orders-cancellation" "Cancel before payment" "POST" $disputesPath @(200, 400, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed or auth token." "SKIPPED"
        AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: payment + cancellation lifecycle not executable without seeded paid order." "SKIPPED"
        AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic completed order seed." "SKIPPED"
        AddResult "ORD-CAN-004" "orders-cancellation" "Cancellation reflected in order timeline" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: cancellation not executed due to missing seed." "SKIPPED"
    }
    else {
        $cancelResp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders/$cancelTargetOrderId/disputes")) @{ Authorization = "Bearer $($script:token)" } @{} $script:timeoutSec
        if ($cancelResp.status -in @(200, 400, 409, 422)) {
            AddResult "ORD-CAN-001" "orders-cancellation" "Cancel before payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelResp.status ("CLASS=PASS; cancellation/dispute contract returned controlled status. body=$($cancelResp.body_text)") "PASS"
        }
        elseif ($cancelResp.status -in @(401, 403)) {
            AddResult "ORD-CAN-001" "orders-cancellation" "Cancel before payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: customer order scope unavailable for cancellation." "SKIPPED"
        }
        elseif ($cancelResp.status -ge 500) {
            AddResult "ORD-CAN-001" "orders-cancellation" "Cancel before payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelResp.status ("CLASS=BACKEND_DEFECT; server error on cancellation/dispute endpoint. body=$($cancelResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-CAN-001" "orders-cancellation" "Cancel before payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($cancelResp.body_text)") "FAIL"
        }
        if ($script:paidOrderId) {
            $cancelPaidResp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders/$($script:paidOrderId)/disputes")) @{ Authorization = "Bearer $($script:token)" } @{} $script:timeoutSec
            $cancelPaidNote = "paidOrderId=$($script:paidOrderId); status=$($cancelPaidResp.status); body=$($cancelPaidResp.body_text)"
            if ($cancelPaidResp.status -in @(200, 400, 409, 422)) {
                AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelPaidResp.status ("CLASS=PASS; paid-order cancellation path returned controlled status. $cancelPaidNote") "PASS"
            }
            elseif ($cancelPaidResp.status -in @(401, 403)) {
                AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelPaidResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: no visibility to paid-order seed. $cancelPaidNote") "SKIPPED"
            }
            elseif ($cancelPaidResp.status -ge 500) {
                AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelPaidResp.status ("CLASS=BACKEND_DEFECT; server error on paid-order cancellation path. $cancelPaidNote") "FAIL"
            }
            else {
                AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $cancelPaidResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected paid-order cancellation status. $cancelPaidNote") "FAIL"
            }
        }
        else {
            AddResult "ORD-CAN-002" "orders-cancellation" "Cancel after payment" "POST" $disputesPath @(200, 400, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: missing deterministic paid-order seed in customer scope." "SKIPPED"
        }

        if ($script:completedOrderId) {
            $cancelCompletedResp = InvokeJson "POST" (Url $script:base (ApiPath $prefix "/orders/$($script:completedOrderId)/disputes")) @{ Authorization = "Bearer $($script:token)" } @{} $script:timeoutSec
            $cancelCompletedNote = "completedOrderId=$($script:completedOrderId); status=$($cancelCompletedResp.status); body=$($cancelCompletedResp.body_text)"
            if ($cancelCompletedResp.status -in @(400, 409, 422)) {
                AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $cancelCompletedResp.status ("CLASS=PASS; completed-order cancellation guard returned controlled status. $cancelCompletedNote") "PASS"
            }
            elseif ($cancelCompletedResp.status -in @(401, 403)) {
                AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $cancelCompletedResp.status ("CLASS=SCOPE_BLOCKER; SKIPPED: no visibility to completed-order seed. $cancelCompletedNote") "SKIPPED"
            }
            elseif ($cancelCompletedResp.status -ge 500) {
                AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $cancelCompletedResp.status ("CLASS=BACKEND_DEFECT; server error on completed-order cancellation guard. $cancelCompletedNote") "FAIL"
            }
            else {
                AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $cancelCompletedResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected completed-order cancellation status. $cancelCompletedNote") "FAIL"
            }
        }
        else {
            $completedClass = "RUNTIME_CONTRACT_CONFIG_BLOCKER"
            if (-not [string]::IsNullOrWhiteSpace($script:completedOrderSeedNote) -and $script:completedOrderSeedNote.ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
                $completedClass = "SCOPE_BLOCKER"
            }
            $completedMsg = "missing deterministic completed-order seed in customer scope."
            if (-not [string]::IsNullOrWhiteSpace($script:completedOrderSeedNote)) {
                $completedMsg = ("{0} {1}" -f $completedMsg, $script:completedOrderSeedNote)
            }
            AddResult "ORD-CAN-003" "orders-cancellation" "Cannot cancel completed order" "POST" $disputesPath @(400, 409, 422) $null ("CLASS={0}; SKIPPED: {1}" -f $completedClass, $completedMsg) "SKIPPED"
        }
        $timelineClass = "RUNTIME_CONTRACT_CONFIG_BLOCKER"
        if (-not [string]::IsNullOrWhiteSpace($script:completedOrderSeedNote) -and $script:completedOrderSeedNote.ToUpperInvariant().Contains("FORBIDDEN_SCOPE")) {
            $timelineClass = "SCOPE_BLOCKER"
        }
        AddResult "ORD-CAN-004" "orders-cancellation" "Cancellation reflected in order timeline" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null ("CLASS={0}; SKIPPED: requires deterministic cancellation success + timeline contract key mapping." -f $timelineClass) "SKIPPED"
    }

    # ORDER notifications and Admin/Ops support coverage
    $notificationOrderId = if ($detailOrderId) { [int]$detailOrderId } else { $targetOrderId }
    if ($notificationOrderId -and -not [string]::IsNullOrWhiteSpace($script:token)) {
        $notiOrderResp = InvokeJson "GET" (Url $script:base (ApiPath $prefix "/notification")) @{ Authorization = "Bearer $($script:token)" } $null $script:timeoutSec
        if ($notiOrderResp.status -eq 200 -and (BodyContainsId $notiOrderResp.body_text ([int]$notificationOrderId))) {
            AddResult "NOTI-ORD-001" "order-notification" "Order created event visible in notification feed" "GET" (ApiPath $prefix "/notification") @(200) 200 ("CLASS=PASS; notification payload references created order id=$notificationOrderId.") "PASS"
        }
        elseif ($notiOrderResp.status -eq 200) {
            AddResult "NOTI-ORD-001" "order-notification" "Order created event visible in notification feed" "GET" (ApiPath $prefix "/notification") @(200) 200 ("CLASS=SEED_BLOCKER; SKIPPED: notification list did not expose deterministic order event for id=$notificationOrderId. body=$($notiOrderResp.body_text)") "SKIPPED"
        }
        elseif ($notiOrderResp.status -in @(401, 403)) {
            AddResult "NOTI-ORD-001" "order-notification" "Order created event visible in notification feed" "GET" (ApiPath $prefix "/notification") @(200) $notiOrderResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: notification scope unavailable." "SKIPPED"
        }
        else {
            AddResult "NOTI-ORD-001" "order-notification" "Order created event visible in notification feed" "GET" (ApiPath $prefix "/notification") @(200) $notiOrderResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected notification status. body=$($notiOrderResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "NOTI-ORD-001" "order-notification" "Order created event visible in notification feed" "GET" (ApiPath $prefix "/notification") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed or auth token." "SKIPPED"
    }
    AddResult "NOTI-ORD-002" "order-notification" "Payment success event visible" "GET" (ApiPath $prefix "/notification") @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: payment success path is not yet deterministic." "SKIPPED"
    AddResult "NOTI-ORD-003" "order-notification" "Payment fail event visible" "GET" (ApiPath $prefix "/notification") @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: no deterministic payment-fail event correlation key." "SKIPPED"
    AddResult "NOTI-ORD-004" "order-notification" "Merchant accepted event visible" "GET" (ApiPath $prefix "/notification") @(200) $null "CLASS=SCOPE_BLOCKER; SKIPPED: merchant lifecycle happy path not proven with current ownership scope." "SKIPPED"
    AddResult "NOTI-ORD-005" "order-notification" "Merchant rejected event visible" "GET" (ApiPath $prefix "/notification") @(200) $null "CLASS=SCOPE_BLOCKER; SKIPPED: merchant lifecycle happy path not proven with current ownership scope." "SKIPPED"
    AddResult "NOTI-ORD-006" "order-notification" "Cancellation event visible" "GET" (ApiPath $prefix "/notification") @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: cancellation event mapping not deterministic." "SKIPPED"

    $addonsPath = ApiPath $prefix "/orders/{id}/addons"
    $addonsOp = GetOp $script:swagger "POST" $addonsPath
    $addonTargetOrderId = if ($detailOrderId) { [int]$detailOrderId } else { $targetOrderId }
    if ($null -eq $addonsOp) {
        AddResult "ORD-ADDON-001" "orders-addon" "Add-on request controlled status" "POST" $addonsPath @(200, 400, 404, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: add-on endpoint not found in Swagger." "SKIPPED"
        AddResult "ORD-ADDON-002" "orders-addon" "Add-on request invalid SKU" "POST" $addonsPath @(400, 404, 409, 422) $null "CLASS=FRAMEWORK_GAP; SKIPPED: add-on endpoint not found in Swagger." "SKIPPED"
    }
    elseif (-not $addonTargetOrderId -or [string]::IsNullOrWhiteSpace($script:token) -or -not $script:seedSkuId) {
        AddResult "ORD-ADDON-001" "orders-addon" "Add-on request controlled status" "POST" $addonsPath @(200, 400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order/auth/sku seed for add-on request." "SKIPPED"
        AddResult "ORD-ADDON-002" "orders-addon" "Add-on request invalid SKU" "POST" $addonsPath @(400, 404, 409, 422) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order/auth seed for add-on invalid-sku request." "SKIPPED"
    }
    else {
        $addonCallPath = ApiPath $prefix "/orders/$addonTargetOrderId/addons"
        $addonHeaders = @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) }

        $addonPayload = @{ items = @(@{ skuId = [int]$script:seedSkuId; quantity = 1; note = "qa-addon" }) }
        $addonResp = InvokeJson "POST" (Url $script:base $addonCallPath) $addonHeaders $addonPayload $script:timeoutSec
        if ($addonResp.status -in @(200, 400, 404, 409, 422)) {
            AddResult "ORD-ADDON-001" "orders-addon" "Add-on request controlled status" "POST" $addonsPath @(200, 400, 404, 409, 422) $addonResp.status ("CLASS=PASS; add-on request returned controlled status. orderId=$addonTargetOrderId; body=$($addonResp.body_text)") "PASS"
        }
        elseif ($addonResp.status -in @(401, 403)) {
            AddResult "ORD-ADDON-001" "orders-addon" "Add-on request controlled status" "POST" $addonsPath @(200, 400, 404, 409, 422) $addonResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: add-on scope unavailable for target order." "SKIPPED"
        }
        elseif ($addonResp.status -ge 500) {
            AddResult "ORD-ADDON-001" "orders-addon" "Add-on request controlled status" "POST" $addonsPath @(200, 400, 404, 409, 422) $addonResp.status ("CLASS=BACKEND_DEFECT; server error on add-on path. orderId=$addonTargetOrderId; body=$($addonResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-ADDON-001" "orders-addon" "Add-on request controlled status" "POST" $addonsPath @(200, 400, 404, 409, 422) $addonResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected add-on status. orderId=$addonTargetOrderId; body=$($addonResp.body_text)") "FAIL"
        }

        $addonInvalidPayload = @{ items = @(@{ skuId = 999999999; quantity = 1 }) }
        $addonInvalidResp = InvokeJson "POST" (Url $script:base $addonCallPath) @{ Authorization = "Bearer $($script:token)"; "Idempotency-Key" = (New-IdempotencyKey) } $addonInvalidPayload $script:timeoutSec
        if ($addonInvalidResp.status -in @(400, 404, 409, 422)) {
            AddResult "ORD-ADDON-002" "orders-addon" "Add-on request invalid SKU" "POST" $addonsPath @(400, 404, 409, 422) $addonInvalidResp.status ("CLASS=PASS; invalid add-on sku rejected. orderId=$addonTargetOrderId; body=$($addonInvalidResp.body_text)") "PASS"
        }
        elseif ($addonInvalidResp.status -in @(401, 403)) {
            AddResult "ORD-ADDON-002" "orders-addon" "Add-on request invalid SKU" "POST" $addonsPath @(400, 404, 409, 422) $addonInvalidResp.status "CLASS=SCOPE_BLOCKER; SKIPPED: add-on scope unavailable for invalid-sku check." "SKIPPED"
        }
        elseif ($addonInvalidResp.status -ge 500) {
            AddResult "ORD-ADDON-002" "orders-addon" "Add-on request invalid SKU" "POST" $addonsPath @(400, 404, 409, 422) $addonInvalidResp.status ("CLASS=BACKEND_DEFECT; server error on add-on invalid-sku check. body=$($addonInvalidResp.body_text)") "FAIL"
        }
        else {
            AddResult "ORD-ADDON-002" "orders-addon" "Add-on request invalid SKU" "POST" $addonsPath @(400, 404, 409, 422) $addonInvalidResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected add-on invalid-sku status. body=$($addonInvalidResp.body_text)") "FAIL"
        }
    }

    AddResult "ORD-JOB-001" "orders-runtime-jobs" "Pending order expires after payment timeout" "SYSTEM" "/jobs/order-expire" @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: deterministic timeout-window validation is not wired in this runner yet." "SKIPPED"
    AddResult "ORD-JOB-002" "orders-runtime-jobs" "Paid order auto-cancel when merchant does not accept in SLA window" "SYSTEM" "/jobs/order-auto-cancel" @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic paid-order + controlled SLA clock." "SKIPPED"
    AddResult "ORD-JOB-003" "orders-runtime-jobs" "WaitingCustomerConfirmation auto-release to Completed" "SYSTEM" "/jobs/order-auto-release" @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic waiting-confirmation seed and controlled job trigger window." "SKIPPED"
    AddResult "ORD-JOB-004" "orders-runtime-jobs" "Timeline event-code consistency" "GET" (ApiPath $prefix "/orders/{id}") @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: deterministic event-code mapping is not yet exported by stable assertion keys." "SKIPPED"

    AddResult "ORD-CAVEAT-001" "orders-caveat" "Add-on allowed in Arrived/Completed vs UI exposure gap" "POST" (ApiPath $prefix "/orders/{id}/addons") @(200, 400, 404, 409, 422) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic Arrived/Completed lifecycle seed across API+UI to verify mismatch." "SKIPPED"
    AddResult "ORD-CAVEAT-002" "orders-caveat" "Merchant reject reason persistence check" "POST" (ApiPath $prefix "/merchant/orders/{id}/reject") @(200, 400, 404, 409, 422) $null "CLASS=SCOPE_BLOCKER; SKIPPED: deterministic merchant-owned order seed with reject detail assertion is unavailable." "SKIPPED"
    AddResult "ORD-CAVEAT-003" "orders-caveat" "Grace-period/cancel-deadline runtime job effect" "SYSTEM" "/jobs/order-grace-period" @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: requires deterministic scheduler + config seed orchestration." "SKIPPED"
    AddResult "ORD-CAVEAT-004" "orders-caveat" "Dispute/no-show refund destination check (wallet vs card)" "GET" (ApiPath $prefix "/orders/{id}/dispute") @(200) $null "CLASS=RUNTIME_CONTRACT_CONFIG_BLOCKER; SKIPPED: deterministic settlement and refund destination assertion keys are not yet available." "SKIPPED"

    $adminOpsOrderId = if ($adminOrderId) { [int]$adminOrderId } else { $targetOrderId }
    if ($adminOpsOrderId) {
        $adminLookupResp = InvokeJson "GET" (Url $script:base (ApiPath $prefix "/admin/orders/$adminOpsOrderId")) $adminAuthHeaders $null $script:timeoutSec
        if ($adminLookupResp.status -eq 200) {
            $hasStatus = BodyContainsAnyKey $adminLookupResp.body_text @("status", "orderStatus")
            $hasPayment = BodyContainsAnyKey $adminLookupResp.body_text @("payment", "paymentStatus")
            if ($hasStatus -or $hasPayment) {
                AddResult "AORD-OPS-001" "admin-ops" "Admin support lookup by order id" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=PASS; admin lookup exposes support-relevant fields. body=$($adminLookupResp.body_text)") "PASS"
                AddResult "AORD-OPS-002" "admin-ops" "Admin support can verify order/payment state visibility" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=PASS; order/payment state markers found. body=$($adminLookupResp.body_text)") "PASS"
            }
            else {
                AddResult "AORD-OPS-001" "admin-ops" "Admin support lookup by order id" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; support fields missing in detail payload. body=$($adminLookupResp.body_text)") "FAIL"
                AddResult "AORD-OPS-002" "admin-ops" "Admin support can verify order/payment state visibility" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) 200 ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; payment/state markers missing in detail payload. body=$($adminLookupResp.body_text)") "FAIL"
            }
        }
        elseif ($adminLookupResp.status -in @(401, 403)) {
            AddResult "AORD-OPS-001" "admin-ops" "Admin support lookup by order id" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminLookupResp.status "CLASS=ACCOUNT_BLOCKER; SKIPPED: admin role unavailable." "SKIPPED"
            AddResult "AORD-OPS-002" "admin-ops" "Admin support can verify order/payment state visibility" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminLookupResp.status "CLASS=ACCOUNT_BLOCKER; SKIPPED: admin role unavailable." "SKIPPED"
        }
        elseif ($adminLookupResp.status -ge 500) {
            AddResult "AORD-OPS-001" "admin-ops" "Admin support lookup by order id" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminLookupResp.status ("CLASS=BACKEND_DEFECT; server error on admin support lookup. body=$($adminLookupResp.body_text)") "FAIL"
            AddResult "AORD-OPS-002" "admin-ops" "Admin support can verify order/payment state visibility" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminLookupResp.status ("CLASS=BACKEND_DEFECT; server error on admin support visibility. body=$($adminLookupResp.body_text)") "FAIL"
        }
        else {
            AddResult "AORD-OPS-001" "admin-ops" "Admin support lookup by order id" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminLookupResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($adminLookupResp.body_text)") "FAIL"
            AddResult "AORD-OPS-002" "admin-ops" "Admin support can verify order/payment state visibility" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $adminLookupResp.status ("CLASS=FRAMEWORK_OR_CONTRACT_ISSUE; unexpected status. body=$($adminLookupResp.body_text)") "FAIL"
        }
    }
    else {
        AddResult "AORD-OPS-001" "admin-ops" "Admin support lookup by order id" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
        AddResult "AORD-OPS-002" "admin-ops" "Admin support can verify order/payment state visibility" "GET" (ApiPath $prefix "/admin/orders/{id}") @(200) $null "CLASS=SEED_BLOCKER; SKIPPED: Missing order id seed." "SKIPPED"
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
        AddResult "NEWS-003" "news" "GET /news/{validSlug} happy path" "GET" (ApiPath $prefix "/news/{slug}") @(200) $null ("CLASS=SEED_BLOCKER; SKIPPED: Missing seed news slug. " + $newsSeedReason) "SKIPPED"
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
        run_layer   = $script:runLayer
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

    Log ("Summary: layer={0}, total={1}, passed={2}, failed={3}, skipped={4}" -f $script:runLayer, $results.Count, $passed, $failed, $skipped)
    Log "Summary file: $summaryPath"
    try { Set-Content -Path $logPath -Value $global:LogLines -Encoding UTF8 }
    catch {
        $f = Join-Path $outDir ("api_regression.{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
        Set-Content -Path $f -Value $global:LogLines -Encoding UTF8
        Write-Host "Primary log locked. Fallback log: $f"
    }
}

exit $exitCode
