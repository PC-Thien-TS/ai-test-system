# Test Obligation Matrix

Mapping of features/screens to required test types and criteria.

## Matrix Structure

### Obligation Types

| Obligation Type | Description | When Required |
|----------------|-------------|---------------|
| Validation | Input validation, field constraints, format checks | All input forms, authentication screens |
| Network | API calls, data fetching, error handling | All screens with network dependencies |
| Lifecycle | Screen lifecycle, state persistence, background handling | All screens |
| Performance | Load time, response time, resource usage | All screens |
| Accessibility | Screen reader, dynamic text, high contrast | All screens |
| Security | Data encryption, secure storage, certificate pinning | Authentication, payment, personal data screens |

## Feature-Specific Obligations

### 1. Authentication Features

#### Login Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Email format validation, password requirements, empty field check | ORC-VAL-001 |
| Network | Yes | Login API call, network error handling, timeout handling | ORC-NET-001 |
| Lifecycle | Yes | Screen state on rotation, background/foreground transition | ORC-LIF-001 |
| Performance | Yes | Login completion time < 3 seconds | ORC-PER-001 |
| Accessibility | Yes | Screen reader announces all fields, labels present | ORC-ACC-001 |
| Security | Yes | Password masking, secure transmission, credential storage | ORC-SEC-001 |

#### Registration Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Email format, password matching, strength check, terms acceptance | ORC-VAL-002 |
| Network | Yes | Registration API call, duplicate account check, verification flow | ORC-NET-002 |
| Lifecycle | Yes | Form state preservation on rotation, step persistence | ORC-LIF-002 |
| Performance | Yes | Registration completion time < 5 seconds | ORC-PER-002 |
| Accessibility | Yes | All form fields accessible, error messages announced | ORC-ACC-002 |
| Security | Yes | Password masking, secure transmission, data encryption | ORC-SEC-002 |

#### Forgot Password Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Email/phone format validation, account existence check | ORC-VAL-003 |
| Network | Yes | Password reset API call, OTP delivery, error handling | ORC-NET-003 |
| Lifecycle | Yes | Screen state on rotation, input persistence | ORC-LIF-003 |
| Performance | Yes | Reset request completion time < 3 seconds | ORC-PER-003 |
| Accessibility | Yes | Input field accessible, instructions announced | ORC-ACC-003 |
| Security | Yes | Rate limiting, secure OTP delivery, no account enumeration | ORC-SEC-003 |

### 2. Navigation Features

#### Onboarding Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | No | N/A | N/A |
| Lifecycle | Yes | Onboarding completion state, skip persistence | ORC-LIF-004 |
| Performance | Yes | Screen transition time < 500ms | ORC-PER-004 |
| Accessibility | Yes | All content accessible, skip button announced | ORC-ACC-004 |
| Security | No | N/A | N/A |

#### Main Tab Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | Tab content loading, badge data fetching | ORC-NET-004 |
| Lifecycle | Yes | Active tab persistence, state on rotation | ORC-LIF-005 |
| Performance | Yes | Tab switch time < 300ms | ORC-PER-005 |
| Accessibility | Yes | Tab bar accessible, active state announced | ORC-ACC-005 |
| Security | No | N/A | N/A |

#### Side Drawer Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Conditional | User profile data, notification badges | ORC-NET-005 |
| Lifecycle | Yes | Drawer state persistence, animation on rotation | ORC-LIF-006 |
| Performance | Yes | Drawer open/close animation < 300ms | ORC-PER-006 |
| Accessibility | Yes | Drawer items accessible, swipe gesture announced | ORC-ACC-006 |
| Security | No | N/A | N/A |

### 3. Content Features

#### Vertical List Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | List data fetching, pagination, error handling | ORC-NET-006 |
| Lifecycle | Yes | Scroll position persistence, state on rotation | ORC-LIF-007 |
| Performance | Yes | List render time < 500ms, scroll smoothness | ORC-PER-007 |
| Accessibility | Yes | List items accessible, scroll position announced | ORC-ACC-007 |
| Security | No | N/A | N/A |

