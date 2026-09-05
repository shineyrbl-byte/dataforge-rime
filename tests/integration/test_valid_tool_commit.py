import asyncio

from backend.control.turn_controller import TurnController
from backend.state.conversation import Booking
from backend.tools.executor import execute_tool


async def modify_tool():
    await asyncio.sleep(0.2)

    return {
        "tool": "modify_booking",
        "booking_id": "flight_tokyo",
        "destination": "Tokyo",
        "status": "modified",
    }


async def main():
    controller = TurnController()

    controller.state.bookings["flight_tokyo"] = Booking(
        booking_id="flight_tokyo",
        booking_type="flight",
        destination="Tokyo",
        status="confirmed",
    )

    context = controller.start_generation()
    generation_id = context.generation.generation_id

    print(
        "BEFORE:",
        controller.state.bookings["flight_tokyo"].status,
    )

    result = await execute_tool(
        controller,
        generation_id,
        "modify_booking",
        modify_tool,
    )

    print("TOOL RESULT:", result)

    print(
        "AFTER:",
        controller.state.bookings["flight_tokyo"].status,
    )


if __name__ == "__main__":
    asyncio.run(main())