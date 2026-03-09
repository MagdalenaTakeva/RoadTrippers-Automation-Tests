import pytest

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.trip_planner
@pytest.mark.auth
def test_trip_planner_page_load(authenticated_home, stabilize_map, login_pg, trip_planner_pg):
    """
       Positive: After login, navigating to the Trip Planner page should load successfully.

       Current behavior:
       - Logged-in user clicks 'Plan Your Trip' (direct or via hover/submenu)
       - Page redirects to https://maps.roadtrippers.com/
       - Main planner UI (discover card, map, search inputs) becomes visible

       Steps to reproduce manually:
       1. Log in to https://roadtrippers.com
       2. Hover over or click 'Plan Your Trip' in the main navigation
       3. Click 'Trip Planner' option (or direct link)
       4. Observe redirect to maps.roadtrippers.com
       5. Discover card and map area are visible

       Expected behavior:
       - Trip Planner page loads without errors
       - is_loaded() returns True (checks for key elements like map or discover card)
       - No redirect loop or blank page

    """
    login_pg.go_to_trip_planner_page(use_hover=True)
    assert trip_planner_pg.is_loaded(), "Trip Planner page did not load correctly"

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.trip_planner
@pytest.mark.auth
def test_create_quick_launch_trip(my_trips_pg, stabilize_map, trip_planner_pg, cleanup_trips):
    """
        Positive: Creating a trip using Quick Launch mode should succeed
        and close the creation modal.

        Current behavior:
        - Open modal → enter origin ("Ca") and destination ("New")
        - Select Quick Launch → modal closes
        - Trip is created and user is redirected to planner/itinerary view

        Steps to reproduce manually:
        1. Log in → go to Trip Planner (maps.roadtrippers.com)
        2. Click Discover card or "Start a new trip"
        3. In modal: enter "Ca" as start, "New" as end
        4. Choose Quick Launch option
        5. Click Create/Launch → modal closes, trip loads in planner

        Expected behavior:
        - Modal closes successfully (is_open() returns False)
        - No crash or validation error
        - Trip appears in planner view

    """

    # Step 1: Go to trip planner page
    my_trips_pg.go_to_trip_planner_page()

    # Step 2: Create a trip using quick_launch
    road_trip_modal = trip_planner_pg.open_road_trip_modal()
    # Set origin, destination, quick_launch, start date, end date
    road_trip_modal.create_trip("Ca", "New", "quick_launch")

    # Assert road_trip_modal is closed
    assert not road_trip_modal.is_open(), "Trip creation modal did not close"

@pytest.mark.regression
@pytest.mark.trip_planner
@pytest.mark.auth
def test_create_autopilot_trip(my_trips_pg, stabilize_map, trip_planner_pg, cleanup_trips):
    """
       Positive end-to-end: Creating a trip using Autopilot mode should succeed,
       close the modal, and redirect to the autopilot view or planner.

       Current behavior:
       - Open modal → enter origin/destination → select Autopilot
       - Modal closes → user may land on autopilot page or planner
       - If on autopilot page, exit returns to main planner map

       Steps to reproduce manually:
       1. Log in → go to Trip Planner
       2. Open modal → enter "Ca" start, "New" end
       3. Select Autopilot mode → click Create
       4. Modal closes → observe redirect to autopilot flow or planner
       5. If on autopilot page, click Exit → return to maps.roadtrippers.com

       Expected behavior:
       - Modal closes successfully
       - If redirected to autopilot, exit brings user back to main planner map
       - URL contains "https://maps.roadtrippers.com/" after exit

    """

    # Step 1: Go to trip planner page
    my_trips_pg.go_to_trip_planner_page()

    # Step 2: Create a trip using autopilot
    road_trip_modal = trip_planner_pg.open_road_trip_modal()
    # Set origin, destination, autopilot, start date, end date
    road_trip_modal.create_trip("Ca", "New", "autopilot")

    # Assert road_trip_modal is closed
    assert not road_trip_modal.is_open(), "Trip creation modal did not close"

    # if redirected to autopilot page click exit and assert user is redirected to maps page
    if "autopilot" in trip_planner_pg.current_url:
        trip_planner_pg.exit_page()
    assert "https://maps.roadtrippers.com/" in trip_planner_pg.current_url

@pytest.mark.regression
@pytest.mark.trip_planner
@pytest.mark.auth
def test_discover_card_navigation(function_driver, stabilize_map, authenticated_home, login_pg, trip_planner_pg):
    """
       Positive: Clicking the Discover Card on the Trip Planner page
       should open the road trip creation modal.

       Current behavior:
       - Logged-in user on planner → Discover Card button is visible
       - Click → modal opens with origin/destination/date options

       Steps to reproduce manually:
       1. Log in → go to Trip Planner (maps.roadtrippers.com)
       2. Locate the Discover Card or "Start a new trip" button
       3. Click it → observe modal popup with trip creation fields

       Expected behavior:
       - Planner page is fully loaded (is_loaded() True)
       - Modal opens successfully (is_open() True)
       - No crash or redirect away from modal

    """
    login_pg.go_to_trip_planner_page()

    assert trip_planner_pg.is_loaded(), "Trip Planner page not ready"

    # Click discover card
    road_trip_modal = trip_planner_pg.open_road_trip_modal()

    # Verify modal opened
    assert road_trip_modal.is_open(), "Discover Card modal did not open"


