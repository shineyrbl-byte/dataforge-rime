import asyncio

from backend.control.turn_controller import TurnController
from backend.tools.executor import (
    GenerationCancelledError,
    execute_tool,
)


async def slow_tool():
    await asyncio.sleep(1.0)

    return {
        "status": "modified",
    }


async def main():
    controller = TurnController()

    context = controller.start_generation()
    generation_id = context.generation.generation_id

    task = asyncio.create_task(
        execute_tool(
            controller,
            generation_id,
            "modify_booking",
            slow_tool,
        )
    )

    # Give the tool time to start
    await asyncio.sleep(0.1)

    print("INTERRUPTING GENERATION")
    controller.invalidate_current_generation()

    try:
        await task
    except asyncio.CancelledError:
        print("TOOL TASK CANCELLED")
    except GenerationCancelledError as exc:
        print("STALE RESULT REJECTED")
        print(exc)

    print(
        "GENERATION VALID:",
        controller.is_generation_valid(generation_id),
    )


if __name__ == "__main__":
    asyncio.run(main())