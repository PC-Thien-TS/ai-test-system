# Menu/Service Module SRS Skeleton

## Module Overview

Catalog readiness for ordering, including menu/category and orderable service/item setup.

## Actors / Roles

- Merchant user
- Admin user
- End user (consumer of published catalog)

## Feature List

- Create/manage menu/category structure
- Configure orderable items/services
- Set pricing and active/published states

## Functional Requirements

- `MENU-REQ-001`: At least one menu/category can be configured for a store.
- `MENU-REQ-002`: At least one orderable item/service can be configured.
- `MENU-REQ-003`: Item/service price is configured and retrievable.
- `MENU-REQ-004`: Catalog publishing/active state controls ordering availability.

## Business Rules

- Ordering requires active and published catalog entities.
- Price must be present for orderable item/service.
- Hidden/inactive catalog entries are not orderable.

## Assumptions / Dependencies

- Catalog-related APIs may be spread across multiple modules.
- Store and merchant linkage are already valid.

## Open Questions

- Exact API ownership for menu/category/service in current product split.
- Required minimum fields for item/service activation.

## Placeholder Traceability IDs

- `MENU-REQ-001` -> `MENU-TBD-001`
- `MENU-REQ-002` -> `MENU-TBD-002`
- `MENU-REQ-003` -> `MENU-TBD-003`
- `MENU-REQ-004` -> `MENU-TBD-004`
