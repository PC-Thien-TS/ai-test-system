## RM-MD-001: Payment callback retry window
module: Payment
submodule: Callback
priority: p0
source_type: api_contract
roles:
- system
acceptance:
- Callback retries transient failure up to 3 times.
- Callback timeout marks order pending_payment_review.
risk_hints:
- callback
- timeout
related_flows:
- payment_callback_retry_timeout
description: Ensure callback retry strategy is deterministic and auditable.

## RM-MD-002: Merchant rejection notification
module: Merchant Operations
priority: p1
source_type: prd
roles:
- merchant
- user
acceptance_criteria:
- Merchant rejection reason is required.
- User receives rejection notification.
business_rules:
- Reject must include predefined reason code.
dependencies:
- Notifications
related_flows:
- merchant_confirm_reject
- notification_triggers
