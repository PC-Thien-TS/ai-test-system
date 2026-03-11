# API_LIST

Generated at: 2026-03-05T03:16:16.539981+00:00

Total endpoints discovered: **346**

Source: `outputs/didaunao_release_audit/didaunao_weekly_release_v2/evidence/backend/dotnet_endpoints.json`

## Authentication (41)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| POST | `/account/otp` | `account` | `SendOtp` | `authorized` | `body` |
| GET | `/auth/accept-confirm/{hashCode}` | `auth` | `AcceptConfirm` | `inherit` | `query` |
| GET | `/auth/accept-forget/{hashCode}` | `auth` | `AcceptForget` | `inherit` | `query` |
| PUT | `/auth/accept-valid-otp` | `auth` | `AcceptValidOTP` | `inherit` | `body` |
| GET | `/auth/check-valid-confirm/{hashCode}` | `auth` | `CheckValidOTP` | `inherit` | `query` |
| POST | `/auth/check-valid-otp` | `auth` | `CheckValidOTP` | `inherit` | `body` |
| POST | `/auth/external-login` | `auth` | `ExternalLogin` | `inherit` | `body` |
| POST | `/auth/forget-password` | `auth` | `ForgetPassword` | `inherit` | `body` |
| POST | `/auth/google-login` | `auth` | `GoogleLogin` | `inherit` | `body` |
| POST | `/auth/limited-login` | `auth` | `LimitedLogin` | `inherit` | `body` |
| POST | `/auth/login` | `auth` | `Register` | `inherit` | `body` |
| POST | `/auth/logout` | `auth` | `Logout` | `authorized` | `body` |
| POST | `/auth/refresh-token` | `auth` | `RefreshToken` | `inherit` | `body` |
| POST | `/auth/register` | `auth` | `Register` | `inherit` | `body` |
| POST | `/auth/register-v2` | `auth` | `RegisterV2` | `inherit` | `body` |
| POST | `/auth/register/end-user` | `auth` | `Logout` | `inherit` | `body` |
| POST | `/auth/send-confirm-email` | `auth` | `SendOTPEmail` | `inherit` | `body` |
| POST | `/auth/send-otp-email` | `auth` | `SendOTPEmail` | `inherit` | `body` |
| POST | `/auth/switch-organization` | `auth` | `SwitchOrganization` | `authorized` | `body` |
| PUT | `/auth/update-password-confirm` | `auth` | `UpdatePasswordByConfirm` | `inherit` | `body` |
| PUT | `/auth/update-password-otp` | `auth` | `UpdatePasswordByOTP` | `inherit` | `body` |
| PUT | `/auth/update-preferences` | `auth` | `UpdateUserPreferences` | `authorized` | `body` |
| DELETE | `/authors` | `authors` | `Delete` | `authorized` | `query` |
| POST | `/authors` | `authors` | `Create` | `authorized` | `form` |
| PUT | `/authors` | `authors` | `Update` | `authorized` | `body` |
| GET | `/authors/block-or-restrict` | `authors` | `Get` | `authorized` | `query` |
| DELETE | `/authors/block/{blockedId:long}` | `authors` | `UnBlock` | `authorized` | `query` |
| PUT | `/authors/block/{blockedId:long}` | `authors` | `Block` | `authorized` | `body` |
| GET | `/authors/last-location` | `authors` | `Get` | `authorized` | `query` |
| PUT | `/authors/last-location` | `authors` | `Get` | `authorized` | `query` |
| PUT | `/authors/photo` | `authors` | `Update` | `authorized` | `form` |
| GET | `/authors/posts` | `authors` | `Get` | `anonymous` | `query` |
| GET | `/authors/profiles` | `authors` | `Get` | `authorized` | `query` |
| PUT | `/authors/restrict` | `authors` | `Block` | `anonymous` | `body` |
| DELETE | `/authors/restrict/{restrictedId:long}` | `authors` | `UnRestrict` | `authorized` | `query` |
| PUT | `/authors/switch` | `authors` | `SwitchProfile` | `authorized` | `body` |
| DELETE | `/authors/{deviceID}/logout-device` | `authors` | `LogoutDevice` | `authorized` | `query` |
| POST | `/authors/{targetAuthorId:long}/follow` | `authors` | `Follow` | `authorized` | `body` |
| DELETE | `/authors/{targetAuthorId:long}/unfollow` | `authors` | `Unfollow` | `authorized` | `query` |
| GET | `/authors/{uniqueId?}` | `authors` | `Get` | `anonymous` | `query` |
| GET | `/searches/authors` | `searches` | `Get` | `anonymous` | `query` |

