# QA Platform v1.0 Baseline

This baseline freezes the current QA platform in a release-ready state before focus shifts to deeper mobile testing.

## Current Capabilities

- Deterministic end-to-end QA pipeline via `scripts/run_full_pipeline.py`
- Decision-driven CI/release evaluation with severity, recurrence, flaky, protected-path, and release-critical signals
- Self-healing v1 that performs decision-driven last-failed reruns and updates release outcome when reruns pass
- Failure memory v1 that records repeated failures, seen counts, flaky score, and rerun success history
- Dashboard snapshot generation from pipeline artifacts
- Lark notification hooks with dry-run-safe behavior and non-blocking execution

## Main Pipeline Flow

1. Run pytest and persist structured report artifacts
2. Analyze failures into grouped failure intelligence
3. Evaluate release decision and gating outcome
4. Execute self-healing v1 only when rerun is recommended
5. Update failure memory from the run result
6. Emit Lark notification hooks
7. Write dashboard and pipeline summary artifacts

## What Is Included In v1.0

- Decision policy engine v2 with memory-aware flaky handling
- Decision-driven pipeline orchestration
- Self-healing v1 last-failed rerun path
- Failure memory v1 persistence and reuse in policy decisions
- Dashboard intelligence snapshot support
- Lark connector and flow-hook integration

## Known Limitations / Technical Debt

- Admin UI login/dashboard flow is still not stable enough for dependable UI E2E gating
- Several API paths remain known backend defects and are tracked in `docs/KNOWN_BLOCKERS.md`
- Some admin/business regressions still depend on account scope and can skip under non-admin credentials
- Windows pytest temp-directory behavior can still interfere with broader tmp-path-heavy test slices
- Self-healing remains intentionally narrow: rerun-focused, not a broader remediation framework

## Next Recommended Direction

Freeze this baseline, keep release changes minimal, and shift the next major effort toward deep mobile testing with the current QA platform as the stable reference point.
