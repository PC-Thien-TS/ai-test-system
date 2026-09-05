# MED315 Known Bug Patterns

Use these patterns when selecting regression cases for a release.

## Data persistence

- Data saves successfully but disappears after reload or reopening the visit.
- Updated data is visible on one screen but stale on another.
- Historical obstetric data is not loaded when expected.

## Cross-module synchronization

- Diagnosis is saved in examination but missing from indication/print.
- Doctor information is incorrect or missing on downstream forms.
- Ultrasound or fetal-heart information is not synchronized correctly.
- Catalog changes are synchronized but not available in downstream workflows.

## Permission and visibility

- User has permission but UI does not display the corresponding information/action.
- UI hides a function but direct access is still possible.
- Data from another branch is accessible outside the user's assigned scope.

## Inventory

- Stock changes twice after repeated confirmation.
- Source/destination stock becomes inconsistent during transfer.
- Lot or expiry information changes unexpectedly across transfer states.
- Branch deactivation is allowed while inventory or pending receipts still exist.

## Printing

- Expiry date wraps incorrectly on A4 transfer documents.
- Vietnamese text overlaps, clips, or loses characters.
- Printed values differ from the values displayed on screen.
- Date/time or doctor information is stale after save and print.

## Navigation and interaction

- Tab order does not follow the expected sequence in vital-sign input.
- Save & Print unexpectedly changes follow-up date or other stored values.

## Regression rule

When a changed module matches one of these patterns, include at least one case that verifies the historical failure mode in addition to the direct functional tests.