from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from selenium.webdriver.support import expected_conditions as EC


class LoginPage(BasePage):
    """
       Page Object for the login popup/modal (id="authorize-with-password").

       This modal appears when clicking "Log in" in the header or navigation.
       It contains:
       - Username/Email and Password fields
       - Password visibility toggle
       - Login button
       - Forgot password link
       - Sign up link
       - Social login buttons (Google, Facebook, Apple)
       - Error messages on invalid submit

       Current behavior:
       - Popup is modal-style, blocks background interaction
       - Client-side + server-side validation (errors shown on submit)
       - Submit shows spinner → on success closes popup and updates header (avatar appears)
       - Forgot password / Sign up links redirect or open new modal
       - Social buttons redirect to provider auth flow

    """

    FORM = (By.ID, "authorize-with-password")
    USERNAME_INPUT = (By.ID, "login-username")
    PASSWORD_INPUT = (By.ID, "login-password")
    PASSWORD_TOGGLE = (By.CSS_SELECTOR, ".password-visibility")
    LOGIN_BTN = (By.ID, "authorize-with-password-submit")
    HEADING = (By.XPATH, "//h3[contains(text(),'Log in to your account')]")
    ERROR_MESSAGE = (By.CSS_SELECTOR, ".popup__error-message")
    FORGOT_PASSWORD = (By.CSS_SELECTOR, ".popup__forgot a")
    SIGNUP_LINK = (By.CSS_SELECTOR, "div.popup__alternative a[data-target='#signup']")
    SOCIAL_GOOGLE = (By.CSS_SELECTOR, ".authorize-with-google")
    SOCIAL_FACEBOOK = (By.CSS_SELECTOR, ".authorize-with-fb")
    SOCIAL_APPLE = (By.CSS_SELECTOR, ".authorize-with-apple")
    SPINNER = (By.CSS_SELECTOR, "#authorize-with-password-submit .loading")

    DISCOVER_CARD_BTN = (By.CSS_SELECTOR, "button.discover-card")

    PLAN_YOUR_TRIP_MENU = (
        By.CSS_SELECTOR,
        "#menu-main-menu li.menu-item-has-children > a[href='https://maps.roadtrippers.com']"
    )

    TRIP_PLANNER_OPTION = (
        By.CSS_SELECTOR,
        "#menu-item-85140 ul.sub-menu a[href='https://maps.roadtrippers.com']"
    )

    AVATAR_BUTTON = (
        By.CSS_SELECTOR,
        "a[href*='https://maps.roadtrippers.com/people']"
    )

    # Methods
    def enter_username(self, username: str) -> None:
        """
        Enter username/email into the login field.

        Args:
            username: The username or email string

        Current behavior:
            - Clears existing value first
            - Sends keys directly

        Steps to reproduce manually:
            1. Open login popup
            2. Type email/username → field accepts input

        Expected behavior:
            - Field value matches input

        """
        input_elem = self.wait.until(EC.visibility_of_element_located(self.USERNAME_INPUT))
        input_elem.clear()
        input_elem.send_keys(username)
        # Screenshot after entering username — shows filled field
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_enter_username"
        )

    def enter_password(self, password: str) -> None:
        """
        Enter password into the login field.

        Args:
            password: The password string

        """
        input_elem = self.wait.until(EC.visibility_of_element_located(self.PASSWORD_INPUT))
        input_elem.clear()
        input_elem.send_keys(password)
        # Screenshot after entering password — shows dots (hidden state)
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_enter_password"
        )

    def toggle_password_visibility(self) -> None:
        """
        Toggle password field between hidden (dots) and visible (plain text).

        Current behavior:
            - Clicks eye icon → switches input type="password" ↔ "text"

        Steps to reproduce manually:
            1. Open login popup
            2. Type password → dots shown
            3. Click eye icon → text visible
            4. Click again → hidden

        Expected behavior:
            - Visibility toggles correctly

        """

        toggle_btn = self.wait.until(EC.element_to_be_clickable(self.PASSWORD_TOGGLE))
        toggle_btn.click()
        # Screenshot after toggle — captures visible/hidden state change
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_toggle_password_visibility"
        )

    def click_forgot_password(self) -> None:
        """
        Click the "Forgot password?" link.

        Current behavior:
            - Redirects to password reset page or opens reset modal

        Steps to reproduce manually:
            1. Open login popup
            2. Click "Forgot password?"
            3. Observe redirect to /password_resets/new or reset form

        Expected behavior:
            - Navigation to reset flow

        """
        link = self.wait.until(EC.element_to_be_clickable(self.FORGOT_PASSWORD))
        link.click()
        # Screenshot after click — shows redirect or new form
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_click_forgot_password"
        )

    def click_signup_link(self) -> None:
        """
        Click the "Sign up" / "Create an account" link.

        Current behavior:
            - Opens signup modal (id="signup")

        Steps to reproduce manually:
            1. Open login popup
            2. Click "Create an account" or "Sign up"
            3. Observe signup modal appears

        Expected behavior:
            - Signup modal opens

        """
        link = self.wait.until(EC.element_to_be_clickable(self.SIGNUP_LINK))
        link.click()
        self.wait_for_ajax(timeout=BasePage.NAVIGATION_TIMEOUT)
        # Screenshot after click — confirms signup modal transition
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_click_signup_link"
        )

    def submit(self) -> None:
        """
        Click the "Log in" submit button.

        Current behavior:
            - Triggers login request
            - Shows spinner during processing
            - On success: popup closes, header updates (avatar appears)

        Steps to reproduce manually:
            1. Open login popup
            2. Fill valid credentials
            3. Click "Log in" → spinner appears → popup closes

        Expected behavior:
            - Submit processes
            - Popup eventually closes on success

        """
        submit_btn = self.wait.until(EC.element_to_be_clickable(self.LOGIN_BTN))
        # Screenshot before submit — shows form ready to send
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_submit"
        )
        submit_btn.click()
        # Screenshot right after click — captures spinner or immediate feedback
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_submit_click"
        )

    def login(self, username: str, password: str, timeout = BasePage.INTERACTION_TIMEOUT) -> None:

        """
        Full login workflow: enter credentials and submit.

        Args:
            username: Username or email
            password: Password
            timeout: Max time for AJAX/spinner wait (default: INTERACTION_TIMEOUT)

        Current behavior:
            - Enters username/password
            - Submits
            - Waits for AJAX completion

        Steps to reproduce manually:
            1. Open login popup
            2. Type username/email and password
            3. Click "Log in"
            4. Popup closes → logged-in state (avatar visible)

        Expected behavior:
            - Successful login
            - Popup closes
            - Header shows logged-in user

        """
        self.enter_username(username)
        self.enter_password(password)
        self.submit()
        self.wait_for_ajax(timeout=timeout)
        # Screenshot at end of login flow — shows popup closed or error
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_full_login_attempt"
        )

    def go_to_trip_planner_page(self, use_hover=False) -> None:
        """
        Navigate from login context to the Trip Planner page.

        Args:
            use_hover: If True, use hover to open submenu before clicking (fallback)

        Current behavior:
            - Prefers direct click on "Plan Your Trip"
            - Falls back to hover + submenu if direct fails
            - Waits for AJAX after navigation

        Steps to reproduce manually:
            1. Open login popup (or be logged in)
            2. Click "Plan Your Trip" in main nav (or hover → select Trip Planner)
            3. Observe redirect to maps.roadtrippers.com

        Expected behavior:
            - Redirects to planner page
            - No crash or stuck modal

        """
        self.log("Opening 'Plan Your Trip' navigation menu", level="debug")
        # Screenshot before navigation attempt — shows current state
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_go_to_planner"
        )

        if use_hover:
            self.log("Navigating via hover menu", level="debug")
            self.hover_and_click(self.PLAN_YOUR_TRIP_MENU, self.TRIP_PLANNER_OPTION)
        else:
            self.log("Navigating via direct click on 'Plan Your Trip'", level="debug")
            self.click(self.PLAN_YOUR_TRIP_MENU)
            self.wait_for_ajax(timeout=BasePage.NAVIGATION_TIMEOUT)

        # Screenshot after navigation — confirms redirect or planner load
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_go_to_planner"
        )


