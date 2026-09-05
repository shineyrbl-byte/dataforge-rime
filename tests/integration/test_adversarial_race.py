import asyncio

from backend.control.turn_controller import TurnController
from backend.tools.executor import execute_tool
from backend.tools.mock_tools import modify_booking


def test_adversarial_late_tool_result_is_rejected():
    async def run_test():
        controller = TurnController()

        context = controller.start_generation()
        generation_id = context.generation.generation_id

        task = asyncio.create_task(
            execute_tool(
                controller,
                generation_id,
                "modify_booking",
                modify_booking,
                "FL123",
                "Tokyo",
            )
        )

        # Give the tool time to start.
        await asyncio.sleep(0.1)

        # Simulate the user's barge-in.
        controller.invalidate_current_generation()

        # The adversarial mock deliberately survives cancellation.
        result = await task

        assert result["status"] == "stale_rejected"
        assert result["generation_id"] == generation_id

        # The stale generation must remain permanently invalid.
        assert controller.is_generation_valid(generation_id) is False

        # The new generation must be valid.
        new_generation = controller.current_generation
        assert new_generation is not None
        assert new_generation.generation_id != generation_id
        assert controller.is_generation_valid(
            new_generation.generation_id
        ) is True

        # Most importantly: the stale result must NOT have modified state.
        assert "FL123" not in controller.state.bookings

    asyncio.run(run_test())