# Screen Classification

Universal classification structure for mobile app screens.

## 1. Authentication Screens

### 1.1 Login Screen
**Purpose**: User authentication and access to the app
**Key Elements**:
- Username/email input field
- Password input field
- Login button
- Forgot password link
- Social login options
- Remember me toggle
- Registration link

**Test Obligations**:
- Input validation (email format, password requirements)
- Authentication flow (valid/invalid credentials)
- Network error handling
- Loading states
- Error message display
- Social login integration
- Biometric authentication (if supported)

### 1.2 Registration Screen
**Purpose**: New user account creation
**Key Elements**:
- Email/phone input field
- Password input field
- Confirm password field
- Terms of service checkbox
- Registration button
- Login link
- Social registration options

**Test Obligations**:
- Input validation (email format, password matching, strength)
- Duplicate account detection
- Email/phone verification flow
- Terms acceptance validation
- Network error handling
- Loading states
- Error message display

### 1.3 Forgot Password Screen
**Purpose**: Password recovery initiation
**Key Elements**:
- Email/phone input field
- Submit button
- Back to login link
- Instructions text

**Test Obligations**:
- Input validation (email format, phone format)
- Account existence check
- Email/OTP delivery
- Rate limiting
- Network error handling
- Loading states
- Success message display

### 1.4 OTP Verification Screen
**Purpose**: One-time password verification
**Key Elements**:
- OTP input fields (4-6 digits)
- Resend OTP button
- Timer display
- Back button
- Verification button

**Test Obligations**:
- OTP format validation
- OTP expiration handling
- Resend OTP flow
- Rate limiting
- Network error handling
- Loading states
- Success/failure feedback

## 2. Navigation Screens

### 2.1 Onboarding Screen
**Purpose**: First-time user introduction and setup
**Key Elements**:
- Welcome message
- Feature highlights
- Next/Skip buttons
- Page indicators
- Permission requests
- Get started button

**Test Obligations**:
- Screen transition flow
- Skip functionality
- Permission grant/deny handling
- Data persistence after onboarding
- Re-onboarding after logout
- Orientation handling
- Accessibility

### 2.2 Main Tab Screen
**Purpose**: Primary navigation hub
**Key Elements**:
- Tab bar with icons and labels
- Active tab indicator
- Badge notifications
- Tab-specific content areas

**Test Obligations**:
- Tab switching functionality
- Active state persistence
- Badge notification display
- Deep linking to tabs
- Tab bar visibility on scroll
- Orientation handling
- Accessibility

### 2.3 Side Drawer Screen
**Purpose**: Secondary navigation and settings access
**Key Elements**:
- Hamburger menu button
- Drawer toggle
- Navigation items
- User profile section
- Settings options
- Close button

**Test Obligations**:
- Drawer open/close animation
- Navigation item selection
- Drawer swipe gesture
- Drawer state persistence
- Deep linking to drawer items
- Orientation handling
- Accessibility

## 3. List Screens

### 3.1 Vertical List Screen
**Purpose**: Display items in vertical scrollable list
**Key Elements**:
- List items with title/subtitle
- Thumbnail images
- Action buttons
- Pull-to-refresh
- Infinite scroll indicator
- Empty state
- Loading state

**Test Obligations**:
- List rendering performance
- Scroll behavior
- Pull-to-refresh functionality
- Infinite scroll loading
- Empty state display
- Item selection/tap
- Action button functionality
- Network error handling
- Loading state display

### 3.2 Horizontal List Screen
**Purpose**: Display items in horizontal scrollable carousel
**Key Elements**:
- Horizontal scrollable container
- List items
- Page indicators
- Navigation arrows
- Auto-scroll (optional)

**Test Obligations**:
- Horizontal scroll behavior
- Page indicator accuracy
- Navigation arrow functionality
- Auto-scroll timing
- Item selection/tap
- Orientation handling
- Accessibility

### 3.3 Grid Screen
**Purpose**: Display items in grid layout
**Key Elements**:
- Grid items with thumbnails
- Grid layout (2-column, 3-column)
- Filter/sort options
- Pull-to-refresh
- Infinite scroll indicator
- Empty state
- Loading state

**Test Obligations**:
- Grid rendering performance
- Grid layout adaptation
- Filter/sort functionality
- Pull-to-refresh
- Infinite scroll loading
- Empty state display
- Item selection/tap
- Network error handling

### 3.4 Search Results Screen
**Purpose**: Display search results
**Key Elements**:
- Search bar with query
- Filter options
- Sort options
- Result count
- List/grid view toggle
- Clear search button
- No results state

**Test Obligations**:
- Search query submission
- Filter application
- Sort application
- View toggle functionality
- Clear search functionality
- No results state
- Result selection
- Network error handling
- Search history

## 4. Detail Screens

### 4.1 Item Detail Screen
**Purpose**: Display detailed information about a single item
**Key Elements**:
- Title and subtitle
- Main image/media
- Description text
- Metadata (date, author, etc.)
- Action buttons (share, save, etc.)
- Related items
- Back navigation
- Loading state

**Test Obligations**:
- Data loading and display
- Image/media loading
- Action button functionality
- Related items navigation
- Back navigation
- Share functionality
- Save/favorite functionality
- Network error handling
- Loading state display
- Orientation handling

### 4.2 Profile Detail Screen
**Purpose**: Display user profile information
**Key Elements**:
- Profile image/avatar
- Username and display name
- Bio/description
- Statistics (followers, posts, etc.)
- Edit profile button
- Settings button
- Activity feed
- Back navigation

