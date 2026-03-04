from datetime import datetime, timedelta
from selenium.common import TimeoutException
from selenium.webdriver.common.by import By

from pages.add_stops_page import AddStopsPage
from pages.base_page import BasePage


class RoadTripModal(BasePage):
    """
    Page Object for the Road Trip creation modal overlay on the Trip Planner page.

    This modal appears when clicking the Discover Card or "Start a new trip".
    It allows entering origin/destination, choosing trip type (Quick Launch or Autopilot),
    setting start/end dates via calendar, and submitting to create the trip.

    Current behavior:
    - Modal blocks interaction until closed or submitted.
    - Autocomplete triggers on partial location input.
    - Dates use MUI calendar picker with month navigation.
    - Submit closes modal and loads Add Stops / planner view.

    """

    # ── Modal Root ───────────────────────────────────────
    MODAL = (By.CSS_SELECTOR, ".rt-modal-content")
    VIEW = (By.ID, "create-trip-manually-modal-view")
    HEADING = (By.XPATH, "//h1[text()='Where are you going?']")
    CLOSE_BUTTON = (By.CSS_SELECTOR, "button.rt-modal-close-button")

    # ── Location Inputs ──────────────────────────────────
    ORIGIN_INPUT = (By.ID, "origin")
    DESTINATION_INPUT = (By.ID, "destination")

    # Autocomplete containers
    ORIGIN_AUTOCOMPLETE_LIST = (
        By.CSS_SELECTOR,
        ".origin-input .rt-autocomplete-list"
    )

    DESTINATION_AUTOCOMPLETE_LIST = (
        By.CSS_SELECTOR,
        ".destination-input .rt-autocomplete-list"
    )

    # First suggestion button (scoped)
    ORIGIN_FIRST_SUGGESTION = (
        By.CSS_SELECTOR,
        ".origin-input .rt-autocomplete-list button.rt-autocomplete-list-item-view"
    )

    DESTINATION_FIRST_SUGGESTION = (
        By.CSS_SELECTOR,
        ".destination-input .rt-autocomplete-list button.rt-autocomplete-list-item-view"
    )

    # ── Trip Type Radios ─────────────────────────────────
    QUICK_LAUNCH_RADIO = (By.CSS_SELECTOR, "input[name='trip-type'][value='false']")
    AUTOPILOT_RADIO = (By.CSS_SELECTOR, "input[name='trip-type'][value='true']")

    # ── Calendar Dates Inputs ─────────────────────────────────────
    START_DATE_INPUT = (By.ID, "start_date")
    END_DATE_INPUT = (By.ID, "end_date")

    # ── Create Action ────────────────────────────────────
    CREATE_TRIP_BUTTON = (
        By.XPATH,
        "//button[.//div[text()='Create trip']]"
    )

    # ── Calendar (MUI) ───────────────────────────────────
    CALENDAR_GRID = (By.CSS_SELECTOR, "div[role='grid']")

    CALENDAR_MONTH_LABEL = (
        By.CSS_SELECTOR,
        ".MuiPickersCalendarHeader-label"
    )

    NEXT_MONTH_BUTTON = (
        By.CSS_SELECTOR,
        "button[aria-label='Next month']"
    )

    PREV_MONTH_BUTTON = (
        By.CSS_SELECTOR,
        "button[aria-label='Previous month']"
    )

    TODAY = (
        By.XPATH,
        "//button[@role='gridcell' and @aria-current='date']"
    )

    EXIT = (By.CSS_SELECTOR, ".nav-link.js-route")

    def is_open(self) -> bool:
        """
        Check if the Road Trip creation modal is currently visible.

        Returns:
            bool: True if modal is visible, False otherwise

        """
        return self.is_visible(self.MODAL, timeout=self.SHORT_TIMEOUT)

    # Enter start and destination location
    def _enter_location(self, text: str, is_destination: bool) -> None:
        """
        Enter a location into origin or destination field and select
        the first autocomplete suggestion.

        Handles:
        - Clearing the field first
        - Waiting for autocomplete list container
        - Waiting for clickable first suggestion
        - Clicking the suggestion to normalize value

        Args:
            text: Partial or full location to type
            is_destination: True for destination field, False for origin

        Raises:
            TimeoutException: If autocomplete list or suggestion not found/clickable

        """

        if is_destination:
            input_locator = self.DESTINATION_INPUT
            list_locator = self.DESTINATION_AUTOCOMPLETE_LIST
            suggestion_locator = self.DESTINATION_FIRST_SUGGESTION
            label = "Destination"
        else:
            input_locator = self.ORIGIN_INPUT
            list_locator = self.ORIGIN_AUTOCOMPLETE_LIST
            suggestion_locator = self.ORIGIN_FIRST_SUGGESTION
            label = "Origin"

        self.log(f"Entering {label}: {text}")

        field = self.wait_for_element_visibility(input_locator)
        field.clear()
        field.send_keys(text)

        # Wait for autocomplete list container
        self.wait_for_element_visibility(list_locator, timeout=20)

        # Wait for first suggestion button to be clickable
        suggestion = self.wait_for_element_to_be_clickable_with_timeout(
            suggestion_locator,
            timeout=20
        )

        suggestion.click()

        self.log(f"{label} selected from autocomplete: {text}")

    def enter_start(self, location: str) -> None:
        """
        Enter and autocomplete the Starting Point (origin) location.

        Args:
            location: Partial or full location text (e.g. "Chi")

        """
        self._enter_location(location, is_destination=False)

    def enter_destination(self, location: str) -> None:
        """
        Enter and autocomplete the Destination location.

        Args:
            location: Partial or full location text (e.g. "New")

        """
        self._enter_location(location, is_destination=True)

    # ── Trip Type ────────────────────────────────────────
    def select_quick_launch(self):
        """
        Select the Quick Launch trip type radio button.

        Current behavior:
            - Sets trip-type value to 'false'
            - Enables quick route generation without AI planning

        """
        self.wait_for_element_to_be_clickable_with_timeout(
            self.QUICK_LAUNCH_RADIO
        ).click()
        self.log("Trip type set to Quick Launch")

    def select_autopilot(self):
        """
        Select the Autopilot trip type radio button.

        Current behavior:
            - Sets trip-type value to 'true'
            - Enables AI-generated itinerary suggestions

        """
        self.wait_for_element_to_be_clickable_with_timeout(
            self.AUTOPILOT_RADIO
        ).click()
        self.log("Trip type set to Autopilot")

    def select_trip_type(self, trip_type: str):
        """
        Select the trip type radio button by name.

        Args:
            trip_type: 'quick_launch' or 'autopilot' (case-insensitive)

        Raises:
            ValueError: If invalid trip_type provided

        """
        trip_type = trip_type.lower()

        if trip_type == "quick_launch":
            locator = self.QUICK_LAUNCH_RADIO
            label = "Quick Launch"
        elif trip_type == "autopilot":
            locator = self.AUTOPILOT_RADIO
            label = "Autopilot"
        else:
            raise ValueError(f"Invalid trip_type: {trip_type}. Must be 'quick_launch' or 'autopilot'.")

        self.wait_for_element_to_be_clickable_with_timeout(locator).click()
        self.log(f"Trip type set to {label}")

    # ── Date Picker Openers ──────────────────────────────
    def open_start_date_picker(self):
        """
        Click the start date input to open the calendar picker.

        """
        self.wait_for_element_to_be_clickable_with_timeout(
            self.START_DATE_INPUT
        ).click()
        self.log("Start date picker opened")

    def open_end_date_picker(self):
        """
        Click the end date input to open the calendar picker.

        """
        self.wait_for_element_to_be_clickable_with_timeout(
            self.END_DATE_INPUT
        ).click()
        self.log("End date picker opened")

    # ── Calendar Navigation Helpers ──────────────────────
    def _get_visible_month_year(self) -> str:
        """
        Get the currently displayed month/year label in the calendar.

        Returns:
            str: e.g. "February 2026"

        """
        label = self.wait_for_element_visibility(self.CALENDAR_MONTH_LABEL)
        return label.text.strip()

    def _navigate_to_month(self, target_date: datetime, max_attempts: int = 12):
        """
        Navigate the calendar to the month/year of the target date.

        Args:
            target_date: The desired date (month/year used)
            max_attempts: Max month clicks (default 12)

        Raises:
            TimeoutException: If target month not reached

        """
        target_label = target_date.strftime("%B %Y")

        for _ in range(max_attempts):
            current_label = self._get_visible_month_year()

            if current_label == target_label:
                return

            current_dt = datetime.strptime(current_label, "%B %Y")

            if current_dt < target_date.replace(day=1):
                self.wait_for_element_to_be_clickable_with_timeout(
                    self.NEXT_MONTH_BUTTON
                ).click()
            else:
                self.wait_for_element_to_be_clickable_with_timeout(
                    self.PREV_MONTH_BUTTON
                ).click()

        raise TimeoutException(
            f"Could not navigate to month {target_label}"
        )

    # ── Date Selection ───────────────────────────────────
    def select_date(self, date_obj: datetime):
        """
        Navigate to correct month and select the given day in the MUI calendar.

        Args:
            date_obj: Full datetime object (day is used for selection)

        Steps (internal):
            1. Navigate to correct month/year
            2. Click enabled button with matching day number

        Raises:
            TimeoutException: If day button not clickable

        """

        self.wait_for_element_visibility(self.CALENDAR_GRID)

        # Navigate to correct month
        self._navigate_to_month(date_obj)

        day_locator = self.day_by_number(date_obj.day)

        self.wait_for_element_to_be_clickable_with_timeout(
            day_locator
        ).click()

        self.log(f"Selected date: {date_obj.strftime('%Y-%m-%d')}")

    def set_trip_dates(self, start_date: datetime, end_date: datetime):
        """
        Set both start and end dates using the calendar pickers.

        Args:
            start_date: Start datetime
            end_date: End datetime

        """
        self.open_start_date_picker()
        self.select_date(start_date)

        self.open_end_date_picker()
        self.select_date(end_date)

        self.log(
            f"Trip dates set: "
            f"{start_date.strftime('%Y-%m-%d')} → "
            f"{end_date.strftime('%Y-%m-%d')}"
        )

    # ── Submit / Close ───────────────────────────────────
    def click_create_trip_btn(self) -> AddStopsPage:
        """
        Click the "Create trip" button to submit and proceed to Add Stops.

        Returns:
            AddStopsPage: Instance of the next page (Add Stops)

        Raises:
            TimeoutException: If button not clickable

        """
        self.wait_for_element_to_be_clickable_with_timeout(
            self.CREATE_TRIP_BUTTON
        ).click()
        self.log("Create Trip clicked")
        return AddStopsPage(self.driver)

    def close(self):
        """
        Close the Road Trip modal without creating a trip.

        Tries normal click; falls back to JS removal if button is obstructed.

        """
        try:
            self.wait_for_element_to_be_clickable_with_timeout(
                self.CLOSE_BUTTON
            ).click()
            self.log("Create Trip modal closed")
        except TimeoutException:
            self.log("Close button not clickable — forcing removal", level="warning")
            self.driver.execute_script(
                "document.querySelector('.rt-modal-content')?.remove();"
            )

    def create_trip(
            self,
            origin: str,
            destination: str,
            trip_type: str,
            start_offset_days: int = 3,
            trip_duration_days: int = 2
    ):
        """
        Full workflow to create a road trip from the modal.

        Steps:
            1. Enter origin and destination (with autocomplete)
            2. Select trip type (Quick Launch or Autopilot)
            3. Set start and end dates (relative to today)
            4. Click "Create trip" button

        Args:
            origin: Partial origin text for autocomplete (e.g. "Ca")
            destination: Partial destination text (e.g. "New")
            trip_type: 'quick_launch' or 'autopilot'
            start_offset_days: Days from today to set as start (default 3)
            trip_duration_days: Trip length in days (default 2)

        Raises:
            ValueError: If invalid trip_type
            TimeoutException: If any step times out

        """
        self.log("Starting trip creation workflow")

        # ── Enter locations ─────────────────────────────
        self.enter_start(origin)
        self.enter_destination(destination)

        # ── Select trip type ───────────────────────────
        self.select_trip_type(trip_type)

        # ── Set trip dates ────────────────────────────
        start_date = datetime.now() + timedelta(days=start_offset_days)
        end_date = start_date + timedelta(days=trip_duration_days)
        self.set_trip_dates(start_date, end_date)

        # ── Submit trip ───────────────────────────────
        self.click_create_trip_btn()

        self.log("Trip creation workflow completed")

    # ── Static Methods ───────────────────────────────────
    @staticmethod
    def day_by_number(day: int):
        """
        Locator factory for calendar day button by visible number.

        Args:
            day: Day of month (1–31)

        Returns:
            tuple: (By.XPATH, locator string) for enabled day button

        """
        return (
            By.XPATH,
            f"//button[@role='gridcell' and not(@disabled) and text()='{day}']"
        )

    def click_exit(self):
        """
        Click the exit link/button on the modal or planner page.

        Raises:
            TimeoutException: If exit element not clickable

        """
        self.wait_for_element_to_be_clickable_with_timeout(self.EXIT, timeout=BasePage.INTERACTION_TIMEOUT).click()