import asyncio

from backend.control.turn_controller import TurnController


async def cancellation_resistant_work():
    """
    Simulates work that ignores cancellation and still returns a result.
    """

    inner_task = asyncio.create_task(
        asyncio.sleep(0.01, result="stale booking result")
    )

    try:
        return await asyncio.shield(inner_task)

    except asyncio.CancelledError:
        # Simulate a tool that ignores cancellation.
        return await inner_task


async def run_trial(trial_number: int) -> bool:
    controller = TurnController()

    # Generation 1 starts.
    context = controller.start_generation()
    generation_id = context.generation.generation_id

    task = asyncio.create_task(
        cancellation_resistant_work()
    )

    operation = controller.register_operation(
        generation_id,
        "modify_booking",
        task,
    )

    # Give the task time to start.
    await asyncio.sleep(0)

    # User interrupts.
    controller.invalidate_current_generation()

    # Old operation eventually finishes.
    result = await task

    # Try to commit the stale result.
    committed = controller.commit_operation(
        operation.operation_id
    )

    success = (
        result == "stale booking result"
        and committed is False
    )

    print(
        f"Trial {trial_number:02d}: "
        f"stale result rejected = {success}"
    )

    return success


async def main():
    total_trials = 50
    successful_trials = 0

    print("B3 STALE-RESULT CORRECTNESS BENCHMARK")
    print("=" * 45)

    for trial in range(1, total_trials + 1):
        if await run_trial(trial):
            successful_trials += 1

    print()
    print("=" * 45)
    print(
        f"RESULT: {successful_trials}/{total_trials} "
        "stale results rejected"
    )

    accuracy = (
        successful_trials / total_trials * 100
    )

    print(f"CORRECTNESS: {accuracy:.1f}%")

    if successful_trials == total_trials:
        print("B3 STATUS: PASS")
    else:
        print("B3 STATUS: FAIL")


if __name__ == "__main__":
    asyncio.run(main())