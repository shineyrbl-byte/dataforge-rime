from backend.control.turn_controller import TurnController
from backend.state.conversation import Booking


def test_state_rollback():
    controller = TurnController()

    controller.state.bookings["FL123"] = Booking(
        booking_id="FL123",
        booking_type="flight",
        destination="Tokyo",
        status="confirmed",
    )

    context = controller.start_generation()
    generation_id = context.generation.generation_id

    # Simulate mutation during the generation.
    controller.state.bookings["FL123"].status = "modified"

    assert controller.state.bookings["FL123"].status == "modified"

    # Interrupt the generation.
    controller.invalidate_current_generation()

    # Old state must be restored.
    assert controller.is_generation_valid(generation_id) is False
    assert controller.state.bookings["FL123"].status == "confirmed"