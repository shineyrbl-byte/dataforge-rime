import asyncio

from backend.control.turn_controller import TurnController


async def slow_work():
    try:
        await asyncio.sleep(5)
        return "finished"
    except asyncio.CancelledError:
        raise


def test_async_cancellation():
    async def run_test():
        controller = TurnController()

        # Start generation 1
        context = controller.start_generation()
        generation_id = context.generation.generation_id

        # Start an asynchronous operation
        task = asyncio.create_task(slow_work())

        operation = controller.register_operation(
            generation_id,
            "modify_booking",
            task,
        )

        assert operation.status.name == "RUNNING"

        # Simulate user interruption
        controller.invalidate_current_generation()

        # Old generation must now be invalid
        assert controller.is_generation_valid(generation_id) is False

        # Cancellation should have been requested
        assert operation.status.name == "CANCELLATION_REQUESTED"

        # Let asyncio process cancellation
        try:
            await task
        except asyncio.CancelledError:
            controller.mark_operation_cancelled(
                operation.operation_id
            )

        # Task should actually be cancelled
        assert task.cancelled() is True

        # Operation should be fully cancelled
        assert operation.status.name == "CANCELLED"

        # Stale operation must never commit
        assert (
            controller.commit_operation(
                operation.operation_id
            )
            is False
        )

    asyncio.run(run_test())