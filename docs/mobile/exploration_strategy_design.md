# Exploration Strategy Design

## Overview

The Exploration Strategy Model provides a structured approach for autonomous mobile testing, enabling the system to decide what to prioritize, when to stop, and how to measure useful coverage. This differs from the current deterministic runner by introducing priority-based action selection, coverage-driven exploration, and adaptive stop conditions.

## How Exploration Uses Priority + Coverage + Stop Rules

### Priority-Based Exploration

The exploration system prioritizes screens and actions based on:

1. **Screen Priority**: Screens are explored in order of priority (AUTH_LOGIN → CONTENT_LIST → CONTENT_DETAIL)
   - Priority 1 (AUTH_LOGIN): Entry point, critical for authentication
   - Priority 2 (CONTENT_LIST): Core content screen, high value
   - Priority 3 (CONTENT_DETAIL): Transaction screen, high value

2. **Action Ranking**: Within each screen, actions are ranked:
   - **Primary actions**: Core functionality (submit, add to cart, navigate)
   - **Secondary actions**: Optional functionality (search, filter, share)
   - **Recovery actions**: Error handling (clear error, retry, navigate back)

3. **Risk Assessment**: Actions are classified by risk:
   - **High risk**: Navigation away from core flow (forgot password, share)
   - **Medium risk**: Filtering and search actions
   - **Low risk**: Core input and submit actions

### Coverage-Driven Exploration

The exploration system tracks and optimizes coverage:

1. **Coverage Elements**: Each screen has defined coverage elements
   - AUTH_LOGIN: INPUT_USERNAME, INPUT_PASSWORD, ACTION_SUBMIT, SIGNAL_ERROR, SIGNAL_LOADING
   - CONTENT_LIST: LIST_CONTENT, INPUT_SEARCH, ACTION_FILTER, SIGNAL_EMPTY, SIGNAL_LOADING
   - CONTENT_DETAIL: CONTENT_IMAGE, CONTENT_TITLE, CONTENT_PRICE, ACTION_ADD_TO_CART, NAVIGATION_BACK

2. **Coverage Calculation**: Weighted average of screen coverage
   - Formula: `(screen_coverage * weight) / total_weight`
   - Weights: AUTH_LOGIN (0.4), CONTENT_LIST (0.3), CONTENT_DETAIL (0.3)

3. **Coverage Thresholds**:
   - Minimum: 60% (acceptable)
   - Satisfactory: 80% (good)
   - Excellent: 95% (optimal)

4. **Coverage Targets**:
   - AUTH_LOGIN: 100% required (critical)
   - CONTENT_LIST: 80% required, 20% optional
   - CONTENT_DETAIL: 80% required, 20% optional

### Stop Conditions

The exploration system stops based on multiple conditions:

1. **Global Stop Conditions**:
   - Max steps reached (default: 100)
   - Max cycles detected (default: 3)
   - Coverage threshold reached (default: 90%)
   - Repeated failure count (default: 5)
   - No valid action available

2. **Per-Screen Stop Conditions**:
   - Max steps per screen reached (default: 20)
   - Screen coverage complete (100%)
   - Screen failure count (default: 3)

3. **Fallback Behavior**:
   - On action failure: Retry → Use recovery action
   - On screen failure: Mark failed → Move to next screen
   - On exhausted actions: Move to next screen → Stop exploration

## Differences from Deterministic Runner

### Current Deterministic Runner

The current bounded exploration runner operates with:
- **Fixed action sequences**: Actions executed in predefined order
- **No priority**: All actions treated equally
- **No coverage tracking**: No measurement of what has been tested
- **Fixed stop conditions**: Stops after max steps or cycles
- **No adaptation**: Does not adjust based on results
- **No risk assessment**: All actions executed regardless of risk

### New Exploration Strategy

The new exploration strategy introduces:

1. **Priority-Based Action Selection**
   - Actions ranked by importance (primary > secondary > recovery)
   - High-risk actions executed last and limited
   - Preferred actions executed first
   - Adaptive based on screen type

2. **Coverage-Driven Exploration**
   - Tracks which elements have been covered
   - Calculates coverage score using weighted formula
   - Stops when coverage threshold reached
   - Prioritizes uncovered elements

3. **Adaptive Stop Conditions**
   - Multiple stop conditions (steps, cycles, coverage, failures)
   - Per-screen stop conditions
   - Early stop on success (coverage threshold)
   - Early stop on failure (repeated failures)

4. **Risk Mitigation**
   - Actions classified by risk level
   - High-risk actions limited in execution
   - Risk-aware action ordering
   - Fallback behaviors for failures

5. **Screen-Specific Policies**
   - Each screen type has custom policy
   - Different max steps per screen
   - Different retry policies
   - Different coverage requirements

6. **Exploration Order**
   - Screens explored in priority order
   - Entry points explored first
   - Exit points explored last
   - Navigation flows respected

## Execution Flow

### Initialization

1. Load exploration policy from `schemas/exploration_policy.yaml`
2. Load screen definitions from `schemas/mobile_app_manifest.yaml`
3. Load screen contracts from `taxonomy/screen_contract_*.md`
4. Initialize coverage tracker
5. Initialize cycle detector

