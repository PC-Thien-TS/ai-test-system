# Screen Type Contract: AUTH_LOGIN

## Definition
AUTH_LOGIN represents the authentication login screen where users enter credentials to access the application.

## Required Elements

### Input Elements (Mandatory)
- **INPUT_USERNAME**: Text field for username/email input
  - Type: text_field
  - Required: true
  - Editable: true
  - Locator hint: test-id:username

- **INPUT_PASSWORD**: Password field for password input
  - Type: password_field
  - Required: true
  - Editable: true
  - Locator hint: test-id:password

### Action Elements (Mandatory)
- **ACTION_SUBMIT**: Button to submit login form
  - Type: button
  - Required: true
  - Editable: false
  - Locator hint: test-id:login-button

### Navigation Elements (Optional)
- **NAVIGATION_FORGOT_PASSWORD**: Link/button to forgot password screen
  - Type: button
  - Required: false
  - Editable: false
  - Locator hint: test-id:forgot-password

### Signal Elements (Optional)
- **SIGNAL_ERROR**: Label for displaying error messages
  - Type: label
  - Required: false
  - Editable: false
  - Locator hint: test-id:error-message

- **SIGNAL_LOADING**: Icon/indicator for loading state
  - Type: icon
  - Required: false
  - Editable: false
  - Locator hint: test-id:loading

## Required Signals

### Input Signals
- **username_change**: Triggered when username field value changes
- **password_change**: Triggered when password field value changes
- **submit_attempt**: Triggered when submit button is tapped

### Output Signals
- **SIGNAL_LOADING**: Indicates login request is in progress
- **SIGNAL_ERROR**: Indicates an error occurred
- **NAVIGATION_HOME**: Indicates successful login and navigation to home

### Lifecycle Signals
- **screen_rotation_event**: Triggered when device orientation changes
- **background_event**: Triggered when app goes to background
- **foreground_event**: Triggered when app returns to foreground

## Required Oracle Support

### Critical Oracles (Must Support)
- **ORC-VAL-003**: Required Field Validation
  - Validates that required fields are not empty
  - Triggers error message on violation

- **ORC-NET-001**: Login API Success
  - Validates successful authentication with valid credentials
  - Expects HTTP 200 with auth token

- **ORC-FAIL-001**: Invalid Credentials Failure
  - Validates rejection of invalid credentials
  - Expects HTTP 401 with error message

- **ORC-SEC-001**: Password Masking
  - Validates password field masking
  - Expects characters displayed as bullets

### High Priority Oracles (Should Support)
- **ORC-LIF-001**: State Preservation on Rotation
  - Validates form data preservation on screen rotation
  - Expects input values unchanged

- **ORC-LIF-002**: Background/Foreground Transition
  - Validates app state preservation during background/foreground
  - Expects form state preserved

- **ORC-PER-001**: Login Completion Time
  - Validates login completes within acceptable time
  - Expects completion within 3 seconds

- **ORC-NET-003**: API Timeout Handling
  - Validates graceful handling of API timeout
  - Expects timeout error message

- **ORC-NET-005**: Offline Detection
  - Validates detection of offline state
  - Expects network unavailable message

- **ORC-ACC-001**: Screen Reader Labels
  - Validates accessibility labels on all interactive elements
  - Expects labels present

## Planner Assumptions

### What Planner May Assume
1. **Screen Structure**: Login screen has exactly two required input fields (username, password) and one submit button
2. **Element Locators**: Elements use test-id locators for reliable identification
3. **API Endpoint**: Login API is at `/api/auth/login` with POST method
4. **Response Format**: Successful response contains auth token in response body
5. **Error Handling**: Error messages are displayed in dedicated error element
6. **Loading State**: Loading indicator is shown during API request
7. **Navigation**: Successful login triggers navigation to home screen
8. **Form Validation**: Client-side validation occurs before API call
9. **Password Security**: Password field is always masked
10. **Network Dependency**: Login requires network connectivity

