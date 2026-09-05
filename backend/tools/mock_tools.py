import asyncio


async def check_availability(destination: str) -> dict:
    await asyncio.sleep(0.5)

    return {
        "tool": "check_availability",
        "destination": destination,
        "available": True,
    }


async def modify_booking(booking_id: str, destination: str) -> dict:
    try:
        await asyncio.sleep(8.0)
    except asyncio.CancelledError:
        # Deliberately ignore cancellation to simulate
        # an external operation that cannot be stopped.
        await asyncio.sleep(2.0)

    return {
        "tool": "modify_booking",
        "booking_id": booking_id,
        "destination": destination,
        "status": "modified",
    }


async def confirm_booking(booking_id: str) -> dict:
    await asyncio.sleep(0.8)

    return {
        "tool": "confirm_booking",
        "booking_id": booking_id,
        "status": "confirmed",
    }