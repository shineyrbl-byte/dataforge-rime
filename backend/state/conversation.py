from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class Booking:
    booking_id: str
    booking_type: str
    destination: str
    status: str


@dataclass
class AgentState:
    """Authoritative state owned by the voice agent."""

    bookings: dict[str, Booking] = field(default_factory=dict)

    def snapshot(self) -> "AgentState":
        """Create an independent copy of the current state."""
        return deepcopy(self)

    def restore(self, snapshot: "AgentState") -> None:
        """Restore state from a previous snapshot."""
        self.bookings = deepcopy(snapshot.bookings)