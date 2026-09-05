from backend.control.turn_controller import TurnController
from backend.state.conversation import Booking


def main():
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

    # Start generation
    context = controller.start_generation()
    generation_id = context.generation.generation_id

    # Simulate an in-progress booking modification
    controller.state.bookings["flight_tokyo"].status = "modified"

    print(
        "STATE BEFORE INTERRUPT:",
        controller.state.bookings["flight_tokyo"].status,
    )

    # User interrupts
    controller.invalidate_current_generation()

    print(
        "GENERATION VALID:",
        controller.is_generation_valid(generation_id),
    )

    print(
        "FLIGHT STATUS AFTER INTERRUPT:",
        controller.state.bookings["flight_tokyo"].status,
    )

    print(
        "HOTEL STATUS AFTER INTERRUPT:",
        controller.state.bookings["hotel_paris"].status,
    )


if __name__ == "__main__":
    main()