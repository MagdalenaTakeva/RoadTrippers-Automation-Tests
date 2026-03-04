from typing import Optional
from selenium.webdriver.common.by import By

from pages.base_page import BasePage
from pages.signup_modal import SignUpPage
from pages.trip_planner_page import TripPlannerPage


class HomePage(BasePage):
    """
       Page Object for the main landing page (https://roadtrippers.com).

       This is the entry point for unauthenticated users.
       Key elements:
       - Search form: Starting Point + Destination inputs with autocomplete
       - "Plan Your Trip" submit button
       - Header links: Log in, Sign up
       - Popups: signup, login, overlays (cookie consent, gist, etc.)

       Current behavior:
       - Autocomplete triggers on partial input (even 1–2 chars)
       - Submit requires both fields filled (client-side check)
       - Errors shown as red borders/messages under fields
       - Signup/login popups open via header links
       - Overlays (cookies, promo) often block interaction → handle_overlays() used

    """
    # ── Search Form ──────────────────────────────────────
    START_INPUT = (By.CSS_SELECTOR, "input.search__input.search_input_from")
    DEST_INPUT = (By.CSS_SELECTOR, "input.search__input.search_input_to")
    GO_BUTTON = (By.CSS_SELECTOR, "button.plan_trip_search_button")
    AUTOCOMPLETE_CONTAINER_FROM = (By.CSS_SELECTOR, ".search__autocomplete.search_autocomplete_from")
    AUTOCOMPLETE_CONTAINER_TO = (By.CSS_SELECTOR, ".search__autocomplete.search_autocomplete_to")
    SUGGESTION_ITEMS = (By.CSS_SELECTOR, "li.autocomplete_item")
    ERROR_START = (By.CSS_SELECTOR, ".search_input_from_error")
    ERROR_DEST = (By.CSS_SELECTOR, ".search_input_to_error")
    URL = "https://roadtrippers.com"

    # ── Popups & Header Links ────────────────────────────
    POPUP = (By.ID, "signup")
    SIGN_UP_LINK = (By.CSS_SELECTOR, "a.header-signup.popup-opener[data-target='#signup']")
    PLANNER = (By.CSS_SELECTOR, "[data-id='planner']")

    LOGIN_TAB = (By.CSS_SELECTOR, ".header-login.popup-opener")

    # ── Navigation ─────────────────────────────
    def navigate(self) -> None:
        """
        Open the Roadtrippers home page and wait for search form readiness.

        Current behavior:
            - Loads https://roadtrippers.com
            - Dismisses overlays (cookies, gist, promo)
            - Waits for start/destination inputs visible

        Steps to reproduce manually:
            1. Open browser → go to https://roadtrippers.com
            2. Dismiss any popups/overlays (cookies, gist)
            3. Observe search form with "Starting Point" and "Destination" fields

        Expected behavior:
            - Page loads fully
            - Search inputs visible and interactable
            - No crash or infinite loading

        """
        self.log(f"Navigating to Home Page: {self.URL}")
        self.open_page(self.URL)
        self.wait_until_page_ready([self.START_INPUT, self.DEST_INPUT])
        # Screenshot after full page ready (search form should be visible)
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_navigate__search_form_ready"
        )
        self.log("Home page ready: search form visible")

    # ── Autocomplete Handling ───────────────────
    def _enter_location(self, text: str, is_destination: bool) -> None:
        """
        Internal helper: Enter location into start or destination field,
        wait for autocomplete container, and select first suggestion.

        Args:
            text: Partial or full location to type
            is_destination: True for destination field, False for origin

        Current behavior:
            - Clears field first (if needed)
            - Sends keys → waits for container visibility
            - Selects first suggestion (normalizes value)

        Steps to reproduce manually:
            1. Open home page
            2. Type "Chi" in Starting Point
            3. Wait → suggestions appear → click first one
            4. Field changes to full location (e.g. "Chicago, IL, USA")

        Expected behavior:
            - Autocomplete container appears
            - First suggestion selected
            - Value normalized to full place

        Raises:
            TimeoutException: If container or suggestion not visible/clickable

        """
        input_name = "Destination" if is_destination else "Start"
        input_locator = self.DEST_INPUT if is_destination else self.START_INPUT
        container_locator = (
            self.AUTOCOMPLETE_CONTAINER_TO
            if is_destination
            else self.AUTOCOMPLETE_CONTAINER_FROM
        )

        self.log(f"Entering {input_name} location: {text}")
        self.handle_overlays()

        self.send_keys(input_locator, text)
        # Screenshot right after typing — shows partial input state
        self.take_screenshot(
            self._get_current_test_name(),
            f"__typed_{input_name.lower()}_{text.replace(' ', '_')}"
        )
        self.log(f"{input_name} input updated, waiting for autocomplete container")

        self.wait_for_element_visibility(container_locator)
        # Screenshot when suggestions appear — critical for autocomplete debugging
        self.take_screenshot(
            self._get_current_test_name(),
            f"__autocomplete_visible_{input_name.lower()}"
        )
        self.log(f"{input_name} autocomplete container visible")

        self.select_first_suggestion(self.SUGGESTION_ITEMS, input_locator, text)
        self.log(f"{input_name} location {text} selected from autocomplete")

    def enter_start(self, location: str) -> None:
        """
        Enter and autocomplete the Starting Point field.

        Args:
            location: Partial or full location text (e.g. "Chi")

        """
        self._enter_location(location, is_destination=False)

    def enter_destination(self, location: str) -> None:
        """
        Enter and autocomplete the Destination field.

        Args:
            location: Partial or full location text (e.g. "New")

        """
        self._enter_location(location, is_destination=True)

    # ── Submit ─────────────────────────────────
    def submit_search(self) -> Optional[TripPlannerPage]:
        """
        Submit the trip search form if both fields are filled.

        Returns:
            Optional[TripPlannerPage]: TripPlannerPage instance if planner loaded,
                                       None if fields empty or no navigation

        Current behavior:
            - Checks both inputs non-empty (client-side)
            - Clicks "Plan Your Trip" button
            - Waits for planner element after navigation
            - Handles overlays before/after click

        Steps to reproduce manually:
            1. Open home page
            2. Fill Starting Point and Destination
            3. Click "Plan Your Trip"
            4. Observe redirect to maps.roadtrippers.com

        Expected behavior:
            - If fields filled → navigates to planner
            - If empty → returns None, no navigation
            - No crash

        """
        self.log("Submitting trip search")
        self.handle_overlays(max_wait=5)

        start_val = self.get_input_value(self.START_INPUT)
        dest_val = self.get_input_value(self.DEST_INPUT)
        self.log(f"Start value: {start_val}, Destination value: {dest_val}")

        if not start_val or not dest_val:
            self.log("Cannot submit search: Start or Destination input empty")
            # Screenshot when submit blocked (empty fields) — shows error state
            self.take_screenshot(
                self._get_current_test_name(),
                "__submit_blocked__empty_fields"
            )
            return None

        self.click(self.GO_BUTTON)
        self.log("Search button clicked")

        self.handle_overlays(max_wait=5)  # ← NEW: after click, before checking planner

        # Screenshot after click — captures any loading/redirect moment
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_submit_click"
        )

        if self.wait_for_element_visibility(self.PLANNER):
            self.log("Trip Planner loaded successfully")
            return TripPlannerPage(self.driver)

        self.log("Trip Planner did not load; staying on Home Page")
        # Screenshot on failure — shows what happened instead of planner
        self.take_screenshot(
            self._get_current_test_name(),
            "__submit_failed__no_planner"
        )
        return None

    # ── Validation Helpers ─────────────────────
    def has_error_message(self) -> bool:
        """
        Check if error messages are visible under start or destination fields.

        Returns:
            bool: True if any error visible, False otherwise

        """
        start_error = self.is_visible(self.ERROR_START)
        dest_error = self.is_visible(self.ERROR_DEST)

        if start_error or dest_error:
            self.log("Error messages detected on search form")
            # Screenshot when errors are present — very useful for negative tests
            self.take_screenshot(
                self._get_current_test_name(),
                "__error_visible__validation_failed"
            )

        return start_error or dest_error

    def is_search_form_ready(self) -> bool:
        """
        Check if the main search form (start + destination inputs) is visible.

        Returns:
            bool: True if both inputs visible, False otherwise

        """
        ready = self.is_visible(self.START_INPUT) and self.is_visible(self.DEST_INPUT)
        self.log(f"Search form ready: {ready}")
        return ready

    def search_trip(self, start: str, destination: str) -> Optional[TripPlannerPage]:
        """
        Full end-to-end trip search: enter start/destination and submit.

        Args:
            start: Starting point text
            destination: Destination text

        Returns:
            Optional[TripPlannerPage]: Planner instance if successful, None otherwise

        """
        self.log(f"Starting full trip search: {start} → {destination}")
        self.enter_start(start)
        self.enter_destination(destination)
        return self.submit_search()

    # ── Signup Popup ──────────────────────────
    def open_signup_popup(self) -> SignUpPage:
        """
        Open the Sign Up popup via the header "Sign up" link.

        Returns:
            SignUpPage: Instance of the opened signup modal

        Current behavior:
            - Handles overlays before/after click
            - Waits for popup visibility
            - Extra overlay handling after popup open

        Steps to reproduce manually:
            1. Open home page
            2. Click "Sign up" in header
            3. Observe signup modal appears

        Expected behavior:
            - Popup opens successfully
            - Signup form visible

        """
        self.log("Opening Sign Up popup")
        self.handle_overlays(max_wait=10)
        self.wait_for_element_visibility(self.SIGN_UP_LINK)
        self.click(self.SIGN_UP_LINK)
        self.handle_overlays(max_wait=5)
        self.wait_for_element_visibility(self.POPUP)
        # Screenshot when popup is visible — confirms open state
        self.take_screenshot(
            self._get_current_test_name(),
            "__signup_popup_visible"
        )
        self.handle_overlays(max_wait=5)  # extra after popup visible, before returning
        self.log("Sign Up popup displayed")
        return SignUpPage(self.driver)

    def click_login_header_link(self):
        """
        Click the "Log in" header link/tab to open the login popup.

        Current behavior:
            - Handles overlays before/after
            - Waits for popup open (extra overlay handling)

        """
        self.handle_overlays(max_wait=10)
        # Screenshot before login click — useful for header issues
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_click_login"
        )
        self.click(self.LOGIN_TAB)
        self.handle_overlays(max_wait=5) # after popup opens, before any inner click
        # Screenshot after click — captures login popup appearance
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_click_login__popup_should_be_open"
        )

    def get_start_attribute_value(self) -> str:
        """
        Get the current value/attribute of the Starting Point input.

        Returns:
            str: Current input value (may be normalized after autocomplete)

        """
        final_value = self.get_attribute_value(self.START_INPUT)
        return final_value

    def get_destination_attribute_value(self) -> str:
        """
        Get the current value/attribute of the Destination input.

        Returns:
            str: Current input value (may be normalized after autocomplete)

        """
        final_value = self.get_attribute_value(self.DEST_INPUT)
        return final_value