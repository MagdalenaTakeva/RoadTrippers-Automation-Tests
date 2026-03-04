# fixtures/driver_fixtures.py

"""
Driver Fixtures Module
------------------------------------------------------------

Purpose:
    Provides Selenium WebDriver instances configured for:
    • Local development (visible Chrome)
    • CI execution (headless Chrome)

Key Design Principles:
    • Fresh browser per test (function scope)
    • No Selenium Grid dependency
    • CI-safe headless configuration
    • Parallel execution compatible (pytest-xdist)
    • Automatic screenshot capture on failure
    • Clean and quiet teardown

Environment Detection:
    CI mode is automatically enabled when:
        CI=true (set by CircleCI)

Usage:
    Any test requiring browser interaction should depend on:
        def test_example(driver):

"""

import os
import logging
import pytest

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager


# ------------------------------------------------------------
# Reduce noisy logs from Selenium / urllib3
# ------------------------------------------------------------
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ------------------------------------------------------------
# Primary WebDriver Fixture (Function Scope)
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def function_driver():
    """
    Provides a fresh Chrome WebDriver instance per test.

    Behavior:
        • Local → visible Chrome browser
        • CI → headless Chrome

    Why function scope?
        Ensures:
            - No session carry-over
            - No shared cookies
            - Parallel execution safety
            - Deterministic tests

    Returns:
        Selenium WebDriver instance
    """

    chrome_options = Options()

    # --------------------------------------------------------
    # Disable password manager & intrusive Chrome services
    # --------------------------------------------------------
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # --------------------------------------------------------
    # Common browser arguments (clean automation environment)
    # --------------------------------------------------------
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--guest")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # Detect CI environment
    is_ci = os.getenv("CI", "false").lower() in ("true", "1", "yes")

    if is_ci:
        # ----------------------------------------------------
        # CI Mode → Headless Chrome
        # ----------------------------------------------------
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

    else:
        # ----------------------------------------------------
        # Local Mode → Visible browser
        # ----------------------------------------------------
        chrome_options.add_argument("--start-maximized")

    # --------------------------------------------------------
    # Initialize WebDriver (local ChromeDriver)
    # webdriver-manager automatically installs compatible driver
    # --------------------------------------------------------
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # Attach default explicit wait timeout to driver instance
    driver.DEFAULT_WAIT_TIMEOUT = int(
        os.getenv("SELENIUM_TIMEOUT", "20" if is_ci else "15")
    )

    yield driver

    # --------------------------------------------------------
    # Teardown: Always attempt clean quit
    # --------------------------------------------------------
    try:
        driver.quit()
    except WebDriverException:
        # Ignore teardown failures (common if browser already closed)
        pass


# ------------------------------------------------------------
# Public Driver Alias (Used by Tests & Page Objects)
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def driver(function_driver):
    """
    Alias fixture for dependency clarity.

    Purpose:
        Acts as the entry point for page object fixtures and tests.

    Example:
        def test_homepage_loads(driver):

    Returns:
        Same WebDriver instance created by function_driver.
    """
    return function_driver


# ------------------------------------------------------------
# Screenshot Capture on Test Failure
# ------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Pytest hook that runs after each test phase.

    If a test fails during execution ("call" phase),
    and a driver fixture is present, a screenshot is saved.

    Screenshot location:
        screenshots/<test_name>.png

    This dramatically improves CI debugging capability.
    """

    outcome = yield
    report = outcome.get_result()

    # Only capture screenshot if test execution failed
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver", None)

        if driver:
            os.makedirs("screenshots", exist_ok=True)
            screenshot_path = f"screenshots/{item.name}.png"
            driver.save_screenshot(screenshot_path)