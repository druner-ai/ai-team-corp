from collections import deque
from game import Direction


class InputBuffer:
    """
    Thread-safe-ish buffer for direction inputs.
    Maximum size is 3. Opposite directions are rejected silently.
    """

    MAX_SIZE = 3

    def __init__(self):
        self._queue = deque()

    @property
    def size(self) -> int:
        return len(self._queue)

    def push(self, direction: Direction, current_direction: Direction) -> None:
        """
        Add a direction to the buffer.
        - Rejects if opposite to current_direction.
        - Rejects if buffer is full (discards the new direction).
        """
        if _is_opposite(direction, current_direction):
            return
        if self.size >= self.MAX_SIZE:
            return
        self._queue.append(direction)

    def pop(self, current_direction: Direction) -> Direction:
        """
        Retrieve the next direction from the buffer.
        - Returns current_direction if buffer is empty.
        - Skips any direction that is opposite to current_direction (defensive).
        """
        if not self._queue:
            return current_direction
        direction = self._queue.popleft()
        # Defensive check: if somehow an opposite direction was queued, skip it
        if _is_opposite(direction, current_direction):
            return self.pop(current_direction)
        return direction


def _is_opposite(d1: Direction, d2: Direction) -> bool:
    """Check if two directions are opposite."""
    return (d1.value[0] + d2.value[0] == 0) and (d1.value[1] + d2.value[1] == 0)