## User management (34)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/account/avatar/{authorID:long}` | `account` | `GetUserAvatar` | `anonymous` | `query` |
| POST | `/account/change-password` | `account` | `ChangePassword` | `authorized` | `body` |
| GET | `/account/get-info` | `account` | `GetInfo` | `authorized` | `query` |
| POST | `/account/update-account-v2` | `account` | `UpdateAccount` | `authorized` | `form` |
| POST | `/account/update-info` | `account` | `UpdateInfo` | `authorized` | `body` |
| POST | `/account/upload-avatar` | `account` | `CreateLogo` | `anonymous` | `form` |
| PUT | `/account/verify` | `account` | `VerifyAccount` | `authorized` | `body` |
| POST | `/devices` | `devices` | `Create` | `inherit` | `form` |
| POST | `/devices/update-language` | `devices` | `UpdateLanguage` | `inherit` | `form` |
| GET | `/member/activity-log/{userId}` | `member` | `GetUserActivityLog` | `authorized` | `query` |
| POST | `/member/create` | `member` | `Create` | `authorized` | `body` |
| GET | `/member/detail/{id}` | `member` | `GetDetail` | `authorized` | `query` |
| GET | `/member/list` | `member` | `GetList` | `authorized` | `query` |
| GET | `/member/paged` | `member` | `GetPagination` | `authorized` | `query` |
| GET | `/member/pagination-selection` | `member` | `GetPaginationSelection` | `authorized` | `query` |
| PATCH | `/member/remove-multiple` | `member` | `Remove` | `authorized` | `body` |
| DELETE | `/member/remove/{id}` | `member` | `Remove` | `authorized` | `query` |
| PUT | `/member/update/{id}` | `member` | `Update` | `authorized` | `body` |
| POST | `/organization/active/{id}` | `organization` | `Active` | `authorized` | `body` |
| POST | `/organization/create` | `organization` | `Create` | `authorized` | `form` |
| GET | `/organization/detail/{id}` | `organization` | `GetDetail` | `authorized` | `query` |
| POST | `/organization/disable/{id}` | `organization` | `Disable` | `authorized` | `body` |
| GET | `/organization/generate-code` | `organization` | `GenerateCode` | `authorized` | `query` |
| GET | `/organization/get-info` | `organization` | `GetInfo` | `authorized` | `query` |
| GET | `/organization/get-organization-type` | `organization` | `GetOrganizationType` | `anonymous` | `query` |
| GET | `/organization/list` | `organization` | `GetList` | `authorized` | `query` |
| GET | `/organization/paged` | `organization` | `GetPagination` | `authorized` | `query` |
| GET | `/organization/pagination-selection` | `organization` | `GetPaginationSelection` | `authorized` | `query` |
| POST | `/organization/remove-member` | `organization` | `Active` | `authorized` | `body` |
| POST | `/organization/remove-multiple-member` | `organization` | `Disable` | `authorized` | `body` |
| DELETE | `/organization/remove/{id}` | `organization` | `Remove` | `authorized` | `query` |
| PUT | `/organization/update` | `organization` | `Update` | `authorized` | `form` |
| PUT | `/organization/update-info` | `organization` | `UpdateInfo` | `authorized` | `form` |
| POST | `/organization/upload-logo` | `organization` | `Update` | `anonymous` | `form` |

