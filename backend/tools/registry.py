from .mock_tools import (
    check_availability,
    modify_booking,
    confirm_booking,
    search_hotels,
    create_hotel_booking,
    search_flights,
    create_flight_booking,
)


TOOLS = {
    "check_availability": check_availability,
    "modify_booking": modify_booking,
    "confirm_booking": confirm_booking,
    "search_hotels": search_hotels,
    "create_hotel_booking": create_hotel_booking,
    "search_flights": search_flights,
    "create_flight_booking": create_flight_booking,
}


def get_tool(name: str):
    """Return a registered travel tool."""
    try:
        return TOOLS[name]
    except KeyError:
        raise ValueError(f"Unknown tool: {name}")
