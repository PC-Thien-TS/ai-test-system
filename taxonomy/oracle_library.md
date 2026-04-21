# Oracle Library

Predefined success and failure conditions for mobile testing.

## Oracle Structure

### Oracle Definition
- **Oracle ID**: Unique identifier
- **Name**: Human-readable name
- **Type**: Success condition or failure condition
- **Category**: Functional, non-functional, security, performance, accessibility
- **Severity**: Critical, high, medium, low
- **Condition**: Testable condition
- **Expected Value**: Expected outcome
- **Operator**: Comparison operator
- **Description**: What the oracle checks
- **Rationale**: Why this oracle is important

## Validation Oracles

### ORC-VAL-001: Email Format Validation
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Email field accepts only valid email format
- **Expected Value**: Valid email regex pattern matched
- **Operator**: Matches
- **Description**: Email input field validates format using regex pattern
- **Rationale**: Prevents invalid email submission, ensures data quality

### ORC-VAL-002: Password Requirements
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Password meets minimum requirements
- **Expected Value**: Length >= 8, contains uppercase, lowercase, number, special character
- **Operator**: All conditions met
- **Description**: Password field enforces complexity requirements
- **Rationale**: Ensures password security, prevents weak passwords

### ORC-VAL-003: Required Field Validation
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: All required fields are filled before submission
- **Expected Value**: No empty required fields
- **Operator**: Equals
- **Description**: Form submission blocked when required fields empty
- **Rationale**: Prevents incomplete data submission, ensures data integrity

### ORC-VAL-004: Phone Format Validation
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Phone number matches valid format
- **Expected Value**: Valid phone regex pattern matched
- **Operator**: Matches
- **Description**: Phone input field validates format
- **Rationale**: Ensures valid phone numbers, prevents invalid submissions

### ORC-VAL-005: Password Matching
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Password and confirm password fields match
- **Expected Value**: Password == Confirm Password
- **Operator**: Equals
- **Description**: Registration form ensures password confirmation matches
- **Rationale**: Prevents user error, ensures password accuracy

### ORC-VAL-006: Terms Acceptance
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Terms of service checkbox must be checked
- **Expected Value**: Checkbox == Checked
- **Operator**: Equals
- **Description**: Registration requires terms acceptance
- **Rationale**: Legal compliance, user consent

### ORC-VAL-007: Quantity Constraints
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Quantity input within valid range
- **Expected Value**: 1 <= Quantity <= Max Stock
- **Operator**: Greater than or equal AND less than or equal
- **Description**: Cart quantity respects stock limits
- **Rationale**: Prevents over-ordering, inventory management

### ORC-VAL-008: Address Validation
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Address fields contain valid data
- **Expected Value**: All required address fields filled, valid format
- **Operator**: All conditions met
- **Description**: Checkout form validates address completeness
- **Rationale**: Ensures delivery success, prevents shipping errors

## Network Oracles

### ORC-NET-001: Login API Success
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Login API returns success on valid credentials
- **Expected Value**: HTTP 200, auth token returned
- **Operator**: Equals
- **Description**: Valid credentials successfully authenticate
- **Rationale**: Core authentication flow must work

### ORC-NET-002: Network Error Handling
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: App displays user-friendly error on network failure
- **Expected Value**: Error message displayed, user can retry
- **Operator**: Contains
- **Description**: Network failures handled gracefully
- **Rationale**: User experience, error resilience

### ORC-NET-003: API Timeout Handling
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: App handles API timeout without crash
- **Expected Value**: Timeout error message displayed, app remains functional
- **Operator**: Contains
- **Description**: API timeouts handled gracefully
- **Rationale**: Prevents app crashes, user experience

### ORC-NET-004: Data Refresh on Pull
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Medium
- **Condition**: Pull-to-refresh refreshes data
- **Expected Value**: New data displayed after pull
- **Operator**: Not equals (before vs after)
- **Description**: Pull gesture triggers data refresh
- **Rationale**: User expectation, data freshness

### ORC-NET-005: Offline Detection
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: App detects offline state
- **Expected Value**: Offline indicator displayed
- **Operator**: Contains
- **Description**: Network state changes detected
- **Rationale**: User awareness, offline functionality

### ORC-NET-006: Pagination Loading
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Medium
- **Condition**: Scroll triggers next page load
- **Expected Value**: Additional items loaded
- **Operator**: Greater than (item count)
- **Description**: Infinite scroll loads more data
- **Rationale**: User experience, data accessibility

## Lifecycle Oracles

### ORC-LIF-001: State Preservation on Rotation
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Form data preserved on screen rotation
- **Expected Value**: Input values unchanged after rotation
- **Operator**: Equals
- **Description**: Screen rotation preserves user input
- **Rationale**: User experience, data loss prevention