## Store / merchant features (54)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/dashboard/store-registrations` | `dashboard` | `GetStoreRegistrations` | `authorized` | `query` |
| GET | `/dashboard/store-registrations-by-date` | `dashboard` | `GetStoreRegistrationsByDateRange` | `authorized` | `query` |
| GET | `/provinces` | `provinces` | `Get` | `inherit` | `query` |
| POST | `/provinces/address/mapping` | `provinces` | `Get` | `inherit` | `query` |
| POST | `/provinces/new` | `provinces` | `CreateNewAddress` | `authorized` | `body` |
| POST | `/provinces/old` | `provinces` | `CreateOldAddress` | `authorized` | `body` |
| GET | `/provinces/population` | `provinces` | `Get` | `inherit` | `query` |
| POST | `/provinces/wards` | `provinces` | `CreateWards` | `inherit` | `body` |
| DELETE | `/provinces/wards/{wardId:long}` | `provinces` | `DeleteWard` | `authorized` | `query` |
| PUT | `/provinces/wards/{wardId:long}` | `provinces` | `UpdateWard` | `authorized` | `body` |
| DELETE | `/provinces/{id:long}` | `provinces` | `DeleteProvince` | `authorized` | `query` |
| GET | `/provinces/{id:long}` | `provinces` | `GetProvinceDetail` | `authorized` | `query` |
| PUT | `/provinces/{id:long}` | `provinces` | `UpdateProvince` | `authorized` | `body` |
| GET | `/provinces/{provinceId:long}/wards` | `provinces` | `Get` | `inherit` | `query` |
| GET | `/searches/stores` | `searches` | `Get` | `anonymous` | `query` |
| GET | `/store` | `store` | `Get` | `anonymous` | `query` |
| PUT | `/store/addresses` | `store` | `Update` | `authorized` | `body` |
| GET | `/store/collections` | `store` | `Get` | `authorized` | `query` |
| POST | `/store/collections` | `store` | `Get` | `authorized` | `form` |
| PUT | `/store/collections` | `store` | `Update` | `authorized` | `body` |
| POST | `/store/collections/items` | `store` | `Get` | `authorized` | `body` |
| DELETE | `/store/collections/{collectionId:long}/items/{itemId:long}` | `store` | `DeleteCollectionItem` | `authorized` | `query` |
| DELETE | `/store/collections/{id:long}` | `store` | `DeleteCollection` | `authorized` | `query` |
| POST | `/store/create` | `store` | `Create` | `authorized` | `body` |
| DELETE | `/store/delete/{id}` | `store` | `Delete` | `authorized` | `query` |
| POST | `/store/google-map` | `store` | `Create` | `authorized` | `form` |
| GET | `/store/list` | `store` | `GetList` | `authorized` | `query` |
| GET | `/store/paged` | `store` | `GetPagination` | `authorized` | `query` |
| GET | `/store/reviews` | `store` | `Update` | `anonymous` | `query` |
| POST | `/store/reviews` | `store` | `Create` | `authorized` | `query` |
| PUT | `/store/update` | `store` | `Update` | `authorized` | `body` |
| GET | `/store/verify` | `store` | `Get` | `authorized` | `query` |
| POST | `/store/verify` | `store` | `Create` | `authorized` | `form` |
| GET | `/store/verify/detail` | `store` | `Get` | `authorized` | `query` |
| GET | `/store/verify/detail/{id:long}` | `store` | `Get` | `authorized` | `query` |
| PUT | `/store/verify/{id:long}/approve` | `store` | `Approve` | `authorized` | `body` |
| PUT | `/store/verify/{id:long}/reject` | `store` | `Reject` | `authorized` | `query` |
| GET | `/store/views` | `store` | `Update` | `authorized` | `body` |
| PUT | `/store/views` | `store` | `Update` | `authorized` | `body` |
| GET | `/store/{id:long}` | `store` | `GetById` | `authorized` | `query` |
| GET | `/store/{uniqueId}` | `store` | `Get` | `anonymous` | `query` |
| GET | `/store-category` | `store-category` | `Get` | `anonymous` | `query` |
| GET | `/store-category/admin/children/{parentId}` | `store-category` | `GetChildren` | `authorized` | `query` |
| POST | `/store-category/admin/create` | `store-category` | `Create` | `authorized` | `form` |
| GET | `/store-category/admin/detail/{id}` | `store-category` | `GetDetail` | `authorized` | `query` |
| GET | `/store-category/admin/generate-code` | `store-category` | `GenerateCode` | `authorized` | `query` |
| GET | `/store-category/admin/paged` | `store-category` | `GetPagination` | `authorized` | `query` |
| PATCH | `/store-category/admin/remove-multiple` | `store-category` | `RemoveMultiple` | `authorized` | `body` |
| DELETE | `/store-category/admin/remove/{id}` | `store-category` | `Remove` | `authorized` | `query` |
| GET | `/store-category/admin/selection` | `store-category` | `GetSelection` | `authorized` | `query` |
| PUT | `/store-category/admin/update/{id}` | `store-category` | `Update` | `authorized` | `form` |
| POST | `/store-category/icons` | `store-category` | `ImportIcons` | `authorized` | `body` |
| GET | `/store-category/list` | `store-category` | `GetList` | `authorized` | `query` |
| GET | `/store-category/population` | `store-category` | `GetPopularCategories` | `anonymous` | `query` |

