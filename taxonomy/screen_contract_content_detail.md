# Screen Type Contract: CONTENT_DETAIL

## Definition
CONTENT_DETAIL represents a screen that displays detailed information about a single content item (product, article, etc.) with actions like add to cart, share, and navigation back.

## Required Elements

### Content Elements (Mandatory)
- **CONTENT_IMAGE**: Main image for the item
  - Type: image
  - Required: true
  - Editable: false
  - Locator hint: test-id:product-image

- **CONTENT_TITLE**: Title or name of the item
  - Type: label
  - Required: true
  - Editable: false
  - Locator hint: test-id:product-title

- **CONTENT_PRICE**: Price or cost of the item
  - Type: label
  - Required: true
  - Editable: false
  - Locator hint: test-id:product-price

- **CONTENT_DESCRIPTION**: Description or details of the item
  - Type: label
  - Required: true
  - Editable: false
  - Locator hint: test-id:product-description

### Action Elements (Mandatory)
- **ACTION_ADD_TO_CART**: Button to add item to cart
  - Type: button
  - Required: true
  - Editable: false
  - Locator hint: test-id:add-to-cart

- **NAVIGATION_BACK**: Button to navigate back to previous screen
  - Type: button
  - Required: true
  - Editable: false
  - Locator hint: test-id:back-button

### Optional Elements
- **ACTION_SHARE**: Button to share item
  - Type: button
  - Required: false
  - Editable: false
  - Locator hint: test-id:share-button

- **SIGNAL_LOADING**: Loading indicator
  - Type: icon
  - Required: false
  - Editable: false
  - Locator hint: test-id:loading

## Required Signals

### Input Signals
- **add_to_cart_action**: Triggered when add to cart button is tapped
- **share_action**: Triggered when share button is tapped
- **back_action**: Triggered when back button is tapped

### Output Signals
- **SIGNAL_LOADING**: Indicates data loading or action in progress
- **NAVIGATION_LIST**: Indicates navigation back to list screen

### Lifecycle Signals
- **screen_rotation_event**: Triggered when device orientation changes
- **background_event**: Triggered when app goes to background
- **foreground_event**: Triggered when app returns to foreground

## Required Oracle Support

### Critical Oracles (Must Support)
- **ORC-NET-008**: Detail Data Loading
  - Validates successful detail data loading
  - Expects HTTP 200 with item details in response

- **ORC-NET-009**: Add to Cart Success
  - Validates successful add to cart action
  - Expects HTTP 200 with cart updated response

### High Priority Oracles (Should Support)
- **ORC-NET-003**: API Timeout Handling
  - Validates graceful handling of API timeout
  - Expects timeout error message

- **ORC-NET-005**: Offline Detection
  - Validates detection of offline state
  - Expects network unavailable message

- **ORC-NET-010**: Add to Cart Failure
  - Validates add to cart failure handling
  - Expects error message displayed

- **ORC-DTL-001**: Share Action
  - Validates share sheet presentation
  - Expects share sheet displayed

- **ORC-DTL-002**: Item Not Found
  - Validates 404 error handling
  - Expects error message and back button enabled

- **ORC-LIF-003**: Scroll Position Preservation
  - Validates scroll position preserved on navigation return
  - Expects scroll position unchanged

## Planner Assumptions

### What Planner May Assume
1. **Screen Structure**: Detail screen has 4 mandatory content elements and 2 mandatory action elements
2. **Element Locators**: Elements use test-id locators for reliable identification
3. **API Endpoint**: Detail API is at `/api/products/:id` with GET method
4. **Response Format**: Successful response contains item details object
5. **Cart API**: Add to cart API is at `/api/cart/items` with POST method
6. **Loading State**: Loading indicator is shown during API request
7. **Back Navigation**: Back button returns to parent screen (usually list)
8. **Scroll Behavior**: Screen is scrollable for long descriptions
9. **Share Behavior**: Share action opens platform share sheet
10. **Network Dependency**: Detail requires network connectivity

