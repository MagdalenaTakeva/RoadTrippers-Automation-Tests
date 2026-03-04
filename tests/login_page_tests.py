import pytest
from selenium.common import TimeoutException


@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.auth
def test_login_with_valid_credentials(function_driver, home_pg):
    """
    Positive: Logging in with valid saved cookies should succeed and mark user as logged in.

    Current behavior:
    - Cookies are injected → user appears logged in without form interaction
    - is_logged_in() checks for logged-in UI elements (avatar, profile link, etc.)

    Steps to reproduce manually:
    1. Open https://roadtrippers.com in an incognito window
    2. Log in manually with valid credentials once
    3. Copy cookies from browser dev tools (Application → Cookies)
    4. Paste cookies into test environment → page reloads as logged-in user
    5. Avatar or profile link appears instead of "Log in"

    Expected behavior:
    - User is marked as logged in (is_logged_in() returns True)
    - No login form is shown
    - No errors or redirects

    """
    home_pg.navigate()
    home_pg.login_via_cookies()

    assert home_pg.is_logged_in(), "User not logged in via cookies"

@pytest.mark.regression
@pytest.mark.negative
@pytest.mark.auth
def test_login_with_invalid_credentials(function_driver, home_pg, login_pg):
    """
    Negative: Attempting login with invalid credentials should fail
    and display an error message (or keep form visible with error state).

    Current behavior:
    - Invalid username/password → server rejects → error message appears
    - Form stays open, no redirect to logged-in state

    Steps to reproduce manually:
    1. Open https://roadtrippers.com
    2. Click "Log in" in header
    3. Enter invalid email (e.g. invalid_user@example.com)
    4. Enter wrong password (e.g. WrongPassword!)
    5. Click "Log in" → observe red error message like "Invalid credentials" or "Incorrect email/password"

    Expected behavior:
    - No successful login (user not logged in)
    - Error message is displayed (contains "invalid", "incorrect", etc.)
    - If no message appears within timeout, test fails with screenshot

    """
    home_pg.navigate()
    home_pg.click_login_header_link()

    login_pg.enter_username("invalid_user@example.com")
    login_pg.enter_password("WrongPassword!")

    login_pg.submit()

    try:
        error_message = login_pg.get_text(login_pg.ERROR_MESSAGE, timeout=8)
        print(f"Error message after invalid login: {error_message}")
        assert error_message, "No error message displayed after invalid login"
        # Optional: check specific text
        assert "invalid" in error_message.lower() or "incorrect" in error_message.lower(), "Unexpected error text"
    except TimeoutException:
        login_pg.take_screenshot("no_error_after_invalid_login.png")
        assert False, "No error message appeared after submitting invalid credentials"

@pytest.mark.regression
@pytest.mark.auth
def test_toggle_password_visibility(function_driver, home_pg, login_pg):
    """
    Positive: Clicking the password visibility toggle should switch between hidden (type="password")
    and visible (type="text") states.

    Current behavior:
    - Initial password field is type="password" (hidden)
    - Toggle → type="text" (visible characters)
    - Toggle again → back to type="password"

    Steps to reproduce manually:
    1. Open https://roadtrippers.com
    2. Click "Log in" in header
    3. In password field type any text (e.g. TestPassword) → dots shown
    4. Click eye/show icon → text becomes visible
    5. Click again → text hidden (dots)

    Expected behavior:
    - Initial type = "password"
    - After first toggle: type = "text"
    - After second toggle: type = "password"

    """

    # Step 1: Navigate to home page and ensure overlays are gone
    home_pg.navigate()

    # Step 2: Click Log in navigation menu
    home_pg.click_login_header_link()

    # Step 3: Enter password
    login_pg.enter_password("TestPassword")

    # Check initial type (should be password)
    initial_type = function_driver.find_element(*login_pg.PASSWORD_INPUT).get_attribute("type")
    assert initial_type == "password", f"Initial password type is '{initial_type}', expected 'password'"

    login_pg.toggle_password_visibility()

    # Check after toggle
    visible_type = function_driver.find_element(*login_pg.PASSWORD_INPUT).get_attribute("type")
    assert visible_type == "text", f"Password type after toggle is '{visible_type}', expected 'text'"

    # Toggle back and check again
    login_pg.toggle_password_visibility()
    hidden_type = function_driver.find_element(*login_pg.PASSWORD_INPUT).get_attribute("type")

    assert hidden_type == "password", "Password not hidden after second toggle"

