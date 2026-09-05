import asyncio

from backend.control.turn_controller import TurnController


async def tool_that_ignores_cancellation():
    try:
        await asyncio.sleep(0.05)
    except asyncio.CancelledError:
        # Simulate a real external operation that cannot be stopped.
        return "stale booking result"

    return "stale booking result"


def test_stale_result_rejected():
    async def run_test():
        controller = TurnController()

        # Start generation 1
        context = controller.start_generation()
        generation_id = context.generation.generation_id

        # Start a tool operation
        task = asyncio.create_task(
            tool_that_ignores_cancellation()
        )

        operation = controller.register_operation(
            generation_id,
            "modify_booking",
            task,
        )
        await asyncio.sleep(0)

        assert operation.status.name == "RUNNING"

        # User interrupts
        controller.invalidate_current_generation()

        # Old generation must be invalid
        assert controller.is_generation_valid(generation_id) is False

        # Cancellation was requested
        assert operation.status.name == "CANCELLATION_REQUESTED"

        # Simulate a tool that still returns despite cancellation
        result = await task

        assert result == "stale booking result"

        # The stale result must be rejected
        committed = controller.commit_operation(
            operation.operation_id
        )

        assert committed is False

        # Mark operation as rejected
        operation.status = operation.status.REJECTED

        assert operation.status.name == "REJECTED"

    asyncio.run(run_test())