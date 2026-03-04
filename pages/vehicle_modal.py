from selenium.common import ElementClickInterceptedException
from selenium.webdriver.common.by import By
from pages.base_page import BasePage


class VehiclePopupPage(BasePage):
    """
       Page Object for the nested "Add vehicle" popup (id="vehicle").

       This popup appears after clicking "Add your vehicle" during onboarding or profile settings.
       It allows sequential selection of: year → make → model → (optional) fuel type.
       Submitting adds the vehicle to the user's profile and closes the popup.

       Current behavior:
       - Popup is modal-style, blocks interaction with background until closed or submitted.
       - Fields are <select> or <input> with dynamic options (year → make → model cascade).
       - Add button may be intercepted by overlays → JS fallback used.
       - Close button is in top-right corner.

    """

    POPUP = (By.ID, "vehicle")

    YEAR_SELECT = (By.ID, "select-vehicle-year")
    MAKE_SELECT = (By.ID, "select-vehicle-make")
    MODEL_SELECT = (By.ID, "select-vehicle-model")
    FUEL_SELECT = (By.ID, "select-vehicle-fuel-type")

    ADD_BUTTON = (By.ID, "add-vehicle-button")
    BACK_BUTTON = (By.CSS_SELECTOR, ".vehicle-popup__back")
    CLOSE_BUTTON = (By.CSS_SELECTOR, ".popup__close.popup__close_action")

    def __init__(self, driver):
        """
        Initialize the VehiclePopupPage and wait for visibility.

        Raises:
            TimeoutException: If popup does not become visible within default timeout
        """
        super().__init__(driver)
        self.log("Waiting for Vehicle popup to become visible")
        self.wait_for_element_visibility(self.POPUP)
        self.log("Vehicle popup is visible")

    # ── Vehicle Popup ──────────────────────────
    def is_open(self, timeout: int = BasePage.NAVIGATION_TIMEOUT) -> bool:

        """
        Check if the Vehicle popup is currently visible.

        Args:
            timeout: Maximum time to wait for visibility check (default: NAVIGATION_TIMEOUT)

        Returns:
            bool: True if popup is visible, False otherwise

        """

        self.log("Checking if Vehicle popup is open")
        visible = self.is_visible(self.POPUP, timeout=timeout)
        self.log(f"Vehicle popup open state: {visible}")
        return visible

    def select_year(self, year: str, timeout=BasePage.DYNAMIC_CONTENT_TIMEOUT):
        """
        Select a vehicle year from the year dropdown/input.

        Args:
            year: The year as string (e.g. "2020")
            timeout: Max time to wait for the year field (default: DYNAMIC_CONTENT_TIMEOUT)

        Current behavior:
            - Clears existing value (if any)
            - Sends keys → field normalizes or auto-selects
            - Logs warning if final value != expected

        Steps to reproduce manually:
            1. Open onboarding or profile → click "Add your vehicle"
            2. In year field type "2020"
            3. Observe field accepts value (may auto-format)

        Expected behavior:
            - Year field value matches input (or closest valid year)
            - No crash or validation error

        """
        self.log(f"Selecting vehicle year: {year}")
        el = self.wait_for_dynamic_element(self.YEAR_SELECT, timeout=timeout)
        el.clear()
        el.send_keys(year)

        selected_value = self.get_input_value(self.YEAR_SELECT)
        if selected_value != year:
            self.log(f"Warning: Year field value mismatch (expected {year}, got {selected_value})", level="warning")
        self.log(f"VehiclePopupPage.select_year: Year selected -> {selected_value}")

    def select_make(self, make: str, timeout= BasePage.DYNAMIC_CONTENT_TIMEOUT):

        """
        Select a vehicle make after year is chosen.

        Args:
            make: Make name (e.g. "Toyota")
            timeout: Max time to wait for make field

        Steps to reproduce manually:
            1. Select a year first
            2. Type "Toyota" in make field
            3. Observe field accepts or auto-completes

        Expected behavior:
            - Make field value matches input
            - Next field (model) becomes enabled

        """

        self.log(f"Selecting vehicle make: {make}")
        el = self.wait_for_dynamic_element(self.MAKE_SELECT, timeout=timeout)
        el.send_keys(make)

        selected_value = self.get_input_value(self.MAKE_SELECT)
        self.log(f"Make field value after selection: {selected_value}")

    def select_model(self, model: str, timeout= BasePage.DYNAMIC_CONTENT_TIMEOUT):

        """
        Select a vehicle model after make is chosen.

        Args:
            model: Model name (e.g. "Camry")
            timeout: Max time to wait for model field

        Expected behavior:
            - Model field accepts input
            - Fuel field (if shown) becomes available

        """

        self.log(f"Selecting vehicle model: {model}")
        el = self.wait_for_dynamic_element(self.MODEL_SELECT, timeout=timeout)
        el.send_keys(model)

        selected_value = self.get_input_value(self.MODEL_SELECT)
        self.log(f"Model field value after selection: {selected_value}")

    def select_fuel(self, fuel: str = "gasoline", timeout= BasePage.DYNAMIC_CONTENT_TIMEOUT):

        """
        Select fuel type (optional field).

        Args:
            fuel: One of "gasoline", "diesel", "electric" (default: "gasoline")
            timeout: Max time to wait for fuel field

        Expected behavior:
            - Fuel field value matches input
            - Does not block submission if skipped

        """

        self.log(f"Selecting vehicle fuel type: {fuel}")
        el = self.wait_for_dynamic_element(self.FUEL_SELECT, timeout=timeout)
        el.send_keys(fuel)

        selected_value = self.get_input_value(self.FUEL_SELECT)
        self.log(f"Fuel field value after selection: {selected_value}")

    # ── Actions ──────────────────────────
    def add_vehicle(self):

        """
        Click the "Add" button to submit the vehicle and close the popup.

        Uses normal click with fallback to JS execution if intercepted
        (common due to overlays, animations, or z-index issues).

        Raises:
            Exception: If button cannot be clicked even via JS

        """

        try:
            self.wait_for_element_to_be_clickable_with_timeout(self.ADD_BUTTON).click()
        except ElementClickInterceptedException:
            self.js_click(self.ADD_BUTTON) # Overlays or z-index issues often cause tests to fail intermittently.

    def close(self):
        """
        Close the vehicle popup without saving.

        Clicks the close (X) button in the top-right corner.

        Raises:
            TimeoutException: If close button is not clickable in time

        """
        self.wait_for_element_to_be_clickable_with_timeout(self.CLOSE_BUTTON).click()