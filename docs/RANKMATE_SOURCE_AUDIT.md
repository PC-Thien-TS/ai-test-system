# RANKMATE Source Audit (Cross-Repo)

## Scope
- Workspace scanned from source code (not docs assumptions):
  - `C:\Projects\Rankmate\rankmate_be`
  - `C:\Projects\Rankmate\rankmate_us`
  - `C:\Projects\Rankmate\didaunao_mc_web`
  - `C:\Projects\Rankmate\rankmate_fe`
  - `C:\Projects\Rankmate\ai_test_system`
- Objective: establish concrete source-backed surface map before new automation implementation.

## A. Backend Audit (`rankmate_be`)

### Findings
- Framework/runtime: ASP.NET Core Web API, API versioning with URL segment.
- Base API route contract is `api/v{version}/[controller]` via base controller.
- Swagger/OpenAPI is enabled in app startup.
- JWT auth + authorization middleware are enabled.
- Real-time channel exists via SignalR hub (`/hubs/notifications`).
- Core domain endpoint families are present and active:
  - Auth: login/register/OTP/refresh/switch org/logout/external/limited login.
  - Search: stores/authors/posts/suggestions/hot keywords/histories.
  - Store/menu: store detail, menu, eligibility, store verify flows.
  - Orders: create/list/detail, pricing preview, create payment intent, retry payment, wallet pay, cancel/reschedule, confirm-arrival, report-not-arrived, confirm-complete, disputes.
  - Payments: methods, momo, stripe intent, momo webhook, stripe webhook, transaction verify.
  - Merchant operations: list/detail + accept/reject/mark-arrived/complete/mark-no-show/cancel.
  - Admin operations: orders list/detail.
- Idempotency is explicitly required for order create/payment/retry endpoints (`Idempotency-Key`).
- Order/payment state model exists and includes transitions around `Pending/Paid/Accepted/Arrived/WaitingCustomerConfirmation/Completed/Failed/Cancelled/Rejected/NoShow`.
- Payment callback handling includes signature checks and dedupe/idempotency behavior.

### Evidence
- Startup/bootstrap:
  - `CoreV2.MVC/Program.cs` (`AddApiVersioning`, `UseAuthentication`, `UseAuthorization`, `UseSwagger`, `MapHub`).
- Base route contract:
  - `CoreV2.MVC/Api/BaseV1Controller.cs` (`[Route("api/v{version:apiVersion}/[controller]")]`).
- Endpoint families:
  - `CoreV2.MVC/Api/AuthController.cs`
  - `CoreV2.MVC/Api/SearchController.cs`
  - `CoreV2.MVC/Api/StoreController.cs`
  - `CoreV2.MVC/Api/StoresController.cs`
  - `CoreV2.MVC/Api/OrdersController.cs`
  - `CoreV2.MVC/Api/PaymentController.cs`
  - `CoreV2.MVC/Api/MerchantOrdersController.cs`
  - `CoreV2.MVC/Api/AdminOrdersController.cs`
  - `CoreV2.MVC/Api/NotificationController.cs`
- Permission boundaries:
  - `CoreV2.MVC/Filters/AdminAuthorizationFilter.cs`
  - `CoreV2.MVC/Filters/OwnerOrganizationAuthorizationFilter.cs`
- State + transition enforcement:
  - `CoreV2.Domain/Constants/AppEnums.cs`
  - `CoreV2.Application/Features/Ordering/Commands/*`
- Callback/webhook handling:
  - `CoreV2.Application/Features/Payments/Commands/Stripe/ProcessPaymentSuccessCommand.cs`
  - `CoreV2.Application/Features/Payments/Commands/Momo/UpdatePaymentCommand.cs`

### Test Implication
- Backend supports high-value API and integration testing immediately around auth/search/order/payment/merchant/admin paths.
- Strong Wave 1 focus: idempotency + callback/webhook + state transition guardrails.

### Risk Notes
- Highest risk APIs: order creation, retry payment, payment webhook handling, merchant transition actions.
- Areas requiring strict negative tests: invalid transitions, duplicate payment callbacks, missing idempotency header.