### ORC-LIF-002: Background/Foreground Transition
- **Type**: Success condition
- **Category**: Functional
- **Severity**: High
- **Condition**: App state preserved on background/foreground
- **Expected Value**: Screen state unchanged after transition
- **Operator**: Equals
- **Description**: App state survives background transition
- **Rationale**: User experience, state management

### ORC-LIF-003: Scroll Position Persistence
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Medium
- **Condition**: Scroll position preserved on navigation
- **Expected Value**: Scroll position unchanged on return
- **Operator**: Equals
- **Description**: List scroll position saved
- **Rationale**: User experience, navigation convenience

### ORC-LIF-004: Tab State Persistence
- **Type**: Success condition
- **Category**: Functional
- **Severity**: Medium
- **Condition**: Active tab preserved on app restart
- **Expected Value**: Same tab active after restart
- **Operator**: Equals
- **Description**: Tab selection remembered
- **Rationale**: User experience, state persistence

## Performance Oracles

### ORC-PER-001: Login Completion Time
- **Type**: Success condition
- **Category**: Performance
- **Severity**: High
- **Condition**: Login completes within acceptable time
- **Expected Value**: Time <= 3 seconds
- **Operator**: Less than or equal
- **Description**: Login flow completes quickly
- **Rationale**: User experience, performance benchmark

### ORC-PER-002: Screen Load Time
- **Type**: Success condition
- **Category**: Performance
- **Severity**: High
- **Condition**: Screen loads within acceptable time
- **Expected Value**: Time <= 2 seconds
- **Operator**: Less than or equal
- **Description**: Screen content displays quickly
- **Rationale**: User experience, performance benchmark

### ORC-PER-003: List Scroll Smoothness
- **Type**: Success condition
- **Category**: Performance
- **Severity**: Medium
- **Condition**: List scrolling maintains 60 FPS
- **Expected Value**: Frame rate >= 55 FPS
- **Operator**: Greater than or equal
- **Description**: Scrolling is smooth and responsive
- **Rationale**: User experience, performance quality

### ORC-PER-004: Animation Smoothness
- **Type**: Success condition
- **Category**: Performance
- **Severity**: Medium
- **Condition**: Animations maintain 60 FPS
- **Expected Value**: Frame rate >= 55 FPS
- **Operator**: Greater than or equal
- **Description**: Transitions are smooth
- **Rationale**: User experience, visual quality

### ORC-PER-005: Memory Usage
- **Type**: Success condition
- **Category**: Performance
- **Severity**: Medium
- **Condition**: App memory usage within limits
- **Expected Value**: Memory <= 500 MB
- **Operator**: Less than or equal
- **Description**: App doesn't leak memory
- **Rationale**: Resource management, stability

## Accessibility Oracles

### ORC-ACC-001: Screen Reader Labels
- **Type**: Success condition
- **Category**: Accessibility
- **Severity**: Critical
- **Condition**: All interactive elements have accessibility labels
- **Expected Value**: Accessibility label present for all interactive elements
- **Operator**: Equals
- **Description**: Screen reader can announce all controls
- **Rationale**: Accessibility compliance, inclusive design

### ORC-ACC-002: Focus Order
- **Type**: Success condition
- **Category**: Accessibility
- **Severity**: High
- **Condition**: Focus order follows visual layout
- **Expected Value**: Focus order matches reading order
- **Operator**: Equals
- **Description**: Keyboard navigation follows logical order
- **Rationale**: Accessibility compliance, keyboard navigation

### ORC-ACC-003: Color Contrast
- **Type**: Success condition
- **Category**: Accessibility
- **Severity**: High
- **Condition**: Text meets WCAG AA contrast ratio
- **Expected Value**: Contrast ratio >= 4.5:1
- **Operator**: Greater than or equal
- **Description**: Text is readable for visually impaired users
- **Rationale**: Accessibility compliance, readability

### ORC-ACC-004: Touch Target Size
- **Type**: Success condition
- **Category**: Accessibility
- **Severity**: High
- **Condition**: Touch targets meet minimum size
- **Expected Value**: Size >= 44x44 points
- **Operator**: Greater than or equal
- **Description**: Buttons and controls are large enough
- **Rationale**: Accessibility compliance, usability

### ORC-ACC-005: Dynamic Text Support
- **Type**: Success condition
- **Category**: Accessibility
- **Severity**: Medium
- **Condition**: UI adapts to system text size
- **Expected Value**: Layout adjusts without breaking
- **Operator**: Not broken
- **Description**: Text scaling works correctly
- **Rationale**: Accessibility compliance, user preference

## Security Oracles

### ORC-SEC-001: Password Masking
- **Type**: Success condition
- **Category**: Security
- **Severity**: Critical
- **Condition**: Password field masks input
- **Expected Value**: Characters displayed as bullets/dots
- **Operator**: Equals
- **Description**: Password input is hidden
- **Rationale**: Security, prevents shoulder surfing

