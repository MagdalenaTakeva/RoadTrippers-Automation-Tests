import pytest

@pytest.mark.regression
@pytest.mark.add_stops
@pytest.mark.trip_planner
@pytest.mark.limit
@pytest.mark.auth
def test_cannot_add_more_than_15_stops(
    my_trips_pg,
    stabilize_map,
    trip_planner_pg,
    cleanup_trips

):
    """
       Negative / limit test: The application should prevent adding more than 15 stops
       in the Add Stops flow (free plan / current limit).

       Current behavior:
       - Up to 15 stops can be added (start + destination + 13 extra stops)
       - When limit is reached, input is disabled or a message appears:
         "You can add up to 15 stops for now. You'll have the option to add more later."
       - Attempting to add a 16th stop fails gracefully (no crash, count stays 15)

       Steps to reproduce manually:
       1. Log in and go to Trip Planner (https://maps.roadtrippers.com)
       2. Open modal → create new trip (quick launch or autopilot)
       3. Go to Add Stops page
       4. Add 13 extra stops (total 15 including start + destination)
       5. Try adding one more → observe input disabled or limit message appears
       6. Stop count remains 15

       Expected behavior:
       - Stop count reaches exactly 15
       - Limit message is visible ("You can add up to 15 stops for now...")
       - No crash or unexpected behavior

    """
    my_trips_pg.go_to_trip_planner_page()
    assert trip_planner_pg.is_loaded()

    road_trip_modal = trip_planner_pg.open_road_trip_modal()
    road_trip_modal.create_trip("Ca", "New", "quick_launch")

    add_stops = trip_planner_pg.add_stops_page

    stops = [
        "Ohio", "Chicago", "Denver", "Las Vegas",
        "Phoenix", "Dallas", "Atlanta", "Miami",
        "Seattle", "Boston", "Nashville", "Austin",
        "Orlando",
    ]

    # Add stops until limit
    for stop in stops:
        current_count = add_stops.get_stop_count()

        if current_count < 15:
            add_stops.add_stop(stop)
            new_count = add_stops.get_stop_count()
            assert new_count == current_count + 1
        else:
            break

    # Ensure we reached max
    assert add_stops.get_stop_count() == 15

    # Assert that when total stops count = 15 message appears:
    # "You can add up to 15 stops for now. You'll have the option to add more later."
    assert add_stops.get_stop_count() == 15

    # Assert
    assert "You can add up to 15 stops for now." in add_stops.get_stops_limit_text()

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.add_stops
@pytest.mark.trip_planner
@pytest.mark.auth
def test_add_stop(my_trips_pg, stabilize_map, trip_planner_pg, cleanup_trips):
    """
        Positive: Adding a single stop to a newly created trip should succeed
        and update the stop count and waypoint list correctly.

        Current behavior:
        - Create trip → Add Stops page opens
        - Add one stop (e.g. "Oh") → count becomes 3 (start + added + destination)
        - Waypoint "Ohio, US" appears in the list

        Steps to reproduce manually:
        1. Log in → go to Trip Planner
        2. Open modal → create new trip (quick launch)
        3. Go to Add Stops
        4. Type "Oh" → select "Ohio, US" from suggestions
        5. Observe: stop count = 3, "Ohio, US" visible in itinerary

        Expected behavior:
        - Stop count increases to 3 (start + 1 added + destination)
        - Waypoint list contains "Ohio,US" (or normalized version)
        - No crash or validation error

        """

    # Go to Trip planner page
    my_trips_pg.go_to_trip_planner_page()

    # Click on the Discover card
    road_trip_modal = trip_planner_pg.open_road_trip_modal()
    # Create trip
    road_trip_modal.create_trip("Ca", "New", "quick_launch")

    # Add stop
    add_stops = trip_planner_pg.add_stops_page
    add_stops.add_stop("Oh")

    # Assert total stops count = 3 (start + added stop + destination)
    assert add_stops.get_stop_count() == 3
    # Assert Ohio,US is among the stops
    assert add_stops.has_waypoint("Ohio,US")

@pytest.mark.smoke
@pytest.mark.regression
@pytest.mark.add_stops
@pytest.mark.trip_planner
@pytest.mark.auth
def test_happy_path_trip_creation(my_trips_pg, stabilize_map, trip_planner_pg, cleanup_trips):
    """
       Positive end-to-end: Full happy path of creating a trip, adding a stop,
       launching it, and verifying the generated itinerary waypoints.

       Current behavior:
       - Create trip → add stop → launch → itinerary loads with start + added + destination
       - Waypoints match expected normalized names

       Steps to reproduce manually:
       1. Log in → go to Trip Planner
       2. Open modal → create new trip (quick launch)
       3. Add stop "Oh" → count becomes 3
       4. Click "Launch trip"
       5. Close any onboarding modal
       6. Observe itinerary with waypoints: Cawker City..., Ohio, US, New York, US

       Expected behavior:
       - Trip created successfully
       - Stop count = 3 after adding one stop
       - "Ohio,US" present in waypoints
       - Itinerary displayed after launch
       - Waypoint names exactly match expected list (normalized)

    """
    my_trips_pg.go_to_trip_planner_page()
    road_trip_modal = trip_planner_pg.open_road_trip_modal()
    road_trip_modal.create_trip("Ca", "New", "quick_launch")
    # Access AddStops component (composition)
    add_stops = trip_planner_pg.add_stops_page

    # Add stop
    add_stops.add_stop("Oh")
    # Verify stop count = 3 (start + added stor + destination)
    assert add_stops.get_stop_count() == 3
    # Verify the expected stop is added successfully
    assert add_stops.has_waypoint("Ohio,US")
    # Click Launch trip button
    add_stops.launch_trip()

    add_stops.close_onboard_modal()

    # Verify Itinerary is displayed
    assert add_stops.itinerary_is_displayed()
    # After creation → verify the generated itinerary waypoints
    trip_planner_pg.assert_waypoint_names([
        "Cawker City, Kansas, United States",
        "Ohio, US",
        "New York, US"
    ])