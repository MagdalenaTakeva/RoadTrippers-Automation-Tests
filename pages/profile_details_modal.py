import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.wait import WebDriverWait

from pages.base_page import BasePage


class ProfileDetailsPage(BasePage):
    """
       Page Object for the post-signup onboarding popup ("Add profile details", id="address").

       This optional modal appears immediately after successful signup.
       It collects:
       - Vehicle (optional: year/make/model/fuel via nested selector)
       - Home address (autocomplete input)
       - Phone number (optional)

       All fields are skippable. Submitting saves data and closes the popup.
       Can be closed without filling anything.

       Current behavior:
       - Popup is modal-style, blocks background interaction
       - Vehicle selection opens inline dropdown → car option → inline form
       - Address uses autocomplete (first suggestion selectable)
       - Save button submits → popup closes on success
       - Close (X) button top-right; no confirmation on close
       - Errors shown per field if invalid data submitted

    """

    # Main popup
    POPUP = (By.ID, "address")
    HEADING = (By.XPATH, "//h3[contains(text(),'Add profile details')]")

    # Vehicle trigger
    VEHICLE_BUTTON = (By.ID, "vehicle-selector")

    # Dropdown after trigger click
    VEHICLE_DROPDOWN = (By.CSS_SELECTOR, ".dropdown-vehicle-selections.active")
    VEHICLE_CAR_OPTION = (By.CSS_SELECTOR, "div[data-vehicle-type='car'] p")

    # Inline vehicle form (after selecting car)
    VEHICLE_FORM = (By.CSS_SELECTOR, ".popup-vehicle-details.car")
    YEAR_SELECT = (By.ID, "select-vehicle-year")
    MAKE_SELECT = (By.ID, "select-vehicle-make")
    MODEL_SELECT = (By.ID, "select-vehicle-model")
    FUEL_SELECT = (By.ID, "select-vehicle-fuel-type")
    ADD_VEHICLE_BUTTON = (By.ID, "add-vehicle-button")

    # Address & Phone
    ADDRESS_INPUT = (By.ID, "rt-address-autocomplete")
    PHONE_INPUT = (By.NAME, "rt-phone")

    # Actions & Errors
    SAVE_BUTTON = (By.ID, "address-submit")
    CLOSE_BUTTON = (By.CSS_SELECTOR, "address .popup__close.popup__close_action")
    VEHICLE_ERROR = (By.ID, "address-vehicle-error")
    ADDRESS_ERROR = (By.ID, "home-address-errors")

    def __init__(self, driver):
        """
        Initialize the ProfileDetailsPage and wait for visibility (optional popup).

        Raises:
            TimeoutException: If heading not found (but logs and continues, since popup is optional)

        """
        super().__init__(driver)
        try:
            self.wait_for_element_visibility(self.HEADING)
            self.log("Profile details popup loaded")
        except TimeoutException:
            self.log("Profile details popup not detected (optional)")
            self.driver.save_screenshot("no_profile_popup.png")

    def is_open(self) -> bool:

        """
        Check if the Profile Details popup is currently visible.

        Returns:
            bool: True if popup visible, False otherwise

        """

        return self.is_visible(self.POPUP, timeout=self.SHORT_TIMEOUT)

    def select_vehicle_car(self) -> None:
        """
        Select 'Car, Truck or Van' from vehicle dropdown → fill year/make/model/fuel
        in inline form → submit vehicle addition.

        Current behavior:
            - Clicks vehicle selector → opens dropdown
            - Selects car → inline form appears
            - Hard-coded example values ("2020", "Honda", "Civic")
            - Submits vehicle (adds to profile)

        Steps to reproduce manually:
            1. Complete signup → profile popup appears
            2. Click "Add your vehicle"
            3. Select "Car, Truck or Van" from dropdown
            4. Fill year/make/model → click "Add vehicle"
            5. Observe inline form closes → vehicle saved

        Expected behavior:
            - Vehicle form opens and submits successfully
            - No crash or validation error (using valid example data)

        Raises:
            TimeoutException: If dropdown, form, or submit button not interactable

        """
        if not self.is_open():
            self.log("Popup not open - skipping vehicle", level="warning")
            return

        try:
            # 1. Click "Add your vehicle"
            self.wait_for_dynamic_element(self.VEHICLE_BUTTON).click()
            self.log("Clicked vehicle selector")

            # 2. Wait for dropdown
            self.wait_for_dynamic_element(self.VEHICLE_DROPDOWN)
            self.log("Dropdown visible")

            # 3. Click car option
            car_option = self.wait_for_dynamic_element(self.VEHICLE_CAR_OPTION)
            car_option.click()
            self.log("Selected Car option")

            # 4. Wait for inline car form
            self.wait.until(
                EC.visibility_of_element_located(self.VEHICLE_FORM),
                message="Car form did not appear after selecting car"
            )
            self.log("Car form visible")

            # 5. Fill year (triggers make/model)
            year_el = self.wait_for_element_visibility(self.YEAR_SELECT)
            year_el.send_keys("2020")  # triggers population

            # 6. Wait for make/model to enable
            self.wait.until(EC.element_to_be_clickable(self.MAKE_SELECT))
            time.sleep(1)  # brief buffer for options load

            make_el = self.driver.find_element(*self.MAKE_SELECT)
            make_el.send_keys("Honda")

            self.wait.until(EC.element_to_be_clickable(self.MODEL_SELECT))
            time.sleep(1)

            model_el = self.driver.find_element(*self.MODEL_SELECT)
            model_el.send_keys("Civic")

            # 8. Submit vehicle addition
            self.wait_for_element_to_be_clickable_with_timeout(self.ADD_VEHICLE_BUTTON).click()
            self.log("Submitted vehicle addition")

        except TimeoutException as e:
            self.log(f"Vehicle selection timed out: {e}", level="error")
            self.driver.save_screenshot("vehicle_form_error.png")
            raise

    def enter_home_address(self, address: str) -> None:
        """
        Enter home address into the autocomplete field and select first suggestion if available.

        Args:
            address: Partial or full address to type

        Current behavior:
            - Clears field first
            - Sends keys → waits for suggestions
            - Attempts to click first suggestion
            - Falls back to direct entry if no suggestions

        Steps to reproduce manually:
            1. Open profile popup
            2. Type "123 Main St" in address field
            3. Wait → suggestions appear → click first one
            4. Observe field normalizes to full address

        Expected behavior:
            - Address field accepts input
            - First suggestion selected if present
            - No crash on timeout

        """
        elem = self.wait_for_element_visibility(self.ADDRESS_INPUT)
        elem.clear()
        elem.send_keys(address)

        time.sleep(1.5)  # allow autocomplete

        try:
            first_suggestion = self.wait_for_element_to_be_clickable_with_timeout(
                (By.CSS_SELECTOR, ".autocomplete li:first-child"), timeout = BasePage.DYNAMIC_CONTENT_TIMEOUT
            )
            first_suggestion.click()
            self.log("Selected first address suggestion")
        except TimeoutException:
            self.log("No suggestions - using direct entry", level="debug")

    def enter_phone(self, phone: str) -> None:
        """
        Enter phone number into the phone field.

        Args:
            phone: Phone number string (e.g. "1234567890")

        """
        elem = self.wait_for_element_visibility(self.PHONE_INPUT)
        elem.clear()
        elem.send_keys(phone)

    def save(self) -> None:
        """
        Click the "Save" button to submit profile details and close popup.

        Current behavior:
            - Submits data
            - Popup closes on success
            - May show errors if validation fails

        Steps to reproduce manually:
            1. Fill optional fields
            2. Click "Save"
            3. Observe popup closes → profile updated

        Expected behavior:
            - Save processes
            - Popup disappears
            - No crash

        """
        btn = self.wait_for_element_to_be_clickable_with_timeout(self.SAVE_BUTTON)
        btn.click()
        self.log("Save clicked")

        try:
            self.wait_for_element_visibility(self.POPUP)
            self.log("Popup closed after save")
        except TimeoutException:
            self.log("Popup did not close after save", level="error")

    def close(self) -> None:
        """
        Close the profile details popup without saving.

        Uses normal click with JS fallback if intercepted.

        """
        try:
            close_btn = self.wait_for_element_to_be_clickable_with_timeout(self.CLOSE_BUTTON)
            self.js_click(close_btn)
            self.log("Close button clicked via JS")

            WebDriverWait(self.driver, 10).until_not(
                EC.visibility_of_element_located(self.POPUP)
            )
            self.log("Popup closed")
        except TimeoutException:
            self.log("Close failed - forcing hide", level="warning")
            self.driver.execute_script("document.getElementById('address')?.remove();")

    def has_errors(self)-> list[str]:
        """
        Return list of visible error messages from vehicle or address fields.

        Returns:
            list[str]: Error texts (empty list if no errors)

        """
        errors = []
        for locator in [self.VEHICLE_ERROR, self.ADDRESS_ERROR]:
            try:
                elem = self.driver.find_element(*locator)
                text = elem.text.strip()
                if elem.is_displayed() and text:
                    errors.append(text)
            except NoSuchElementException:
                pass
        return errors

    def wait_for_profile_modal_to_be_visible(self):
        """
        Wait until the profile details popup becomes visible.

        Raises:
            TimeoutException: If popup not visible in time

        """
        self.wait_for_element_visibility(self.POPUP)