## Search (8)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/searches/filters` | `searches` | `Get` | `anonymous` | `query` |
| DELETE | `/searches/histories` | `searches` | `Delete` | `anonymous` | `query` |
| GET | `/searches/histories` | `searches` | `Get` | `anonymous` | `query` |
| POST | `/searches/histories` | `searches` | `Update` | `anonymous` | `body` |
| GET | `/searches/hot-keywords` | `searches` | `Get` | `anonymous` | `query` |
| GET | `/searches/posts` | `searches` | `Get` | `anonymous` | `query` |
| GET | `/searches/posts/recommendation` | `searches` | `Get` | `anonymous` | `query` |
| GET | `/searches/suggestions/{keyword}` | `searches` | `Get` | `anonymous` | `query` |

## Menu / catalog (43)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| POST | `/category/create` | `category` | `Create` | `authorized` | `body` |
| DELETE | `/category/delete/{id}` | `category` | `Delete` | `authorized` | `query` |
| GET | `/category/list` | `category` | `GetList` | `authorized` | `query` |
| GET | `/category/paged` | `category` | `GetPagination` | `authorized` | `query` |
| PUT | `/category/update` | `category` | `Update` | `authorized` | `body` |
| GET | `/category/{id}` | `category` | `GetById` | `authorized` | `query` |
| POST | `/category-admin/create` | `category-admin` | `Create` | `inherit` | `body` |
| GET | `/category-admin/detail/{id}` | `category-admin` | `GetDetail` | `inherit` | `query` |
| GET | `/category-admin/generate-code` | `category-admin` | `GenerateCode` | `inherit` | `query` |
| GET | `/category-admin/list` | `category-admin` | `GetList` | `inherit` | `query` |
| GET | `/category-admin/paged` | `category-admin` | `GetPagination` | `inherit` | `query` |
| PATCH | `/category-admin/remove-multiple` | `category-admin` | `Remove` | `inherit` | `body` |
| DELETE | `/category-admin/remove/{id}` | `category-admin` | `Remove` | `inherit` | `query` |
| GET | `/category-admin/selection` | `category-admin` | `GetSelection` | `inherit` | `query` |
| PUT | `/category-admin/update/{id}` | `category-admin` | `Update` | `inherit` | `body` |
| POST | `/document/create` | `document` | `Create` | `authorized` | `form` |
| GET | `/document/detail/{id}` | `document` | `GetDetail` | `authorized` | `query` |
| GET | `/document/list` | `document` | `GetList` | `authorized` | `query` |
| GET | `/document/paged` | `document` | `GetPagination` | `authorized` | `query` |
| DELETE | `/document/remove/{id}` | `document` | `Remove` | `authorized` | `query` |
| PUT | `/document/update/{id}` | `document` | `Update` | `authorized` | `body` |
| POST | `/folder/create` | `folder` | `Create` | `authorized` | `body` |
| GET | `/folder/detail/{id}` | `folder` | `GetDetail` | `authorized` | `query` |
| GET | `/folder/generate-code` | `folder` | `GenerateCode` | `authorized` | `query` |
| GET | `/folder/list` | `folder` | `GetList` | `authorized` | `query` |
| GET | `/folder/paged` | `folder` | `GetPagination` | `authorized` | `query` |
| DELETE | `/folder/remove/{id}` | `folder` | `Remove` | `authorized` | `query` |
| PUT | `/folder/update` | `folder` | `Update` | `authorized` | `body` |
| GET | `/api/v1/ionic-web/categories/products` | `ionic-web` | `GetCategoriesWithProducts` | `anonymous` | `query` |
| GET | `/api/v1/ionic-web/product/paged` | `ionic-web` | `GetPagination` | `anonymous` | `query` |
| GET | `/api/v1/ionic-web/product/review` | `ionic-web` | `GetProductReview` | `anonymous` | `query` |
| POST | `/api/v1/ionic-web/product/review/generate` | `ionic-web` | `GenerateAIReview` | `anonymous` | `body` |
| POST | `/api/v1/ionic-web/product/review/generate-v2` | `ionic-web` | `GenerateAIReviewV2` | `anonymous` | `body` |
| PUT | `/api/v1/ionic-web/product/review/status` | `ionic-web` | `UpdateProductReviewStatus` | `anonymous` | `body` |
| POST | `/product/bulk-create` | `product` | `BulkCreate` | `authorized` | `body` |
| POST | `/product/create` | `product` | `Create` | `authorized` | `body` |
| DELETE | `/product/delete/{id}` | `product` | `Delete` | `authorized` | `query` |
| GET | `/product/list` | `product` | `GetList` | `authorized` | `query` |
| POST | `/product/menu-extraction` | `product` | `Extraction` | `authorized` | `form` |
| GET | `/product/paged` | `product` | `GetPagination` | `authorized` | `query` |
| PUT | `/product/update` | `product` | `Update` | `authorized` | `body` |
| POST | `/product/upload-image` | `product` | `Update` | `anonymous` | `form` |
| GET | `/product/{id}` | `product` | `GetById` | `authorized` | `query` |

