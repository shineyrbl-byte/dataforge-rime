from dataclasses import dataclass
from enum import Enum, auto


class GenerationStatus(Enum):
    CREATED = auto()
    ACTIVE = auto()
    INVALIDATED = auto()
    DRAINING = auto()
    TERMINATED = auto()


@dataclass
class Generation:
    generation_id: int
    status: GenerationStatus = GenerationStatus.CREATED


class GenerationFence:
    """
    Tracks the currently valid generation.

    A generation is valid only while it is ACTIVE and is the
    current generation.
    """

    def __init__(self):
        self._current_generation: Generation | None = None
        self._next_generation_id = 1

    def create_generation(self) -> Generation:
        """Create and activate a new generation."""
        generation = Generation(
            generation_id=self._next_generation_id,
            status=GenerationStatus.ACTIVE,
        )

        self._next_generation_id += 1
        self._current_generation = generation

        return generation

    def invalidate(self, generation_id: int) -> bool:
        """
        Invalidate a generation if it is still the current one.

        Returns True if invalidation happened.
        """
        current = self._current_generation

        if current is None:
            return False

        if current.generation_id != generation_id:
            return False

        if current.status != GenerationStatus.ACTIVE:
            return False

        current.status = GenerationStatus.INVALIDATED
        return True

    def is_valid(self, generation_id: int) -> bool:
        """Return True only if this generation is currently active."""
        current = self._current_generation

        return (
            current is not None
            and current.generation_id == generation_id
            and current.status == GenerationStatus.ACTIVE
        )

    @property
    def current_generation(self) -> Generation | None:
        return self._current_generation