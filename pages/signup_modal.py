from typing import Optional

from selenium.common import TimeoutException, ElementClickInterceptedException, NoSuchElementException, \
    StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pages.base_page import BasePage


class SignUpPage(BasePage):
    """
    Page Object for the signup popup (id="signup").

    This modal/popup appears when clicking "Sign up" / "Create an account" from login or header.
    It contains:
    - Username, Email, Password fields
    - Optional opt-in checkbox (marketing/newsletter)
    - Social signup options (Google, Facebook, Apple)
    - Submit button
    - Close (X) button
    - Per-field and global error messages

    Current behavior:
    - Popup is modal-style, blocks background interaction
    - Client-side validation + server-side errors (shown on submit)
    - Submit shows spinner → may redirect or close on success
    - Close button top-right; errors appear below fields or in wrapper

    """

    # Popup root
    POPUP = (By.ID, "signup")

    # Form fields
    USERNAME_INPUT = (By.ID, "signup-username")
    EMAIL_INPUT = (By.ID, "signup-email")
    PASSWORD_INPUT = (By.ID, "signup-password")
    OPTIN_CHECKBOX = (By.ID, "signup-optin")

    # Submit button
    SIGNUP_BUTTON = (By.CSS_SELECTOR, "#register-with-password-submit")

    # Close button
    CLOSE_BUTTON = (By.CSS_SELECTOR, ".popup__close popup__close_action")

    # Error messages (wrapper + inner div)
    ERROR_WRAPPER = (By.CSS_SELECTOR, ".popup__signup-error-message")  # inner error text
    USERNAME_WRAPPER = (By.ID, "signup-username-wrapper")
    EMAIL_WRAPPER = (By.ID, "signup-email-wrapper")
    EMAIL_ERROR_MESSAGE = (By.CSS_SELECTOR, "#signup-email-wrapper .popup__signup-error-message")
    PASSWORD_WRAPPER = (By.ID, "signup-password-wrapper")

    # Optional: Password visibility toggle (if I want to interact with it)
    PASSWORD_TOGGLE = (By.CSS_SELECTOR, ".password-visibility")
    AVATAR = (By.CSS_SELECTOR, ".rt-user-img [href*='/people']")

    def __init__(self, driver):
        """
        Initialize the SignUpPage and ensure popup is present.

        Raises:
            TimeoutException: If popup does not appear within default timeout
        """
        super().__init__(driver)


    def is_open(self, timeout: Optional[int] = None) -> bool:
        """
        Check if the Sign Up popup is currently visible.

        Args:
            timeout: Max time to wait (default: BasePage.SHORT_TIMEOUT)

        Returns:
            bool: True if popup visible and submit button clickable, False otherwise

        """
        timeout = timeout or BasePage.SHORT_TIMEOUT  # interaction-tier
        try:
            self.wait_for_element_to_be_clickable_with_timeout(self.SIGNUP_BUTTON, timeout=timeout)

            # Screenshot when popup is confirmed open — baseline state
            self.take_screenshot(
                self._get_current_test_name(),
                "__signup_popup_open_confirmed"
            )

            return True
        except TimeoutException:
            self.take_screenshot(
                self._get_current_test_name(),
                "__signup_popup_not_open__timeout"
            )
            return False

    def wait_for_signup_modal_to_be_invisible(self) -> None:
        """
        Wait until the signup popup is no longer visible (after close/submit).

        Raises:
            TimeoutException: If popup remains visible too long

        """
        try:
            self.wait_for_element_invisibility(self.POPUP)

            # Screenshot after modal gone — confirms close/submit success
            self.take_screenshot(
                self._get_current_test_name(),
                "__signup_modal_invisible__success"
            )
        except TimeoutException:
            self.take_screenshot(
                self._get_current_test_name(),
                "__signup_modal_still_visible__timeout"
            )
            raise

    def enter_username(self, username: str) -> None:
        """
        Enter username into the signup field.

        Args:
            username: The username string to type

        """
        elem = self.wait_for_element_visibility(self.USERNAME_INPUT)
        elem.clear()
        elem.send_keys(username)

        # Screenshot after entering username — shows field state
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_enter_username"
        )

    def enter_email(self, email: str) -> None:
        """
        Enter email address into the signup field.

        Args:
            email: Valid or invalid email string

        """
        elem = self.wait_for_element_visibility(self.EMAIL_INPUT)
        elem.clear()
        elem.send_keys(email)

        # Screenshot after entering email
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_enter_email"
        )

    def enter_password(self, password: str) -> None:
        """
        Enter password into the signup field.

        Args:
            password: The password string

        """
        elem = self.wait_for_element_visibility(self.PASSWORD_INPUT)
        elem.clear()
        elem.send_keys(password)

        # Screenshot after entering password (hidden)
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_enter_password"
        )

    def toggle_optin(self, check: bool = True) -> None:
        """
        Set the opt-in checkbox (marketing/newsletter) to checked or unchecked.

        Args:
            check: True to check, False to uncheck (default True)

        """
        checkbox = self._find(self.OPTIN_CHECKBOX)
        if checkbox.is_selected() != check:
            checkbox.click()

            # Screenshot after opt-in toggle
            self.take_screenshot(
                self._get_current_test_name(),
                f"__optin_toggled_to_{check}"
            )

    def submit(self, timeout=BasePage.NAVIGATION_TIMEOUT):
        """
                Click the "Sign Up" / submit button and wait for processing.

                Handles:
                - Spinner detection and wait for it to disappear
                - AJAX completion
                - Overlay dismissal
                - JS fallback if click intercepted

                Args:
                    timeout: Max time to wait for spinner/AJAX (default: NAVIGATION_TIMEOUT)

                Current behavior:
                    - Button shows loading spinner during submit
                    - On success: popup closes or redirects
                    - On failure: errors appear

                Steps to reproduce manually:
                    1. Open signup popup
                    2. Fill fields → click "Sign Up"
                    3. Observe spinner → wait for it to disappear
                    4. Popup closes or user logged in

                Expected behavior:
                    - Submit processes without crash
                    - Spinner appears/disappears
                    - Popup eventually closes or success state reached

        """
        btn = self.wait_for_element_to_be_clickable_with_timeout(self.SIGNUP_BUTTON, timeout=timeout)

        # Screenshot before submit — shows filled form state
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_signup_submit"
        )

        try:
            btn.click()
        except ElementClickInterceptedException:
            self.js_click(btn)
            self.log("Used JS fallback click on signup button", level="warning")

        # Screenshot right after click — captures spinner or immediate feedback
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_submit_click"
        )

        # Critical: wait for spinner to disappear (this is what was missing)
        spinner_locator = (By.CSS_SELECTOR, "#register-with-password-submit .loading")
        try:
            # Wait for spinner to appear first (optional but good)
            self.wait_for_element_visibility(spinner_locator, timeout=6)
            self.log("Signup spinner appeared", level="debug")

            # Screenshot when spinner visible
            self.take_screenshot(
                self._get_current_test_name(),
                "__signup_spinner_visible"
            )

            # Wait for it to disappear
            self.wait_for_element_invisibility(spinner_locator, timeout=30)
            self.log("Signup spinner disappeared — request processed", level="info")

            # Screenshot after spinner gone
            self.take_screenshot(
                self._get_current_test_name(),
                "__after_spinner_disappeared"
            )
        except TimeoutException:
            self.log("No spinner or it didn't disappear — possible silent submit", level="warning")
            self.take_screenshot("signup_no_spinner")

        # Wait for any remaining AJAX
        self.wait_for_ajax(timeout=timeout)
        self.handle_overlays(max_wait=8)

        # Optional: screenshot after processing
        # Final screenshot after full processing
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_signup_submit_full")

        self.wait_for_element_to_be_clickable_with_timeout(self.SIGNUP_BUTTON, timeout=timeout).click()

    def get_error_messages(self, field: str = None) -> list[str] | str:
        """
        Retrieve error messages from the signup popup.

        Args:
            field: Optional. One of: "username", "email", "password".
                   If provided → returns error for that field (str, empty if none).
                   If None → returns all visible errors as list[str].

        Returns:
            list[str] if field is None (empty list if no errors)
            str if field is specified (empty string if no error)

        Current behavior:
            - Errors appear in per-field wrappers or global wrapper
            - Text is visible only when displayed

        Steps to reproduce manually:
            1. Open signup popup
            2. Submit empty/invalid fields
            3. Observe red error text below fields or at top

        Expected behavior:
            - Returns correct error strings
            - Empty list/string if no errors visible

        """
        field_map = {
            "username": self.USERNAME_WRAPPER,
            "email": self.EMAIL_WRAPPER,
            "password": self.PASSWORD_WRAPPER,
        }

        def _get_field_error(wrapper_locator: tuple) -> str:
            """Helper: extract displayed error text from a wrapper locator."""
            try:
                # Wait up to 3 seconds for wrapper to be present
                wrapper = WebDriverWait(self.driver, BasePage.SHORT_TIMEOUT).until(
                    EC.presence_of_element_located(*wrapper_locator)
                )
                error_el = wrapper.find_element(*self.ERROR_WRAPPER)
                if error_el.is_displayed():
                    text = error_el.text.strip()
                    # Screenshot when error is visible for this field
                    self.take_screenshot(
                        self._get_current_test_name(),
                        f"__error_visible_{field or 'global'}__{text[:20].replace(' ', '_')}"
                    )
                    return text
            except (NoSuchElementException, TimeoutException, StaleElementReferenceException):
                pass
            return ""

        # ── Single-field mode ───────────────────────
        if field:
            if field not in field_map:
                self.log(f"Unknown field '{field}' - returning empty string")
                return ""

            return _get_field_error(field_map[field])

        # ── All-fields mode ─────────────────────────
        return [
            text
            for wrapper_loc in field_map.values()
            if (text := _get_field_error(wrapper_loc))
        ]


    def close_popup(self) -> None:
        """
        Close the signup popup using the top-right X button.

        Uses normal click with JS fallback if intercepted.

        """
        # Screenshot before close attempt
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_close_popup"
        )

        close_btn = self.wait_for_element_to_be_clickable_with_timeout(self.CLOSE_BUTTON)
        try:
            close_btn.click()
        except ElementClickInterceptedException:
            self.js_click(close_btn)
        self.log("Closed signup popup")
        # Screenshot after close — confirms popup gone
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_close_popup"
        )

    def is_success(self, timeout: int = None) -> bool:
        """
        Check if signup succeeded by looking for:
        - Popup no longer visible, OR
        - Logged-in state (avatar/profile link present)

        Args:
            timeout: Max time to wait (default: BasePage.SHORT_TIMEOUT)

        Returns:
            bool: True if success indicators found, False otherwise

        Current behavior:
            - Success: popup closes + avatar appears in header
            - Failure: popup stays + errors visible

        Steps to reproduce manually:
            1. Fill valid details → click Sign Up
            2. Popup closes → header shows avatar/profile instead of Log in

        Expected behavior:
            - Popup invisible or logged-in avatar present

        """

        timeout = timeout or BasePage.SHORT_TIMEOUT

        # Screenshot at start of success check
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_is_success_check"
        )

        # 1. Popup no longer visible
        if not self.is_visible(self.POPUP, timeout=timeout):
            return True

        # 2. Logged-in state (avatar)
        try:
            self.wait_for_presence_of_element_located(self.AVATAR, timeout=timeout)
            self.take_screenshot(
                self._get_current_test_name(),
                "__is_success_true__avatar_visible"
            )
            return True
        except TimeoutException:
            pass

        self.take_screenshot(
            self._get_current_test_name(),
            "__is_success_false__final"
        )

        return False

