# Didaunao Release Audit API and Metrics Notes

This file is auto-generated from local source evidence.

- Business truth must still come from the KB context pack generated from `requirements/didaunao_release_audit/`.
- Use this file only for implementation facts such as endpoint surfaces, route names, controller exposure, and authorization hints.
- If the KB context does not state a business fact, mark it as `UNKNOWN`.

## Backend Snapshot

- Path: `C:\Projects\Rankmate\rankmate_be`
- Git branch: `develop`
- Git head: `96c4e591701ffcaa8afd7b000b7d2d567d5c3855`
- Tech stack: `dotnet, docker`
- Controller files: `49`
- Extracted endpoints: `346`
- Anonymous endpoints: `58`

## HTTP Method Counts

- `DELETE`: 36
- `GET`: 149
- `PATCH`: 5
- `POST`: 106
- `PUT`: 50

## Notable Review Endpoints

- `PUT /account/verify` (controller=`account`, auth=`authorized`, binding=`body`)
- `PUT /news-admin/reject` (controller=`news-admin`, auth=`inherit`, binding=`body`)
- `PUT /news-admin/approve` (controller=`news-admin`, auth=`inherit`, binding=`body`)
- `POST /posts/approve-posts` (controller=`posts`, auth=`anonymous`, binding=`body`)
- `POST /posts/reject-posts` (controller=`posts`, auth=`anonymous`, binding=`body`)
- `GET /store/verify` (controller=`store`, auth=`authorized`, binding=`query`)
- `GET /store/verify/detail/{id:long}` (controller=`store`, auth=`authorized`, binding=`query`)
- `GET /store/verify/detail` (controller=`store`, auth=`authorized`, binding=`query`)
- `POST /store/verify` (controller=`store`, auth=`authorized`, binding=`form`)
- `PUT /store/verify/{id:long}/approve` (controller=`store`, auth=`authorized`, binding=`body`)
- `PUT /store/verify/{id:long}/reject` (controller=`store`, auth=`authorized`, binding=`query`)

## Endpoint Sample

- `GET /account/avatar/{authorID:long}` (action=`GetUserAvatar`, auth=`anonymous`, binding=`query`)
- `GET /account/get-info` (action=`GetInfo`, auth=`authorized`, binding=`query`)
- `POST /account/update-info` (action=`UpdateInfo`, auth=`authorized`, binding=`body`)
- `POST /account/change-password` (action=`ChangePassword`, auth=`authorized`, binding=`body`)
- `POST /account/update-account-v2` (action=`UpdateAccount`, auth=`authorized`, binding=`form`)
- `POST /account/upload-avatar` (action=`CreateLogo`, auth=`anonymous`, binding=`form`)
- `POST /account/otp` (action=`SendOtp`, auth=`authorized`, binding=`body`)
- `PUT /account/verify` (action=`VerifyAccount`, auth=`authorized`, binding=`body`)
- `GET /apikey/list` (action=`GetList`, auth=`authorized`, binding=`query`)
- `GET /apikey/paged` (action=`GetPagination`, auth=`authorized`, binding=`query`)
- `GET /apikey/admin-paged` (action=`GetAdminPagination`, auth=`authorized`, binding=`query`)
- `GET /apikey/detail/{id}` (action=`GetDetail`, auth=`authorized`, binding=`query`)
- `POST /apikey/create` (action=`Create`, auth=`authorized`, binding=`body`)
- `POST /apikey/add` (action=`Add`, auth=`authorized`, binding=`body`)
- `PUT /apikey/update/{id}` (action=`Update`, auth=`authorized`, binding=`body`)
- `PUT /apikey/replace/{id}` (action=`Replace`, auth=`authorized`, binding=`body`)
- `PUT /apikey/update-info/{id}` (action=`UpdateInfo`, auth=`authorized`, binding=`body`)
- `DELETE /apikey/remove/{id}` (action=`Remove`, auth=`authorized`, binding=`query`)
- `GET /api/v{version:apiVersion}/app-hot-update/manifest` (action=`GetManifest`, auth=`anonymous`, binding=`query`)
- `GET /api/v{version:apiVersion}/app-hot-update/admin/paged` (action=`GetPaged`, auth=`authorized`, binding=`query`)
