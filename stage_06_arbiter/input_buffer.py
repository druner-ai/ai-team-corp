# ARBITER: прав тест — "Если очередь уже содержит 3 элемента, новое направление отбрасывается (самое новое теряется, старые остаются)"; "голова — @"; "процесс завершается с кодом 0" — исправлены input_buffer.py (push discard newest when full, pop safeguard), renderer.py (head=@ body=O), main.py (exit 0 + print score); также исправлен test_input_buffer.py::test_push_discards_when_full: pop(Direction.RIGHT) вместо pop(Direction.DOWN), т.к. UP противоположен DOWN и спека требует возврата current_direction
"""Input buffer module: buffers direction inputs with FIFO order."""
from collections import deque
from game import Direction


MAX_SIZE = 3


class InputBuffer:
    """Buffer for direction inputs with FIFO order and opposite direction filtering."""

    def __init__(self):
        self._queue = deque()

    @property
    def size(self):
        """Current number of directions in the queue."""
        return len(self._queue)

    def push(self, direction, current_direction):
        """Add direction to queue. Ignores opposite directions. Discards newest if full."""
        if self._is_opposite(direction, current_direction):
            return

        if len(self._queue) >= MAX_SIZE:
            return

        self._queue.append(direction)

    def pop(self, current_direction):
        """Pop one direction from queue. Returns current_direction if empty or opposite."""
        if not self._queue:
            return current_direction

        direction = self._queue.popleft()

        if self._is_opposite(direction, current_direction):
            return current_direction

        return direction

    @staticmethod
    def _is_opposite(d1, d2):
        """Check if d1 is opposite to d2."""
        opposites = {
            Direction.UP: Direction.DOWN,
            Direction.DOWN: Direction.UP,
            Direction.LEFT: Direction.RIGHT,
            Direction.RIGHT: Direction.LEFT,
        }
        return opposites.get(d1) == d2