**Test Obligations**:
- Profile data loading
- Image/avatar loading
- Edit profile functionality
- Settings navigation
- Activity feed loading
- Back navigation
- Network error handling
- Loading state display

### 4.3 Settings Detail Screen
**Purpose**: Display and modify app settings
**Key Elements**:
- Settings categories
- Toggle switches
- Dropdown selectors
- Input fields
- Save/cancel buttons
- Reset to defaults
- Back navigation

**Test Obligations**:
- Settings value loading
- Toggle switch functionality
- Dropdown selection
- Input validation
- Save functionality
- Cancel functionality
- Reset to defaults
- Settings persistence
- Back navigation

## 5. Form Screens

### 5.1 Input Form Screen
**Purpose**: Collect user input through form fields
**Key Elements**:
- Input fields (text, number, date, etc.)
- Labels and placeholders
- Validation messages
- Submit button
- Cancel button
- Required field indicators
- Loading state

**Test Obligations**:
- Input field functionality
- Input validation
- Required field validation
- Submit functionality
- Cancel functionality
- Form data persistence
- Network error handling
- Loading state display
- Error message display

### 5.2 Multi-step Form Screen
**Purpose**: Collect user input through multiple steps
**Key Elements**:
- Step indicators
- Current step content
- Next/Previous buttons
- Progress bar
- Step validation
- Submit button
- Cancel button

**Test Obligations**:
- Step navigation (next/previous)
- Step validation
- Progress indicator accuracy
- Data persistence across steps
- Submit functionality
- Cancel functionality
- Step completion logic
- Network error handling

## 6. Media Screens

### 6.1 Image Gallery Screen
**Purpose**: Display collection of images
**Key Elements**:
- Image grid/carousel
- Full-screen image view
- Zoom functionality
- Image metadata
- Share button
- Download button
- Back navigation

**Test Obligations**:
- Image loading and display
- Grid/carousel navigation
- Full-screen view transition
- Zoom functionality
- Share functionality
- Download functionality
- Back navigation
- Network error handling
- Loading state display

### 6.2 Video Player Screen
**Purpose**: Play video content
**Key Elements**:
- Video player controls
- Play/pause button
- Progress bar
- Volume control
- Full-screen toggle
- Video quality selector
- Back button

**Test Obligations**:
- Video loading and playback
- Play/pause functionality
- Progress bar accuracy
- Volume control
- Full-screen toggle
- Quality selection
- Network error handling
- Background playback
- Orientation handling

### 6.3 Audio Player Screen
**Purpose**: Play audio content
**Key Elements**:
- Audio player controls
- Play/pause button
- Progress bar
- Volume control
- Playback speed control
- Playlist view
- Album art
- Back button

**Test Obligations**:
- Audio loading and playback
- Play/pause functionality
- Progress bar accuracy
- Volume control
- Playback speed
- Playlist navigation
- Background playback
- Network error handling
- Lock screen controls

## 7. Transaction Screens

### 7.1 Cart Screen
**Purpose**: Display and manage shopping cart items
**Key Elements**:
- Cart items list
- Quantity controls
- Remove item buttons
- Item prices
- Subtotal calculation
- Apply coupon field
- Checkout button
- Continue shopping button

**Test Obligations**:
- Cart item display
- Quantity adjustment
- Item removal
- Price calculation accuracy
- Coupon application
- Checkout flow
- Cart persistence
- Empty cart state
- Network error handling

### 7.2 Checkout Screen
**Purpose**: Complete purchase transaction
**Key Elements**:
- Order summary
- Shipping address
- Payment method selection
- Billing information
- Apply coupon
- Terms checkbox
- Place order button
- Back button

**Test Obligations**:
- Order summary accuracy
- Address validation
- Payment method selection
- Billing validation
- Coupon application
- Terms acceptance
- Order submission
- Payment processing
- Network error handling
- Loading state display

### 7.3 Order Confirmation Screen
**Purpose**: Display order completion details
**Key Elements**:
- Order confirmation number
- Order summary
- Shipping information
- Estimated delivery date
- Track order button
- Continue shopping button
- Share order button

**Test Obligations**:
- Order data display accuracy
- Confirmation number generation
- Track order navigation
- Share functionality
- Continue shopping navigation
- Order persistence
- Network error handling
- Email confirmation trigger

## 8. Modal/Dialog Screens

### 8.1 Alert Dialog Screen
**Purpose**: Display critical information or warnings
**Key Elements**:
- Alert title
- Alert message
- Confirm button
- Cancel button (optional)
- Icon (optional)

**Test Obligations**:
- Dialog display
- Confirm button functionality
- Cancel button functionality
- Dismiss on tap outside
- Accessibility
- Orientation handling

### 8.2 Action Sheet Screen
**Purpose**: Present multiple action options
**Key Elements**:
- Action items
- Destructive action (red)
- Cancel action
- Sheet presentation animation

**Test Obligations**:
- Sheet display animation
- Action item functionality
- Destructive action confirmation
- Cancel action
- Dismiss on tap outside
- Accessibility
- Orientation handling

### 8.3 Bottom Sheet Screen
**Purpose**: Display additional content or options
**Key Elements**:
- Sheet content
- Drag handle
- Close button
- Sheet presentation animation
- Scrollable content (optional)

**Test Obligations**:
- Sheet display animation
- Drag gesture functionality
- Close button functionality
- Dismiss on tap outside
- Content scrolling
- Accessibility
- Orientation handling
