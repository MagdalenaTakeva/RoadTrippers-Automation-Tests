import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from pages.add_stops_page import AddStopsPage
from pages.base_page import BasePage
from pages.road_trip_modal import RoadTripModal

class TripPlannerPage(BasePage):
    """
    Page Object representing the Trip Planner page (maps.roadtrippers.com).

    Handles navigation, modal interactions, adding stops, launching trips,
    exiting the planner, and verifying generated itineraries/waypoints.

    """

    MAP_CONTAINER = (By.CSS_SELECTOR, "#map-details")
    DISCOVER_CARD_BTN = (By.CSS_SELECTOR, "button.discover-card")

    EXIT = (By.CSS_SELECTOR, ".nav-link.js-route")
    CONFIRM_VIEW = (By.CSS_SELECTOR, ".confirm-view")
    CONFIRM_EXIT = (By.CSS_SELECTOR, ".confirm .new-button.default.large.red")
    CANCEL_EXIT = (By.CSS_SELECTOR, "..confirm .new-button.flat.gray")

    # Map Action Bar
    ITINERARY_BTN_MAP_ACTION_BAR = (By.CSS_SELECTOR, "#map-action-bar button.itinerary-button")
    MY_TRIPS_BTN_MAP_ACTION_BAR = (By.CSS_SELECTOR, "#map-action-bar button.my-trips-button")
    ADD_TO_TRIP_BTN_MAP_ACTION_BAR = (By.CSS_SELECTOR, "#map-action-bar button.add-waypoint-button")

    # Map Details
    TRIP_CARD_LINK = (By.CSS_SELECTOR, "#map-details div.my-trips a.rt-trip-card-link.js-route")
    SEE_ALL_TRIPS_LINK = (By.CSS_SELECTOR, "#map-details div.my-trips a[href*='trips']")

    # Itinerary
    ITINERARY_WAYPOINT_GROUP_LIST = (By.CSS_SELECTOR, "div.itinerary .waypoint-group-list")
    WAYPOINT_NAME_LOCATOR = (By.CSS_SELECTOR,
                                 ".waypoint-details button.waypoint-primary-label")

    @property
    def road_trip_modal(self) -> RoadTripModal:
        """
        Returns a RoadTripModal instance bound to this page.
        The modal is not automatically opened; call open_modal() to show it.
        """
        return RoadTripModal(self.driver)

    @property
    def add_stops_page(self) -> AddStopsPage:
        """
        Returns a RoadTripModal instance bound to this page.
        The modal is not automatically opened; call open_modal() to show it.
        """
        return AddStopsPage(self.driver)

    def is_loaded(self, timeout: int = BasePage.NAVIGATION_TIMEOUT) -> bool:

        """
        Wait for Trip Planner page to load (map container visible) and dismiss overlays.

        Args:
            timeout: Maximum time to wait for page readiness (default: BasePage.NAVIGATION_TIMEOUT)

        Returns:
            bool: True if page loaded successfully

        Raises:
            TimeoutException: If map container or key elements are not visible in time
        """
        self.wait_until_page_ready([self.MAP_CONTAINER], timeout=timeout)
        self.log("Trip Planner page ready and overlays dismissed")
        return True

    def click_discover_card(self):
        self.click(self.DISCOVER_CARD_BTN, timeout=BasePage.NAVIGATION_TIMEOUT)

    def open_road_trip_modal(self):
        """
            Clicks the Discover Card button to open the Road Trip creation modal.

            Returns:
                RoadTripModal: Instance of the opened modal

            Raises:
                AssertionError: If modal does not open after click
        """
        self.click_discover_card()
        modal = self.road_trip_modal
        assert modal.is_open(), "Road Trip modal did not open"
        return modal

    def exit_page(self):
        """
           Attempts to exit the current trip/planner view by clicking the exit icon
           and confirming via the confirmation dialog.

           Handles menu opening, confirmation visibility, and clicking 'YES, EXIT'.
           Uses JS fallback if normal click fails.

           Raises:
               Exception: If menu or confirmation cannot be opened/confirmed
        """
        # Open Confirm Exit menu
        try:
            exit_icon = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.EXIT)
            )
            exit_icon.click()
            time.sleep(0.8)
            self.log("Exit menu opened")
        except Exception as e:
            self.log(f"Failed to open menu: {str(e)}", level="error")
            self.take_screenshot("exit_menu_open_failed")
            return False

        # Wait for menu list
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.CONFIRM_VIEW)
            )
            self.log("Confirm Menu list visible")
        except:
            self.log("Confirm Menu list not visible", level="error")
            return False

        # Click 'YES, EXIT' in menu
        try:
            delete_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable(self.CONFIRM_EXIT)
            )
            delete_btn.click()
            self.log("'YES, EXIT' clicked in menu")
        except Exception as e:
            self.log(f"'YES, EXIT' click failed: {str(e)} - trying JS", level="warn")
            try:
                btn = self.driver.find_element(*self.CONFIRM_EXIT)
                self.driver.execute_script("arguments[0].click();", btn)
                self.log("JS click on 'YES, EXIT' succeeded")
            except:
                self.log("All attempts failed", level="error")
                return False

    def assert_waypoint_names(self, expected_names: list[str]) -> None:
        """
        Assert that the visible waypoints in the itinerary match the expected names in order.

        Args:
            expected_names: List of strings with the exact waypoint names you expect,
                        in the order they should appear.

        Raises:
            AssertionError: If names do not match or count is wrong
           TimeoutException: If itinerary or waypoints are not found in time
    """
        self.log(f"Asserting waypoint names: {expected_names}")

        # Wait for the itinerary container to be visible
        WebDriverWait(self.driver, timeout = BasePage.INTERACTION_TIMEOUT).until(
            EC.visibility_of_element_located(self.ITINERARY_WAYPOINT_GROUP_LIST),
            message="Itinerary container not visible after timeout"
        )

        # Wait a moment for all waypoints to render
        time.sleep(1.5)

        # Find all waypoint primary labels

        waypoint_elements = WebDriverWait(self.driver, timeout=BasePage.INTERACTION_TIMEOUT).until(
            lambda d: d.find_elements(*self.WAYPOINT_NAME_LOCATOR)
        )

        if not waypoint_elements:
            raise AssertionError("No waypoint names found in the itinerary")

        # Extract visible text from each waypoint label
        actual_names = []
        for el in waypoint_elements:
            name = el.text.strip()
            if name:  # skip empty or hidden elements
                actual_names.append(name)

        # Normalize comparison (remove extra whitespace, case-insensitive if desired)
        actual_clean = [n.strip() for n in actual_names if n.strip()]
        expected_clean = [n.strip() for n in expected_names]

        assert actual_clean == expected_clean, (
            f"Waypoint names mismatch\n"
            f"Expected: {expected_clean}\n"
            f"Actual:   {actual_clean}"
        )

        self.log("Waypoint names assertion passed successfully")