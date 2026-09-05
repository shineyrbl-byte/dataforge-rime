import asyncio

from backend.control.turn_controller import TurnController
from backend.tools.executor import (
    GenerationCancelledError,
    execute_tool,
)


async def cancellation_resistant_tool():
    inner_task = asyncio.create_task(
        asyncio.sleep(1.0, result="STALE BOOKING RESULT")
    )

    try:
        return await asyncio.shield(inner_task)

    except asyncio.CancelledError:
        print("TOOL IGNORED CANCELLATION")

        # Continue waiting for the underlying operation.
        return await inner_task


async def main():
    controller = TurnController()

    context = controller.start_generation()
    generation_id = context.generation.generation_id

    task = asyncio.create_task(
        execute_tool(
            controller,
            generation_id,
            "modify_booking",
            cancellation_resistant_tool,
        )
    )

    # Let the tool actually start.
    await asyncio.sleep(0.1)

    print("INTERRUPTING GENERATION")
    controller.invalidate_current_generation()

    try:
        result = await task
        print("TOOL RESULT:", result)

    except GenerationCancelledError:
        print("STALE RESULT REJECTED")

    except asyncio.CancelledError:
        print("UNEXPECTED: TOOL TASK CANCELLED")

    print(
        "GENERATION VALID:",
        controller.is_generation_valid(generation_id),
    )


if __name__ == "__main__":
    asyncio.run(main())