---

## B. User App Audit (`rankmate_us`)

### Findings
- Framework/runtime: Vite + Ionic React + React Router + Redux.
- Route map includes critical user funnel pages:
  - `/sign-up`, `/otp`, `/verify`
  - `/search`, `/search/result`
  - `/store/:uniqueId`, `/store/:uniqueId/menu`
  - `/orders/checkout`, `/orders/:orderId`, `/payment-result`, `/history-orders`
- API client base points to backend `/api/v1`.
- Request interceptor injects `Authorization` and auto-adds `Idempotency-Key` for `POST orders*` requests.
- User order lifecycle interactions are wired in UI:
  - create order / pricing preview / create payment intent / wallet pay
  - retry payment
  - confirm arrival / confirm complete / report not arrived / create dispute
- Route permission logic exists via `RouteGuard` + `authGuard` + route category constants.

### Evidence
- Route definitions:
  - `src/routes/AppRoutes.tsx`
  - `src/constants/routes.ts`
  - `src/routes/RouteGuard.ts`
  - `src/middlewares/authGuard.ts`
- API + token/idempotency wiring:
  - `src/services/mainAxios.ts`
  - `src/services/apis/authAPI.ts`
  - `src/services/apis/search.api.ts`
  - `src/services/apis/store.api.ts`
  - `src/services/apis/order.api.ts`
  - `src/services/apis/payment.api.ts`
- Flow components:
  - `src/components/search/result/SearchResult.tsx`
  - `src/components/stores/detail/StoreDetail.tsx`
  - `src/components/orders/StoreMenuPage.tsx`
  - `src/components/orders/OrderCheckoutPage.tsx`
  - `src/components/orders/OrderTrackingPage.tsx`

### Test Implication
- P0 user e2e paths are source-clear and testable end-to-end against backend: search -> store -> cart/menu -> checkout -> payment -> order tracking.
- Permission and auth redirect behavior should be tested as part of UI + e2e baseline.

### Risk Notes
- Checkout/payment branch behavior and retry conditions are critical and easy to regress.
- Route guard behavior depends on token/session hydration timing; flaky scenarios are possible if not synchronized in tests.

---

## C. Merchant Web Audit (`didaunao_mc_web`)

### Findings
- Framework/runtime: Vite + React Router + Redux + AntD.
- Route structure enforces merchant auth and selected-store gating:
  - Public: `/login`
  - Protected: `/select-store`, `/dashboard`, `/orders`, `/orders/:id`, etc.
- Merchant API surface is explicitly mapped to backend `merchant/orders` actions:
  - list/detail/accept/reject/mark-arrived/complete/mark-no-show/cancel
- Session model uses dual-token behavior:
  - user token for `/store/verify` and `/authors/switch`
  - store token for merchant operational APIs
- Store selection flow restores/activates store context before operations.

### Evidence
- Routing/guards:
  - `src/App.tsx`
- API clients:
  - `src/services/apis/orders.api.ts`
  - `src/services/apis/store.api.ts`
  - `src/services/apis/auth.api.ts`
  - `src/services/mainAxios.ts`
- Merchant operation pages:
  - `src/features/orders/OrdersPage.tsx`
  - `src/features/orders/OrderDetailPage.tsx`
  - `src/features/store/StoreSelectPage.tsx`

### Test Implication
- Merchant order handling is testable via API-first and UI operational flows.
- High-value tests: action availability by status, rejection reason handling, status refresh after action.

### Risk Notes
- Token-context switching (user/store token) is a known integration risk.
- Order action availability by state must be validated against backend truth to prevent mismatched UI affordances.

---

## D. Admin Site Audit (`rankmate_fe`)

### Findings
- Framework/runtime: Next.js (SSR pages) + React + Redux + AntD.
- Admin access control exists both at SSR layer and HOC/component layer.
- Critical admin pages are present and source-wired:
  - `/admin/orders` list/detail
  - `/admin/disputes` list/detail/resolve
  - `/admin/verify-store`
  - dashboard summary panels using admin APIs
- Admin APIs include monitoring + operations across orders/disputes/store verification + finance/wallet observability.

