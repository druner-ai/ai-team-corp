from collections import deque
from game import Direction


class InputBuffer:
    def __init__(self):
        self._queue = deque(maxlen=3)

    def push(self, direction: Direction, current_direction: Direction):
        # Ignore opposite direction
        if (direction == Direction.UP and current_direction == Direction.DOWN) or \
           (direction == Direction.DOWN and current_direction == Direction.UP) or \
           (direction == Direction.LEFT and current_direction == Direction.RIGHT) or \
           (direction == Direction.RIGHT and current_direction == Direction.LEFT):
            return
        if len(self._queue) < 3:
            self._queue.append(direction)

    def pop(self, current_direction: Direction) -> Direction:
        if self._queue:
            # Fixed: use popleft() to get the oldest direction (FIFO)
            return self._queue.popleft()
        return current_direction

    @property
    def size(self):
        return len(self._queue)
