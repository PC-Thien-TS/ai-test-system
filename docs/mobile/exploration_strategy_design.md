# Exploration Strategy Design

This mobile exploration policy keeps autonomous exploration deterministic and bounded.

Rules:
- screen priorities weight coverage progress
- action ranking controls which supported action is chosen for each screen type
- risky actions can be skipped by policy
- stop conditions cap the loop and stop on cycles, no valid action, or repeated failures

Current supported screen types:
- `AUTH_LOGIN`
- `CONTENT_LIST`
- `CONTENT_DETAIL`