#### Search Results Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Search query format, filter constraints | ORC-VAL-004 |
| Network | Yes | Search API call, debouncing, error handling | ORC-NET-007 |
| Lifecycle | Yes | Search query persistence, filter state on rotation | ORC-LIF-008 |
| Performance | Yes | Search results display < 1 second, filter application < 300ms | ORC-PER-008 |
| Accessibility | Yes | Search field accessible, results count announced | ORC-ACC-008 |
| Security | No | N/A | N/A |

#### Item Detail Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | Item data fetching, image loading, related items | ORC-NET-008 |
| Lifecycle | Yes | Scroll position persistence, state on rotation | ORC-LIF-009 |
| Performance | Yes | Detail load time < 2 seconds, image load < 3 seconds | ORC-PER-009 |
| Accessibility | Yes | All content accessible, actions announced | ORC-ACC-009 |
| Security | Conditional | Personal data encryption, secure sharing | ORC-SEC-004 |

### 4. Interaction Features

#### Input Form Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | All field validations, required checks, format constraints | ORC-VAL-005 |
| Network | Conditional | Form submission API, validation API | ORC-NET-009 |
| Lifecycle | Yes | Form data persistence on rotation, draft saving | ORC-LIF-010 |
| Performance | Yes | Form submit time < 2 seconds, validation feedback < 100ms | ORC-PER-010 |
| Accessibility | Yes | All fields accessible, validation errors announced | ORC-ACC-010 |
| Security | Yes | Input sanitization, secure transmission, data encryption | ORC-SEC-005 |

#### Multi-step Form Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Step-specific validations, overall form validation | ORC-VAL-006 |
| Network | Conditional | Step data validation, form submission API | ORC-NET-010 |
| Lifecycle | Yes | Step data persistence, progress state on rotation | ORC-LIF-011 |
| Performance | Yes | Step transition < 300ms, form submit < 3 seconds | ORC-PER-011 |
| Accessibility | Yes | Progress indicator announced, steps accessible | ORC-ACC-011 |
| Security | Yes | Data encryption, secure transmission, step data protection | ORC-SEC-006 |

### 5. Transaction Features

#### Cart Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Quantity constraints, coupon format, item availability | ORC-VAL-007 |
| Network | Yes | Cart data fetching, price calculation, coupon validation | ORC-NET-011 |
| Lifecycle | Yes | Cart state persistence, quantity changes on rotation | ORC-LIF-012 |
| Performance | Yes | Cart load time < 1 second, price update < 100ms | ORC-PER-012 |
| Accessibility | Yes | Cart items accessible, totals announced | ORC-ACC-012 |
| Security | Yes | Price calculation integrity, secure cart storage | ORC-SEC-007 |

#### Checkout Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | Yes | Address validation, payment method validation, terms acceptance | ORC-VAL-008 |
| Network | Yes | Order submission API, payment processing, address validation | ORC-NET-012 |
| Lifecycle | Yes | Checkout data persistence, state on rotation | ORC-LIF-013 |
| Performance | Yes | Checkout completion < 5 seconds, payment processing < 3 seconds | ORC-PER-013 |
| Accessibility | Yes | All fields accessible, error messages announced | ORC-ACC-013 |
| Security | Yes | Payment encryption, PCI compliance, secure data transmission | ORC-SEC-008 |

#### Order Confirmation Screen
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Conditional | Order data fetching, tracking API | ORC-NET-013 |
| Lifecycle | Yes | Confirmation state persistence | ORC-LIF-014 |
| Performance | Yes | Confirmation display < 1 second | ORC-PER-014 |
| Accessibility | Yes | All information accessible, actions announced | ORC-ACC-014 |
| Security | Yes | Order data protection, secure sharing | ORC-SEC-009 |

### 6. Mobile-Specific Features

#### Camera Access
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | No | N/A | N/A |
| Lifecycle | Yes | Camera permission handling, state on permission grant/deny | ORC-LIF-015 |
| Performance | Yes | Camera launch time < 2 seconds, capture < 1 second | ORC-PER-015 |
| Accessibility | Yes | Camera controls accessible | ORC-ACC-015 |
| Security | Yes | Permission request, secure image storage, metadata removal | ORC-SEC-010 |

