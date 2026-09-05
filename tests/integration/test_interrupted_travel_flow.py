import asyncio

from backend.control.turn_controller import TurnController
from backend.state.conversation import Booking
from backend.tools.executor import (
    GenerationCancelledError,
    execute_tool,
)
from backend.tools.mock_tools import (
    check_availability,
    modify_booking,
    confirm_booking,
)


async def main():
    controller = TurnController()

    # Initial authoritative state
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

    # -----------------------------
    # GENERATION 1
    # -----------------------------

    context = controller.start_generation()
    generation_1 = context.generation.generation_id

    print("=== GENERATION 1 STARTED ===")

    print(
        "Tokyo flight:",
        controller.state.bookings["flight_tokyo"].status,
    )

    print(
        "Paris hotel:",
        controller.state.bookings["hotel_paris"].status,
    )

    # Check availability
    await execute_tool(
        controller,
        generation_1,
        "check_availability",
        check_availability,
        "Tokyo",
    )

    # Start modifying Tokyo flight
    modification_task = asyncio.create_task(
        execute_tool(
            controller,
            generation_1,
            "modify_booking",
            modify_booking,
            "flight_tokyo",
            "Tokyo",
        )
    )

    # Let the tool start running
    await asyncio.sleep(0.2)

    # -----------------------------
    # USER INTERRUPTS
    # -----------------------------

    print("\n!!! USER INTERRUPTS !!!")
    print('"STOP! Cancel that. Just change the flight."')

    controller.invalidate_current_generation()

    # Wait for old operation
    try:
        await modification_task
    except asyncio.CancelledError:
        print("OLD TOOL CANCELLED")
    except GenerationCancelledError:
        print("OLD TOOL RESULT REJECTED")

    print(
        "\nSTATE AFTER ROLLBACK:"
    )

    print(
        "Tokyo flight:",
        controller.state.bookings["flight_tokyo"].status,
    )

    print(
        "Paris hotel:",
        controller.state.bookings["hotel_paris"].status,
    )

    # -----------------------------
    # GENERATION 2
    # -----------------------------

    context = controller.start_generation()
    generation_2 = context.generation.generation_id

    print("\n=== GENERATION 2 STARTED ===")

    # User's corrected request:
    # only modify the Tokyo flight

    await execute_tool(
        controller,
        generation_2,
        "modify_booking",
        modify_booking,
        "flight_tokyo",
        "Tokyo",
    )

    print("\n=== FINAL STATE ===")

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