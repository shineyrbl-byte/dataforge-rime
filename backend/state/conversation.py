from copy import deepcopy
from dataclasses import dataclass, field


@dataclass
class Booking:
    booking_id: str
    booking_type: str
    destination: str
    status: str

    # Hotel-specific details
    hotel_name: str | None = None
    check_in: str | None = None
    check_out: str | None = None
    adults: int = 0
    children: int = 0
    price_per_night: float | None = None
    currency: str | None = None


@dataclass
class AgentState:
    """Authoritative state owned by the voice agent."""

    bookings: dict[str, Booking] = field(default_factory=dict)
    flight_search_results: list[dict] = field(default_factory=list)

    def snapshot(self) -> "AgentState":
        """Create an independent copy of the current state."""
        return deepcopy(self)

    def restore(self, snapshot: "AgentState") -> None:
        """Restore state from a previous snapshot."""
        self.bookings = deepcopy(snapshot.bookings)