@pytest.mark.regression
@pytest.mark.auth
def test_signup_link(function_driver, home_pg, login_pg, signup_pg):
    """
    Positive: Clicking "Create an account" / Sign Up link from login modal
    should open the signup popup/modal.

    Current behavior:
    - Login modal open → click "Create an account" → signup modal appears

    Steps to reproduce manually:
    1. Open https://roadtrippers.com
    2. Click "Log in" in header
    3. In login modal find and click "Create an account"
    4. Observe signup form/modal appears (fields: email, password, etc.)

    Expected behavior:
    - Signup modal/popup is open (is_open() returns True)
    - No crash or redirect away from popup

    """
    # Step 1: Navigate to home page and ensure overlays are gone
    home_pg.navigate()

    # Step 2: Click Log in navigation menu
    home_pg.click_login_header_link()

    # Step 3: Click the "Create an account" link
    login_pg.click_signup_link()

    # Step 4: Verify Signup modal is open
    assert signup_pg.is_open()

@pytest.mark.regression
@pytest.mark.auth
def test_forgot_password_link(function_driver, home_pg, login_pg):
    """
    Positive: Clicking "Forgot password" link from login modal
    should navigate to the password reset page.

    Current behavior:
    - Login modal open → click "Forgot password" → redirect to /password_resets/new

    Steps to reproduce manually:
    1. Open https://roadtrippers.com
    2. Click "Log in" in header
    3. In login modal click "Forgot password?"
    4. Observe URL changes to include "/password_resets/new" or reset form loads

    Expected behavior:
    - Current URL contains "password_resets/new"
    - Reset form or page is reachable

    """
    # Step 1: Navigate to home page and ensure overlays are gone
    home_pg.navigate()

    # Step 2: Click Log in navigation menu
    home_pg.click_login_header_link()

    # Step 3: Click "Forgot password" link
    login_pg.click_forgot_password()

    # Step 4: Verify "password_resets/new" in the url
    assert "password_resets/new" in function_driver.current_url

# ======================================
# Test: Login + Navigate to Trip Planner
# ======================================

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.auth
@pytest.mark.trip_planner
def test_login_and_open_trip_planner_with_direct_click(authenticated_home, login_pg):
    """
    End-to-end positive: After successful login (via cookies),
    clicking 'Plan Your Trip' should navigate to the Trip Planner page.

    Current behavior:
    - Logged-in user → direct click on 'Plan Your Trip' → planner loads
    - Discover card button becomes visible

    Steps to reproduce manually:
    1. Log in to https://roadtrippers.com
    2. Click 'Plan Your Trip' in main navigation
    3. Observe redirect to maps.roadtrippers.com
    4. Discover card / "Start a new trip" button appears

    Expected behavior:
    - User remains logged in
    - Planner page loads successfully
    - Discover card button is visible

    """
    # Step 1: Ensure login via cookies
    authenticated_home.navigate()
    assert authenticated_home.is_logged_in(), "User failed to log in via cookies"

    # Step 2: Navigate to Trip Planner
    login_pg.go_to_trip_planner_page()

    # Step 3: Verify the page loaded successfully
    assert login_pg.discover_card_btn_is_displayed(), \
        "Trip Planner Page did not load successfully: Discover Card button not visible"

@pytest.mark.regression
@pytest.mark.trip_planner
@pytest.mark.auth
def test_login_and_open_trip_planner_submenu_option(function_driver, authenticated_home, login_pg):
    """
    End-to-end positive: After login, using hover + submenu to select 'Trip Planner'
    should navigate to the Trip Planner page.

    Current behavior:
    - Logged-in user → hover 'Plan Your Trip' → click submenu option → planner loads
    - Discover card button becomes visible

    Steps to reproduce manually:
    1. Log in to https://roadtrippers.com
    2. Hover over 'Plan Your Trip' in main navigation
    3. Click 'Trip Planner' in the dropdown/submenu
    4. Observe redirect to maps.roadtrippers.com
    5. Discover card / "Start a new trip" button appears

    Expected behavior:
    - User remains logged in
    - Planner page loads successfully
    - Discover card button is visible
    """
    # Step 1: Ensure login via cookies
    authenticated_home.navigate()
    assert authenticated_home.is_logged_in(), "User failed to log in via cookies"

    # Step 2: Navigate to Trip Planner using hover + submenu option
    login_pg.go_to_trip_planner_page(use_hover=True)

    # Step 3: Verify the page loaded successfully
    assert login_pg.discover_card_btn_is_displayed(), \
        "Trip Planner Page did not load successfully: Discover Card button not visible"
