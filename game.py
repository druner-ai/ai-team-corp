from enum import Enum
from dataclasses import dataclass, field
import random


class Direction(Enum):
    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


@dataclass
class GameState:
    width: int = 20
    height: int = 10
    snake: list = field(default_factory=list)
    food: tuple = (0, 0)
    score: int = 0
    game_over: bool = False
    direction: Direction = Direction.RIGHT


def init_state(width: int, height: int, rng: random.Random) -> GameState:
    """
    Creates the initial game state.
    Snake length 3, centered horizontally, direction RIGHT.
    Food placed at a random free cell.
    """
    center_x = width // 2
    center_y = height // 2
    snake = [
        (center_x, center_y),
        (center_x - 1, center_y),
        (center_x - 2, center_y)
    ]
    food = _place_food(width, height, snake, rng)
    return GameState(
        width=width,
        height=height,
        snake=snake,
        food=food,
        score=0,
        game_over=False,
        direction=Direction.RIGHT
    )


def step(state: GameState, direction: Direction | None, rng: random.Random) -> GameState:
    """
    Advances the game state by one tick.
    Returns a NEW GameState (immutable).
    """
    if state.game_over:
        return state

    # Determine effective direction
    current_dir = state.direction
    if direction is not None:
        if _is_opposite(direction, current_dir):
            effective_dir = current_dir
        else:
            effective_dir = direction
    else:
        effective_dir = current_dir

    # Calculate new head position
    head_x, head_y = state.snake[0]
    dx, dy = effective_dir.value
    new_head = (head_x + dx, head_y + dy)

    # Check wall collision
    if new_head[0] < 0 or new_head[0] >= state.width or new_head[1] < 0 or new_head[1] >= state.height:
        return GameState(
            width=state.width,
            height=state.height,
            snake=state.snake,
            food=state.food,
            score=state.score,
            game_over=True,
            direction=effective_dir
        )

    # Check if eating food
    eating = new_head == state.food

    # Build new snake
    new_snake = [new_head] + state.snake

    # Collision with body (tail moves if not eating, so exclude current tail if not eating)
    tail_can_move = not eating
    body_to_check = new_snake[1:-1] if tail_can_move else new_snake[1:]
    if new_head in body_to_check:
        return GameState(
            width=state.width,
            height=state.height,
            snake=state.snake,
            food=state.food,
            score=state.score,
            game_over=True,
            direction=effective_dir
        )

    # Update snake length and score based on eating
    if eating:
        new_score = state.score + 10
        new_food = _place_food(state.width, state.height, new_snake, rng)
    else:
        new_score = state.score
        new_snake.pop()  # remove tail (length unchanged)
        new_food = state.food

    return GameState(
        width=state.width,
        height=state.height,
        snake=new_snake,
        food=new_food,
        score=new_score,
        game_over=False,
        direction=effective_dir
    )


def _is_opposite(d1: Direction, d2: Direction) -> bool:
    """Check if two directions are opposite."""
    return (d1.value[0] + d2.value[0] == 0) and (d1.value[1] + d2.value[1] == 0)


def _place_food(width: int, height: int, snake: list, rng: random.Random) -> tuple:
    """Place food at a random free cell."""
    snake_set = set(snake)
    free_cells = [(x, y) for x in range(width) for y in range(height) if (x, y) not in snake_set]
    if not free_cells:
        # No free cells — shouldn't happen in normal play
        return snake[0]  # fallback, though game should be won at this point
    return rng.choice(free_cells)
