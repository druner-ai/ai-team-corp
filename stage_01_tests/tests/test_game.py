"""Tests for game logic: init_state, step, collisions, food."""
import pytest
import random
from game import Direction, GameState, init_state, step


class TestInitState:
    def test_snake_length_and_position(self):
        """ASSERT-15: init_state creates a snake of length 3 in the center, direction RIGHT."""
        rng = random.Random(42)
        state = init_state(20, 10, rng)
        assert len(state.snake) == 3
        # Center of 20x10 is (10,5) but coordinates are 0-indexed? The spec says center.
        # We'll check that the head is at (10,5) and the body extends left.
        assert state.snake[0] == (10, 5)
        assert state.snake[1] == (9, 5)
        assert state.snake[2] == (8, 5)
        assert state.direction == Direction.RIGHT

    def test_deterministic_with_same_seed(self, fixed_rng):
        """ASSERT-16: Same seed produces identical initial states (same food position)."""
        state1 = init_state(20, 10, fixed_rng)
        # Create a new Random with the same seed
        rng2 = random.Random(42)
        state2 = init_state(20, 10, rng2)
        assert state1.food == state2.food
        assert state1.snake == state2.snake
        assert state1.score == state2.score
        assert state1.direction == state2.direction

    def test_food_not_on_snake(self, fixed_rng):
        """ASSERT-17: Food is placed on a cell not occupied by the snake."""
        state = init_state(20, 10, fixed_rng)
        assert state.food not in state.snake


class TestStep:
    def test_movement(self, fixed_rng):
        """Snake moves one step in the current direction."""
        state = init_state(20, 10, fixed_rng)
        new_state = step(state, None, fixed_rng)  # None -> use current direction
        # Head should move right by one
        assert new_state.snake[0] == (state.snake[0][0] + 1, state.snake[0][1])
        # Length unchanged
        assert len(new_state.snake) == len(state.snake)

    def test_wall_collision(self, fixed_rng):
        """ASSERT-04: step returns game_over=True when head moves outside the field."""
        # Create a state with head at right edge, direction RIGHT
        state = GameState(
            width=20, height=10,
            snake=[(19, 5), (18, 5), (17, 5)],
            food=(10, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        new_state = step(state, Direction.RIGHT, fixed_rng)
        assert new_state.game_over is True

    def test_self_collision(self, fixed_rng):
        """ASSERT-05: step returns game_over=True when head collides with body (except tail that moves)."""
        # Snake moving right, head will hit its own body if it turns into itself.
        # Simpler: create a snake that is about to bite its own body.
        state = GameState(
            width=20, height=10,
            snake=[(5, 5), (6, 5), (6, 6), (5, 6), (4, 6)],  # head at (5,5), body includes (6,5) etc.
            food=(10, 10),
            score=0,
            game_over=False,
            direction=Direction.UP
        )
        # Moving UP from (5,5) goes to (5,4) – no collision.
        # We need a scenario where head moves into body.
        # Let's set snake moving left into its own body.
        state = GameState(
            width=20, height=10,
            snake=[(5, 5), (6, 5), (7, 5), (7, 6), (6, 6), (5, 6)],
            food=(10, 10),
            score=0,
            game_over=False,
            direction=Direction.LEFT
        )
        # Head at (5,5), moving LEFT to (4,5) – no collision.
        # Better: create a snake that forms a loop and head moves into the body.
        # Use a snake that is about to eat its own tail? But tail moves away if not eating.
        # The spec says collision with body except the tail that will move.
        # So if head moves into the position currently occupied by the tail, and no food is eaten, it's safe.
        # We need a collision with a non-tail segment.
        # Let's construct: snake length 4, head at (5,5), body: (6,5), (6,6), (5,6). Direction LEFT.
        # Head moves to (4,5) – no collision.
        # To force collision, we can make the snake turn into itself.
        # We'll set direction so that head moves into a body segment that is not the tail.
        # For example, snake: [(5,5), (6,5), (6,6), (5,6), (4,6)] with direction UP.
        # Head at (5,5) moving UP to (5,4) – no collision.
        # Let's use a snake that is long and the head is adjacent to a body segment.
        # We'll create a state where head is at (5,5), body includes (5,6), direction DOWN.
        # Then head moves to (5,6) which is the second segment (not tail if length>2).
        state = GameState(
            width=20, height=10,
            snake=[(5, 5), (5, 6), (6, 6), (6, 5)],  # head (5,5), body (5,6), (6,6), (6,5)
            food=(10, 10),
            score=0,
            game_over=False,
            direction=Direction.DOWN
        )
        # Moving DOWN from (5,5) to (5,6) – that's the second segment, collision.
        new_state = step(state, Direction.DOWN, fixed_rng)
        assert new_state.game_over is True

    def test_eat_food(self, fixed_rng):
        """ASSERT-06: Eating food increases score by 10 and length by 1."""
        # Place food directly in front of the snake
        state = GameState(
            width=20, height=10,
            snake=[(5, 5), (4, 5), (3, 5)],
            food=(6, 5),  # one step right from head
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        new_state = step(state, Direction.RIGHT, fixed_rng)
        assert new_state.score == 10
        assert len(new_state.snake) == 4
        # Head should be at food position
        assert new_state.snake[0] == (6, 5)
        # New food should be generated and not on snake
        assert new_state.food not in new_state.snake

    def test_ignore_opposite_direction(self, fixed_rng):
        """ASSERT-07: step ignores a direction that is opposite to current, uses current direction."""
        state = init_state(20, 10, fixed_rng)  # direction RIGHT
        # Try to go LEFT (opposite)
        new_state = step(state, Direction.LEFT, fixed_rng)
        # Head should still move RIGHT
        assert new_state.snake[0] == (state.snake[0][0] + 1, state.snake[0][1])
        assert new_state.direction == Direction.RIGHT

    def test_game_over_state_unchanged(self, fixed_rng):
        """If game is already over, step returns the state unchanged."""
        state = GameState(
            width=20, height=10,
            snake=[(5, 5), (4, 5), (3, 5)],
            food=(10, 10),
            score=0,
            game_over=True,
            direction=Direction.RIGHT
        )
        new_state = step(state, Direction.UP, fixed_rng)
        assert new_state == state

    def test_new_food_not_on_snake_after_eating(self, fixed_rng):
        """ASSERT-17: After eating, new food is placed on a free cell."""
        state = GameState(
            width=5, height=5,
            snake=[(2, 2), (1, 2), (0, 2)],
            food=(3, 2),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        new_state = step(state, Direction.RIGHT, fixed_rng)
        assert new_state.food not in new_state.snake


class TestGameModuleNoIO:
    def test_no_print_or_input_in_game_module(self):
        """ASSERT-18: game.py must not contain print() or input() calls."""
        import inspect
        import game
        source = inspect.getsource(game)
        assert 'print(' not in source, "game.py should not call print()"
        assert 'input(' not in source, "game.py should not call input()"