### Exploration Loop

```
For each screen in exploration_order:
  1. Load screen-specific policy
  2. For each step up to max_steps_per_screen:
     a. Select action based on ranking and risk
     b. Execute action
     c. Update coverage tracker
     d. Check stop conditions
     e. Handle failures with retry/recovery
  3. Check screen coverage
  4. Move to next screen or stop

Check global stop conditions
Calculate final coverage score
Report results
```

### Action Selection

1. **Check coverage**: Identify uncovered elements
2. **Rank actions**: Prioritize primary actions that cover uncovered elements
3. **Assess risk**: Filter high-risk actions if limit reached
4. **Select action**: Choose highest-ranked available action
5. **Execute action**: Perform action and track result

### Coverage Tracking

1. **Element coverage**: Track which elements have been interacted with
2. **Screen coverage**: Calculate percentage of covered elements per screen
3. **Overall coverage**: Calculate weighted average across screens
4. **Coverage contribution**: Each screen contributes based on weight

## Integration with Existing Components

### Classifier
- Uses screen type to load exploration policy
- Identifies current screen for priority lookup

### Planner
- Uses action ranking to generate action sequence
- Respects risk assessment for action selection
- Applies retry policies for failed actions

### Oracle
- Validates action results
- Provides coverage feedback
- Triggers recovery actions on failure

### Action Selector
- Selects next action based on ranking
- Respects risk limits
- Prioritizes uncovered elements

### Bounded Exploration Runner
- Enforces stop conditions
- Tracks steps and cycles
- Manages exploration state

## Example Scenarios

### Scenario 1: Happy Path Exploration

1. Start with AUTH_LOGIN (priority 1)
2. Execute primary actions: INPUT_USERNAME, INPUT_PASSWORD, ACTION_SUBMIT
3. Validate with oracle (ORC-NET-001)
4. Navigate to CONTENT_LIST (priority 2)
5. Execute primary actions: LIST_CONTENT, open_first_item
6. Navigate to CONTENT_DETAIL (priority 3)
7. Execute primary actions: ACTION_ADD_TO_CART, NAVIGATION_BACK
8. Return to CONTENT_LIST
9. Calculate coverage: 100% (AUTH_LOGIN) + 80% (CONTENT_LIST) + 80% (CONTENT_DETAIL)
10. Stop when coverage threshold reached

### Scenario 2: Error Recovery

1. Start with AUTH_LOGIN
2. Execute INPUT_USERNAME, INPUT_PASSWORD
3. Execute ACTION_SUBMIT
4. Oracle fails (ORC-FAIL-001)
5. Apply retry policy: retry_submit (max 3 attempts)
6. Retry fails
7. Apply recovery action: clear_error
8. Retry login with valid credentials
9. Succeed and continue exploration

### Scenario 3: Coverage Optimization

1. Start with CONTENT_LIST
2. Execute LIST_CONTENT (covers LIST_CONTENT element)
3. Execute INPUT_SEARCH (covers INPUT_SEARCH element)
4. Execute ACTION_FILTER (covers ACTION_FILTER element)
5. Check coverage: 60% (3/5 elements)
6. Continue exploration to cover remaining elements
7. Execute pull_to_refresh (covers SIGNAL_LOADING)
8. Execute search with empty result (covers SIGNAL_EMPTY)
9. Check coverage: 100% (5/5 elements)
10. Move to next screen

## Configuration

### Tuning Parameters

- **max_total_steps**: Increase for more thorough exploration
- **max_steps_per_screen**: Adjust based on screen complexity
- **max_cycles**: Increase for more cycle tolerance
- **coverage_threshold**: Adjust based on quality requirements
- **retry_policy**: Adjust for network reliability

### Adding New Screen Types

1. Add screen priority to `screen_priorities`
2. Add coverage strategy to `coverage_strategy`
3. Add action ranking to `action_ranking`
4. Add to `exploration_order`
5. Create screen contract in `taxonomy/`

### Modifying Risk Assessment

1. Update `risk_assessment` section
2. Adjust risk levels for actions
3. Modify risk mitigation strategies
4. Update action ranking if needed

## Benefits

1. **Prioritized Exploration**: Focus on high-value screens and actions first
2. **Coverage-Driven**: Stop when sufficient coverage achieved
3. **Risk-Aware**: Limit risky actions to prevent exploration divergence
4. **Adaptive**: Adjust behavior based on results
5. **Configurable**: Easy to tune for different requirements
6. **Measurable**: Clear coverage metrics for reporting

## Limitations

1. **Static Policy**: Policy must be updated manually for new screen types
2. **No Learning**: Does not learn from previous explorations
3. **Fixed Weights**: Coverage weights are static
4. **No Context**: Does not consider user behavior patterns
5. **Limited Adaptation**: Adaptation is rule-based, not AI-driven

## Future Enhancements

1. **Dynamic Policy Generation**: Generate policy from screen contracts automatically
2. **Learning-Based Exploration**: Use ML to prioritize actions based on historical data
3. **Adaptive Weights**: Adjust coverage weights based on app structure
4. **Context Awareness**: Consider user behavior patterns
5. **Multi-Objective Optimization**: Balance coverage, time, and risk
