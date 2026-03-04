from dataclasses import dataclass
from typing import Optional

import factory


@dataclass
class LocationData:
    """
    Data container for location strings used in trip planning and autocomplete tests.

    This dataclass holds consistent test data for:
    - Happy-path trip creation (full valid locations)
    - Autocomplete normalization tests (partial inputs → expected full output)
    - Negative cases (invalid input)
    - Edge cases (very long input)

    Attributes:
        start: Full valid starting location (default or paired with partial_start)
        destination: Full valid destination location (default or paired with partial_dest)
        waypoint: Valid intermediate stop for route tests
        invalid: Deliberately invalid/non-existent location for negative testing
        partial_start: Short prefix that should trigger autocomplete for start field
        partial_dest: Short prefix that should trigger autocomplete for destination field
        long_start: Very long but valid location name (tests input limits, truncation, delay)

    When using partial_start or partial_dest:
        - These are currently fixed strings (not random) to ensure reliable test results
        - The factory sets corresponding expected full cities (expected_start_city / expected_dest_city)
        - Tests should assert the expected city appears in the normalized final value

    Intended Use:
        - Passed to trip creation flows (e.g. road_trip_modal.create_trip(...))
        - Autocomplete tests: partial input → normalized full location
        - Negative tests: invalid input validation
        - Edge cases: long input handling, typing performance

    """

    start: str
    destination: str
    waypoint: str
    invalid: str = "nonexistent xyz 987654 invalid place"
    partial_start: Optional[str] = None
    partial_dest: Optional[str] = None
    long_start: Optional[str] = None


class LocationFactory(factory.Factory):
    """
    Factory for generating LocationData instances for Roadtrippers trip tests.

    This factory provides:
    - Fixed default full locations for consistency
    - Fixed partial strings that reliably trigger autocomplete suggestions
    - Paired expected cities for partial inputs (via expected_start_city / expected_dest_city)
    - Invalid and long strings for negative/edge-case testing

    Current behavior:
    - partial_start and partial_dest are **fixed** (not random) to guarantee test stability
    - expected_start_city / expected_dest_city are populated based on the chosen partial
    - start and destination defaults can be overridden when partials are used

    Intended Use:
        - Autocomplete normalization: type partial → assert expected city in result
        - Trip creation: supply start/destination/waypoint
        - Negative tests: use .invalid for invalid input validation
        - Edge cases: use .long_start for input length/scrolling/performance

    Examples of generated data:
        {
            'start': 'Chicago, IL',
            'destination': 'New York, USA',
            'waypoint': 'Starved Rock State Park',
            'invalid': 'nonexistent xyz 987654 invalid place',
            'partial_start': 'Chi',
            'partial_dest': 'New',
            'long_start': 'International Falls, Minnesota, United States',
            'expected_start_city': 'Chicago',
            'expected_dest_city': 'New York'
        }

    """

    class Meta:
        model = LocationData

    start = "Chicago, IL"
    destination = "New York, USA"
    waypoint = "Starved Rock State Park"
    invalid = "nonexistent xyz 987654 invalid place"
    long_start = "International Falls, Minnesota, United States"

    # Fixed partial for start field (reliable trigger for Chicago)
    @factory.lazy_attribute
    def partial_start(self):
        """
        Returns a short prefix that reliably triggers autocomplete for Chicago.

        Chosen value:
            - "Chi" → almost always completes to "Chicago, IL"

        Returns:
            str: Fixed partial string for consistent test behavior

        """
        return "Chi"

    # Fixed partial for destination field (reliable trigger for New York)
    @factory.lazy_attribute
    def partial_dest(self):
        """
        Returns a short prefix that reliably triggers autocomplete for New York.

        Chosen value:
            - "New" → commonly completes to "New York, USA" or similar

        Returns:
            str: Fixed partial string for consistent test behavior

        """
        return "New"

    # Optional long input (no pairing needed)
    @factory.lazy_attribute
    def long_start(self):
        """
        Returns a very long but valid location name.

        Useful for:
        - Testing input field limits
        - Checking truncation, scrolling, or typing delay
        - Ensuring autocomplete/normalization handles long strings

        Returns:
            str: Full long location name

        """
        return "International Falls, Minnesota, United States"