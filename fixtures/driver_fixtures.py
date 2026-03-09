"""
Driver Fixtures Module
------------------------------------------------------------

Purpose:
    Provides isolated Selenium WebDriver instances for each test function.
    Ensures:
    • Fresh browser session per test (no state leakage)
    • Parallel execution safety (pytest-xdist compatible)
    • CI-friendly headless mode
    • Local visible browser for debugging
    • Automatic screenshot capture on failure

Key Design Choices:
    • function scope → maximum isolation (no shared cookies/state)
    • webdriver-manager → auto-downloads compatible ChromeDriver
    • No Selenium Grid → simplifies CI (no extra services)
    • CI detection via env var "CI=true" (set by CircleCI)
    • Screenshot hook → saves image on any test failure (call phase)

Usage in tests:
    def test_example(driver):  # ← injects fresh Chrome instance
        driver.get("https://maps.roadtrippers.com")
        ...

Teardown:
    • Always attempts driver.quit() (ignores if already closed)
    • Saves screenshot if test failed
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
# Suppress noisy logs from Selenium & urllib3
# (prevents console spam in CI and local runs)
# ------------------------------------------------------------
logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


# ------------------------------------------------------------
# Primary WebDriver Fixture – fresh browser per test
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def function_driver():
    chrome_options = Options()

    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "profile.password_manager_leak_detection": False,
    }

    chrome_options.add_experimental_option("prefs", prefs)

    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-infobars")
    chrome_options.add_argument("--guest")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--window-size=1920,1080")

    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    is_ci = os.getenv("CI", "false").lower() in ("true", "1", "yes")

    if is_ci:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        chrome_options.add_argument("--use-angle=gl")
        chrome_options.add_argument("--use-gl=angle")
        chrome_options.add_argument("--enable-webgl")
        chrome_options.add_argument("--ignore-gpu-blocklist")

        chrome_options.add_argument("--disable-features=UseSkiaGraphite")
        chrome_options.add_argument("--disable-gpu-driver-bug-workarounds")

        chrome_options.add_argument("--use-gl=swiftshader")

        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        )

    else:
        chrome_options.add_argument("--start-maximized")

    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.DEFAULT_WAIT_TIMEOUT = int(
        os.getenv("SELENIUM_TIMEOUT", "45" if is_ci else "15")
    )

    yield driver

    try:
        driver.quit()
    except WebDriverException:
        pass


# ------------------------------------------------------------
# Public alias fixture (used in tests & page objects)
# ------------------------------------------------------------
@pytest.fixture(scope="function")
def driver(function_driver):
    """
    Simple alias to make dependency injection clearer.

    Example:
        def test_homepage(driver):
            driver.get("https://roadtrippers.com")

    Returns:
        Same WebDriver from function_driver fixture
    """
    return function_driver


# ------------------------------------------------------------
# Automatic Screenshot on Failure (pytest hook)
# ------------------------------------------------------------
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Pytest hook: Runs after each test phase (setup/call/teardown).

    If the test fails during execution ("call" phase),
    and the test uses the 'driver' fixture,
    saves a screenshot named after the test.

    Screenshot location: screenshots/<test_name>.png

    Why this is powerful:
        • Immediate visual proof of failure state
        • Essential for CI debugging (download from artifacts)
        • No need to add screenshot code in every test
    """

    outcome = yield
    report = outcome.get_result()

    # Only capture on execution failure (not setup/teardown)
    if report.when == "call" and report.failed:
        driver = item.funcargs.get("driver", None)

        if driver:
            # Ensure screenshots folder exists
            os.makedirs("screenshots", exist_ok=True)

            # Use test node name as filename (safe, unique)
            screenshot_path = f"screenshots/{item.name}.png"

            try:
                driver.save_screenshot(screenshot_path)
                print(f"Screenshot saved: {screenshot_path}")
            except Exception as e:
                print(f"Failed to save screenshot: {e}")