### Evidence
- Guards/access:
  - `src/features/admin/lib/adminPage.ts`
  - `src/HOCs/withAdminConsoleHOC.tsx`
  - `src/HOCs/withAuthHOC.tsx`
- Admin pages:
  - `src/pages/admin/orders/index.tsx`
  - `src/pages/admin/orders/[id].tsx`
  - `src/pages/admin/disputes/index.tsx`
  - `src/pages/admin/disputes/[id].tsx`
  - `src/pages/admin/verify-store/index.tsx`
- Admin feature/API wiring:
  - `src/features/admin/orders/AdminOrdersPage.tsx`
  - `src/features/admin/orders/AdminOrderDetailPage.tsx`
  - `src/components/disputes-admin/AdminDisputesList.tsx`
  - `src/components/disputes-admin/AdminDisputeDetail.tsx`
  - `src/libs/redux/asyncThunks/verify.store.action.ts`
  - `src/services/apis/orders.admin.api.ts`
  - `src/services/apis/disputesAdmin.api.ts`
  - `src/services/apis/verify-store.api.ts`
  - `src/services/apis/finance.admin.api.ts`

### Test Implication
- Admin observability/monitoring workflows are testable as UI + API integration targets.
- P0 admin tests should center on order queue filters/status drill-down and dispute resolution correctness.

### Risk Notes
- Some admin pages rely on aggregated async data sources; race/partial-load behavior should be tested.
- Admin authorization must be validated with non-admin accounts to catch access leakage.

---

## E. AI QA Repo Audit (`ai_test_system`)

### Findings
- Requirement-aware generation and risk prioritization are implemented and typed.
- Deterministic execution-queue contract exists for orchestrator consumption.
- Plugin/harness architecture exists and is reusable for later execution automation.
- API includes both `/projects` and canonical `/runs` mounts (plus legacy compatibility route mounting).

### Evidence
- Advanced QA models/generation/prioritization:
  - `orchestrator/advanced_qa/requirement_generator.py`
  - `orchestrator/advanced_qa/requirement_models.py`
  - `orchestrator/advanced_qa/requirement_parser.py`
  - `orchestrator/advanced_qa/requirement_mapper.py`
  - `orchestrator/advanced_qa/requirement_outputs.py`
  - `orchestrator/advanced_qa/requirement_rules.py`
  - `orchestrator/advanced_qa/risk_prioritizer.py`
  - `orchestrator/advanced_qa/risk_models.py`
  - `orchestrator/advanced_qa/risk_rules.py`
  - `orchestrator/advanced_qa/execution_queue.py`
- Plugin/harness orchestration:
  - `orchestrator/plugins/base.py`
  - `orchestrator/plugins/registry.py`
  - `orchestrator/plugins/executor.py`
  - `orchestrator/plugins/integration.py`
- Run API integration:
  - `api/app.py`
  - `api/routes/runs.py`
- Existing tests:
  - `tests/test_requirement_generator.py`
  - `tests/test_risk_prioritizer.py`

### Test Implication
- Best integration point for source-derived map is the requirement/risk input path, then queue generation for orchestrator execution.
- The new cross-repo source map can be fed into `Requirement` artifacts, then prioritized via `RiskPrioritizer` before execution plugins.

### Risk Notes
- Mapping ingestion format should be standardized now (repo/domain/module/route/page + dependency + risk signals) to avoid inconsistent downstream planning.

---

## Known Unknowns / Blockers from Source Scan
- Backend callback signature testability depends on valid provider-like payload/signature construction for MoMo/Stripe handlers.
- Full end-to-end multi-role flow requires coordinated seed data: user + merchant-store linkage + admin account + order candidates.
- Real-time notification path exists (`/hubs/notifications`) but cross-repo UI subscription usage was not the focus of this pass and should be validated in a dedicated Wave 2 track.
- Some admin/verify-store actions are routed through Redux thunks; API linkage is clear but UI element-level assertions should be derived from component behavior during test design.

## Decision
- Source scan is complete enough to proceed to concrete coverage mapping and Wave 1 execution planning.