## Payment (7)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/payments/methods` | `payments` | `GetPaymentMethods` | `anonymous` | `query` |
| POST | `/payments/momo` | `payments` | `Payment` | `authorized` | `body` |
| POST | `/payments/momo/webhook` | `payments` | `Webhook` | `anonymous` | `body` |
| POST | `/payments/stripe` | `payments` | `Payment` | `anonymous` | `body` |
| POST | `/payments/stripe/webhook` | `payments` | `Handle` | `anonymous` | `body` |
| GET | `/wallets` | `wallets` | `GetWallet` | `authorized` | `query` |
| GET | `/wallets/transactions` | `wallets` | `GetTransactions` | `authorized` | `query` |

## Notifications (24)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/notification` | `notification` | `GetMyNotifications` | `authorized` | `query` |
| POST | `/notification/delete` | `notification` | `Delete` | `authorized` | `body` |
| POST | `/notification/enqueue` | `notification` | `Enqueue` | `authorized` | `body` |
| POST | `/notification/mark-all-read` | `notification` | `MarkAllRead` | `authorized` | `body` |
| POST | `/notification/mark-read` | `notification` | `MarkRead` | `authorized` | `body` |
| POST | `/notification/test-realtime` | `notification` | `TestRealtime` | `authorized` | `body` |
| GET | `/notification/unread-count` | `notification` | `GetUnreadCount` | `authorized` | `query` |
| POST | `/notification-policy-admin/create` | `notification-policy-admin` | `Create` | `inherit` | `body` |
| GET | `/notification-policy-admin/detail/{id}` | `notification-policy-admin` | `GetDetail` | `inherit` | `query` |
| GET | `/notification-policy-admin/paged` | `notification-policy-admin` | `GetPagination` | `inherit` | `query` |
| DELETE | `/notification-policy-admin/remove/{id}` | `notification-policy-admin` | `Remove` | `inherit` | `query` |
| PUT | `/notification-policy-admin/update/{id}` | `notification-policy-admin` | `Update` | `inherit` | `body` |
| POST | `/notification-seed-data/all` | `notification-seed-data` | `SeedAll` | `inherit` | `body` |
| POST | `/notification-seed-data/policies` | `notification-seed-data` | `SeedPolicies` | `inherit` | `body` |
| POST | `/notification-seed-data/templates` | `notification-seed-data` | `SeedTemplates` | `inherit` | `body` |
| POST | `/notification-template-admin/create` | `notification-template-admin` | `Create` | `inherit` | `body` |
| GET | `/notification-template-admin/detail/{id}` | `notification-template-admin` | `GetDetail` | `inherit` | `query` |
| GET | `/notification-template-admin/paged` | `notification-template-admin` | `GetPagination` | `inherit` | `query` |
| DELETE | `/notification-template-admin/remove/{id}` | `notification-template-admin` | `Remove` | `inherit` | `query` |
| PUT | `/notification-template-admin/update/{id}` | `notification-template-admin` | `Update` | `inherit` | `body` |
| GET | `/notification-template-placeholder/all` | `notification-template-placeholder` | `GetAllPlaceholders` | `inherit` | `query` |
| GET | `/notification-template-placeholder/by-template-code/{templateCode}` | `notification-template-placeholder` | `GetPlaceholdersByTemplateCode` | `inherit` | `query` |
| POST | `/sent-notify/regiter_token` | `sent-notify` | `RegiterToken` | `inherit` | `body` |
| POST | `/sent-notify/send` | `sent-notify` | `Send` | `inherit` | `body` |

