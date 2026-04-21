"""Build deterministic merchant transition seed IDs for Wave 1 tests.

Discovery-first strategy:
1) Authenticate customer + merchant and switch merchant store context.
2) Discover merchant-visible orders and classify by status.
3) Fill seed slots deterministically (newest order id first).
4) Create a new pending order only when pending seed is missing and creation is possible.
5) Export machine + human readable outputs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.rankmate_wave1.helpers.api_client import RankmateApiClient  # noqa: E402
from tests.rankmate_wave1.helpers.auth_helper import AuthHelper  # noqa: E402
from tests.rankmate_wave1.helpers.config import Wave1Config, load_wave1_config  # noqa: E402
from tests.rankmate_wave1.helpers.merchant_helper import MerchantHelper  # noqa: E402
from tests.rankmate_wave1.helpers.order_helper import OrderHelper  # noqa: E402
from tests.rankmate_wave1.helpers.assertion_helper import envelope_data  # noqa: E402


SEED_SLOTS: list[str] = [
    "API_PENDING_ORDER_ID",
    "API_PAID_ORDER_ID",
    "API_REJECTABLE_PAID_ORDER_ID",
    "API_ACCEPTED_ORDER_ID",
    "API_ARRIVED_ORDER_ID",
    "API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID",
    "API_NON_PAID_ORDER_ID",
    "API_STALE_TRANSITION_ORDER_ID",
    "API_NO_SHOW_ORDER_ID",
    "API_MERCHANT_CANCELLABLE_ORDER_ID",
    "API_CONSISTENCY_ORDER_ID",
    "API_CANCELLED_ORDER_ID",
    "API_COMPLETED_ORDER_ID",
]

MUTATION_SLOTS = {
    "API_PAID_ORDER_ID",
    "API_REJECTABLE_PAID_ORDER_ID",
    "API_ACCEPTED_ORDER_ID",
    "API_ARRIVED_ORDER_ID",
    "API_MERCHANT_CANCELLABLE_ORDER_ID",
    "API_NO_SHOW_ORDER_ID",
}

STATUS_NAMES = {
    10: "Pending",
    20: "Paid",
    21: "Accepted",
    22: "Arrived",
    23: "Completed",
    24: "WaitingCustomerConfirmation",
    30: "Failed",
    40: "Refunded",
    50: "Expired",
    60: "Cancelled",
    90: "Rejected",
    91: "NoShow",
}


@dataclass
class SlotResult:
    slot: str
    order_id: int | None
    status: int | None
    source: str
    note: str


def _load_json_or_none(response) -> dict[str, Any] | None:
    try:
        return response.json()
    except Exception:
        return None


def _extract_rows(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    data = envelope_data(payload)
    if isinstance(data, dict):
        for key in ("data", "items", "rows", "records"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, dict)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    return []


def _extract_id_and_status(row: dict[str, Any]) -> tuple[int | None, int | None]:
    raw_id = row.get("id")
    if not isinstance(raw_id, int):
        raw_id = row.get("orderId")
    raw_status = row.get("status")
    if not isinstance(raw_status, int):
        raw_status = row.get("orderStatus")
    return (raw_id if isinstance(raw_id, int) else None, raw_status if isinstance(raw_status, int) else None)


def _build_client(cfg: Wave1Config) -> RankmateApiClient:
    return RankmateApiClient(
        base_url=cfg.normalized_base_url,
        api_prefix=cfg.normalized_api_prefix,
        timeout_sec=cfg.timeout_sec,
        verify_ssl=cfg.verify_ssl,
        debug=cfg.debug,
    )


def _login(auth: AuthHelper, email: str | None, password: str | None, role: str) -> tuple[str | None, str]:
    if not email or not password:
        return None, f"{role} credentials missing in .env"
    try:
        response = auth.login(email=email, password=password)
    except Exception as exc:
        return None, f"{role} login request failed: {exc}"
    payload = _load_json_or_none(response)
    if response.status_code != 200 or not isinstance(payload, dict):
        return None, f"{role} login failed status={response.status_code}"
    data = envelope_data(payload)
    if not isinstance(data, dict):
        return None, f"{role} login payload missing data"
    token = data.get("token")
    if not isinstance(token, str) or not token.strip():
        return None, f"{role} login payload missing token"
    return token, "ok"


def _merchant_store_session(cfg: Wave1Config, merchant: MerchantHelper, merchant_user_token: str) -> tuple[str | None, int | None, str]:
    try:
        verify_resp = merchant.get_verify_stores(token=merchant_user_token)
    except Exception as exc:
        return None, None, f"merchant verify stores request failed: {exc}"
    verify_payload = _load_json_or_none(verify_resp)
    if verify_resp.status_code != 200 or not isinstance(verify_payload, dict):
        return None, None, f"merchant verify stores failed status={verify_resp.status_code}"

    preferred_store = cfg.merchant_store_id or cfg.order_store_id or cfg.store_id
    try:
        store_id, profile_id = merchant.extract_store_candidate(verify_payload, preferred_store)
    except Exception as exc:  # pragma: no cover - runtime safety
        return None, None, f"merchant store selection failed: {exc}"

    try:
        switch_resp = merchant.switch_profile(token=merchant_user_token, store_id=store_id, profile_id=profile_id)
    except Exception as exc:
        return None, None, f"merchant switch profile request failed: {exc}"
    switch_payload = _load_json_or_none(switch_resp)
    if switch_resp.status_code != 200 or not isinstance(switch_payload, dict):
        return None, None, f"merchant switch profile failed status={switch_resp.status_code}"
    data = envelope_data(switch_payload)
    if not isinstance(data, dict):
        return None, None, "merchant switch payload missing data"
    store_token = data.get("token")
    if not isinstance(store_token, str) or not store_token.strip():
        return None, None, "merchant switch payload missing token"
    return store_token, store_id, "ok"


def _fetch_merchant_orders(client: RankmateApiClient, merchant_store_token: str, store_id: int, max_pages: int) -> tuple[dict[int, dict[str, Any]], list[str]]:
    notes: list[str] = []
    orders: dict[int, dict[str, Any]] = {}

    def fetch_with_status(status: int | None) -> None:
        for page in range(max_pages):
            params: dict[str, Any] = {"pageNumber": page, "pageSize": 50, "storeId": store_id}
            if status is not None:
                params["status"] = status
            try:
                resp = client.get("/merchant/orders", token=merchant_store_token, params=params)
            except Exception as exc:
                notes.append(
                    f"list_orders status_filter={status if status is not None else 'ALL'} page={page} request failed: {exc}"
                )
                break
            if resp.status_code != 200:
                notes.append(
                    f"list_orders status_filter={status if status is not None else 'ALL'} page={page} -> {resp.status_code}"
                )
                break
            payload = _load_json_or_none(resp)
            rows = _extract_rows(payload)
            if not rows:
                break
            for row in rows:
                order_id, order_status = _extract_id_and_status(row)
                if not isinstance(order_id, int) or not isinstance(order_status, int):
                    continue
                existing = orders.get(order_id)
                if existing is None:
                    orders[order_id] = {"id": order_id, "status": order_status, "row": row}
                else:
                    existing["status"] = order_status
                    existing["row"] = row
            if len(rows) < 50:
                break

    # Discovery-first: broad pull, then targeted statuses.
    fetch_with_status(None)
    for s in (10, 20, 21, 22, 23, 24, 50, 60, 90, 91):
        fetch_with_status(s)
    return orders, notes


def _safe_number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def _has_offline_due(order_detail_data: dict[str, Any]) -> bool:
    for key in (
        "payAtStoreRemainingAmount",
        "remainingPayAtStoreAmount",
        "remainingAtStoreAmount",
        "remainingAmountAtStore",
    ):
        if _safe_number(order_detail_data.get(key)) > 0:
            return True

    total = _safe_number(order_detail_data.get("totalAmount"))
    due_now = _safe_number(order_detail_data.get("totalDueNowAmount"))
    return (total - due_now) > 0.01


def _fetch_detail_cache(client: RankmateApiClient, merchant_store_token: str, order_ids: Iterable[int]) -> dict[int, dict[str, Any]]:
    details: dict[int, dict[str, Any]] = {}
    for oid in sorted(set(order_ids), reverse=True):
        try:
            resp = client.get(f"/merchant/orders/{oid}", token=merchant_store_token)
        except Exception:
            continue
        payload = _load_json_or_none(resp)
        if resp.status_code == 200 and isinstance(payload, dict):
            data = envelope_data(payload)
            if isinstance(data, dict):
                details[oid] = data
    return details


def _pick_candidate(
    *,
    orders: dict[int, dict[str, Any]],
    details: dict[int, dict[str, Any]],
    statuses: set[int],
    used_ids: set[int],
    unique_preferred: bool,
    require_offline_due: bool = False,
) -> tuple[int | None, int | None, str]:
    candidates = [o for o in orders.values() if o["status"] in statuses]
    candidates.sort(key=lambda x: int(x["id"]), reverse=True)

    preferred = [c for c in candidates if c["id"] not in used_ids] if unique_preferred else candidates
    pool = preferred or candidates
    if require_offline_due:
        filtered: list[dict[str, Any]] = []
        for c in pool:
            detail_data = details.get(int(c["id"]))
            if isinstance(detail_data, dict) and _has_offline_due(detail_data):
                filtered.append(c)
        pool = filtered

    if not pool:
        return None, None, "no candidate discovered"
    chosen = pool[0]
    note = "selected newest order id by deterministic rule (descending id)"
    if unique_preferred and int(chosen["id"]) in used_ids:
        note += "; reused because unique candidate unavailable"
    return int(chosen["id"]), int(chosen["status"]), note


def _resolve_sku_for_store(client: RankmateApiClient, store_id: int) -> tuple[int | None, str]:
    try:
        resp = client.get(f"/stores/{store_id}/menu")
    except Exception as exc:
        return None, f"menu lookup request failed for storeId={store_id}: {exc}"
    payload = _load_json_or_none(resp)
    if resp.status_code != 200 or not isinstance(payload, dict):
        return None, f"menu lookup failed for storeId={store_id} status={resp.status_code}"
    data = envelope_data(payload)
    if not isinstance(data, dict):
        return None, "menu payload missing data object"
    categories = data.get("categories")
    if not isinstance(categories, list):
        return None, "menu categories missing"
    for category in categories:
        if not isinstance(category, dict):
            continue
        items = category.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            skus = item.get("skus")
            if not isinstance(skus, list):
                continue
            for sku in skus:
                if not isinstance(sku, dict):
                    continue
                sku_id = sku.get("id")
                if not isinstance(sku_id, int):
                    continue
                is_active = sku.get("isActive")
                availability_status = sku.get("availabilityStatus")
                if (is_active is False) or (isinstance(availability_status, int) and availability_status != 0):
                    continue
                return sku_id, f"resolved first active skuId={sku_id} from store menu"
    return None, "no active sku found in menu"


def _create_pending_seed(
    *,
    cfg: Wave1Config,
    client: RankmateApiClient,
    order: OrderHelper,
    customer_token: str | None,
    store_id: int | None,
) -> tuple[int | None, str]:
    if not customer_token:
        return None, "customer token unavailable"
    if not isinstance(store_id, int):
        return None, "merchant store id unavailable"
    sku_id, sku_note = _resolve_sku_for_store(client, store_id)
    if not isinstance(sku_id, int):
        return None, f"pending seed creation blocked: {sku_note}"

    try:
        create = order.create_order(
            token=customer_token,
            store_id=store_id,
            items=order.build_items(sku_id, quantity=1),
            idempotency_key=f"wave1-seed-builder-{uuid4().hex[:12]}",
        )
    except Exception as exc:
        return None, f"create order request failed: {exc}"
    payload = _load_json_or_none(create)
    if create.status_code != 200 or not isinstance(payload, dict):
        return None, f"create order failed status={create.status_code}"
    data = envelope_data(payload)
    if not isinstance(data, dict):
        return None, "create order response missing data"
    order_id = data.get("id")
    if not isinstance(order_id, int):
        return None, "create order response missing id"
    return order_id, f"created pending via customer create_order; {sku_note}"


def _compose_slot_results(
    orders: dict[int, dict[str, Any]],
    details: dict[int, dict[str, Any]],
    cfg: Wave1Config,
) -> list[SlotResult]:
    used_ids: set[int] = set()
    results: list[SlotResult] = []

    def add(
        slot: str,
        statuses: set[int],
        *,
        unique_preferred: bool = False,
        require_offline_due: bool = False,
    ) -> None:
        oid, status, note = _pick_candidate(
            orders=orders,
            details=details,
            statuses=statuses,
            used_ids=used_ids,
            unique_preferred=unique_preferred,
            require_offline_due=require_offline_due,
        )
        if oid is not None and unique_preferred:
            used_ids.add(oid)
        results.append(
            SlotResult(
                slot=slot,
                order_id=oid,
                status=status,
                source="discovered" if oid is not None else "missing",
                note=note,
            )
        )

    # Transition-driving slots prefer unique ids to avoid cross-test mutation contamination.
    add("API_PAID_ORDER_ID", {20}, unique_preferred=True)
    add("API_REJECTABLE_PAID_ORDER_ID", {20}, unique_preferred=True)
    add("API_ACCEPTED_ORDER_ID", {21}, unique_preferred=True)
    add("API_ARRIVED_ORDER_ID", {22}, unique_preferred=True)
    add("API_MERCHANT_CANCELLABLE_ORDER_ID", {20, 21, 10}, unique_preferred=True)
    add("API_NO_SHOW_ORDER_ID", {91, 21}, unique_preferred=True)

    add("API_PENDING_ORDER_ID", {10})
    add("API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID", {22}, require_offline_due=True)
    add("API_CANCELLED_ORDER_ID", {60})
    add("API_COMPLETED_ORDER_ID", {23})
    add("API_NON_PAID_ORDER_ID", {10, 21, 22, 23, 24, 60, 90, 91, 40, 50, 30})
    add("API_STALE_TRANSITION_ORDER_ID", {23, 24, 60, 90, 91, 40, 50, 30})
    add("API_CONSISTENCY_ORDER_ID", {20, 21, 22, 23, 24, 60, 90, 91, 40, 50, 30})

    # Preserve explicit env overrides if they exist and are integers.
    env_override_map = {
        "API_PENDING_ORDER_ID": cfg.pending_order_id,
        "API_PAID_ORDER_ID": cfg.paid_order_id,
        "API_REJECTABLE_PAID_ORDER_ID": cfg.rejectable_paid_order_id,
        "API_ACCEPTED_ORDER_ID": cfg.accepted_order_id,
        "API_ARRIVED_ORDER_ID": cfg.arrived_order_id,
        "API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID": cfg.arrived_order_with_offline_due_id,
        "API_NON_PAID_ORDER_ID": cfg.non_paid_order_id,
        "API_STALE_TRANSITION_ORDER_ID": cfg.stale_transition_order_id,
        "API_NO_SHOW_ORDER_ID": cfg.no_show_order_id,
        "API_MERCHANT_CANCELLABLE_ORDER_ID": cfg.merchant_cancellable_order_id,
        "API_CONSISTENCY_ORDER_ID": cfg.consistency_order_id,
        "API_CANCELLED_ORDER_ID": cfg.cancelled_order_id,
        "API_COMPLETED_ORDER_ID": cfg.completed_order_id,
    }
    result_by_slot = {r.slot: r for r in results}
    for slot, override in env_override_map.items():
        if isinstance(override, int):
            existing = result_by_slot[slot]
            existing.order_id = override
            existing.source = "env_existing"
            existing.note = "kept existing env value"
            status = orders.get(override, {}).get("status")
            existing.status = status if isinstance(status, int) else None
    return results


def _write_outputs(
    *,
    json_path: Path,
    env_path: Path,
    report_path: Path,
    results: list[SlotResult],
    diagnostics: list[str],
    mutation_notes: list[str],
    metadata: dict[str, Any],
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "generatedAtUtc": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata,
        "results": [
            {
                "slot": r.slot,
                "orderId": r.order_id,
                "status": r.status,
                "statusName": STATUS_NAMES.get(r.status or -1),
                "source": r.source,
                "note": r.note,
            }
            for r in results
        ],
        "diagnostics": diagnostics,
        "mutations": mutation_notes,
    }
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    env_lines = [
        "# Auto-generated by scripts/build_merchant_state_seeds.py",
        f"# generated_at_utc={data['generatedAtUtc']}",
    ]
    for r in results:
        if r.order_id is None:
            env_lines.append(f"# {r.slot}=  # MISSING ({r.note})")
        else:
            env_lines.append(f"{r.slot}={r.order_id}")
    env_path.write_text("\n".join(env_lines) + "\n", encoding="utf-8")

    rows = []
    for r in results:
        status_name = STATUS_NAMES.get(r.status or -1, "")
        oid = str(r.order_id) if r.order_id is not None else ""
        rows.append(f"| `{r.slot}` | `{oid}` | `{r.status or ''}` | `{status_name}` | `{r.source}` | {r.note} |")

    report = [
        "# MERCHANT_STATE_SEEDS_REPORT",
        "",
        f"- Generated at: `{data['generatedAtUtc']}`",
        f"- Base URL: `{metadata.get('baseUrl', '')}`",
        f"- Merchant store id: `{metadata.get('merchantStoreId', '')}`",
        "",
        "Deterministic selection rule:",
        "- Discovery-first from merchant list/detail.",
        "- Choose newest candidate (`highest order id`) per slot.",
        "- For transition-driving slots, prefer distinct order ids to reduce cross-test mutation contamination.",
        "",
        "## Seed Slots",
        "",
        "| Seed Slot | Order ID | Status | Status Name | Source | Note |",
        "|---|---:|---:|---|---|---|",
        *rows,
        "",
        "## Copy-ready .env lines",
        "",
        "```env",
        *[line for line in env_lines if not line.startswith("# Auto-generated") and not line.startswith("# generated_at_utc")],
        "```",
        "",
        "## Diagnostics",
        "",
        *([f"- {line}" for line in diagnostics] if diagnostics else ["- none"]),
        "",
        "## Mutations performed",
        "",
        *([f"- {line}" for line in mutation_notes] if mutation_notes else ["- none (discovery only)"]),
        "",
    ]
    report_path.write_text("\n".join(report), encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic merchant state seeds for Wave 1")
    parser.add_argument("--base-url", default=None, help="Optional API base url override")
    parser.add_argument("--max-pages", type=int, default=5, help="Max merchant list pages per query")
    parser.add_argument("--allow-create", action="store_true", help="Allow safe pending-order creation when missing")
    parser.add_argument(
        "--json-out",
        default="merchant_state_seeds.json",
        help="Path for machine-readable seed output",
    )
    parser.add_argument(
        "--env-out",
        default="merchant_state_seeds.env",
        help="Path for copy-ready env output",
    )
    parser.add_argument(
        "--report-out",
        default="docs/wave1_runtime/MERCHANT_STATE_SEEDS_REPORT.md",
        help="Path for markdown report output",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    diagnostics: list[str] = []
    mutation_notes: list[str] = []

    cfg = load_wave1_config(REPO_ROOT)
    if args.base_url:
        os.environ["API_BASE_URL"] = args.base_url
        cfg = load_wave1_config(REPO_ROOT)

    client = _build_client(cfg)
    auth = AuthHelper(
        client,
        phone_number=cfg.phone_number or "string",
        campaign=cfg.campaign or "string",
        device_id=cfg.device_id or "string",
    )
    merchant = MerchantHelper(client)
    order = OrderHelper(client)

    customer_token, customer_note = _login(auth, cfg.user_email, cfg.user_password, "customer")
    merchant_user_token, merchant_login_note = _login(auth, cfg.merchant_email, cfg.merchant_password, "merchant")
    diagnostics.append(f"customer_login={customer_note}")
    diagnostics.append(f"merchant_login={merchant_login_note}")

    merchant_store_token: str | None = None
    merchant_store_id: int | None = None
    if merchant_user_token:
        merchant_store_token, merchant_store_id, merchant_store_note = _merchant_store_session(
            cfg, merchant, merchant_user_token
        )
        diagnostics.append(f"merchant_store_context={merchant_store_note}")
    else:
        diagnostics.append("merchant_store_context=skipped (merchant login unavailable)")

    orders: dict[int, dict[str, Any]] = {}
    details: dict[int, dict[str, Any]] = {}
    if merchant_store_token and isinstance(merchant_store_id, int):
        orders, list_notes = _fetch_merchant_orders(client, merchant_store_token, merchant_store_id, max(1, args.max_pages))
        diagnostics.extend(list_notes)
        details = _fetch_detail_cache(client, merchant_store_token, orders.keys())
    else:
        diagnostics.append("merchant_discovery=blocked (store-scoped merchant token unavailable)")

    # Safe creation: only pending seed and only when explicitly requested.
    if args.allow_create and merchant_store_token and isinstance(merchant_store_id, int):
        has_pending = any(v.get("status") == 10 for v in orders.values())
        if not has_pending:
            created_order_id, create_note = _create_pending_seed(
                cfg=cfg,
                client=client,
                order=order,
                customer_token=customer_token,
                store_id=merchant_store_id,
            )
            if created_order_id is not None:
                mutation_notes.append(f"Created pending orderId={created_order_id}")
                diagnostics.append(f"pending_seed_creation={create_note}")
                refreshed_orders, list_notes = _fetch_merchant_orders(
                    client, merchant_store_token, merchant_store_id, max(1, args.max_pages)
                )
                orders = refreshed_orders
                diagnostics.extend([f"refresh: {n}" for n in list_notes])
                details = _fetch_detail_cache(client, merchant_store_token, orders.keys())
            else:
                diagnostics.append(f"pending_seed_creation=blocked ({create_note})")

    results = _compose_slot_results(orders, details, cfg)

    metadata = {
        "baseUrl": cfg.normalized_base_url,
        "merchantStoreId": merchant_store_id,
        "totalDiscoveredOrders": len(orders),
        "allowCreate": bool(args.allow_create),
    }
    _write_outputs(
        json_path=(REPO_ROOT / args.json_out).resolve(),
        env_path=(REPO_ROOT / args.env_out).resolve(),
        report_path=(REPO_ROOT / args.report_out).resolve(),
        results=results,
        diagnostics=diagnostics,
        mutation_notes=mutation_notes,
        metadata=metadata,
    )

    filled = sum(1 for r in results if r.order_id is not None)
    missing = len(results) - filled
    print(f"Merchant seed builder completed: filled={filled} missing={missing}")
    for r in results:
        status_name = STATUS_NAMES.get(r.status or -1, "")
        print(f"- {r.slot}: {r.order_id or 'MISSING'} status={r.status or ''} {status_name} source={r.source}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:  # pragma: no cover - top-level runtime safety
        traceback.print_exc()
        raise SystemExit(1)