### What Planner May NOT Assume
1. **Quantity Selector**: Presence of quantity adjustment controls
2. **Wishlist Button**: Presence of wishlist/favorite button
3. **Reviews Section**: Presence of reviews or ratings
4. **Related Items**: Presence of related items section
5. **Image Gallery**: Presence of multiple images or image gallery
6. **Video Content**: Presence of video content
7. **Variant Selection**: Presence of size/color/variant selectors
8. **Stock Status**: Presence of stock availability indicator
9. **Delivery Info**: Presence of delivery information
10. **Discount Display**: Presence of discount or promotion display

## Executor Assumptions

### What Executor May Assume
1. **Element Visibility**: All required elements are visible when data loads
2. **Loading Behavior**: Loading indicator appears before API call and disappears after response
3. **Button State**: Add to cart button is enabled when item is available
4. **Navigation Timing**: Back navigation returns to parent screen
5. **Network Behavior**: Network failures are detectable and trigger error state
6. **Cart Update**: Add to cart updates cart badge if present
7. **Share Sheet**: Share action opens platform share sheet
8. **Scroll Behavior**: Screen supports smooth scrolling
9. **Image Loading**: Image loads and displays correctly
10. **Error Handling**: 404 errors display error message and enable back button

### What Executor May NOT Assume
1. **Animation Timing**: Specific duration of animations or transitions
2. **Image Loading Time**: Specific time for image to load
3. **Cart Badge**: Presence or behavior of cart badge
4. **Quantity Limits**: Maximum quantity that can be added
5. **Stock Check**: Whether stock is checked before add to cart
6. **Toast Messages**: Presence of toast notifications
7. **Haptic Feedback**: Specific haptic feedback on actions
8. **Button Disable**: Whether button is disabled during API call
9. **Data Persistence**: Whether detail data is cached
10. **Analytics**: Analytics tracking events

## Test Data Requirements

### Required Test Data
- Valid item ID: Existing item for successful load
- Invalid item ID: Non-existent item for 404 testing
- Valid cart data: For add to cart testing

### Optional Test Data
- Out of stock item: For stock testing
- Item with variants: For variant selection testing
- Item with reviews: For reviews testing

## Platform-Specific Considerations

### iOS
- Navigation: UINavigationController back button
- Share: UIActivityViewController
- Image: UIImageView with caching
- Scroll: UIScrollView or UIScrollView subclasses
- Keyboard: No keyboard expected

### Android
- Navigation: ActionBar back button or toolbar
- Share: Intent.ACTION_SEND with chooser
- Image: ImageView with Glide/Picasso loading
- Scroll: ScrollView or NestedScrollView
- Keyboard: No keyboard expected

## Dependencies

### Screen Dependencies
- CONTENT_LIST (parent screen for navigation)
- Authentication (if requires_auth: true)

### Feature Dependencies
- Cart functionality (for add to cart)
- Share functionality (for share action)

### API Dependencies
- `/api/products/:id`: GET endpoint for item details
- `/api/cart/items`: POST endpoint for add to cart
- `/api/products/:id`: GET endpoint for refresh

## Integration Points

### Upstream Screens
- List screen (item selection)
- Search results (item selection)
- Cart screen (item details)
- Wishlist screen (item details)

### Downstream Screens
- Cart screen (after add to cart)
- Wishlist screen (after add to wishlist)
- Review screen (item reviews)
- Related items screen (related products)

### External Systems
- Content API server
- Cart API server
- Share service (platform share sheet)
- Image CDN (if external images)

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
- Does not support variant selection
- Does not support quantity adjustment
- Does not support reviews display
- Does not support related items

### Future Enhancements
- Add support for variant selection
- Add support for quantity adjustment
- Add support for reviews display
- Add support for related items
- Add support for image gallery
- Add support for wishlist functionality
- Add support for stock availability
