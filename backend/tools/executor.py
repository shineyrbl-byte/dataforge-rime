import asyncio
import logging

from backend.control.turn_controller import TurnController


logger = logging.getLogger("travel-agent")


class GenerationCancelledError(Exception):
    """Raised when a tool result belongs to a stale generation."""


async def execute_tool(
    controller: TurnController,
    generation_id: int,
    operation_type: str,
    tool,
    *args,
    **kwargs,
):
    # Make sure this generation is still active before starting work
    if not controller.is_generation_valid(generation_id):
        raise GenerationCancelledError(
            f"Generation {generation_id} is no longer valid"
        )

    # Register the operation
    operation = controller.register_operation(
        generation_id,
        operation_type,
    )
    logger.info(
        "OPERATION STARTED: operation=%s type=%s generation=%s",
        operation.operation_id,
        operation_type,
        generation_id,
    )

    # Attach the current asyncio task so the controller can request cancellation
    task = asyncio.current_task()

    if task is not None:
        controller.attach_task(operation.operation_id, task)

    try:
        # Execute the actual tool
        result = await tool(*args, **kwargs)

    except asyncio.CancelledError:
        controller.mark_operation_cancelled(operation.operation_id)
        raise

    # IMPORTANT:
    # The tool may have finished even after interruption.
    # The result is NOT trusted until the generation fence validates it.

    if not controller.commit_operation(
        operation.operation_id,
        result,
    ):
        logger.warning(
            "STALE RESULT REJECTED: operation=%s generation=%s",
            operation.operation_id,
            generation_id,
        )

        return {
            "status": "stale_rejected",
            "generation_id": generation_id,
            "operation_id": operation.operation_id,
        }

    logger.info(
        "OPERATION COMPLETED: operation=%s generation=%s",
        operation.operation_id,
        generation_id,
    )

    return result