## Admin panel (50)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| POST | `/apikey/add` | `apikey` | `Add` | `authorized` | `body` |
| GET | `/apikey/admin-paged` | `apikey` | `GetAdminPagination` | `authorized` | `query` |
| POST | `/apikey/create` | `apikey` | `Create` | `authorized` | `body` |
| GET | `/apikey/detail/{id}` | `apikey` | `GetDetail` | `authorized` | `query` |
| GET | `/apikey/list` | `apikey` | `GetList` | `authorized` | `query` |
| GET | `/apikey/paged` | `apikey` | `GetPagination` | `authorized` | `query` |
| DELETE | `/apikey/remove/{id}` | `apikey` | `Remove` | `authorized` | `query` |
| PUT | `/apikey/replace/{id}` | `apikey` | `Replace` | `authorized` | `body` |
| PUT | `/apikey/update-info/{id}` | `apikey` | `UpdateInfo` | `authorized` | `body` |
| PUT | `/apikey/update/{id}` | `apikey` | `Update` | `authorized` | `body` |
| POST | `/api/v{version:apiVersion}/app-hot-update/admin/create` | `apphotupdate` | `Create` | `authorized` | `body` |
| GET | `/api/v{version:apiVersion}/app-hot-update/admin/detail/{id}` | `apphotupdate` | `GetDetail` | `authorized` | `query` |
| GET | `/api/v{version:apiVersion}/app-hot-update/admin/paged` | `apphotupdate` | `GetPaged` | `authorized` | `query` |
| DELETE | `/api/v{version:apiVersion}/app-hot-update/admin/remove/{id}` | `apphotupdate` | `Remove` | `authorized` | `query` |
| PATCH | `/api/v{version:apiVersion}/app-hot-update/admin/set-active/{id}` | `apphotupdate` | `SetActive` | `authorized` | `body` |
| PUT | `/api/v{version:apiVersion}/app-hot-update/admin/update/{id}` | `apphotupdate` | `Update` | `authorized` | `body` |
| GET | `/dashboard/qr-registrations` | `dashboard` | `GetQRRegistrations` | `authorized` | `query` |
| GET | `/dashboard/qr-registrations-by-date` | `dashboard` | `GetQRRegistrationsByDateRange` | `authorized` | `query` |
| GET | `/dashboard/qr-scans` | `dashboard` | `GetQRScans` | `authorized` | `query` |
| GET | `/dashboard/qr-scans-by-date` | `dashboard` | `GetQRScansByDateRange` | `authorized` | `query` |
| GET | `/dashboard/user-registrations` | `dashboard` | `GetUserRegistrations` | `authorized` | `query` |
| GET | `/dashboard/user-registrations-by-date` | `dashboard` | `GetUserRegistrationsByDateRange` | `authorized` | `query` |
| PUT | `/feedback/hide/{id}` | `feedback` | `HideFeedback` | `authorized` | `body` |
| GET | `/feedback/list` | `feedback` | `GetList` | `authorized` | `query` |
| GET | `/feedback/paged` | `feedback` | `GetPagination` | `authorized` | `query` |
| POST | `/media/upload-news` | `media` | `CreateMediaByNews` | `authorized` | `form` |
| GET | `/news` | `news` | `GetPagination` | `anonymous` | `query` |
| GET | `/news/{slug}` | `news` | `Get` | `anonymous` | `query` |
| PUT | `/news-admin/approve` | `news-admin` | `Approve` | `inherit` | `body` |
| POST | `/news-admin/create` | `news-admin` | `Create` | `inherit` | `body` |
| GET | `/news-admin/detail/{id}` | `news-admin` | `GetDetail` | `inherit` | `query` |
| POST | `/news-admin/duplicate/{id}` | `news-admin` | `Duplicate` | `inherit` | `body` |
| GET | `/news-admin/generate-code` | `news-admin` | `GenerateCode` | `inherit` | `query` |
| GET | `/news-admin/list` | `news-admin` | `GetList` | `inherit` | `query` |
| GET | `/news-admin/paged` | `news-admin` | `GetPagination` | `inherit` | `query` |
| GET | `/news-admin/pagination-selection` | `news-admin` | `GetPaginationSelection` | `inherit` | `query` |
| PUT | `/news-admin/reject` | `news-admin` | `Reject` | `inherit` | `body` |
| PATCH | `/news-admin/remove-multiple` | `news-admin` | `Remove` | `inherit` | `body` |
| DELETE | `/news-admin/remove/{id}` | `news-admin` | `Remove` | `inherit` | `query` |
| PUT | `/news-admin/request-publish/{id}` | `news-admin` | `RequestPublish` | `inherit` | `body` |
| GET | `/news-admin/selection` | `news-admin` | `GetSelection` | `inherit` | `query` |
| PUT | `/news-admin/update/{id}` | `news-admin` | `Update` | `inherit` | `body` |
| PUT | `/reports` | `reports` | `Get` | `anonymous` | `body` |
| GET | `/reports/reasons` | `reports` | `Get` | `anonymous` | `query` |
| POST | `/support/create` | `support` | `Create` | `authorized` | `body` |
| DELETE | `/support/delete/{id}` | `support` | `Delete` | `authorized` | `query` |
| GET | `/support/list` | `support` | `GetList` | `authorized` | `query` |
| GET | `/support/paged` | `support` | `GetPagination` | `authorized` | `query` |
| PUT | `/support/update` | `support` | `Update` | `authorized` | `body` |
| GET | `/support/{id}` | `support` | `GetById` | `authorized` | `query` |

