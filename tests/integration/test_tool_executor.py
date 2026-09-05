import asyncio

from backend.control.turn_controller import TurnController
from backend.tools.executor import (
    GenerationCancelledError,
    execute_tool,
)
from backend.tools.mock_tools import modify_booking


def test_tool_executor_rejects_stale_result():
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

        # Let the tool start before interruption.
        await asyncio.sleep(0.1)

        # User interrupts.
        controller.invalidate_current_generation()

        # The mock tool deliberately ignores cancellation.
        # Therefore execute_tool should finish normally,
        # but the stale result must be rejected.
        result = await task

        assert result["status"] == "stale_rejected"
        assert result["generation_id"] == generation_id
        assert controller.is_generation_valid(generation_id) is False

    asyncio.run(run_test())