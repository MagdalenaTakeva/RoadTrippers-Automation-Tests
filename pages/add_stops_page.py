from selenium.common import TimeoutException
from selenium.webdriver.common.by import By

from pages.base_page import BasePage


class AddStopsPage(BasePage):
    """
       Page Object for the Add Stops screen in a newly created road trip.

       This screen appears after creating a trip (quick launch or autopilot).
       It allows:
       - Adding stops via autocomplete input
       - Viewing current waypoints (start + stops + destination)
       - Launching the trip (generates itinerary)
       - Handling onboarding modal
       - Displaying stop limit banner (15 stops max in free plan)

       Current behavior:
       - Autocomplete triggers on partial input
       - Added stops appear in waypoint list (count includes start + destination)
       - Limit banner shows at 15 stops
       - Launch button generates itinerary (may show onboarding first)
       - Toasts appear for async actions (e.g. autosave)
       - Onboarding modal may overlay on first launch

    """
    # ── Add Stop Input & Autocomplete ────────────────────
    STOP_INPUT = (
        By.XPATH,
        "//label[normalize-space()='Add stops']/preceding-sibling::input"
    )

    RT_AUTOCOMPLETE_LIST = (
        By.CSS_SELECTOR,
        ".rt-autocomplete-list"
    )

    # ── Waypoint List ────────────────────────────────────
    WAYPOINT_LIST_CONTAINER = (By.CSS_SELECTOR, ".waypoint-list")
    WAYPOINT_LIST = (By.CSS_SELECTOR, ".waypoint-list .onboarding-waypoint-view")

    # ── Limit Banner & Toasts ────────────────────────────
    STOP_LIMIT_BANNER = (By.CSS_SELECTOR, ".rt-banner")
    STOP_LIMIT_TEXT = (
        By.XPATH,
        "//div[contains(@class,'rt-banner-secondary-text') "
        "and contains(.,'You can add up to 15 stops')]"
    )

    TOAST = (By.CSS_SELECTOR, ".Toastify__toast")
    TOAST_ERROR = (
        By.XPATH,
        "//div[contains(@class,'Toastify__toast') "
        "and contains(.,'Ooops')]"
    )

    # ── Actions ──────────────────────────────────────────
    LAUNCH_TRIP_BTN = (By.CSS_SELECTOR, ".sidebar-actions-container button")

    ONBOARD_MODAL = (By.ID, "onboard-modal")
    ONBOARD_MODAL_CLOSE_BTN = (By.CSS_SELECTOR, ".rt-button.rt-modal-close-button.cream.small.circle")
    ITINERARY = (By.CSS_SELECTOR, "button.enabled")

    @staticmethod
    def autocomplete_option_by_text(text: str):
        """
        Locator factory for autocomplete suggestion by visible text.

        Args:
            text: Exact or partial text of the suggestion

        Returns:
            tuple: (By.XPATH, locator string) for matching button

        """
        return (
            By.XPATH,
            f"//div[@class='rt-autocomplete-list-item-name' "
            f"and normalize-space()='{text}']"
            f"/ancestor::button"
        )

    # ── Methods ──────────────────────────────────────────

    def add_stop(self, stop_text: str, suggestion_to_select: str = None) -> None:
        """
        Add a stop using the autocomplete input field.

        Args:
            stop_text: Text to type in the add stops input
            suggestion_to_select: Optional exact text of suggestion to click
                                 (if None, clicks first visible suggestion)

        Current behavior:
            - Types text → waits for autocomplete list
            - Selects specific suggestion or first one
            - Waits for toast to disappear (autosave)

        Steps to reproduce manually:
            1. Create new trip → go to Add Stops
            2. Type "Ohio" in "Add stops" field
            3. Wait → suggestions appear → click "Ohio, US"
            4. Observe new waypoint added to list

        Expected behavior:
            - Stop added to waypoint list
            - Count increases
            - No crash or persistent toast

        Raises:
            TimeoutException: If autocomplete list or suggestion not found

        """
        self.send_keys(self.STOP_INPUT, stop_text)
        self.log(f"Typed stop text: {stop_text}")

        # Screenshot after typing — shows partial input before suggestions
        self.take_screenshot(
            self._get_current_test_name(),
            f"__typed_stop_{stop_text.replace(' ', '_')}"
        )

        self.wait_for_element_visibility(self.RT_AUTOCOMPLETE_LIST)

        # Screenshot when autocomplete list appears — critical for suggestion debugging
        self.take_screenshot(
            self._get_current_test_name(),
            "__autocomplete_list_visible"
        )

        if suggestion_to_select:
            option_locator = self.autocomplete_option_by_text(
                suggestion_to_select
            )
        else:
            option_locator = (
                By.CSS_SELECTOR,
                ".rt-autocomplete-list-item-view"
            )

        option = self.wait_for_element_to_be_clickable_with_timeout(
            option_locator
        )

        option.click()

        self.log(
            f"Selected stop: "
            f"{suggestion_to_select if suggestion_to_select else 'first suggestion'}"
        )

        # Screenshot after selection — shows waypoint added to list
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_select_stop"
        )

        # Wait for stop to be added
        self.wait_for_toast_to_disappear()

        # Screenshot after toast gone — final state after add
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_add_stop__toast_gone"
        )

    def has_waypoint(self, place: str) -> bool:
        """
        Check if a specific place name is present in the waypoint list.

        Args:
            place: Expected place text (e.g. "Ohio,US")

        Returns:
            bool: True if waypoint with matching text exists

        Current behavior:
            - Matches partial text (case-insensitive)
            - Uses waypoint view elements

        Steps to reproduce manually:
            1. Add "Ohio" stop
            2. Look in itinerary list → see "Ohio, US"

        Expected behavior:
            - Returns True if place visible in list

        """
        try:
            self.wait_for_element_visibility(self.WAYPOINT_LIST, timeout=BasePage.INTERACTION_TIMEOUT)

            # Screenshot when waypoint list is visible — helps debug count/matching issues
            self.take_screenshot(
                self._get_current_test_name(),
                "__waypoint_list_visible__checking_has_waypoint"
            )

            found = any(
                place.split(",")[0].lower() in el.text.lower() for el in self.driver.find_elements(*self.WAYPOINT_LIST))

            if found:
                self.take_screenshot(
                    self._get_current_test_name(),
                    f"__has_waypoint_true__{place.replace(' ', '_')}"
                )
            else:
                self.take_screenshot(
                    self._get_current_test_name(),
                    f"__has_waypoint_false__{place.replace(' ', '_')}"
                )

            return found
        except TimeoutException:
            self.take_screenshot(
                self._get_current_test_name(),
                "__waypoint_list_timeout__has_waypoint_check_failed"
            )
            return False

    def get_stop_count(self) -> int:
        """
        Get the current number of waypoints/stops in the itinerary.

        Returns:
            int: Number of visible waypoint elements (includes start + destination)

        Current behavior:
            - Counts onboarding-waypoint-view elements
            - Returns 0 if list not visible

        Steps to reproduce manually:
            1. Create trip with no extra stops → count = 2 (start + dest)
            2. Add one stop → count = 3

        Expected behavior:
            - Accurate count of visible stops

        """
        try:
            self.wait_for_element_visibility(self.WAYPOINT_LIST, timeout=self.INTERACTION_TIMEOUT)

            # Screenshot when counting waypoints — visual proof of list state
            self.take_screenshot(
                self._get_current_test_name(),
                "__before_count_waypoints"
            )

            count = len(self.driver.find_elements(*self.WAYPOINT_LIST))

            # Screenshot with count in name — easy to correlate with assertion
            self.take_screenshot(
                self._get_current_test_name(),
                f"__stop_count_{count}"
            )

            return count
        except TimeoutException:
            return 0

    def wait_for_toast_to_disappear(self):
        """
        Wait until any Toastify notification disappears (e.g. after adding stop).

        Current behavior:
            - Handles autosave toast or error toast
            - Tolerates no toast appearing

        Steps to reproduce manually:
            1. Add a stop → brief "Saved" or "Added" toast appears
            2. Toast fades after ~3–5 seconds

        Expected behavior:
            - Toast disappears or never appears → no hang

        """
        try:
            self.wait_for_element_visibility(self.TOAST, timeout=BasePage.INTERACTION_TIMEOUT)

            # Screenshot when toast appears — useful for toast timing issues
            self.take_screenshot(
                self._get_current_test_name(),
                "__toast_visible"
            )

            self.wait_for_element_invisibility(self.TOAST, timeout=BasePage.INTERACTION_TIMEOUT)

            self.take_screenshot(
                self._get_current_test_name(),
                "__toast_disappeared"
            )
        except TimeoutException:
            # No toast appeared — acceptable, but screenshot for context
            self.take_screenshot(
                self._get_current_test_name(),
                "__no_toast_appeared"
            )
            pass

    def launch_trip(self) -> None:
        """
        Click the "Launch trip" button to generate the itinerary.

        Current behavior:
            - Triggers trip computation
            - May show onboarding modal first time

        Steps to reproduce manually:
            1. Add stops (or none)
            2. Click "Launch trip"
            3. Observe itinerary generation (or onboarding)

        Expected behavior:
            - Button clicked successfully
            - Itinerary loads or onboarding appears

        """
        # Screenshot before launch — shows current stops/state
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_launch_trip"
        )

        self.click(self.LAUNCH_TRIP_BTN)

        # Screenshot after click — captures loading or immediate feedback
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_launch_click"
        )

    def close_onboard_modal(self) -> None:
        """
        Close the first-time onboarding modal after launching a trip.

        Current behavior:
            - Uses normal click
            - JS fallback if button not interactable

        Steps to reproduce manually:
            1. Launch first trip
            2. Onboarding modal appears → click X
            3. Modal closes → itinerary visible

        Expected behavior:
            - Modal closes
            - No crash

        """
        try:
            # Screenshot when trying to close — shows modal state
            self.take_screenshot(
                self._get_current_test_name(),
                "__before_close_onboard_modal"
            )

            self.click(self.ONBOARD_MODAL_CLOSE_BTN)
            self.log("Create Trip modal closed")

            # Screenshot after close attempt
            self.take_screenshot(
                self._get_current_test_name(),
                "__after_close_onboard_modal"
            )
        except TimeoutException:
            self.log("Close button not clickable — forcing removal", level="warning")
            self.driver.execute_script(
                "document.querySelector('onboard-modal')?.remove();"
            )
            self.take_screenshot(
                self._get_current_test_name(),
                "__onboard_modal_force_remove__close_timeout"
            )

    def itinerary_is_displayed(self):
        """
        Check if the itinerary button is displayed (post-launch).

        Returns:
            bool: True if itinerary enabled button visible

        """
        try:
            el = self.wait_for_element_visibility(self.ITINERARY, timeout=BasePage.INTERACTION_TIMEOUT)

            # Screenshot when checking itinerary — visual confirmation
            self.take_screenshot(
                self._get_current_test_name(),
                "__checking_itinerary_displayed"
            )

            is_displayed = el.is_displayed()

            if is_displayed:
                self.take_screenshot(
                    self._get_current_test_name(),
                    "__itinerary_displayed_true"
                )
            else:
                self.take_screenshot(
                    self._get_current_test_name(),
                    "__itinerary_displayed_false"
                )

            return is_displayed
        except TimeoutException:
            self.take_screenshot(
                self._get_current_test_name(),
                "__itinerary_timeout__not_displayed"
            )
            return False

    def get_stops_limit_text(self) -> str:
        """
        Get the text of the stop limit banner (e.g. when 15 stops reached).

        Returns:
            str: Banner text (e.g. "You can add up to 15 stops for now...")

        Raises:
            TimeoutException: If banner not visible

        """
        try:
            banner = self.wait_for_element_visibility(self.STOP_LIMIT_TEXT, timeout=BasePage.INTERACTION_TIMEOUT)

            # Screenshot when limit banner appears — key for limit tests
            self.take_screenshot(
                self._get_current_test_name(),
                "__stop_limit_banner_visible"
            )

            text = banner.text
            self.log(f"Stop limit banner text: {text}")
            return text
        except TimeoutException:
            self.take_screenshot(
                self._get_current_test_name(),
                "__stop_limit_banner_not_visible"
            )
            raise
