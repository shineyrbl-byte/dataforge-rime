import asyncio
from dataclasses import dataclass, field
from enum import Enum, auto

from .fence import Generation, GenerationFence, GenerationStatus
from backend.state.conversation import AgentState, Booking

class OperationStatus(Enum):
    RUNNING = auto()
    CANCELLATION_REQUESTED = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    REJECTED = auto()


@dataclass
class Operation:
    operation_id: str
    generation_id: int
    operation_type: str
    task: asyncio.Task | None = None
    status: OperationStatus = OperationStatus.RUNNING


@dataclass
class TurnContext:
    generation: Generation
    history_snapshot: list[dict] = field(default_factory=list)
    state_snapshot: AgentState | None = None

class TurnController:
    """
    Central control plane for user turns.

    Owns the GenerationFence and tracks asynchronous operations
    belonging to each generation.
    """

    def __init__(self):
        self.fence = GenerationFence()
        self.conversation_history: list[dict] = []
        self.state = AgentState()
        # Deterministic demo booking used by the interruption/stale-result demo.
        self.state.bookings["FLT-DEMO-TYO"] = Booking(
            booking_id="FLT-DEMO-TYO",
            booking_type="flight",
            destination="TYO",
            status="confirmed",
        )

        self._current_context: TurnContext | None = None
        self._operations: dict[str, Operation] = {}
        self._next_operation_id = 1
        

    def start_generation(self) -> TurnContext:
        """Invalidate the previous generation and create a new one."""

        history_snapshot = list(self.conversation_history)
        state_snapshot = self.state.snapshot()

        current = self.fence.current_generation

        if current is not None and current.status == GenerationStatus.ACTIVE:
            self.fence.invalidate(current.generation_id)

        generation = self.fence.create_generation()

        context = TurnContext(
            generation=generation,
            history_snapshot=history_snapshot,
            state_snapshot=state_snapshot,
        )

        self._current_context = context

        return context

    def invalidate_current_generation(self) -> bool:
        """Invalidate the current generation and prepare the next generation."""

        current = self.fence.current_generation

        if current is None:
            return False

        generation_id = current.generation_id
        invalidated = self.fence.invalidate(current.generation_id)

        if not invalidated:
            return False

        # First stop/cancel work belonging to the stale generation.
        self.cancel_generation_operations(generation_id)
        # Restore authoritative state to the snapshot from before this generation.
        self.rollback_current_generation()
        # Create the next generation from the clean rolled-back state.
        self.start_generation()
        return True

    def is_generation_valid(self, generation_id: int) -> bool:
        """Check whether a generation is still allowed to commit."""
        return self.fence.is_valid(generation_id)

    def register_operation(
        self,
        generation_id: int,
        operation_type: str,
        task: asyncio.Task | None = None,
    ) -> Operation:
        """Register an asynchronous operation with a generation."""

        if not self.is_generation_valid(generation_id):
            raise ValueError(
                f"Cannot register operation for invalid generation "
                f"{generation_id}"
            )

        operation_id = f"op-{self._next_operation_id}"
        self._next_operation_id += 1

        operation = Operation(
            operation_id=operation_id,
            generation_id=generation_id,
            operation_type=operation_type,
            task=task,
        )

        self._operations[operation_id] = operation

        return operation

    def attach_task(
        self,
        operation_id: str,
        task: asyncio.Task,
    ) -> None:
        """Attach an asyncio task to an existing operation."""

        operation = self._operations.get(operation_id)

        if operation is None:
            raise ValueError(f"Unknown operation: {operation_id}")

        operation.task = task

    def mark_operation_cancelled(self, operation_id: str) -> None:
        """Mark an operation as cancelled after its task stops."""
        operation = self._operations.get(operation_id)
        if operation is None:
            return
        if operation.status == OperationStatus.CANCELLATION_REQUESTED:
            operation.status = OperationStatus.CANCELLED

    def validate_operation(self, operation_id: str) -> bool:
        """Check whether an operation is still allowed to commit."""

        operation = self._operations.get(operation_id)

        if operation is None:
            return False

        if operation.status != OperationStatus.RUNNING:
            return False

        return self.is_generation_valid(operation.generation_id)

    def commit_operation(self, operation_id: str, result: dict | None = None) -> bool:
        """
        Commit an operation only if its generation is still valid.
        This is the correctness boundary.
        """
        operation = self._operations.get(operation_id)
        if operation is None:
            return False
        if not self.validate_operation(operation_id):
            operation.status = OperationStatus.REJECTED
            return False
        # Only mutate authoritative state after validation.
        if result is not None:
            self._apply_tool_result(result)
        operation.status = OperationStatus.COMPLETED
        return True

    def _apply_tool_result(self, result: dict) -> None:
        """Apply a validated tool result to authoritative state."""
        tool = result.get("tool")
        if tool == "modify_booking":
            booking_id = result["booking_id"]
            if booking_id in self.state.bookings:
                self.state.bookings[booking_id].status = result["status"]

        elif tool == "confirm_booking":
            booking_id = result["booking_id"]

            if booking_id in self.state.bookings:
                self.state.bookings[booking_id].status = result["status"]

        elif tool == "create_hotel_booking":
            booking_id = result["booking_id"]

            self.state.bookings[booking_id] = Booking(
                booking_id=booking_id,
                booking_type="hotel",
                destination=result["destination"],
                status="confirmed",
                hotel_name=result["hotel_name"],
                check_in=result["check_in"],
                check_out=result["check_out"],
                adults=result["adults"],
                children=result["children"],
                price_per_night=result.get("price_per_night"),
                currency=result.get("currency"),
            )

    def cancel_generation_operations(self, generation_id: int) -> int:
        """
        Request cancellation of all running tasks belonging to a generation.
        
        Cancellation is best-effort. The generation fence remains the
        final correctness mechanism.
        """
        requested = 0
        for operation in self._operations.values():
            if (
                operation.generation_id == generation_id
                and operation.status == OperationStatus.RUNNING
            ):
                if operation.task is not None and not operation.task.done():
                    operation.status = OperationStatus.CANCELLATION_REQUESTED
                    operation.task.cancel()
                    requested += 1
        return requested

    def has_active_operations(self, generation_id: int | None = None) -> bool:
        """Return True if the generation has work that can still commit."""
        if generation_id is None:
            current = self.current_generation
            if current is None:
                return False
            generation_id = current.generation_id

        return any(
            operation.generation_id == generation_id
            and operation.status == OperationStatus.RUNNING
            for operation in self._operations.values()
        )

    def get_operation(self, operation_id: str) -> Operation | None:
        return self._operations.get(operation_id)

    @property
    def current_generation(self) -> Generation | None:
        return self.fence.current_generation

    def rollback_current_generation(self) -> bool:
        """Restore state from the current generation's snapshot."""
        context = self._current_context
        if context is None:
            return False
        if context.state_snapshot is None:
            return False
        self.state.restore(context.state_snapshot)
        return True