## Monitoring / operations (2)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/api/v{version:apiVersion}/app-hot-update/manifest` | `apphotupdate` | `GetManifest` | `anonymous` | `query` |
| POST | `/user-behavior/track-interaction` | `user-behavior` | `TrackInteraction` | `anonymous` | `body` |

## Content / community (38)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| POST | `/chat/create` | `chat` | `Create` | `authorized` | `body` |
| GET | `/chat/detail/{id}` | `chat` | `GetDetail` | `authorized` | `query` |
| GET | `/chat/list` | `chat` | `GetList` | `authorized` | `query` |
| DELETE | `/chat/remove/{id}` | `chat` | `Remove` | `authorized` | `query` |
| POST | `/chat/sse` | `chat` | `StreamSse` | `authorized` | `body` |
| POST | `/chat/submit_file` | `chat` | `Submit_File` | `authorized` | `body` |
| PUT | `/chat/update-info/{id}` | `chat` | `UpdateInfo` | `authorized` | `body` |
| PUT | `/chat/update/{id}` | `chat` | `Update` | `authorized` | `body` |
| GET | `/comments` | `comments` | `Get` | `anonymous` | `query` |
| POST | `/comments` | `comments` | `Create` | `authorized` | `form` |
| POST | `/comments/add-comment` | `comments` | `AddComment` | `authorized` | `form` |
| POST | `/comments/add-reaction` | `comments` | `AddReaction` | `authorized` | `form` |
| DELETE | `/comments/delete-reaction/{id}` | `comments` | `DeleteReaction` | `authorized` | `query` |
| DELETE | `/comments/{id}` | `comments` | `DeleteComment` | `authorized` | `query` |
| PUT | `/comments/{id}` | `comments` | `UpdateComment` | `authorized` | `body` |
| POST | `/media/delete` | `media` | `DeletePrefixMediaStore` | `authorized` | `form` |
| POST | `/media/upload` | `media` | `CreateMediaStore` | `authorized` | `form` |
| POST | `/media/upload-file-chat` | `media` | `CreateChatMedia` | `authorized` | `form` |
| POST | `/media/upload-prefix` | `media` | `CreatePrefixMediaStore` | `authorized` | `form` |
| GET | `/posts` | `posts` | `Get` | `anonymous` | `query` |
| POST | `/posts` | `posts` | `Create` | `authorized` | `form` |
| PUT | `/posts` | `posts` | `Update` | `authorized` | `body` |
| POST | `/posts/add-reaction` | `posts` | `AddReaction` | `authorized` | `form` |
| POST | `/posts/approve-posts` | `posts` | `Approve` | `anonymous` | `body` |
| GET | `/posts/categories` | `posts` | `Get` | `anonymous` | `query` |
| POST | `/posts/create-crawled-post` | `posts` | `CreateCrawledPost` | `authorized` | `form` |
| DELETE | `/posts/delete-reaction/{id}` | `posts` | `DeleteReaction` | `authorized` | `query` |
| GET | `/posts/ids` | `posts` | `GetByIds` | `anonymous` | `query` |
| GET | `/posts/pending` | `posts` | `Get` | `authorized` | `query` |
| GET | `/posts/recommend` | `posts` | `GetRecommendPosts` | `anonymous` | `query` |
| POST | `/posts/reject-posts` | `posts` | `Reject` | `anonymous` | `body` |
| PUT | `/posts/scores` | `posts` | `Update` | `authorized` | `body` |
| POST | `/posts/tiktok/import` | `posts` | `Import` | `authorized` | `body` |
| DELETE | `/posts/{id:long}` | `posts` | `Delete` | `authorized` | `query` |
| GET | `/posts/{id:long}` | `posts` | `Get` | `anonymous` | `query` |
| GET | `/socials` | `socials` | `Get` | `inherit` | `query` |
| GET | `/videos/{id:long}` | `videos` | `Get` | `authorized` | `query` |
| GET | `/videos/{id:long}/stream` | `videos` | `Stream` | `authorized` | `query` |

## Infrastructure / platform (45)

