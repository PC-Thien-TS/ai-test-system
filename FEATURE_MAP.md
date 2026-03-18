# FEATURE_MAP

Generated at: 2026-03-05T03:16:16.539981+00:00

Scope: `ai_test_system` repository plus local source evidence repos referenced by `outputs/didaunao_release_audit/didaunao_weekly_release_v2/evidence`.

## Source Snapshot

- Backend repo: `C:\Projects\Rankmate\rankmate_be` @ `develop` (`96c4e591701ffcaa8afd7b000b7d2d567d5c3855`)
- Web admin repo: `C:\Projects\Rankmate\rankmate_fe` @ `develop` (`34862e539f558d87fba4b4a30ecbb577edc8e570`)
- App repo: `C:\Projects\Rankmate\rankmate_us` @ `develop` (`2ebde67d88e3b556f9be074f66377c175a81d2cd`)

## Discovered Features by Module

### Authentication

- Description: Sign-in/sign-up, token refresh, password recovery, and session lifecycle APIs.
- Related routes: 5
  - `app /otp`
  - `web_admin /forgot-password/otp`
  - `web_admin /login`
  - `web_admin /register`
  - `web_admin /register/otp`
- Related API endpoints: 41
  - `POST /account/otp (account)`
  - `GET /auth/accept-confirm/{hashCode} (auth)`
  - `GET /auth/accept-forget/{hashCode} (auth)`
  - `PUT /auth/accept-valid-otp (auth)`
  - `GET /auth/check-valid-confirm/{hashCode} (auth)`
  - `POST /auth/check-valid-otp (auth)`
  - `POST /auth/external-login (auth)`
  - `POST /auth/forget-password (auth)`
  - `POST /auth/google-login (auth)`
  - `POST /auth/limited-login (auth)`
  - `... (31 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/AuthController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/AuthorController.cs`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/forgot-password/otp/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/login/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/register/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/register/otp/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/services/apis/auth.api.ts`
  - `C:/Projects/Rankmate/rankmate_fe/src/services/functions/auth.function.ts`
  - `C:/Projects/Rankmate/rankmate_us/src/routes/AppRoutes.tsx`
  - `C:/Projects/Rankmate/rankmate_us/src/services/apis/authAPI.ts`
  - `C:/Projects/Rankmate/rankmate_us/src/services/apis/author.api.ts`
  - `C:/Projects/Rankmate/rankmate_us/src/services/functions/auth.function.ts`

### User management

- Description: Account/profile/member/organization management and related identity settings.
- Related routes: 10
  - `app /profile/edit`
  - `app /profile/edit-location`
  - `app /profile/edit-social`
  - `app /profile/edit-social/:index?`
  - `app /profile/u/:uniqueId?`
  - `web_admin /member`
  - `web_admin /member-admin`
  - `web_admin /organization`
  - `web_admin /settings/account`
  - `web_admin /settings/member`
- Related API endpoints: 34
  - `GET /account/avatar/{authorID:long} (account)`
  - `POST /account/change-password (account)`
  - `GET /account/get-info (account)`
  - `POST /account/update-account-v2 (account)`
  - `POST /account/update-info (account)`
  - `POST /account/upload-avatar (account)`
  - `PUT /account/verify (account)`
  - `POST /devices (devices)`
  - `POST /devices/update-language (devices)`
  - `GET /member/activity-log/{userId} (member)`
  - `... (24 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Organization.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/OrganizationType.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/OrganizationUser.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Account/AccountModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Account/UserHashCodeModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Device/UserDeviceModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Member/MemberListModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Member/MemberModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Member/MemberSelectionModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Member/OrganizationUserModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Organization/MediaOrganizationModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Organization/OrganizationListModel.cs`
  - `... (3 more)`

### Store / merchant features

- Description: Store lifecycle, merchant verification, categories, location, and store operations.
- Related routes: 16
  - `app /select-location`
  - `app /select-ward/:provinceId`
  - `app /settings/manage-store/verify-status/:authorId/:storeId`
  - `app /store`
  - `app /store-list`
  - `app /store-list/category-level1`
  - `app /store-list/category-level2`
  - `app /store/:uniqueId`
  - `app /store/verify`
  - `app /store/verify/:storeId/:authorId/:verifyId?`
  - `... (6 more)`
- Related API endpoints: 54
  - `GET /dashboard/store-registrations (dashboard)`
  - `GET /dashboard/store-registrations-by-date (dashboard)`
  - `GET /provinces (provinces)`
  - `POST /provinces/address/mapping (provinces)`
  - `POST /provinces/new (provinces)`
  - `POST /provinces/old (provinces)`
  - `GET /provinces/population (provinces)`
  - `POST /provinces/wards (provinces)`
  - `DELETE /provinces/wards/{wardId:long} (provinces)`
  - `PUT /provinces/wards/{wardId:long} (provinces)`
  - `... (44 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/OldProvince.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/OldWard.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Province.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Store.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/StoreCategory.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/StoreMedium.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/StoreOpenHour.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/StoreProduct.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/StoreReview.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/UserLastLocation.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/VerifyStoreRequest.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/VerifyStoreRequestImage.cs`
  - `... (3 more)`

### Search

- Description: Search endpoints and query flows for posts/authors/stores with suggestions and histories.
- Related routes: 5
  - `app /search`
  - `app /search*`
  - `app /search/mobile/posts/*`
  - `app /search/mobile/posts/:uniqueId/:id`
  - `app /search/result`
- Related API endpoints: 8
  - `GET /searches/filters (searches)`
  - `DELETE /searches/histories (searches)`
  - `GET /searches/histories (searches)`
  - `POST /searches/histories (searches)`
  - `GET /searches/hot-keywords (searches)`
  - `GET /searches/posts (searches)`
  - `GET /searches/posts/recommendation (searches)`
  - `GET /searches/suggestions/{keyword} (searches)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/SearchController.cs`
  - `C:/Projects/Rankmate/rankmate_us/src/routes/AppRoutes.tsx`
  - `C:/Projects/Rankmate/rankmate_us/src/services/apis/search.api.ts`
  - `C:/Projects/Rankmate/rankmate_us/src/utils/navigationUtils.ts`

### Menu / catalog

- Description: Product/category/document and catalog management flows.
- Related routes: 4
  - `web_admin /admin/category`
  - `web_admin /category`
  - `web_admin /document`
  - `web_admin /product`
- Related API endpoints: 43
  - `POST /category/create (category)`
  - `DELETE /category/delete/{id} (category)`
  - `GET /category/list (category)`
  - `GET /category/paged (category)`
  - `PUT /category/update (category)`
  - `GET /category/{id} (category)`
  - `POST /category-admin/create (category-admin)`
  - `GET /category-admin/detail/{id} (category-admin)`
  - `GET /category-admin/generate-code (category-admin)`
  - `GET /category-admin/list (category-admin)`
  - `... (33 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Category.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/CategoryAdmin.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/CategoryLanguage.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/CategoryNews.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Document.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Folder.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Product.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/ProductPrice.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/ProductReview.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Category/CategoryListModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Category/CategoryModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/CategoryAdmin/CategoryLanguageModel.cs`
  - `... (3 more)`

### Payment

- Description: Payment, wallet, and top-up transaction flows.
- Related routes: 3
  - `app /create-topup`
  - `app /payment-result`
  - `app /wallet`
- Related API endpoints: 7
  - `GET /payments/methods (payments)`
  - `POST /payments/momo (payments)`
  - `POST /payments/momo/webhook (payments)`
  - `POST /payments/stripe (payments)`
  - `POST /payments/stripe/webhook (payments)`
  - `GET /wallets (wallets)`
  - `GET /wallets/transactions (wallets)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/Payments/IMomoService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/PaymentGateway.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/PaymentMethod.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/PaymentTransaction.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Wallet.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/WalletBalance.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/WalletTransaction.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Payments/PaymentMethodModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Wallets/WalletModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Models/Wallets/WalletTransactionModel.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Infrastructure/Services/Payments/MomoService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/PaymentController.cs`
  - `... (3 more)`

### Notifications

- Description: Notification send, policy/template management, and user notification experiences.
- Related routes: 3
  - `app /notification`
  - `web_admin /admin/notification-policy`
  - `web_admin /admin/notification-template`
- Related API endpoints: 24
  - `GET /notification (notification)`
  - `POST /notification/delete (notification)`
  - `POST /notification/enqueue (notification)`
  - `POST /notification/mark-all-read (notification)`
  - `POST /notification/mark-read (notification)`
  - `POST /notification/test-realtime (notification)`
  - `GET /notification/unread-count (notification)`
  - `POST /notification-policy-admin/create (notification-policy-admin)`
  - `GET /notification-policy-admin/detail/{id} (notification-policy-admin)`
  - `GET /notification-policy-admin/paged (notification-policy-admin)`
  - `... (14 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationOrchestrator.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationPolicyValidator.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationRealtimeService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationSeedDataService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationStreamProcessor.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationTemplatePlaceholderService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/INotificationTemplateRenderer.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/NotificationLog.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/NotificationPolicy.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/NotificationTemplate.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/NotificationTemplateTranslation.cs`
  - `... (3 more)`

### Admin panel

- Description: Administrative dashboards, moderation, backoffice CRUD, and operational controls.
- Related routes: 11
  - `app /news`
  - `web_admin /admin`
  - `web_admin /admin/app-hot-update`
  - `web_admin /admin/news`
  - `web_admin /admin/posts-approval`
  - `web_admin /admin/posts-report`
  - `web_admin /dashboard`
  - `web_admin /feedback`
  - `web_admin /settings/apikey`
  - `web_admin /settings/create-apikey`
  - `... (1 more)`
- Related API endpoints: 50
  - `POST /apikey/add (apikey)`
  - `GET /apikey/admin-paged (apikey)`
  - `POST /apikey/create (apikey)`
  - `GET /apikey/detail/{id} (apikey)`
  - `GET /apikey/list (apikey)`
  - `GET /apikey/paged (apikey)`
  - `DELETE /apikey/remove/{id} (apikey)`
  - `PUT /apikey/replace/{id} (apikey)`
  - `PUT /apikey/update-info/{id} (apikey)`
  - `PUT /apikey/update/{id} (apikey)`
  - `... (40 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/ApiKeyController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/DashboardController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/FeedbackController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/NewsAdminController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/NewsController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/ReportController.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.MVC/Api/SupportController.cs`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/admin/app-hot-update/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/admin/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/admin/news/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/admin/posts-approval/index.tsx`
  - `C:/Projects/Rankmate/rankmate_fe/src/pages/admin/posts-report/index.tsx`
  - `... (3 more)`

### Monitoring / operations

- Description: Observability, hot update, telemetry-like endpoints, and release/ops controls.
- Related routes: 0
  - `UNKNOWN` (no route artifacts detected)
- Related API endpoints: 2
  - `GET /api/v{version:apiVersion}/app-hot-update/manifest (apphotupdate)`
  - `POST /user-behavior/track-interaction (user-behavior)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_fe/src/services/apis/app-hot-update.api.ts`

### Content / community

- Description: Posts/comments/media/news/social/community content workflows.
- Related routes: 4
  - `app /mobile/create-post`
  - `app /mobile/posts/*`
  - `app /mobile/posts/:uniqueId/:id`
  - `app /posts/:uniqueId/:id`
- Related API endpoints: 38
  - `POST /chat/create (chat)`
  - `GET /chat/detail/{id} (chat)`
  - `GET /chat/list (chat)`
  - `DELETE /chat/remove/{id} (chat)`
  - `POST /chat/sse (chat)`
  - `POST /chat/submit_file (chat)`
  - `PUT /chat/update-info/{id} (chat)`
  - `PUT /chat/update/{id} (chat)`
  - `GET /comments (comments)`
  - `POST /comments (comments)`
  - `... (28 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/ElasticSearch/IPostElasticClient.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IMediaProcessingService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IMediaService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IPostDetectService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Chat.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Comment.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/CommentMedium.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/CommentReact.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/MediaFile.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/Post.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/PostCategory.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Domain/Entities/PostCategoryInterest.cs`
  - `... (3 more)`

### Infrastructure / platform

- Description: Cross-cutting platform services including storage and system integration pieces.
- Related routes: 24
  - `app /`
  - `app /favorites`
  - `app /favorites/collections/:collectionId`
  - `app /home`
  - `app /home-mobile`
  - `app /mobile/blogs`
  - `app /mobile/blogs/*`
  - `app /mobile/blogs/:uniqueId/:id`
  - `app /onboarding`
  - `app /settings`
  - `... (14 more)`
- Related API endpoints: 45
  - `GET /country/list (country)`
  - `GET /interests (interests)`
  - `POST /interests (interests)`
  - `GET /interests/user-interests (interests)`
  - `POST /interests/user-interests (interests)`
  - `DELETE /interests/user-interests/{id} (interests)`
  - `DELETE /interests/{id} (interests)`
  - `GET /interests/{id} (interests)`
  - `PUT /interests/{id} (interests)`
  - `POST /invitation/accept-invitation (invitation)`
  - `... (35 more)`
- Key files involved:
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/ElasticSearch/IBaseElasticClient.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/ElasticSearch/IStoreElasticClient.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IDapperService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IEmailSender.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IHangfireService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IHttpService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IMapAddressService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/ISmsService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/ISyncDataToElasticJob.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/ITokenService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IUserAvatarCacheService.cs`
  - `C:/Projects/Rankmate/rankmate_be/CoreV2.Application/Services/IUserBehaviorService.cs`
  - `... (3 more)`

## Inventory Summary

- Total features discovered (non-empty modules): 11
- Total API endpoints: 346
- Total UI routes: 85
- Top modules by size:
  - Store / merchant features: 70
  - Infrastructure / platform: 69
  - Admin panel: 61
  - Menu / catalog: 47
  - Authentication: 46