#### Push Notifications
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | Notification delivery, payload validation | ORC-NET-014 |
| Lifecycle | Yes | Notification handling in background/foreground | ORC-LIF-016 |
| Performance | Yes | Notification display < 100ms | ORC-PER-016 |
| Accessibility | Yes | Notification content announced | ORC-ACC-016 |
| Security | Yes | Secure payload, permission handling | ORC-SEC-011 |

#### Offline Mode
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | Offline detection, sync on reconnect, conflict resolution | ORC-NET-015 |
| Lifecycle | Yes | Offline state persistence, data caching | ORC-LIF-017 |
| Performance | Yes | Offline data load < 500ms, sync completion reasonable | ORC-PER-017 |
| Accessibility | Yes | Offline indicator announced | ORC-ACC-017 |
| Security | Yes | Secure offline storage, data encryption | ORC-SEC-012 |

### 7. Non-Functional Features

#### Performance (All Screens)
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | No | N/A | N/A |
| Lifecycle | No | N/A | N/A |
| Performance | Yes | App launch time < 3 seconds, screen load < 2 seconds | ORC-PER-018 |
| Accessibility | No | N/A | N/A |
| Security | No | N/A | N/A |

#### Reliability (All Screens)
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | Network resilience, error recovery, retry logic | ORC-NET-016 |
| Lifecycle | Yes | Crash recovery, state restoration | ORC-LIF-018 |
| Performance | No | N/A | N/A |
| Accessibility | No | N/A | N/A |
| Security | No | N/A | N/A |

#### Security (All Screens)
| Obligation Type | Required | Test Criteria | Oracle ID |
|----------------|----------|---------------|-----------|
| Validation | No | N/A | N/A |
| Network | Yes | HTTPS enforcement, certificate pinning | ORC-NET-017 |
| Lifecycle | No | N/A | N/A |
| Performance | No | N/A | N/A |
| Accessibility | No | N/A | N/A |
| Security | Yes | Data encryption, secure storage, anti-tampering | ORC-SEC-013 |

## Obligation Priority Matrix

### Critical Obligations (Must Test)
- Authentication validation and security
- Payment processing security
- Personal data protection
- Network error handling for critical flows
- Accessibility for authentication and payment screens

### High Priority Obligations (Should Test)
- Validation for all input forms
- Network handling for data-dependent screens
- Lifecycle for stateful screens
- Performance for user-facing screens
- Accessibility for all screens

### Medium Priority Obligations (Nice to Test)
- Performance for non-critical screens
- Network for non-critical data
- Lifecycle for simple screens

### Low Priority Obligations (Optional)
- Validation for read-only screens
- Network for static content
- Lifecycle for transient screens

## Obligation Execution Rules

### Automated Obligations
- All validation tests (input format, constraints)
- Network API calls and error handling
- Basic lifecycle tests (rotation, background/foreground)
- Performance thresholds (load times, response times)
- Accessibility basic checks (labels, focus)

### Manual Obligations
- Complex security tests (encryption, certificate pinning)
- Visual accessibility tests (contrast, layout)
- User experience flows (multi-step processes)
- Edge case scenarios (network interruption, permission denial)

### Conditional Obligations
- Network obligations only for screens with API calls
- Security obligations only for screens with sensitive data
- Lifecycle obligations only for stateful screens
- Performance obligations only for user-facing screens

## Obligation Dependencies

### Validation Dependencies
- Validation depends on field presence
- Validation depends on field type
- Validation depends on business rules

### Network Dependencies
- Network depends on API availability
- Network depends on authentication state
- Network depends on data freshness requirements

### Lifecycle Dependencies
- Lifecycle depends on screen complexity
- Lifecycle depends on state management
- Lifecycle depends on navigation pattern

### Performance Dependencies
- Performance depends on data volume
- Performance depends on device capabilities
- Performance depends on network conditions
