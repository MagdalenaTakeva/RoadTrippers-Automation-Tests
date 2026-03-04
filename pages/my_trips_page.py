import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from pages.base_page import BasePage


class MyTripsPage(BasePage):
    """
    Page Object for the My Trips / Profile page on Roadtrippers (maps.roadtrippers.com/people/<username>).

    Handles:
    - Checking for saved trips (has_trips)
    - Deleting individual trips (delete_first_trip) or all trips (delete_all_trips)
    - Navigating to Trip Planner
    - Interacting with trip cards, menus, and confirmation dialogs

    Current behavior:
    - Empty state shows "You don’t have any trips yet..." message
    - Trips displayed as cards with ellipsis menu → delete option
    - Deletion requires confirmation popup
    - Page may need refresh after delete for UI sync
    - Navigation to planner uses main menu link (direct click or hover fallback)

    """

    # Locators
    EMPTY_LIST_TEXT = (
        By.XPATH,
        "//div[@class='empty-list-view']//p[contains(text(), 'You don’t have any trips yet')]"
    )

    FIRST_TRIP_CARD = (By.CSS_SELECTOR, "section.rt-trip-card")

    FIRST_TRIP_MENU_BUTTON = (
        By.CSS_SELECTOR,
        "section.rt-trip-card .rt-menu > button"
    )

    FIRST_TRIP_MENU_LIST_VISIBLE = (
        By.CSS_SELECTOR,
        "section.rt-trip-card .rt-menu .rt-menu-list.visible"
    )

    DELETE_TRIP_BUTTON = (
        By.CSS_SELECTOR,
        "section.rt-trip-card .rt-menu .rt-menu-list.visible button.delete-trip"
    )

    CONFIRM_VIEW = (By.CSS_SELECTOR, ".confirm-view")

    CONFIRM_DELETE_BUTTON = (
        By.CSS_SELECTOR,
        ".confirm-view .new-button.default.large.red"
    )

    # Main navigation menu -> Trip Planner
    TRIP_PLANNER_NAV = (
        By.CSS_SELECTOR,
        "a.nav-link.js-route[data-id='trip-planner']"
    )

    TRIP_PLANNER_OPTION = (
        By.CSS_SELECTOR,
        "#menu-item-85140 ul.sub-menu a[href='https://maps.roadtrippers.com']"
    )

    CREATE_TRIP_BUTTON = (By.CSS_SELECTOR, ".create-trip.rt-button")

    TRIPS_TAB = (By.CSS_SELECTOR, "li.active a.js-route[href*='trips']")

    def has_trips(self) -> bool:
        """
        Check if there are any saved trips visible on the My Trips page.

        Returns:
            bool: True if at least one trip card is present, False if empty state message shown

        Current behavior:
            - Waits for preloader to disappear
            - Checks for empty message first (fast path)
            - Then looks for trip card elements

        Steps to reproduce manually:
            1. Log in → go to https://maps.roadtrippers.com/people/<username>
            2. If no trips: see "You don’t have any trips yet..." message
            3. If trips exist: see one or more trip cards with title, map preview, etc.

        Expected behavior:
            - Returns True if trip cards visible
            - Returns False if empty message present
            - No timeout crash

        """
        self.log("Checking for saved trips...")

        # Wait for preloader to disappear
        try:
            self.wait_for_element_invisibility(
                (By.CSS_SELECTOR, ".preloader-view"),
                timeout=BasePage.INTERACTION_TIMEOUT
            )
            time.sleep(0.6)  # small buffer for content to settle
        except TimeoutException:
            self.log("Preloader did not disappear in time - proceeding", level="warn")

        # Screenshot after preloader gone — shows initial page state
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_preloader__checking_trips"
        )

        # Check empty state message
        if len(self.driver.find_elements(*self.EMPTY_LIST_TEXT)) > 0:
            self.log("Empty trips message found → no trips")
            return False

        # Check for trip cards
        cards = self.driver.find_elements(*self.FIRST_TRIP_CARD)
        count = len(cards)
        self.log(f"Found {count} trip cards")
        # Screenshot when trips are present — shows cards before any action
        self.take_screenshot(
            self._get_current_test_name(),
            f"__has_trips_{count > 0}__found_{count}_cards"
        )
        return count > 0

    def delete_first_trip(self) -> bool:
        """
        Delete the first visible trip card on the page.

        Returns:
            bool: True if deletion succeeded (no trips remain after refresh), False otherwise

        Current behavior:
            - Opens ellipsis menu → clicks Delete
            - Handles confirmation popup (if appears)
            - Refreshes page to force UI sync
            - Re-checks has_trips() to confirm

        Steps to reproduce manually:
            1. Log in → go to My Trips page with at least one trip
            2. Click ellipsis (...) on first trip card
            3. Click "Delete trip" in menu
            4. Confirm in popup (if shown)
            5. Page refreshes → trip card gone

        Expected behavior:
            - Menu opens and Delete clicked
            - Confirmation handled or skipped
            - After refresh: no trip cards remain
            - Returns True on success

        """
        if not self.has_trips():
            self.log("No trips to delete.")
            return False

        self.log("Starting deletion of first trip...")

        # Ensure no preloader
        try:
            self.wait_for_element_invisibility(
                (By.CSS_SELECTOR, ".preloader-view"),
                timeout=BasePage.INTERACTION_TIMEOUT
            )
        except:
            pass

        # Screenshot before any action — baseline state with trip visible
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_delete__trip_visible"
        )

        # Open ellipsis menu
        try:
            menu_btn = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.FIRST_TRIP_MENU_BUTTON)
            )
            menu_btn.click()
            time.sleep(0.8)
            self.log("Ellipsis menu opened")
            # Screenshot after menu open — confirms menu appeared
            self.take_screenshot(
                self._get_current_test_name(),
                "__ellipsis_menu_opened"
            )
        except Exception as e:
            self.log(f"Failed to open menu: {str(e)}", level="error")
            self.take_screenshot(
                self._get_current_test_name(),
                "__menu_open_failed"
            )
            return False

        # Wait for menu list
        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(self.FIRST_TRIP_MENU_LIST_VISIBLE)
            )
            self.log("Menu list visible")
        except:
            self.log("Menu list not visible", level="error")
            return False

        # Click Delete Trip in menu
        try:
            delete_btn = WebDriverWait(self.driver, 8).until(
                EC.element_to_be_clickable(self.DELETE_TRIP_BUTTON)
            )
            delete_btn.click()
            self.log("Delete Trip clicked in menu")
            # Screenshot after delete click — before confirmation
            self.take_screenshot(
                self._get_current_test_name(),
                "__delete_clicked_in_menu"
            )
        except Exception as e:
            self.log(f"Delete menu click failed: {str(e)} - trying JS", level="warn")
            try:
                btn = self.driver.find_element(*self.DELETE_TRIP_BUTTON)
                self.driver.execute_script("arguments[0].click();", btn)
                self.log("JS click on Delete Trip succeeded")
                self.take_screenshot(
                    self._get_current_test_name(),
                    "__delete_js_click_success"
                )
            except:
                self.log("All delete attempts failed", level="error")
                self.take_screenshot(
                    self._get_current_test_name(),
                    "__delete_all_attempts_failed"
                )
                return False

        # Handle confirmation popup
        try:
            WebDriverWait(self.driver, 8).until(
                EC.visibility_of_element_located(self.CONFIRM_VIEW)
            )
            self.log("Confirmation popup appeared")

            # Screenshot when confirmation appears — key debug point
            self.take_screenshot(
                self._get_current_test_name(),
                "__confirmation_popup_visible"
            )

            confirm_btn = WebDriverWait(self.driver, 6).until(
                EC.element_to_be_clickable(self.CONFIRM_DELETE_BUTTON)
            )
            confirm_btn.click()
            self.log("Clicked 'Delete' in confirmation popup")
            time.sleep(1.5)
            # Screenshot after confirm click
            self.take_screenshot(
                self._get_current_test_name(),
                "__after_confirm_delete"
            )
        except TimeoutException:
            self.log("No confirmation popup appeared - assuming direct delete")
        except Exception as e:
            self.log(f"Confirmation handling failed: {str(e)}", level="warn")
            self.take_screenshot(
                self._get_current_test_name(),
                "__confirmation_handling_failed"
            )

        # Refresh and verify deletion
        self.log("Refreshing page to force UI sync after delete")
        self.driver.refresh()
        time.sleep(4)

        # Screenshot after refresh — final state check
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_refresh_post_delete"
        )

        if not self.has_trips():
            self.log("No trips remaining after refresh → deletion successful")
            return True
        else:
            self.log("Trip card still present after delete + refresh", level="error")
            self.take_screenshot(
                self._get_current_test_name(),
                "__delete_failed_final__trip_still_present"
            )
            return False

    def delete_all_trips(self) -> None:
        """
        Delete all visible saved trips in a loop until none remain.

        Useful for cleanup in free plan (limited to one trip) or before tests.

        Current behavior:
            - Calls delete_first_trip() repeatedly
            - Stops on failure or when no trips left
            - Small delay between deletions for stability

        Steps to reproduce manually:
            1. Go to My Trips with multiple trips
            2. Delete first trip → page refreshes → repeat until empty

        Expected behavior:
            - All trips removed (has_trips() becomes False)
            - No infinite loop or crash

        """
        while self.has_trips():
            self.log("Deleting one trip...")
            success = self.delete_first_trip()
            if not success:
                self.log("Deletion failed - stopping loop", level="error")
                self.take_screenshot(
                    self._get_current_test_name(),
                    "__delete_all_failed_at_trip"
                )
                break
            time.sleep(1.5)  # small pause between deletions

        # Final screenshot after loop — confirms empty state
        self.take_screenshot(
            self._get_current_test_name(),
            "__delete_all_complete__final_state"
        )

    def go_to_trip_planner_page(self, use_hover: bool = False) -> None:
        """
        Navigate from My Trips page to the Trip Planner page via main navigation menu.

        Args:
            use_hover: If True, use hover to open submenu before clicking (fallback)

        Current behavior:
            - Prefers direct click on main link
            - Falls back to hover + submenu click if direct fails
            - Waits for AJAX after click

        Steps to reproduce manually:
            1. Go to My Trips page
            2. Click "Trip Planner" in main nav (or hover → select from submenu)
            3. Observe redirect to maps.roadtrippers.com

        Expected behavior:
            - Redirects to planner page
            - No crash or stuck state

        """
        self.log("Navigating to Trip Planner...")
        # Screenshot before navigation — shows current My Trips state
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_nav_to_planner"
        )

        if use_hover:
            self.hover_and_click(self.TRIP_PLANNER_NAV, self.TRIP_PLANNER_OPTION)
        else:
            try:
                self.click(self.TRIP_PLANNER_NAV)
                self.wait_for_ajax(timeout=BasePage.NAVIGATION_TIMEOUT)
            except Exception as e:
                self.log(f"Direct click failed: {str(e)} - trying hover fallback", level="warning")
                self.hover_and_click(self.TRIP_PLANNER_NAV, self.TRIP_PLANNER_OPTION)

        # Screenshot after navigation attempt — confirms redirect
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_nav_to_planner"
        )

    def click_create_trip_button(self) -> None:
        """
        Click the "Create Trip" button if visible on the page.

        Raises:
            TimeoutException: If button not clickable in time

        """
        # Screenshot before click — shows button state
        self.take_screenshot(
            self._get_current_test_name(),
            "__before_click_create_trip"
        )
        self.click(self.CREATE_TRIP_BUTTON, timeout=BasePage.INTERACTION_TIMEOUT)
        self.log("Create Trip button clicked")

        # Screenshot after click — captures modal open or action
        self.take_screenshot(
            self._get_current_test_name(),
            "__after_click_create_trip"
        )

    def click_trips_tab(self) -> None:
        """
        Click the "Trips" tab to force refresh or switch to trips view.

        Current behavior:
            - Targets active tab link
            - Logs debug if not found/clickable

        """
        try:
            # Screenshot before tab click
            self.take_screenshot(
                self._get_current_test_name(),
                "__before_click_trips_tab"
            )

            self.click(self.TRIPS_TAB, timeout=BasePage.INTERACTION_TIMEOUT)
            self.log("Trips tab clicked")

            # Screenshot after tab click
            self.take_screenshot(
                self._get_current_test_name(),
                "__after_click_trips_tab"
            )
        except Exception as e:
            self.log(f"Could not click Trips tab: {str(e)}", level="debug")