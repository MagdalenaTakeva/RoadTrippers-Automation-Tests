import inspect
import os
import pickle
import time
from datetime import datetime
from typing import Optional, Union, Tuple
import base64

from PIL import Image
from urllib.parse import quote
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.support.select import Select

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException,
    ElementClickInterceptedException, ElementNotInteractableException,
    JavascriptException, WebDriverException, InvalidSessionIdException, InvalidCookieDomainException
)


class BasePage(object):
    """
    Base class for all Page Objects in the Roadtrippers test suite.

    Provides:
    - Common WebDriver utilities (waits, clicks, scrolling, logging)
    - Overlay handling (cookies, Gist, create account modals)
    - Screenshot capture on failure
    - Logging with test context (test name + page class)
    - Lazy-loaded header component
    - AJAX / page load waiting
    - Cookie-based login

    All page objects inherit from this class.

    Current behavior:
    - Uses tiered timeouts (NAVIGATION, DYNAMIC_CONTENT, INTERACTION, SHORT)
    - Aggressive overlay dismissal (polling + JS removal)
    - Robust stale element handling (retries in send_keys)
    - Defensive JS click fallback for intercepted clicks
    - Logs to both file (logs.log) and console

    Usage:
        class HomePage(BasePage):
            def __init__(self, driver):
                super().__init__(driver)
                # page-specific locators & init

    """
    # ── Timeout Tiers ─────────────────────────────────────
    DEFAULT_TIMEOUT = 15

    NAVIGATION_TIMEOUT = 30  # Full page load / navigation
    DYNAMIC_CONTENT_TIMEOUT = 20  # AJAX / dependent dropdowns / SPA refresh
    INTERACTION_TIMEOUT = 12  # Clicks, send_keys, visibility waits
    SHORT_TIMEOUT = 5  # Validation checks / quick state checks

    # ── Static Locators ─────────────────────────────────────
    COOKIE_ACCEPT_ALL = (By.ID, "onetrust-accept-btn-handler")
    GIST_IFRAME = (By.CSS_SELECTOR, "iframe.gist-message")
    GIST_DISMISS_BUTTON = (By.XPATH, "//button[contains(@onclick,'message.dismiss')]")
    CREATE_ACCOUNT_CLOSE = (
        By.CSS_SELECTOR,
        "button[data-sweetchuck-id='modal__button--close']",
    )

    CREATE_ACCOUNT_MODAL_CLOSE_OLD = (
        By.CSS_SELECTOR,
        "div.c1iayu8k.chcmyku > button"
    )

    @property
    def header(self):
        """
        Lazy-loaded HeaderComponent available on every page.

        Returns:
            HeaderComponent: Instance for header interactions (login, avatar, navigation)

        Note:
            Avoids circular imports by importing inside the property.
        """
        from components.header_component import HeaderComponent  # avoid circular import
        return HeaderComponent(self.driver, self)

    # ── TLogger Setup ─────────────────────────────────────

    # Create a logger instance named "BasePage" for this classto allow
    # unique logging identification across the application.
    _logger = logging.getLogger("BasePage")

    # Check if the logger already has handlers to avoid duplicate setup.
    if not _logger.hasHandlers():
        # Define the log file path using the current working directory.
        log_path = os.path.join(os.getcwd(), "logs.log")

        # Create a file handler to write logs to "logs.log".
        handler = logging.FileHandler(log_path)

        # Apply the formatter to the file handler for consistent log output.
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)

        # Add the file handler to the logger to enable file logging.
        _logger.addHandler(handler)

        # Set the logger level to DEBUG to capture all log levels.
        _logger.setLevel(logging.DEBUG)

        # Create a console handler to output logs to the terminal.
        console_handler = logging.StreamHandler()

        # Apply the same formatter to the console handler.
        console_handler.setFormatter(formatter)

        # Add the console handler to enable real-time log viewing.
        _logger.addHandler(console_handler)

    def __init__(self, driver):
        """
        Initialize BasePage with WebDriver instance.

        Args:
            driver: Selenium WebDriver instance

        Sets up:
        - self.driver
        - self.wait (default timeout)
        - Logs initialization
        """
        # Store WebDriver instance for page interactions.
        self.driver = driver
        self.wait = WebDriverWait(driver, self.DEFAULT_TIMEOUT)
        self.log("BasePage initialized", level="debug")

    # --- Logging Helper with Test Context ---
    def log(self, message: str, level: str = "debug") -> None:
        """
        Log a message with current test name and page class context.

        Args:
            message: Log message content
            level: Log level ("debug", "info", "warning", "error"). Default: "debug"

        Raises:
            ValueError: If invalid log level provided

        Note:
            Uses inspect to detect current test name (starts with "test_").
            Falls back to "UnknownTest" if not found.
        """
        # Fetch the current test name using the static method _get_current_test_name
        test_name = self._get_current_test_name()
        level = level.lower()
        log_methods = {
            "debug": self._logger.debug,
            "info": self._logger.info,
            "warning": self._logger.warning,
            "error": self._logger.error
        }

        if level not in log_methods:
            raise ValueError(
                f"Invalid log level: {level}. "
                f"Use 'debug', 'info', 'warning', or 'error'."
            )

        log_methods[level](f"[{test_name}] [{self.__class__.__name__}] {message}")

    @staticmethod
    def _get_current_test_name() -> str:
        """
        Inspect call stack to find current pytest test function name.

        Returns:
            str: Test name (e.g. "test_partial_start_selects_suggestion") or "UnknownTest"

        Note:
            Static method — does not depend on instance state.
        """
        for frame_info in inspect.stack():
            if frame_info.function.startswith("test_"):
                return frame_info.function
        return "UnknownTest"

    # --- Element Helpers ---
    def _find(self, locator: tuple[str, str], timeout: int = None) -> Optional[WebElement]:
        """
        Find a single element using locator, waiting for presence.

        Args:
            locator: (By strategy, value)
            timeout: Override default (uses INTERACTION_TIMEOUT)

        Returns:
            WebElement: Located element

        Raises:
            TimeoutException / NoSuchElementException: If not found in time
            Exception: Unexpected driver errors
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Finding element: {locator}", level="debug")
        try:
            return WebDriverWait(self.driver, effective_timeout).until(
                EC.presence_of_element_located(locator)
            )
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to find element {locator}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error finding element {locator}: {str(e)}", level="error")
            raise

    def _find_all(self, locator: tuple[str, str], timeout: int = None) -> list[WebElement]:

        """
        Find all elements matching locator, waiting for at least one.

        Args:
            locator: (By strategy, value)
            timeout: Override default (uses INTERACTION_TIMEOUT)

        Returns:
            list[WebElement]: Matching elements (may be empty if none found after wait)

        Raises:
            TimeoutException: If wait fails
            Exception: Unexpected errors
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Finding all elements: {locator}", level="debug")
        try:
            return WebDriverWait(self.driver, effective_timeout).until(EC.presence_of_all_elements_located(locator))
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to find all elements {locator}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error finding all elements {locator}: {str(e)}", level="error")
            raise

    def click(self, locator_or_element: tuple[str, str] | WebElement, timeout: int = None) -> None:
        """
        Click element (locator or WebElement) with scroll and fallback.

        Args:
            locator_or_element: Locator tuple or WebElement
            timeout: Override default (uses INTERACTION_TIMEOUT)

        Raises:
            TimeoutException / ElementClickInterceptedException / StaleElementReferenceException
            Exception: Unexpected errors
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Clicking element: {locator_or_element}", level="debug")
        try:
            element = (
                locator_or_element
                # If locator_or_element is already a WebElement, use it directly.
                # Otherwise, wait for the element to be clickable.
                if isinstance(locator_or_element, WebElement)
                else self.wait_for_element_to_be_clickable_with_timeout(locator_or_element, timeout=effective_timeout)
            )
            self.log(f"Element found and clickable: {locator_or_element}", level="debug")
            self.scroll_to_element(element, timeout=effective_timeout)
            element.click()
            self.log(f"Successfully clicked element {locator_or_element}", level="debug")
        except (TimeoutException, StaleElementReferenceException, ElementClickInterceptedException) as e:
            state = self._get_element_state(locator_or_element) if isinstance(locator_or_element, tuple) else "N/A"
            self.log(f"Failed to click element {locator_or_element}: {str(e)}. Element state: {state}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error clicking {locator_or_element}: {str(e)}", level="error")
            raise

    def _get_element_state(self, locator)-> dict | str:
        """
        Get diagnostic state of element (displayed, enabled, location, size).

        Args:
            locator: (By strategy, value)

        Returns:
            dict: State info or str error message ("Element not found", "Element stale", etc.)
        """
        try:
            element = self.driver.find_element(*locator)
            return {
                "displayed": element.is_displayed(),
                "enabled": element.is_enabled(),
                "location": element.location,
                "size": element.size
            }

        except NoSuchElementException:
            return "Element not found"

        except StaleElementReferenceException:
            return "Element stale"

        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def send_keys(self, locator: tuple[str, str], text, timeout: int = None, _retries: int = 2)-> None:
        """Send keys to an element using the provided locator, with automatic recovery from stale references.

        This method:
        1. Waits for the element to be clickable.
        2. Clears and sends keys.
        3. **If the element becomes stale (e.g. DOM refresh), it retries up to `_retries` times.**
        4. On each retry, **waits intelligently** for the element to re-appear in the DOM.

        This is critical for dynamic SPAs where fields are removed/re-added during form fill.

        Args:
            locator (tuple): Locator tuple (By strategy, value).
            text (str): Text to send to the element.
            timeout: Override default (uses INTERACTION_TIMEOUT)
            _retries (int): Number of retry attempts on stale element (internal, default=2)

        Raises:
            TimeoutException: If element not interactable within wait timeout.
            ElementNotInteractableException: If element cannot receive input.
            StaleElementReferenceException: Only after all retries are exhausted
            Exception: For unexpected errors (e.g. driver crash)

        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Sending keys to {locator}: {text}", level="debug")

        for attempt in range(_retries + 1):
            try:
                # Log attempt
                self.log(
                    f"Attempt {attempt + 1}/{_retries + 1} – sending keys to {locator}: {text}",
                    level="debug"
                )

                # 1. Wait for a *fresh* element to be clickable
                element = self.wait_for_element_to_be_clickable_with_timeout(locator, timeout=effective_timeout)

                # 2. Scroll and interact
                self.scroll_to_element(element, timeout=effective_timeout)
                element.clear()
                element.send_keys(text)

                # Success!
                self.log(f"Successfully sent keys to {locator}", level="debug")
                return

            except StaleElementReferenceException:
                # Element was detached from DOM — likely due to JS refresh
                if attempt == _retries:
                    self.log(
                        f"StaleElementReferenceException after {_retries + 1} attempts for {locator}",
                        level="error"
                    )
                    raise

                self.log(
                    f"Stale element on attempt {attempt + 1} – waiting for DOM to restore {locator}...",
                    level="warning"
                )

                # Smart wait: give the app up to 3s to re-create the element
                try:
                    self.wait_for_presence_of_element_located(locator, timeout=effective_timeout)
                    self.log(f"Element {locator} restored in DOM, retrying...", level="debug")
                except TimeoutException:
                    self.log(
                        f"Element {locator} not restored within 3s, proceeding to next retry...",
                        level="debug"
                    )
                # Continue to next attempt

            except (TimeoutException, ElementNotInteractableException) as e:
                # These are permanent failures — no point retrying
                self.log(f"Failed to send keys to {locator}: {e}", level="error")
                raise

            except Exception as e:
                # Catch-all for unexpected issues (e.g. driver crash)
                self.log(f"Unexpected error sending keys to {locator}: {e}", level="error")
                raise

    def get_text(self, locator: tuple[str, str], timeout: int = None) -> str:
        """ Get the text content of an element.

        What it does:
        Waits for visibility
        Returns normalized text

        Args:
            locator (tuple): Locator tuple (By strategy, value).
            timeout: Override default (uses INTERACTION_TIMEOUT)

        Returns:
            str: Cleaned text (whitespace normalized)

        Raises:
            TimeoutException: If the element is not visible within the timeout.
            NoSuchElementException: If the element is not found.
            Exception: For unexpected errors.

        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Getting text from {locator}", level="debug")
        try:
            element = self.wait_for_element_visibility(locator, timeout=effective_timeout)
            text = " ".join(element.text.split())  # normalize whitespace
            self.log(f"Retrieved text from {locator}: {text}", level="debug")
            return text
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to get text from {locator}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error getting text from {locator}: {str(e)}", level="error")
            raise

        # --- Utility Actions ---

    def scroll_to_element(self, element: WebElement, timeout: int = None) -> None:
        """
        Scroll element into view (centered) to make it visible, with a visibility check.

        Args:
            element (WebElement): The element to scroll to.
            timeout: Override default (uses INTERACTION_TIMEOUT)


        Raises:
            TimeoutException: If the element is not visible within the timeout.
            JavascriptException: If the scroll script fails.
            StaleElementReferenceException: If the element becomes stale during execution.
            Exception: For unexpected errors.

        Notes:
            - Uses WebDriverWait to ensure the element is visible before scrolling.
            - Executes JavaScript scrollIntoView to center the element in the viewport.
            - Logs visibility and scroll attempts for debugging.
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Scrolling to element {element}", level="debug")
        try:
            # Wait for the element to be visible
            self.wait_for_element_visibility(element, timeout=effective_timeout)
            self.log(f"Element {element} is visible", level="debug")

            # Scroll to the element
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            self.log(f"Successfully scrolled to element {element}", level="debug")

        except TimeoutException as e:
            self.log(
                f"Failed to scroll to element {element}: Element not visible within {effective_timeout}s: {str(e)}",
                level="error")
            self.take_screenshot(f"scroll_to_element_{id(element)}_timeout_error.png")
            raise
        except (JavascriptException, StaleElementReferenceException) as e:
            self.log(f"Failed to scroll to element {element}: {str(e)}", level="error")
            self.take_screenshot(f"scroll_to_element_{id(element)}_error.png")
            raise
        except Exception as e:
            self.log(f"Unexpected error scrolling to element {element}: {str(e)}", level="error")
            self.take_screenshot(f"scroll_to_element_{id(element)}_unexpected_error.png")
            raise

    def wait_for_element_to_be_displayed(self, locator, timeout: int = None) -> WebElement:
        """Waits for element to be displayed on the page based on provided locator and returns it.

        This method explicitly checks if an element is displayed (visible and non-zero size) using
        is_displayed(). It is useful for debugging visibility issues in CI environments.

        Args:
            locator: A tuple (By strategy, value)
            timeout: Override default (uses INTERACTION_TIMEOUT)

        Raises:
            TimeoutException: If element is not displayed within timeout.
            NoSuchElementException: If element not found.
            Exception: For other unexpected errors.
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Waiting for element {locator} to be displayed with timeout {effective_timeout}s", level="debug")
        try:
            def _displayed(driver):
                el = driver.find_element(*locator)
                return el if el.is_displayed() else False

            element = WebDriverWait(self.driver, effective_timeout).until(_displayed)

            self.log(f"Element {locator} is displayed", level="debug")
            return element
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to wait for element {locator} to be displayed: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error waiting for element {locator} to be displayed: {str(e)}", level="error")
            raise

    def hover_and_click(self, parent_locator, child_locator, timeout=None):
        """
        Hover over a parent menu item to reveal a dropdown/submenu, then click a child item.

        This method is designed for navigation menus where hovering is required to make submenu items visible and clickable.

        Handles common real-world issues:
        - Hover-triggered dropdowns / submenus
        - Animation / transition delays after hover
        - StaleElementReferenceException (DOM refresh after hover)
        - ElementClickInterceptedException (overlapping elements, spinners, animations)
        - Single retry on stale element

        Args:
            parent_locator: Locator tuple for the parent menu item (e.g. main nav link)
            child_locator: Locator tuple for the child submenu item to click
            timeout: Optional override for maximum wait time (default: NAVIGATION_TIMEOUT = 30s)

        Raises:
            TimeoutException: If parent or child is not found/visible/clickable within timeout
            StaleElementReferenceException: After retry attempt fails
            ElementClickInterceptedException: If fallback JS click also fails
            Exception: For unexpected driver or JavaScript errors

        Behavior notes:
            - Waits for parent visibility before hovering
            - Uses ActionChains for reliable hover
            - Waits for child to be clickable after hover
            - Falls back to JS click if normal click is intercepted
            - Retries once on stale element (common after hover triggers DOM change)
            - Takes screenshot on final failure (via caller or self.log)

        Example usage:
            self.hover_and_click(
                (By.CSS_SELECTOR, "a.nav-link[data-id='trip-planner']"),
                (By.CSS_SELECTOR, "#menu-item-85140 ul.sub-menu a[href*='maps.roadtrippers.com']")
            )
        """

        effective_timeout = timeout or self.NAVIGATION_TIMEOUT

        try:
            # Wait for parent
            parent = self.wait_for_element_visibility(
                parent_locator,
                timeout=effective_timeout
            )

            # Hover
            ActionChains(self.driver) \
                .move_to_element(parent) \
                .perform()

            # Wait for child to become clickable
            child = self.wait_for_element_to_be_clickable_with_timeout(
                child_locator,
                timeout=effective_timeout
            )

            try:
                child.click()
            except ElementClickInterceptedException:
                # Fallback JS click if animation overlay interferes
                self.log("Click intercepted — falling back to JS click", level="warning")
                self.js_click(child)

            self.log(f"Hovered and clicked submenu item: {child_locator}")

        except StaleElementReferenceException:
            self.log("Stale element detected during hover — retrying once", level="warning")

            # Retry once
            parent = self.wait_for_element_visibility(
                parent_locator,
                timeout=effective_timeout
            )
            ActionChains(self.driver) \
                .move_to_element(parent) \
                .perform()

            child = self.wait_for_element_to_be_clickable_with_timeout(
                child_locator,
                timeout=effective_timeout
            )
            child.click()

        except TimeoutException as e:
            self.log(
                f"Failed to hover/click submenu. "
                f"Parent: {parent_locator}, Child: {child_locator}",
                level="error"
            )
            raise e

    def open_page(self, url):
        """Navigate to the specified URL using the WebDriver.

        Args:
            url (str): The URL of the page to open (e.g., 'https://example.com'). Must be a valid URL string.

        Raises:
            WebDriverException: If the WebDriver fails to navigate to the URL (e.g., network issues, invalid driver state).
            Exception: For unexpected errors not covered by WebDriverException (e.g., runtime errors).

        Note:
            This method relies on the WebDriver instance (self.driver) being properly initialized.
            Successful navigation is logged at the 'debug' level, while failures are logged at the 'error' level.
        """
        self.log(f"Opening page: {url}", level="debug")
        try:
            self.driver.get(url)
            self.wait_until_page_loads_completely()
            self.log(f"Successfully opened page {url}", level="debug")
        except WebDriverException as e:
            self.log(f"Failed to open page {url}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error opening page {url}: {str(e)}", level="error")
            raise

    def take_screenshot(self, test_name, context=""):
        """The method attempts to save a screenshot, verify it with PIL.Image,
        and handle potential errors during file operations or image processing

        Args:
            test_name (str): Name of the test.
            context (str, optional): Additional context for the screenshot. Defaults to "".

        Returns:
            str: Path to the saved screenshot or None if failed.

        Raises:
            Exception: For file or image processing errors.
        """
        self.log(f"Taking screenshot for test {test_name} with context {context}", level="debug")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = os.path.join(os.getcwd(), "screenshots")
        try:
            os.makedirs(screenshot_dir, exist_ok=True)
            self.log(f"Created/verified directory: {screenshot_dir}", level="debug")
        except PermissionError as e:
            self.log(f"Permission denied creating directory {screenshot_dir}: {e}", level="error")
            return None
        base_test_name = os.path.splitext(test_name)[0]
        safe_test_name = quote(base_test_name, safe="").replace("%20", "_")  # Replace %20 with _
        filename = f"{safe_test_name}{context}{timestamp}.png"
        path = os.path.join(screenshot_dir, filename)
        self.log(f"Attempting to save screenshot to: {path}", level="debug")
        try:
            self.driver.save_screenshot(path)
            with Image.open(path) as img:
                img.verify()
                self.log(f"Screenshot verified at {path}", level="debug")
            with Image.open(path) as img:
                img.save(path, "PNG")
                self.log(f"Screenshot saved to {path} as valid PNG", level="debug")
            return path
        except Exception as e:
            self.log(f"Failed to save or validate screenshot at {path}: {e}", level="error")
            if os.path.exists(path):
                os.remove(path)
            return None

    def wait_for_element_to_be_clickable_with_timeout(self, locator: tuple[str, str],
                                                      timeout: int = None) -> WebElement:
        """
        Wait for an element to be both present and clickable (visible, enabled, non-overlapped), then return it.

        This is the preferred method for elements you intend to interact with (click, send_keys).

        Args:
            locator: Selenium locator tuple (e.g. (By.CSS_SELECTOR, ".submit-btn"))
            timeout: Optional override (defaults to INTERACTION_TIMEOUT = 12s)

        Returns:
            WebElement: The now-clickable element

        Raises:
            TimeoutException: Element not clickable within timeout
            NoSuchElementException: Element not found in DOM
            Exception: Unexpected driver or JavaScript errors

        Behavior:
            - Uses Selenium's EC.element_to_be_clickable (checks visibility + enabled + not obstructed)
            - Automatically scrolls element into view after wait
            - Logs attempts and success/failure
            - No retry logic (use send_keys/click for stale recovery)

        Example:
            submit_btn = self.wait_for_element_to_be_clickable_with_timeout((By.ID, "submit"))
            submit_btn.click()
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Waiting for element {locator} to be clickable with timeout {effective_timeout}s", level="debug")
        try:
            element = WebDriverWait(self.driver, effective_timeout).until(EC.element_to_be_clickable(locator))
            self.scroll_to_element(element, timeout=effective_timeout)
            self.log(f"Element {locator} is now clickable", level="debug")
            return element
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to wait for element {locator} to be clickable: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error waiting for element {locator}: {str(e)}", level="error")
            raise

    def wait_for_dynamic_element(self, locator: tuple[str, str], timeout: int = None) -> WebElement:
        """
        Wait for a dynamically loaded element to be present in DOM, then clickable.

        Useful for elements that appear after AJAX, animation, or SPA update.

        Args:
            locator: Selenium locator tuple
            timeout: Optional override (defaults to DYNAMIC_CONTENT_TIMEOUT = 20s)

        Returns:
            WebElement: The ready-to-interact element

        Raises:
            TimeoutException: Element not present or not clickable in time
            NoSuchElementException: Element never appears in DOM
            Exception: Unexpected errors

        Behavior:
            - Sequential waits: first presence, then clickability
            - Total wait can be up to ~2× timeout
            - Automatically scrolls into view after clickability confirmed
            - Logs each stage for debugging dynamic UI issues

        Note:
            Use this for elements that may take longer to appear (dropdowns, modals, lazy-loaded content).
            For simple static elements, prefer wait_for_element_to_be_clickable_with_timeout.
        """
        effective_timeout = timeout or self.DYNAMIC_CONTENT_TIMEOUT
        self.log(f"Waiting for dynamic element {locator} with timeout {effective_timeout}s", level="debug")
        try:
            WebDriverWait(self.driver, timeout=effective_timeout).until(EC.presence_of_element_located(locator))
            element = WebDriverWait(self.driver, timeout=effective_timeout).until(EC.element_to_be_clickable(locator))
            self.scroll_to_element(element, timeout=effective_timeout)
            self.log(f"Dynamic element {locator} is ready and clickable", level="debug")
            return element
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to wait for dynamic element {locator}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error waiting for dynamic element {locator}: {str(e)}", level="error")
            raise

    def wait_for_presence_of_element_located(self, locator, timeout: int = None):
        """
        Wait until an element is present in the DOM (not necessarily visible or clickable).

        Useful for:
        - Waiting for containers before searching inside them
        - Checking existence without caring about visibility

        Args:
            locator: Selenium locator tuple
            timeout: Optional override (defaults to DYNAMIC_CONTENT_TIMEOUT = 20s)

        Raises:
            TimeoutException: Element not present within timeout
            NoSuchElementException: Never found
            Exception: Unexpected errors

        Note:
            Does **not** check visibility or interactability — use wait_for_element_visibility() for that.
            Example use: wait for a modal container before waiting for its close button.
        """
        effective_timeout = timeout or self.DYNAMIC_CONTENT_TIMEOUT
        self.log(f"Waiting for presence of element {locator} with timeout {effective_timeout}s", level="debug")
        try:
            WebDriverWait(self.driver, timeout=effective_timeout).until(EC.presence_of_element_located(locator))
            self.log(f"Element {locator} is present", level="debug")
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to wait for presence of element {locator}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error waiting for presence of element {locator}: {str(e)}", level="error")
            raise

    def wait_for_element_visibility(self, locator: Union[Tuple[str, str], WebElement], timeout: int = None,
                                    parent: Optional[WebElement] = None) -> WebElement:
        """
        Wait until an element is visible (displayed and non-zero size).

        Supports:
        - Locator tuple or already-found WebElement
        - Optional parent element to scope search (e.g. inside modal)

        Args:
            locator: Locator tuple or WebElement
            timeout: Optional override (defaults to INTERACTION_TIMEOUT = 12s)
            parent: Optional parent WebElement (searches within it)

        Returns:
            WebElement: The now-visible element

        Raises:
            TimeoutException: Not visible within timeout
            NoSuchElementException / StaleElementReferenceException
            InvalidSessionIdException: Session lost
            Exception: Unexpected driver errors
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Waiting for element {locator} to be visible" + (f" within parent {parent}" if parent else ""),
                 level="debug")
        try:
            if isinstance(locator, WebElement):
                element = WebDriverWait(self.driver, effective_timeout).until(
                    EC.visibility_of(locator)
                )
            else:
                if parent:
                    element = WebDriverWait(self.driver, effective_timeout).until(
                        lambda driver: parent.find_element(*locator) if parent.find_element(
                            *locator).is_displayed() else False
                    )
                else:
                    element = WebDriverWait(self.driver, effective_timeout).until(
                        EC.visibility_of_element_located(locator)
                    )
            self.log(f"Element {locator} is visible", level="debug")
            return element
        except (TimeoutException, NoSuchElementException, StaleElementReferenceException,
                InvalidSessionIdException) as e:
            self.log(f"Error waiting for element {locator}: {str(e)}", level="error")
            try:
                if self.driver.session_id:
                    self.take_screenshot("wait_for_element_visibility_error.png")
            except Exception as se:
                self.log(f"Failed to capture screenshot: {str(se)}", level="error")
            raise

    def wait_for_element_invisibility(self, locator: WebElement | Tuple[str,str], timeout=None):
        """
        Wait until an element becomes invisible or is removed from the DOM.

        Useful for:
        - Waiting for modals/popups to close
        - Spinners/loaders to disappear
        - Confirmation that an element is gone after delete/action

        Args:
            locator: Locator tuple or WebElement
            timeout: Optional override (defaults to INTERACTION_TIMEOUT = 12s)

        Raises:
            TimeoutException: Element still visible after timeout
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        WebDriverWait(self.driver, effective_timeout).until(
            EC.invisibility_of_element_located(locator),
            message=f"Element {locator} did not become invisible within {effective_timeout}s"
        )

    def wait_until_page_loads_completely(self, timeout: int = None):
        """
        Wait for document.readyState to reach 'complete' (initial page load finished).

        Args:
            timeout: Optional override (defaults to NAVIGATION_TIMEOUT = 30s)

        Raises:
            TimeoutException: Page not complete within timeout
            Exception: JavaScript execution or driver errors

        Notes:
            - Checks document.readyState via JS
            - Does **not** wait for AJAX/fetch/XHR — use wait_for_ajax() for that
            - Useful after driver.get() or refresh()
        """
        effective_timeout = timeout or self.NAVIGATION_TIMEOUT
        self.log(f"Waiting for page to load completely with timeout {effective_timeout}s", level="debug")
        try:
            js = "return document.readyState == 'complete'"
            WebDriverWait(self.driver, effective_timeout).until(lambda driver: driver.execute_script(js))
            self.log("Page loaded completely.", level="debug")
        except TimeoutException as e:
            self.log(f"Timeout waiting for page to load: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error waiting for page load: {str(e)}", level="error")
            raise

    def select_dropdown_option(self, locator: tuple[str, str], visible_text: str, timeout: int = None):
        """
        Select an option from a <select> dropdown by its visible text.

        Args:
            locator: Locator tuple for the <select> element
            visible_text: Exact text of the <option> to select
            timeout: Optional override (defaults to INTERACTION_TIMEOUT = 12s)

        Raises:
            TimeoutException: Select not clickable in time
            NoSuchElementException: Option text not found
            Exception: Unexpected errors (e.g. not a select element)

        Behavior:
            - Waits for select to be clickable
            - Scrolls into view
            - Uses Selenium's Select class for reliable selection
            - Logs success/failure
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Selecting dropdown option {visible_text} at {locator}", level="debug")
        try:
            element = self.wait_for_element_to_be_clickable_with_timeout(locator, timeout=effective_timeout)
            self.scroll_to_element(element, timeout=effective_timeout)
            select = Select(element)
            select.select_by_visible_text(visible_text)
            self.log(f"Successfully selected dropdown option {visible_text}", level="debug")
        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to select dropdown option {visible_text} at {locator}: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error selecting dropdown option {visible_text}: {str(e)}", level="error")
            raise

    @property
    def current_url(self):
        """
        Get the current browser URL.

        Returns:
            str: The current URL.

        Raises:
            WebDriverException: If URL retrieval fails.
            Exception: For unexpected errors.

        Notes:
            Does not involve timeouts or page synchronization, as it directly retrieves the browser's current URL.
        """
        self.log("Retrieving current URL", level="debug")
        try:
            url = self.driver.current_url
            self.log(f"Current URL retrieved: {url}", level="debug")
            return url
        except WebDriverException as e:
            self.log(f"Failed to retrieve current URL: {str(e)}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error retrieving current URL: {str(e)}", level="error")
            raise

    def js_click(self, locator_or_element: Union[tuple[str, str], WebElement], timeout: Optional[int] = None) -> None:
        """
        Performs a JavaScript-based click on an element.

        This method is useful when:
        - Normal .click() fails due to overlays, z-index issues, animations, or non-interactable states
        - You want to replicate the exact behavior of execute_script("arguments[0].click()")
        - You're in a conservative refactoring phase and want minimal behavior change

        What it does:
        Waits for visibility
        Scrolls
        Executes JS click
        Defensive fallback interaction

        Args:
            locator_or_element: Either a locator tuple (By, value) or an already-found WebElement
            timeout:

        Raises:
            TimeoutException / NoSuchElementException: if element cannot be located
            JavascriptException: if the JS execution fails
            StaleElementReferenceException: if element becomes detached during process
            Exception: other unexpected driver issues

        Example:
            self.js_click(self.COOKIE_ACCEPT_ALL)
            self.js_click((By.CSS_SELECTOR, ".close-btn"), timeout=5)
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        self.log(f"Performing JS click on {locator_or_element}", level="debug")

        try:
            # Get the element (wait for visibility / presence)
            if isinstance(locator_or_element, tuple):
                element = self.wait_for_element_visibility(
                    locator_or_element,
                    timeout=effective_timeout
                )
            else:
                # Already have WebElement → just make sure it's still attached
                element = locator_or_element
                # Quick visibility check to avoid stale surprises
                WebDriverWait(self.driver, self.SHORT_TIMEOUT).until(
                    lambda d: element.is_displayed()
                )

            # Scroll into view (helps JS click reliability in many cases)
            self.scroll_to_element(element, timeout=effective_timeout)

            # Execute the JS click
            self.driver.execute_script("arguments[0].click();", element)
            self.log(f"JS click executed successfully on {locator_or_element}", level="debug")

        except (TimeoutException, NoSuchElementException) as e:
            self.log(f"Failed to locate element for JS click: {str(e)}", level="error")
            raise
        except JavascriptException as e:
            self.log(f"JavaScript click failed: {str(e)}", level="error")
            self.take_screenshot("js_click_javascript_failure.png")
            raise
        except StaleElementReferenceException as e:
            self.log(f"Stale element during JS click: {str(e)}", level="warning")
            raise
        except Exception as e:
            self.log(f"Unexpected error during JS click: {str(e)}", level="error")
            self.take_screenshot("js_click_unexpected_error.png")
            raise

    def is_visible(self,
                   locator: Union[Tuple[str, str], WebElement],
                   timeout: int = None
    ) -> bool:
        """
        Check if an element is visible (displayed and non-zero size) within the given timeout.

        Returns True if visible, False otherwise (timeout, not found, or error).

        Args:
            locator: Locator tuple or already-found WebElement
            timeout: Optional override (defaults to SHORT_TIMEOUT = 5s)

        Returns:
            bool: True if element is visible, False otherwise

        Raises:
            None — swallows exceptions and returns False for robustness

        Behavior:
            - Delegates to wait_for_element_visibility()
            - Short timeout by default for fast negative checks
            - Logs unexpected errors at warning level
            - Safe for use in assertions or conditional flows

        Example:
            if self.is_visible((By.ID, "signup")):
                self.log("Signup modal is visible")
        """
        effective_timeout = timeout or self.SHORT_TIMEOUT
        try:
            self.wait_for_element_visibility(locator, timeout=effective_timeout)
            return True
        except (TimeoutException, NoSuchElementException):
            return False
        except Exception as e:
            self.log(f"Unexpected error checking visibility of {locator}: {str(e)}", level="warning")
            return False

    def _try_dismiss_element(
        self,
        locator: tuple[str,str],
        context_name: str,
        timeout: int = 3
    ) -> bool:
        """
        Attempt to locate, verify visibility, and dismiss (click via js_click) a single overlay/close button.

        Returns True if the element was found visible and clicked, False otherwise.

        Args:
            locator: Locator tuple for the dismiss/close button
            context_name: Human-readable name for logging (e.g. "cookie consent banner")
            timeout: Short timeout for quick check (default 3s)

        Returns:
            bool: True if dismissal action was performed, False if not found/not visible

        Behavior:
            - Uses _find() for presence
            - Checks is_displayed() before click
            - Uses js_click() for reliability
            - Swallows most exceptions to continue overlay cleanup
        """
        try:
            element = self._find(locator, timeout=timeout)
            if element.is_displayed():
                self.js_click(element)
                self.log(f"Dismissed {context_name} via js_click", level="info")
                return True
            return False
        except (TimeoutException, NoSuchElementException):
            return False
        except Exception as e:
            self.log(f"Error dismissing {context_name}: {str(e)}", level="debug")
            return False


    def _try_dismiss_multiple_elements(
        self,
        locator: tuple[str,str],
        context_name: str,
        timeout: int = None,
        require_displayed: bool = True
    ) -> bool:
        """
        Attempt to locate multiple elements (e.g. dismiss buttons), check visibility if required,
        and dismiss each visible one via js_click.

        Returns True if at least one element was clicked/dismissed.

        Args:
            locator: Locator tuple for multiple matching elements
            context_name: Human-readable name for logging
            timeout: Override default (uses DYNAMIC_CONTENT_TIMEOUT)
            require_displayed: If True, only click visible elements (default True)

        Returns:
            bool: True if at least one dismissal occurred, False otherwise

        Behavior:
            - Uses _find_all() for presence
            - Checks is_displayed() per element if required
            - Uses js_click() for reliability
            - Swallows exceptions to continue cleanup
        """
        effective_timeout = timeout or self.DYNAMIC_CONTENT_TIMEOUT
        try:
            elements = self._find_all(locator, timeout = effective_timeout)
            if not elements:
                return False

            clicked_something = False
            for element in elements:
                if not require_displayed or element.is_displayed():
                    self.js_click(element)
                    self.log(f"Dismissed {context_name} via js_click", level="info")
                    clicked_something = True

            return clicked_something

        except (TimeoutException, NoSuchElementException):
            return False
        except Exception as e:
            self.log(f"Error while dismissing multiple {context_name}: {str(e)}", level="debug")
            return False

    def handle_overlays(self, max_wait: float = 15.0) -> None:
        """
        Aggressively dismiss known overlays (Gist/Customer.io iframes, create account/newsletter modals,
        OneTrust cookie consent banner, and associated Gist background layers) within the specified time limit.

        This method uses a polling loop with early exit when no progress is made in a round.
        It delegates specific overlay handling to private helper methods for clarity and maintainability.

        Args:
            max_wait: Maximum total time in seconds to keep polling (default: 15s).
                      Increased from earlier versions to accommodate slow-loading Gist/Customer.io overlays.

        Behavior:
            - Runs in short polling cycles (0.3s sleep between rounds)
            - Calls helper methods in sequence:
              - _dismiss_gist_iframes_and_background(): Gist iframes (dismiss buttons) + background JS removal
              - _dismiss_create_account_modal(): Create account/newsletter close buttons
              - _dismiss_cookie_banner(): OneTrust cookie accept button
            - Accumulates dismissal success across rounds
            - Exits early if a full round passes with no dismissals (prevents infinite polling)
            - Logs high-level progress and final outcome (info level on success, debug on no-op)
            - All detailed per-overlay logging and error handling occurs in the helpers

        Returns:
            None — side-effect method (modifies DOM by dismissing overlays)

        Raises:
            None — swallows exceptions in helpers to ensure loop continues; logs errors at debug level

        Notes:
            - Safe and idempotent — can be called after every navigation/action that might trigger popups
            - Designed to handle flaky overlays (slow load, re-appearing, non-interactable)
            - Uses short timeouts in helpers (2–4s) to keep polling responsive
            - If overlays persist beyond max_wait, method exits gracefully (no raise)
            - Recommended call sites: after driver.get(), refresh(), or any submit/login action

        Dependencies:
            - Relies on the following helpers:
              - _dismiss_gist_iframes_and_background()
              - _dismiss_create_account_modal()
              - _dismiss_cookie_banner()
            - Uses _try_dismiss_element() and _try_dismiss_multiple_elements() internally

        Example:
            self.handle_overlays()  # After page load to clear popups before interacting
        """
        self.log(f"handle_overlays started (max {max_wait}s)", level="debug")

        end_time = time.time() + max_wait
        any_dismissed = False

        while time.time() < end_time:
            this_round_dismissed = False

            # Handle all known overlay types
            this_round_dismissed |= self._dismiss_gist_iframes_and_background()
            # this_round_dismissed |= self._dismiss_create_account_modal()
            this_round_dismissed |= self._dismiss_cookie_banner()

            if not this_round_dismissed:
                self.log("No overlays dismissed this iteration — exiting loop", level="debug")
                break

            any_dismissed = True
            time.sleep(0.3)  # Give site time to settle / load new overlays

        status = "at least one overlay was dismissed" if any_dismissed else "no overlays were found"
        self.log(f"handle_overlays finished — {status}", level="info" if any_dismissed else "debug")

    def _dismiss_gist_iframes_and_background(self) -> bool:
        """
        Coordinate dismissal of Gist/Customer.io promo iframes and force-remove their background overlays.

        This helper is called repeatedly inside the polling loop of handle_overlays().
        It combines iframe button dismissal and background JS removal for efficiency.

        Returns:
            bool: True if **any** dismissal action succeeded (button click or JS remove), False otherwise.

        Behavior:
            - Delegates to _dismiss_gist_buttons_in_iframes() for content inside iframes
            - Delegates to _force_remove_gist_background() for overlay/background layers
            - Accumulates success using |= (short-circuit safe)
            - Does **not** retry — relies on outer loop polling
            - Logs only high-level outcome (detailed logs come from sub-methods)

        Note:
            Designed to be idempotent and safe to call multiple times.
            Gist/Customer.io overlays are particularly flaky → hence separate aggressive handling.
        """
        dismissed = False

        # Part A: Dismiss buttons inside matching iframes
        dismissed |= self._dismiss_gist_buttons_in_iframes()

        # Part B: Force-remove Gist overlay/background elements
        dismissed |= self._force_remove_gist_background()

        return dismissed

    def _dismiss_gist_buttons_in_iframes(self) -> bool:
        """
        Locate Gist/Customer.io iframes and attempt to click their dismiss buttons.

        Switches context into each matching iframe, tries to dismiss, then switches back.

        Returns:
            bool: True if at least one dismiss button was successfully clicked, False otherwise.

        Behavior:
            - Finds all <iframe> elements on page
            - Filters by class containing "gist-message" or "customerio"
            - Switches frame context, attempts multi-element dismiss
            - Always restores default content (even on error)
            - Uses short timeout (3s) per iframe to avoid hanging
            - Logs per-iframe errors but continues (robustness)

        Note:
            Gist iframes often load asynchronously → safe to call repeatedly.
            Uses _try_dismiss_multiple_elements() which handles visibility checks.
        """
        dismissed = False
        # iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
        iframes = self.driver.find_elements(By.CSS_SELECTOR, "iframe.gist-message, iframe.customerio")

        for iframe in iframes:
            try:
                iframe_class = iframe.get_attribute("class") or ""
                if "gist-message" not in iframe_class.lower() and "customerio" not in iframe_class.lower():
                    continue

                self.driver.switch_to.frame(iframe)
                try:
                    if self._try_dismiss_multiple_elements(
                            self.GIST_DISMISS_BUTTON,
                            context_name="Gist dismiss button inside iframe",
                            timeout=3
                    ):
                        dismissed = True
                        self.log("Dismissed Gist button inside iframe", level="info")
                finally:
                    self.driver.switch_to.default_content()

            except Exception as e:
                self.driver.switch_to.default_content()
                self.log(f"Error handling Gist iframe: {str(e)}", level="debug")

        return dismissed

    def _force_remove_gist_background(self) -> bool:
        """
        Force-remove Gist overlay wrapper (#gist-overlay) and background layers via JavaScript.

        Uses direct DOM manipulation because these elements are often non-interactable overlays.

        Returns:
            bool: True if at least one element was removed, False otherwise.

        Behavior:
            - Targets #gist-overlay first (main promo wrapper)
            - Then targets .gist-background / .gist-visible (semi-transparent layers)
            - Checks is_displayed() before removal
            - Applies JS remove() to bypass click/visibility restrictions
            - Adds 1-second pause after any removal to allow DOM settle
            - Catches all exceptions to prevent loop crash

        Note:
            Called repeatedly until gist_removed flag is set (in outer loop).
            Essential for stubborn overlays that ignore clicks.
        """
        dismissed = False

        try:
            # Remove main overlay wrapper
            for el in self.driver.find_elements(By.ID, "gist-overlay"):
                if el.is_displayed():
                    self.driver.execute_script("arguments[0].remove();", el)
                    dismissed = True
                    self.log("Removed Gist overlay wrapper (#gist-overlay)", level="info")

            # Remove semi-transparent background layers
            for el in self.driver.find_elements(By.CSS_SELECTOR, ".gist-background, .gist-visible"):
                if el.is_displayed():
                    self.driver.execute_script("arguments[0].remove();", el)
                    dismissed = True
                    self.log("Removed Gist background layer", level="info")

            if dismissed:
                time.sleep(1.0)  # Longer pause after removal — site may re-add

        except Exception as e:
            self.log(f"Error forcing Gist background removal: {str(e)}", level="debug")

        return dismissed

    def _dismiss_create_account_modal(self) -> bool:
        """
        Attempt to dismiss the create account / newsletter signup modal if present.

        Tries both current and legacy close button locators.

        Returns:
            bool: True if modal close button was found and clicked, False otherwise.

        Behavior:
            - Uses short timeout (5s) for quick check
            - Tries primary locator first, then fallback
            - Uses _try_dismiss_element() (visibility check + js_click)
            - Returns on first successful dismissal (no need to try second locator)
            - Logs success for traceability

        Note:
            Modal may appear after login/signup attempts or page load.
            Safe to call repeatedly — idempotent.
        """
        for loc in [self.CREATE_ACCOUNT_CLOSE, self.CREATE_ACCOUNT_MODAL_CLOSE_OLD]:
            if self._try_dismiss_element(
                    locator=loc,
                    context_name="create account modal close",
                    timeout=BasePage.SHORT_TIMEOUT
            ):
                self.log("Dismissed create account modal", level="info")
                return True
        return False

    def _dismiss_cookie_banner(self) -> bool:
        """
        Attempt to dismiss the OneTrust cookie consent banner if present.

        Returns:
            bool: True if cookie accept button was found and clicked, False otherwise.

        Behavior:
            - Uses short timeout (5s) for fast negative check
            - Delegates to _try_dismiss_element() for visibility + js_click
            - Logs success only (failure is silent — expected when banner gone)
            - Idempotent and safe to call in loop

        Note:
            Banner appears on first visit or after cookie expiry.
            OneTrust ID is stable: #onetrust-accept-btn-handler
        """
        if self._try_dismiss_element(
                locator=self.COOKIE_ACCEPT_ALL,
                context_name="cookie consent banner",
                timeout=BasePage.SHORT_TIMEOUT
        ):
            self.log("Dismissed cookie consent banner", level="info")
            return True
        return False

    def wait_until_page_ready(self, main_locators: list[Union[Tuple[str, str], WebElement]], timeout: int = None):
        """
        Wait until page is fully loaded AND all required main locators are visible,
        while aggressively dismissing overlays in each loop.

        Args:
            main_locators: List of locators (tuples or WebElements) that must be visible
            timeout: Max wait time (defaults to NAVIGATION_TIMEOUT = 30s)

        Raises:
            TimeoutException: Page/elements not ready within timeout

        Behavior:
            - Checks document.readyState == 'complete'
            - Calls handle_overlays() repeatedly
            - Verifies all main locators are visible
            - Early exit if no progress after multiple overlay attempts
            - Takes screenshot on timeout
        """
        effective_timeout = timeout or self.NAVIGATION_TIMEOUT
        self.log(
            f"wait_until_page_ready started (timeout={effective_timeout}s, watching {len(main_locators)} locators)",
            level="debug")

        end_time = time.time() + effective_timeout
        overlay_attempts = 0
        max_overlay_attempts = 4  # prevent infinite loop if overlays keep reappearing

        while time.time() < end_time:
            # 1. Check document ready state
            if self.driver.execute_script("return document.readyState") != "complete":
                self.log("Document not complete yet, waiting...", level="debug")
                time.sleep(0.4)
                continue

            # 2. Aggressive overlay dismissal (longer max_wait than before)
            self.handle_overlays(max_wait=5.0)  # increased from 1.2s — Gist needs time
            overlay_attempts += 1

            # 3. Check all required locators
            all_visible = True
            for loc in main_locators:
                if not self.is_visible(loc, timeout=2):  # short per-element timeout
                    self.log(f"Locator not visible yet: {loc}", level="debug")
                    all_visible = False
                    break

            if all_visible:
                self.log("Page ready condition met — all main locators visible", level="info")
                return

            # Early exit if no progress and overlays already heavily attempted
            if overlay_attempts >= max_overlay_attempts and not all_visible:
                self.log(f"Stopping early — overlays handled {overlay_attempts} times, but elements still not visible",
                         level="warning")
                break

            time.sleep(0.5)  # slightly longer — better balance

        # Timeout — take screenshot for debug
        self.take_screenshot("wait_until_page_ready_timeout")
        raise TimeoutException(f"Page did not become ready within {effective_timeout}s. "
                               f"Last checked locators: {main_locators}")

    def is_logged_in(self, expected_username: str = None) -> bool:
        """
        Check if user is logged in by looking for avatar/profile link in header.

        Optionally verifies the username in the href.

        Args:
            expected_username: Optional username to match against href

        Returns:
            bool: True if logged-in avatar is present (and username matches if provided)

        Behavior:
            - Waits for avatar link visibility
            - Checks href contains "/people/"
            - Extracts username from URL if expected_username given
            - Returns False on timeout or missing avatar
        """
        locator = (By.CSS_SELECTOR, ".rt-user-img a")

        try:
            link = self.wait_for_element_visibility(locator, timeout=self.SHORT_TIMEOUT)
            href = link.get_attribute("href") or ""

            if not href or "/people/" not in href:
                return False

            username = href.split("/people/")[-1].strip("/").lower()

            if expected_username:
                match = username == expected_username.lower()
                self.log(f"Login check — expected: {expected_username.lower()}, actual: {username}, match: {match}",
                         level="debug")
                return match

            self.log("Avatar link with /people/ found -> appears logged in", level="debug")
            return True

        except (TimeoutException, NoSuchElementException):
            self.log("No avatar link -> not logged in", level="debug")
            return False
        except Exception as e:
            self.log(f"is_logged_in error: {str(e)}", level="warning")
            return False

    def get_input_value(self, locator, timeout=None)-> str:
        """
        Get the current value attribute of an input/textarea element.

        Args:
            locator: Locator tuple for the input
            timeout: Optional override (defaults to INTERACTION_TIMEOUT = 12s)

        Returns:
            str: Stripped value attribute (or empty string on failure)

        Raises:
            TimeoutException / NoSuchElementException if wait fails
        """
        effective_timeout = timeout or self.INTERACTION_TIMEOUT
        element = self.wait_for_dynamic_element(locator, timeout=effective_timeout)
        return element.get_attribute("value").strip()

    def select_first_suggestion(
            self,
            suggestion_locator,
            input_locator,
            expected_text,
            timeout=None
    ):
        """
        Select the first visible autocomplete suggestion and verify input updated.

        Args:
            suggestion_locator: Locator for suggestion items
            input_locator: Locator for the input field
            expected_text: Original text typed (for comparison)
            timeout: Optional override (defaults to DYNAMIC_CONTENT_TIMEOUT = 20s)

        Raises:
            TimeoutException: No suggestions or input didn't update
        """
        effective_timeout = timeout or self.DYNAMIC_CONTENT_TIMEOUT

        suggestions = WebDriverWait(self.driver, effective_timeout).until(
            lambda d: [
                el for el in d.find_elements(*suggestion_locator)
                if el.is_displayed()
            ],
            message="No visible autocomplete suggestions found"
        )
        suggestions[0].click()

        WebDriverWait(self.driver, effective_timeout    ).until(
            lambda d: d.find_element(*input_locator)
                      .get_attribute("value")
                      .strip()
                      .lower() != expected_text.strip().lower(),
            message="Autocomplete selection did not update input value"
        )

    def wait_for_ajax(self, timeout: int = None) -> None:
        """
        Wait for all jQuery AJAX requests to complete (jQuery.active == 0).

        Args:
            timeout: Optional override (defaults to NAVIGATION_TIMEOUT = 30s)

        Raises:
            TimeoutException: AJAX not complete within timeout
            JavascriptException: JS execution failed
        """
        effective_timeout = timeout or self.NAVIGATION_TIMEOUT
        self.log(f"Waiting for AJAX completion (timeout={effective_timeout}s)", level="debug")

        try:
            # Check if jQuery exists
            jquery_present = self.driver.execute_script("return typeof jQuery !== 'undefined';")
            if jquery_present:
                WebDriverWait(self.driver, effective_timeout).until(
                    lambda driver: driver.execute_script("return jQuery.active === 0")
                )
                self.log("All AJAX requests completed.", level="debug")
            else:
                self.log("jQuery not detected — skipping AJAX wait.", level="warning")
        except TimeoutException as e:
            self.log(f"Timeout waiting for AJAX: {e}", level="error")
            raise
        except JavascriptException as e:
            self.log(f"JavaScript error while waiting for AJAX: {e}", level="error")
            raise
        except Exception as e:
            self.log(f"Unexpected error while waiting for AJAX: {e}", level="error")
            raise

    def wait_for_modal_close(
            self,
            modal_locator: tuple[str, str],
            spinner_locator: tuple[str, str] | None = None,
            timeout: int | None = None
    ) -> None:
        """
        Wait for a modal/popup to fully close after an action (e.g. submit/login).

        Handles:
        - Spinner disappearance (if provided)
        - AJAX completion
        - Modal invisibility
        - Optional page refresh for header sync

        Args:
            modal_locator: Locator for modal container (e.g. (By.ID, 'signup'))
            spinner_locator: Optional spinner locator inside modal/button
            timeout: Override default (uses NAVIGATION_TIMEOUT = 30s)

        Raises:
            TimeoutException: Modal/spinner not closed in time
        """
        effective_timeout = timeout or self.NAVIGATION_TIMEOUT

        self.log(f"Waiting for modal close: {modal_locator} (timeout={effective_timeout}s)", level="debug")

        try:
            # 1. Wait for spinner to disappear (if provided)
            if spinner_locator:
                self.log(f"Waiting for spinner invisibility: {spinner_locator}", level="debug")
                self.wait_for_element_invisibility(spinner_locator, timeout=effective_timeout)
                self.log("Spinner disappeared - submission likely processed", level="info")

            # 2. Wait for any ongoing AJAX / network requests to settle
            self.wait_for_ajax(timeout=effective_timeout)  # assuming you have this helper

            # 3. Wait for modal to become invisible (or detached)
            self.log(f"Waiting for modal invisibility: {modal_locator}", level="debug")
            self.wait_for_element_invisibility(modal_locator, timeout=effective_timeout)

            self.log("Modal successfully closed / invisible", level="info")

            # Optional small buffer + refresh for header/login sync
            time.sleep(1.5)
            try:
                self.driver.refresh()
                time.sleep(2)
                self.log("Refreshed page after modal close for header sync", level="debug")
            except Exception as e:
                self.log(f"Refresh after modal close failed: {e}", level="warning")

        except TimeoutException as e:
            self.log(f"Timeout waiting for modal to close: {str(e)}", level="error")
            self.take_screenshot("modal_close_timeout.png")
            raise

        except Exception as e:
            self.log(f"Unexpected error during modal close wait: {str(e)}", level="error")
            self.take_screenshot("modal_close_unexpected.png")
            raise

    def login_via_cookies(self, cookie_file="roadtrippers_cookies.pkl", timeout=20):
        """
        Authenticate by injecting previously saved cookies and refreshing the page.

        This method supports CI environments by automatically decoding cookies from the
        COOKIES_BASE64 environment variable if the cookie file does not exist locally.

        Args:
            cookie_file (str): Path to pickled cookies file (default: "roadtrippers_cookies.pkl").
            timeout (int): Maximum wait time in seconds for the logged-in avatar to appear (default: 20).

        Raises:
            TimeoutException: If the avatar element is not found after refreshing the page.
            InvalidCookieDomainException: If a cookie cannot be added due to domain mismatch.
            RuntimeError: If the cookie file is missing and COOKIES_BASE64 is not set.
            Exception: For other file or driver-related errors.

        Behavior:
            1. Ensures cookie file exists locally:
               - Uses local file if present.
               - If missing, decodes COOKIES_BASE64 from environment variable into cookie_file.
            2. Opens the Roadtrippers homepage.
            3. Injects all cookies into the current domain.
            4. Refreshes the page to activate the session.
            5. Waits for the user avatar as a logged-in indicator.
        """
        # Step 1 — Ensure cookie file exists
        if not os.path.exists(cookie_file):
            cookies_b64 = os.getenv("COOKIES_BASE64")
            if not cookies_b64:
                raise RuntimeError(
                    f"Cookie file '{cookie_file}' missing and COOKIES_BASE64 env variable not set. "
                    "Please save session locally or provide the env variable in CI."
                )
            # Decode base64 into cookie file
            with open(cookie_file, "wb") as f:
                f.write(base64.b64decode(cookies_b64))
            self.log(f"Decoded cookies from COOKIES_BASE64 into '{cookie_file}'", level="info")

        # Step 2 — Open site before injecting cookies
        self.log("Opening domain before injecting cookies", level="debug")
        self.driver.get("https://roadtrippers.com")

        # Step 3 — Load cookies
        with open(cookie_file, "rb") as f:
            cookies = pickle.load(f)

        self.log(f"Injecting {len(cookies)} cookies", level="debug")

        for cookie in cookies:
            # Selenium expects integer expiry
            if "expiry" in cookie:
                cookie["expiry"] = int(cookie["expiry"])
            try:
                self.driver.add_cookie(cookie)
            except InvalidCookieDomainException:
                self.log(f"Skipped cookie for domain mismatch: {cookie.get('domain')}", level="warning")
                continue

        # Step 4 — Refresh page to activate session
        self.log("Refreshing browser to activate session", level="debug")
        self.driver.refresh()

        # Step 5 — Wait for avatar (logged-in indicator)
        avatar_locator = (By.CSS_SELECTOR, ".rt-user-img [href*='/people']")
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located(avatar_locator)
        )

        self.log("Login via cookies successful", level="info")

    def get_attribute_value(self, locator) -> str:
        """
        Get the 'value' attribute of an input/textarea element.

        Args:
            locator: Locator tuple for the input

        Returns:
            str: Stripped value attribute (empty string on failure)

        Raises:
            NoSuchElementException / TimeoutException if wait fails
        """
        final_value = self.driver.find_element(*locator).get_attribute("value")
        return final_value