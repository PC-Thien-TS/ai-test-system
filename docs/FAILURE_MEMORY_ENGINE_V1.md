# Failure Memory Engine v1

## Overview

`FailureMemoryEngine` is the intelligence layer between incoming failures and persistent memory.

- `MemoryRepository`: storage persistence
- `VectorMemoryRepository`: semantic candidate lookup
- `FailureMemoryEngine`: resolution, merge/create decisions, confidence evolution, action learning

## Resolution Pipeline

1. Build canonical signature from normalized failure input.
2. Attempt exact match by `signature_hash`.
3. If no exact hit, run semantic lookup and rank candidates.
4. Decide one of:
   - `EXACT_MATCH`
   - `SIMILAR_MATCH`
   - `AMBIGUOUS_MATCH`
   - `NEW_MEMORY`

## Deterministic Merge/Create Rules

- Exact hit: update recurrence and confidence.
- Similarity >= auto-merge threshold and non-ambiguous: merge/update existing memory.
- Ambiguous similarity: return candidates without auto-merge.
- No valid candidate: create new memory.

## Action Learning

Action outcomes update:

- `action_history`
- `action_effectiveness[action_type]` with:
  - `success_count`
  - `failure_count`
  - `effectiveness_score`

Best action selection is deterministic and score-based.

## Confidence Evolution

Rules (configurable):

- exact recurrence: confidence boost
- similar merge: smaller confidence boost
- contradictory root-cause signal: confidence decay

## Configuration

Supported env controls:

- `MEMORY_EXACT_MATCH_ENABLED`
- `MEMORY_SEMANTIC_MATCH_ENABLED`
- `MEMORY_SIMILARITY_THRESHOLD`
- `MEMORY_AUTO_MERGE_THRESHOLD`
- `MEMORY_AMBIGUOUS_THRESHOLD`
- `MEMORY_CONFIDENCE_BOOST_EXACT`
- `MEMORY_CONFIDENCE_DECAY_CONTRADICTION`

## Integration Notes

### Triage

Pre-triage:
- call `build_triage_memory_context(...)`
- feed memory context into LLM triage prompt

Post-triage:
- call `update_memory_after_triage(...)` with final root cause and confidence

### Self-healing

- choose action via `choose_action_for_self_healing(...)`
- execute action
- record result via `record_self_healing_outcome(...)`

### CI Gate

- consume recurrence/severity signal via `derive_ci_memory_signal(...)`
- increase strictness when recurring high-severity memory is detected

## Migration Path

1. Keep current deterministic pipelines unchanged.
2. Add pre-triage memory resolution call.
3. Add post-triage memory update call.
4. Add self-healing action outcome recording.
5. Add CI gate severity/recurrence consumption.
6. Surface recurring memory + best actions in dashboard.