### ORC-SEC-002: HTTPS Enforcement
- **Type**: Success condition
- **Category**: Security
- **Severity**: Critical
- **Condition**: All API calls use HTTPS
- **Expected Value**: Protocol == HTTPS
- **Operator**: Equals
- **Description**: Network traffic encrypted
- **Rationale**: Security, data protection in transit

### ORC-SEC-003: Data Encryption
- **Type**: Success condition
- **Category**: Security
- **Severity**: Critical
- **Condition**: Sensitive data encrypted at rest
- **Expected Value**: Data stored in encrypted format
- **Operator**: Not readable plain text
- **Description**: Sensitive data encrypted in storage
- **Rationale**: Security, data protection at rest

### ORC-SEC-004: Certificate Pinning
- **Type**: Success condition
- **Category**: Security
- **Severity**: High
- **Condition**: App validates SSL certificates
- **Expected Value**: Certificate validation enabled
- **Operator**: Equals
- **Description**: SSL certificates validated
- **Rationale**: Security, prevents MITM attacks

### ORC-SEC-005: Input Sanitization
- **Type**: Success condition
- **Category**: Security
- **Severity**: High
- **Condition**: User input sanitized before processing
- **Expected Value**: No injection vulnerabilities
- **Operator**: Not contains injection patterns
- **Description**: Input validated and sanitized
- **Rationale**: Security, prevents injection attacks

### ORC-SEC-006: Session Management
- **Type**: Success condition
- **Category**: Security
- **Severity**: Critical
- **Condition**: Session expires after timeout
- **Expected Value**: Session invalid after timeout
- **Operator**: Equals
- **Description**: Sessions have limited lifetime
- **Rationale**: Security, prevents session hijacking

### ORC-SEC-007: Biometric Authentication
- **Type**: Success condition
- **Category**: Security
- **Severity**: High
- **Condition**: Biometric auth requires fallback
- **Expected Value**: Password fallback available
- **Operator**: Contains
- **Description**: Biometric has password backup
- **Rationale**: Security, user experience, backup access

## Failure Condition Oracles

### ORC-FAIL-001: Invalid Credentials
- **Type**: Failure condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Login fails with invalid credentials
- **Expected Value**: Error message displayed, login blocked
- **Operator**: Contains
- **Description**: Invalid credentials rejected
- **Rationale**: Security, prevents unauthorized access

### ORC-FAIL-002: Duplicate Account
- **Type**: Failure condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Registration fails with duplicate email
- **Expected Value**: Error message displayed, registration blocked
- **Operator**: Contains
- **Description**: Duplicate email rejected
- **Rationale**: Data integrity, prevents duplicate accounts

### ORC-FAIL-003: Network Timeout
- **Type**: Failure condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Operation fails on network timeout
- **Expected Value**: Timeout error displayed, operation cancelled
- **Operator**: Contains
- **Description**: Timeout triggers error handling
- **Rationale**: Error handling, user feedback

### ORC-FAIL-004: Permission Denied
- **Type**: Failure condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Feature fails without required permission
- **Expected Value**: Permission request displayed, feature blocked
- **Operator**: Contains
- **Description**: Permission denial handled gracefully
- **Rationale**: User experience, permission management

### ORC-FAIL-005: Payment Failure
- **Type**: Failure condition
- **Category**: Functional
- **Severity**: Critical
- **Condition**: Payment fails on invalid card
- **Expected Value**: Error message displayed, payment blocked
- **Operator**: Contains
- **Description**: Invalid payment rejected
- **Rationale**: Security, prevents invalid transactions

### ORC-FAIL-006: Out of Stock
- **Type**: Failure condition
- **Category**: Functional
- **Severity**: High
- **Condition**: Order fails when item out of stock
- **Expected Value**: Out of stock message displayed, order blocked
- **Operator**: Contains
- **Description**: Inventory check prevents overselling
- **Rationale**: Inventory management, business logic

## Oracle Usage Guidelines

### Oracle Selection
- Use validation oracles for input fields and forms
- Use network oracles for API-dependent screens
- Use lifecycle oracles for stateful screens
- Use performance oracles for user-facing screens
- Use accessibility oracles for all screens
- Use security oracles for sensitive data screens

### Oracle Composition
- Combine multiple oracles for comprehensive testing
- Prioritize critical oracles for essential flows
- Use conditional oracles based on feature requirements
- Adapt oracles based on platform differences (iOS vs Android)

### Oracle Customization
- Extend base oracles with app-specific conditions
- Add custom oracles for unique app features
- Adjust thresholds based on performance requirements
- Modify conditions based on business rules

### Oracle Maintenance
- Review and update oracles regularly
- Add new oracles for new features
- Remove obsolete oracles for deprecated features
- Document oracle changes and rationale