| Method | Route | Controller | Action | Auth | Binding |
|---|---|---|---|---|---|
| GET | `/country/list` | `country` | `GetList` | `inherit` | `query` |
| GET | `/interests` | `interests` | `GetAllInterest` | `anonymous` | `query` |
| POST | `/interests` | `interests` | `CreateInterest` | `authorized` | `body` |
| GET | `/interests/user-interests` | `interests` | `GetUserInterests` | `authorized` | `query` |
| POST | `/interests/user-interests` | `interests` | `CreateUserInterest` | `anonymous` | `form` |
| DELETE | `/interests/user-interests/{id}` | `interests` | `DeleteUserInterest` | `authorized` | `query` |
| DELETE | `/interests/{id}` | `interests` | `DeleteInterest` | `authorized` | `query` |
| GET | `/interests/{id}` | `interests` | `GetInterest` | `anonymous` | `query` |
| PUT | `/interests/{id}` | `interests` | `UpdateInterest` | `authorized` | `body` |
| POST | `/invitation/accept-invitation` | `invitation` | `AcceptConfirm` | `inherit` | `body` |
| POST | `/invitation/create` | `invitation` | `Create` | `authorized` | `body` |
| POST | `/api/v1/ionic-web/qr/scan` | `ionic-web` | `IncrementTotalScans` | `anonymous` | `body` |
| POST | `/api/v1/ionic-web/upload-image-review` | `ionic-web` | `CreateImageReview` | `anonymous` | `body` |
| POST | `/language/create` | `language` | `Create` | `authorized` | `body` |
| GET | `/language/detail/{id}` | `language` | `GetDetail` | `authorized` | `query` |
| GET | `/language/generate-code` | `language` | `GenerateCode` | `authorized` | `query` |
| GET | `/language/list` | `language` | `GetList` | `authorized` | `query` |
| GET | `/language/paged` | `language` | `GetPagination` | `authorized` | `query` |
| DELETE | `/language/remove/{id}` | `language` | `Remove` | `authorized` | `query` |
| GET | `/language/selection` | `language` | `GetSelection` | `anonymous` | `query` |
| PUT | `/language/update/{id}` | `language` | `Update` | `authorized` | `body` |
| POST | `/qr/create` | `qr` | `Create` | `authorized` | `body` |
| DELETE | `/qr/delete/{id}` | `qr` | `Delete` | `authorized` | `query` |
| GET | `/qr/list` | `qr` | `GetList` | `authorized` | `query` |
| GET | `/qr/paged` | `qr` | `GetPagination` | `authorized` | `query` |
| GET | `/qr/scan-chart/{qrId}` | `qr` | `GetScanChart` | `authorized` | `query` |
| GET | `/qr/scanner/{qrCode}` | `qr` | `ScanQR` | `anonymous` | `query` |
| PUT | `/qr/update` | `qr` | `Update` | `authorized` | `body` |
| GET | `/qr/{id}` | `qr` | `GetById` | `authorized` | `query` |
| DELETE | `/storages/files` | `storages` | `DeleteFiles` | `authorized` | `body` |
| GET | `/storages/files` | `storages` | `ListFiles` | `authorized` | `query` |
| GET | `/storages/files/key` | `storages` | `GetFile` | `anonymous` | `query` |
| GET | `/storages/files/keys` | `storages` | `GetFiles` | `anonymous` | `query` |
| GET | `/storages/files/paged` | `storages` | `ListFilesPaged` | `authorized` | `query` |
| GET | `/storages/files/presigned-url` | `storages` | `GetPreSignedUrl` | `anonymous` | `query` |
| GET | `/storages/files/presigned-url/multiple` | `storages` | `GetPreSignedUrl` | `anonymous` | `query` |
| POST | `/storages/files/upload` | `storages` | `UploadFile` | `authorized` | `form` |
| POST | `/storages/files/upload/multiple` | `storages` | `UploadFiles` | `authorized` | `form` |
| POST | `/storages/files/upload/url` | `storages` | `UploadFileFromUrl` | `authorized` | `body` |
| POST | `/storages/files/upload/urls` | `storages` | `UploadFilesFromUrls` | `authorized` | `body` |
| DELETE | `/storages/files/{key}` | `storages` | `DeleteFile` | `authorized` | `query` |
| GET | `/storages/paged` | `storages` | `GetFilesPaged` | `authorized` | `query` |
| POST | `/toxic-word` | `toxic-word` | `CreateToxicWord` | `inherit` | `body` |
| GET | `/toxic-word/list` | `toxic-word` | `GetList` | `inherit` | `query` |
| GET | `/toxic-word/list-check` | `toxic-word` | `GetListCheck` | `inherit` | `query` |

