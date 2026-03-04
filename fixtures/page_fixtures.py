import pytest
from pages.home_page import HomePage
from pages.login_modal import LoginPage
from pages.my_trips_page import MyTripsPage
from pages.signup_modal import SignUpPage
from pages.trip_planner_page import TripPlannerPage
from factories.location_factory import LocationFactory
import time


# ======================================
# Web Page Object Fixtures
# ======================================

@pytest.fixture
def home_pg(driver):
    """
    Provides a fresh instance of the HomePage Page Object.

    This fixture creates and returns a HomePage object bound to the shared Selenium WebDriver instance.

    Scope:
        function (default) – new instance for each test

    Intended Use:
        Tests that interact with the landing page (search form, autocomplete, header links, popups)

    Dependencies:
        driver (pytest-selenium fixture): Shared WebDriver instance

    Returns:
        HomePage: Fully initialized HomePage object ready for navigation/interaction

    """
    return HomePage(driver)

@pytest.fixture(scope="function")
def authenticated_home(driver):
    """
    Provides a HomePage instance with the user already authenticated via cookies.

    This fixture:
        1. Creates HomePage object
        2. Navigates to the base URL
        3. Injects persisted session cookies to log in the user automatically

    Scope:
        function – fresh authenticated session per test (isolated)

    Intended Use:
        Tests requiring logged-in state without automating the login form
        (e.g. trip creation, profile, my trips, planner access)

    Dependencies:
        driver (pytest-selenium fixture): Shared WebDriver instance

    Returns:
        HomePage: Authenticated HomePage instance (user logged in)

    """
    home = HomePage(driver)
    home.navigate()
    home.login_via_cookies()
    return home

@pytest.fixture
def login_pg(driver):
    """
    Provides a LoginPage Page Object instance.

    This fixture supplies the login modal/page abstraction.
    Navigation to open the login modal must be handled by the test or a higher fixture.

    Scope:
        function (default)

    Intended Use:
        Tests that interact with the login form (valid/invalid credentials, forgot password, social login)

    Dependencies:
        driver (pytest-selenium fixture)

    Returns:
        LoginPage: LoginPage object ready for interaction

    """
    return LoginPage(driver)

@pytest.fixture
def login_modal(home_pg, login_pg):
    """
    Provides a LoginPage instance with the login modal already opened.

    This fixture abstracts the steps needed to:
        1. Load the home page
        2. Click the login trigger in the header

    Scope:
        function

    Intended Use:
        Login-related tests where the modal needs to be visible before interaction

    Dependencies:
        home_pg (HomePage fixture): Used to navigate and trigger login
        login_pg (LoginPage fixture): Returned with modal open

    Returns:
        LoginPage: LoginPage object with modal visible and ready

    """
    home_pg.navigate()
    home_pg.click_login_header_link()
    return login_pg

@pytest.fixture
def signup_pg(driver):
    """
    Provides a SignUpPage Page Object instance.

    This fixture supplies the signup modal abstraction.
    Opening the signup popup must be handled by the test or a higher fixture.

    Scope:
        function (default)

    Intended Use:
        Tests covering user registration flow (valid/invalid inputs, social signup, errors)

    Dependencies:
        driver (pytest-selenium fixture)

    Returns:
        SignUpPage: SignUpPage object ready for interaction

    """
    return SignUpPage(driver)


@pytest.fixture
def trip_planner_pg(driver):
    """
    Provides a TripPlannerPage Page Object instance.

    This fixture supplies the planner page abstraction.
    Navigation to the planner must be handled by the test or a higher fixture.

    Scope:
        function (default)

    Intended Use:
        Tests for trip creation, editing, adding stops, launching routes, itinerary verification

    Dependencies:
        driver (pytest-selenium fixture)

    Returns:
        TripPlannerPage: TripPlannerPage object ready for interaction

    """
    return TripPlannerPage(driver)

@pytest.fixture(scope="function")
def cleanup_trips(authenticated_home, login_pg, my_trips_pg):
    """
    Fixture to ensure a clean state with no existing trips before each test.

    This fixture performs cleanup by:
        1. Navigating directly to the user's My Trips page
        2. Checking for existing trips
        3. Deleting any found trips (free account allows only one)
        4. Taking screenshots at key steps for debugging

    Scope:
        function – runs before each test, ensures isolation

    Dependencies:
        authenticated_home: Provides logged-in HomePage
        login_pg: Used for navigation helpers
        my_trips_pg: Used for trip deletion and checks

    Yields:
        None – control passed to test with clean state

    Teardown:
        No explicit teardown (trips are left as deleted)

    Current behavior:
        - Forces navigation to avoid redirect issues
        - Uses 4-second sleep after force-nav for stability
        - Deletes only first trip (loop not used since free plan limit = 1)
        - Takes screenshots for manual verification

    Intended Use:
        All trip creation/editing tests to avoid "trip already exists" conflicts

    """

    # Step 1: Force open My trips page
    my_trips_pg.open_page("https://maps.roadtrippers.com/people/MagdalenaTakeva")
    time.sleep(4)  # give time for any redirect to happen or not
    my_trips_pg.take_screenshot(
        "cleanup_trips_fixture",
        "__after_force_nav__waited_4s"
    )

    # Step 2: Check if My trips page has saved trip. Only one can be saved with free account
    has_trips = my_trips_pg.has_trips()
    my_trips_pg.log(f"Has trips after forced nav: {has_trips}")

    authenticated_home.log(f"has_trips() returned: {has_trips} ===", level="info")
    my_trips_pg.take_screenshot(
        "cleanup_trips_fixture",
        "__after_has_trips"
    )

    # Step 3: If trips exist → delete them
    if has_trips:
        authenticated_home.log("Trips detected → starting deletion ===", level="info")
        success = my_trips_pg.delete_first_trip()
        authenticated_home.log(f"delete_first_trip() returned: {success} ===", level="info")
        my_trips_pg.take_screenshot(
            "cleanup_trips_fixture",
            "__after_delete"
        )
    else:
        authenticated_home.log("=== MANUAL DEBUG: No trips detected by has_trips() ===", level="warning")
        my_trips_pg.take_screenshot(
            "cleanup_trips_fixture",
            "__no_trips_detected"
        )

    yield  # ← Test runs here with clean state (no trips)

@pytest.fixture
def my_trips_pg(driver):
    """
    Provides a MyTripsPage Page Object instance.

    Scope:
        function (default)

    Intended Use:
        Tests that interact with saved trips, deletion, or navigation to planner

    Dependencies:
        driver (pytest-selenium fixture)

    Returns:
        MyTripsPage: MyTripsPage object ready for interaction

    """
    return MyTripsPage(driver)

@pytest.fixture
def loc_factory():
    """
    Provides access to the LocationFactory utility class.

    The LocationFactory generates deterministic or dynamic location data
    for trip planning scenarios (origins, destinations, stops).

    Scope:
        function (default)

    Intended Use:
        Supplying consistent test locations
        Data-driven trip creation tests
        Avoiding hard-coded strings in tests

    Returns:
        LocationFactory: Utility instance for generating location data

    """
    return LocationFactory
