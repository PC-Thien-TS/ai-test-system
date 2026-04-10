param()

$ErrorActionPreference = "Stop"

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

function OptInt([string]$name, $defaultValue = $null) {
    $v = [Environment]::GetEnvironmentVariable($name)
    if ([string]::IsNullOrWhiteSpace($v)) { return $defaultValue }
    $n = 0
    if ([int]::TryParse($v, [ref]$n)) { return $n }
    throw "Invalid integer environment variable: $name=$v"
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

function Url([string]$base, [string]$pathWithQuery) {
    return ($base.TrimEnd("/") + $pathWithQuery)
}

function InvokeJson([string]$method, [string]$url, [hashtable]$headers, $body, [int]$timeoutSec = 30) {
    try {
        $params = @{
            Method = $method
            Uri = $url
            Headers = $headers
            TimeoutSec = $timeoutSec
            ErrorAction = "Stop"
        }
        if ($null -ne $body) {
            $params.ContentType = "application/json; charset=utf-8"
            $params.Body = ($body | ConvertTo-Json -Depth 16 -Compress)
        }
        $resp = Invoke-RestMethod @params
        return [pscustomobject]@{ status = 200; body = $resp; bodyText = ($resp | ConvertTo-Json -Depth 16 -Compress) }
    }
    catch {
        $status = $null
        try { $status = [int]$_.Exception.Response.StatusCode } catch {}
        $bodyText = $_.ErrorDetails.Message
        if ([string]::IsNullOrWhiteSpace($bodyText)) {
            try {
                $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
                $bodyText = $reader.ReadToEnd()
                $reader.Close()
            }
            catch { $bodyText = "" }
        }
        return [pscustomobject]@{ status = $status; body = $null; bodyText = $bodyText }
    }
}

function ExtractToken($loginBody) {
    if ($null -eq $loginBody) { return $null }
    if ($loginBody.token) { return [string]$loginBody.token }
    if ($loginBody.accessToken) { return [string]$loginBody.accessToken }
    if ($loginBody.data -and $loginBody.data.token) { return [string]$loginBody.data.token }
    if ($loginBody.data -and $loginBody.data.accessToken) { return [string]$loginBody.data.accessToken }
    if ($loginBody.login -and $loginBody.login.data -and $loginBody.login.data.token) { return [string]$loginBody.login.data.token }
    return $null
}

function FindSkuInStoreMenu($menuBody, [int]$skuId) {
    if ($null -eq $menuBody -or $null -eq $menuBody.data -or $null -eq $menuBody.data.categories) { return $false }
    foreach ($cat in @($menuBody.data.categories)) {
        foreach ($item in @($cat.items)) {
            foreach ($sku in @($item.skus)) {
                if ($null -ne $sku.id -and [int]$sku.id -eq $skuId) { return $true }
            }
        }
    }
    return $false
}

function Emit([string]$status, [string]$name, [string]$note) {
    Write-Host ("[{0}] {1} - {2}" -f $status, $name, $note)
}

$base = (Req "API_BASE_URL").TrimEnd("/")
$prefix = NormalizePrefix (Opt "API_PREFIX" "/api/v1")
$timeoutSec = [int](Opt "API_TIMEOUT_SEC" "30")

$user = Req "API_USER"
$pass = Req "API_PASS"
$merchantUser = Opt "API_MERCHANT_USER" $user
$merchantPass = Opt "API_MERCHANT_PASS" $pass
$adminUser = Opt "API_ADMIN_USER" $user
$adminPass = Opt "API_ADMIN_PASS" $pass

$storeId = OptInt "API_STORE_ID" 9768
$storeUniqueId = Opt "API_STORE_UNIQUE_ID" ""
$orderStoreId = OptInt "API_ORDER_STORE_ID" $storeId
$orderSkuId = OptInt "API_ORDER_SKU_ID" $null
$altStoreId = OptInt "API_ALT_STORE_ID" $null
$altSkuId = OptInt "API_ALT_SKU_ID" $null
$merchantStoreId = OptInt "API_MERCHANT_STORE_ID" $null
$pendingOrderId = OptInt "API_PENDING_ORDER_ID" $null
$paidOrderId = OptInt "API_PAID_ORDER_ID" $null
$cancelledOrderId = OptInt "API_CANCELLED_ORDER_ID" $null
$completedOrderId = OptInt "API_COMPLETED_ORDER_ID" $null

$failures = 0
$blocked = 0

$loginPath = ApiPath $prefix "/auth/login"
$customerLogin = InvokeJson "POST" (Url $base $loginPath) @{} @{ email = $user; password = $pass; deviceID = "qa-seed-precheck" } $timeoutSec
$customerToken = $null
if ($customerLogin.status -eq 200) {
    $customerToken = (ExtractToken $customerLogin.body)
    if (-not [string]::IsNullOrWhiteSpace($customerToken)) {
        Emit "PASS" "customer_login" "status=200"
    } else {
        Emit "BLOCKED" "customer_login" "status=200 but token not found"
        $blocked++
    }
}
else {
    Emit "BLOCKED" "customer_login" ("status={0}; body={1}" -f $customerLogin.status, $customerLogin.bodyText)
    $blocked++
}

$merchantLogin = InvokeJson "POST" (Url $base $loginPath) @{} @{ email = $merchantUser; password = $merchantPass; deviceID = "qa-seed-precheck-merchant" } $timeoutSec
$merchantToken = $null
if ($merchantLogin.status -eq 200) {
    $merchantToken = (ExtractToken $merchantLogin.body)
    Emit "PASS" "merchant_login" "status=200"
}
else {
    Emit "BLOCKED" "merchant_login" ("status={0}; body={1}" -f $merchantLogin.status, $merchantLogin.bodyText)
    $blocked++
}

$adminLogin = InvokeJson "POST" (Url $base $loginPath) @{} @{ email = $adminUser; password = $adminPass; deviceID = "qa-seed-precheck-admin" } $timeoutSec
$adminToken = $null
if ($adminLogin.status -eq 200) {
    $adminToken = (ExtractToken $adminLogin.body)
    Emit "PASS" "admin_login" "status=200"
}
else {
    Emit "BLOCKED" "admin_login" ("status={0}; body={1}" -f $adminLogin.status, $adminLogin.bodyText)
    $blocked++
}

$storeHeaders = @{}
if (-not [string]::IsNullOrWhiteSpace($customerToken)) { $storeHeaders.Authorization = "Bearer $customerToken" }
$storeResp = InvokeJson "GET" (Url $base (ApiPath $prefix "/store/$storeId")) $storeHeaders $null $timeoutSec
if ($storeResp.status -eq 200) {
    Emit "PASS" "store_exists" ("storeId={0}" -f $storeId)
}
else {
    Emit "BLOCKED" "store_exists" ("storeId={0}; status={1}; body={2}" -f $storeId, $storeResp.status, $storeResp.bodyText)
    $blocked++
}

if (-not [string]::IsNullOrWhiteSpace($storeUniqueId)) {
    $u = [System.Uri]::EscapeDataString($storeUniqueId)
    $storeUResp = InvokeJson "GET" (Url $base ((ApiPath $prefix "/store/$u") + "?UniqueId=$u")) @{} $null $timeoutSec
    if ($storeUResp.status -eq 200) {
        Emit "PASS" "store_unique_id_resolves" ("uniqueId={0}" -f $storeUniqueId)
    }
    else {
        Emit "BLOCKED" "store_unique_id_resolves" ("uniqueId={0}; status={1}; body={2}" -f $storeUniqueId, $storeUResp.status, $storeUResp.bodyText)
        $blocked++
    }
}

if ($orderStoreId -and $orderSkuId) {
    $menuResp = InvokeJson "GET" (Url $base (ApiPath $prefix "/stores/$orderStoreId/menu")) @{} $null $timeoutSec
    if ($menuResp.status -eq 200 -and (FindSkuInStoreMenu $menuResp.body ([int]$orderSkuId))) {
        Emit "PASS" "order_sku_belongs_to_order_store" ("storeId={0}; skuId={1}" -f $orderStoreId, $orderSkuId)
    }
    else {
        Emit "BLOCKED" "order_sku_belongs_to_order_store" ("storeId={0}; skuId={1}; status={2}" -f $orderStoreId, $orderSkuId, $menuResp.status)
        $blocked++
    }
}
else {
    Emit "BLOCKED" "order_sku_belongs_to_order_store" "API_ORDER_STORE_ID/API_ORDER_SKU_ID not fully configured"
    $blocked++
}

if ($altStoreId -and $altSkuId) {
    $altMenuResp = InvokeJson "GET" (Url $base (ApiPath $prefix "/stores/$altStoreId/menu")) @{} $null $timeoutSec
    if ($altMenuResp.status -eq 200 -and (FindSkuInStoreMenu $altMenuResp.body ([int]$altSkuId))) {
        Emit "PASS" "alt_sku_belongs_to_alt_store" ("storeId={0}; skuId={1}" -f $altStoreId, $altSkuId)
    }
    else {
        Emit "BLOCKED" "alt_sku_belongs_to_alt_store" ("storeId={0}; skuId={1}; status={2}" -f $altStoreId, $altSkuId, $altMenuResp.status)
        $blocked++
    }
}

if ($merchantStoreId -and -not [string]::IsNullOrWhiteSpace($merchantToken)) {
    $mList = InvokeJson "GET" (Url $base ((ApiPath $prefix "/merchant/orders") + "?PageNumber=1&PageSize=20")) @{ Authorization = "Bearer $merchantToken" } $null $timeoutSec
    if ($mList.status -eq 200 -and ($mList.bodyText -match ('"storeId"\s*:\s*{0}([,\s\}}])' -f [regex]::Escape([string]$merchantStoreId)))) {
        Emit "PASS" "merchant_store_ownership_hint" ("merchant storeId={0} observed in merchant order list" -f $merchantStoreId)
    }
    elseif ($mList.status -eq 200) {
        Emit "BLOCKED" "merchant_store_ownership_hint" ("merchant storeId={0} not observed in first page merchant list" -f $merchantStoreId)
        $blocked++
    }
    else {
        Emit "BLOCKED" "merchant_store_ownership_hint" ("status={0}; body={1}" -f $mList.status, $mList.bodyText)
        $blocked++
    }
}

if (-not [string]::IsNullOrWhiteSpace($adminToken)) {
    $adminHeaders = @{ Authorization = "Bearer $adminToken" }
    $adminChecks = @(
        @{ Name = "admin_scope_orders"; Path = (ApiPath $prefix "/admin/orders?pageNumber=1&pageSize=1") },
        @{ Name = "admin_scope_category_admin"; Path = (ApiPath $prefix "/category-admin/list") },
        @{ Name = "admin_scope_dashboard"; Path = (ApiPath $prefix "/Dashboard/user-registrations") },
        @{ Name = "admin_scope_member"; Path = (ApiPath $prefix "/member/list") },
        @{ Name = "admin_scope_store_category_admin"; Path = (ApiPath $prefix "/store-category/admin/selection") }
    )
    foreach ($chk in $adminChecks) {
        $resp = InvokeJson "GET" (Url $base $chk.Path) $adminHeaders $null $timeoutSec
        if ($resp.status -eq 200) {
            Emit "PASS" $chk.Name ("status={0}" -f $resp.status)
        }
        elseif ($resp.status -in @(401, 403)) {
            Emit "BLOCKED" $chk.Name ("admin scope missing for endpoint; status={0}" -f $resp.status)
            $blocked++
        }
        else {
            Emit "BLOCKED" $chk.Name ("status={0}; body={1}" -f $resp.status, $resp.bodyText)
            $blocked++
        }
    }

    if ($null -ne (OptInt "API_CATEGORY_ADMIN_ID" $null)) {
        $catId = [int](OptInt "API_CATEGORY_ADMIN_ID" $null)
        $resp = InvokeJson "GET" (Url $base (ApiPath $prefix "/category-admin/detail/$catId")) $adminHeaders $null $timeoutSec
        if ($resp.status -eq 200) { Emit "PASS" "admin_scope_category_detail" ("id={0}" -f $catId) }
        elseif ($resp.status -in @(401, 403)) { Emit "BLOCKED" "admin_scope_category_detail" ("id={0}; admin scope missing status={1}" -f $catId, $resp.status); $blocked++ }
        else { Emit "BLOCKED" "admin_scope_category_detail" ("id={0}; status={1}" -f $catId, $resp.status); $blocked++ }
    }

    if ($null -ne (OptInt "API_STORE_CATEGORY_ADMIN_ID" $null)) {
        $scId = [int](OptInt "API_STORE_CATEGORY_ADMIN_ID" $null)
        $resp = InvokeJson "GET" (Url $base (ApiPath $prefix "/store-category/admin/detail/$scId")) $adminHeaders $null $timeoutSec
        if ($resp.status -eq 200) { Emit "PASS" "admin_scope_store_category_detail" ("id={0}" -f $scId) }
        elseif ($resp.status -in @(401, 403)) { Emit "BLOCKED" "admin_scope_store_category_detail" ("id={0}; admin scope missing status={1}" -f $scId, $resp.status); $blocked++ }
        else { Emit "BLOCKED" "admin_scope_store_category_detail" ("id={0}; status={1}" -f $scId, $resp.status); $blocked++ }
    }
}

$runtimeSeeds = @(
    @{ Name = "pending_order_seed"; Id = $pendingOrderId },
    @{ Name = "paid_order_seed"; Id = $paidOrderId },
    @{ Name = "cancelled_order_seed"; Id = $cancelledOrderId },
    @{ Name = "completed_order_seed"; Id = $completedOrderId }
)
foreach ($seed in $runtimeSeeds) {
    if (-not $seed.Id) { continue }
    if ([string]::IsNullOrWhiteSpace($customerToken)) {
        Emit "BLOCKED" $seed.Name ("id={0}; customer token unavailable for existence check" -f $seed.Id)
        $blocked++
        continue
    }
    $resp = InvokeJson "GET" (Url $base (ApiPath $prefix "/orders/$($seed.Id)")) @{ Authorization = "Bearer $customerToken" } $null $timeoutSec
    if ($resp.status -eq 200) {
        Emit "PASS" $seed.Name ("id={0}" -f $seed.Id)
    }
    elseif ($resp.status -in @(401, 403)) {
        Emit "BLOCKED" $seed.Name ("id={0}; scope mismatch status={1}" -f $seed.Id, $resp.status)
        $blocked++
    }
    else {
        Emit "BLOCKED" $seed.Name ("id={0}; status={1}" -f $seed.Id, $resp.status)
        $blocked++
    }
}

Write-Host ("SUMMARY: PASS/BLOCKED/FAIL diagnostics complete. failures={0}, blocked={1}" -f $failures, $blocked)
if ($failures -gt 0) { exit 1 }
exit 0