### What Planner May NOT Assume
1. **Social Login**: Presence of social login buttons (Google, Facebook, etc.)
2. **Biometric Login**: Presence of biometric authentication options
3. **Remember Me**: Presence of remember me checkbox
4. **Registration Link**: Presence of registration link
5. **Session Duration**: Length of authenticated session
6. **Account Lockout**: Number of failed attempts before lockout
7. **Password Requirements**: Specific password complexity rules beyond length
8. **Multi-factor**: Presence of MFA requirements
9. **API Rate Limiting**: Rate limiting on login endpoint
10. **Error Message Content**: Specific text of error messages

## Executor Assumptions

### What Executor May Assume
1. **Element Visibility**: All required elements are visible and tappable when screen loads
2. **Element State**: Submit button is enabled when form is valid, disabled when invalid
3. **API Behavior**: Login API returns within reasonable timeout (default 30s)
4. **Network Behavior**: Network failures are detectable and trigger error state
5. **Form State**: Form data persists across screen rotation
6. **Background Behavior**: Login request continues in background or is resumable
7. **Double Submit**: Submit button is disabled during request to prevent double submission
8. **Error Clearing**: Error messages clear when user modifies input
9. **Loading State**: Loading indicator appears before API call and disappears after response
10. **Navigation Timing**: Navigation occurs only after successful API response

### What Executor May NOT Assume
1. **Animation Timing**: Specific duration of animations or transitions
2. **Keyboard Behavior**: Keyboard dismissal behavior
3. **Focus Management**: Automatic focus behavior
4. **Scroll Behavior**: Screen scrolling behavior (should not scroll)
5. **Touch Feedback**: Specific haptic feedback or visual feedback
6. **Throttling**: Input throttling or debouncing
7. **Caching**: Response caching behavior
8. **Retry Logic**: Automatic retry behavior on failure
9. **Session Management**: Session storage mechanism
10. **Analytics**: Analytics tracking events

## Test Data Requirements

### Required Test Data
- Valid username/email: "test@example.com"
- Valid password: "ValidPass123!"
- Invalid password: "WrongPassword123!"
- Empty username: ""
- Empty password: ""

### Optional Test Data
- Social login credentials (if social login supported)
- Biometric enrollment data (if biometric supported)
- Locked account credentials (for lockout testing)

## Platform-Specific Considerations

### iOS
- Keyboard type: Email keyboard for username field
- Secure text entry: Enabled for password field
- Return key: "Go" or "Login"
- Text autocorrect: Disabled for password field
- Text autocapitalization: Disabled for password field

### Android
- Input type: textEmailAddress for username field
- Input type: textPassword for password field
- IME options: Action done or login
- Password visibility toggle: Optional (eye icon)

## Dependencies

### Screen Dependencies
- None (AUTH_LOGIN is entry point screen)

### Feature Dependencies
- None (Login is independent feature)

### API Dependencies
- `/api/auth/login`: POST endpoint for authentication
- `/api/auth/refresh`: POST endpoint for token refresh (optional)
- `/api/auth/logout`: POST endpoint for logout (optional)

## Integration Points

### Upstream Screens
- None (Entry point)

### Downstream Screens
- Home screen (on successful login)
- Forgot password screen (optional)
- Registration screen (optional)
- MFA screen (if MFA required)

### External Systems
- Authentication server
- User directory service
- Session management service

## Coverage Requirements

### Minimum Coverage
- All required elements: 100%
- All required signals: 100%
- All critical oracles: 100%
- All mandatory test cases: 100%

### Recommended Coverage
- Optional elements: 50%
- Optional signals: 50%
- High priority oracles: 100%
- Optional test cases: 50%

## Maintenance Notes

### Version History
- v1.0: Initial contract definition

### Known Limitations
- Does not support social login variations
- Does not support MFA flows
- Does not support account lockout scenarios
- Does not support password complexity validation

### Future Enhancements
- Add support for social login
- Add support for MFA flows
- Add support for account lockout testing
- Add support for password complexity validation
- Add support for biometric authentication
