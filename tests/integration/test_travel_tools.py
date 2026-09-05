import asyncio

from backend.control.turn_controller import TurnController
from backend.state.conversation import Booking
from backend.tools.executor import execute_tool
from backend.tools.mock_tools import (
    check_availability,
    modify_booking,
    confirm_booking,
)


async def main():
    controller = TurnController()

    controller.state.bookings["flight_tokyo"] = Booking(
        booking_id="flight_tokyo",
        booking_type="flight",
        destination="Tokyo",
        status="confirmed",
    )

    controller.state.bookings["hotel_paris"] = Booking(
        booking_id="hotel_paris",
        booking_type="hotel",
        destination="Paris",
        status="confirmed",
    )

    context = controller.start_generation()
    generation_id = context.generation.generation_id

    print("INITIAL STATE")
    print(
        "Tokyo flight:",
        controller.state.bookings["flight_tokyo"].status,
    )
    print(
        "Paris hotel:",
        controller.state.bookings["hotel_paris"].status,
    )

    availability = await execute_tool(
        controller,
        generation_id,
        "check_availability",
        check_availability,
        "Tokyo",
    )

    print("\nAVAILABILITY:", availability)

    modification = await execute_tool(
        controller,
        generation_id,
        "modify_booking",
        modify_booking,
        "flight_tokyo",
        "Tokyo",
    )

    print("\nMODIFICATION:", modification)

    confirmation = await execute_tool(
        controller,
        generation_id,
        "confirm_booking",
        confirm_booking,
        "hotel_paris",
    )

    print("\nCONFIRMATION:", confirmation)

    print("\nFINAL STATE")
    print(
        "Tokyo flight:",
        controller.state.bookings["flight_tokyo"].status,
    )
    print(
        "Paris hotel:",
        controller.state.bookings["hotel_paris"].status,
    )


if __name__ == "__main__":
    asyncio.run(main())