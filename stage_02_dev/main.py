#!/usr/bin/env python3
"""
Snake Game - Console Edition.
Entry point: handles input, game loop, rendering.
"""
import sys
import os
import tty
import termios
import select
import random
import argparse

from game import Direction, GameState, init_state, step
from input_buffer import InputBuffer
from renderer import render


class Game:
    """
    Game coordinator class.
    Wraps the pure game logic with input handling and rendering for testability.
    """

    def __init__(self, width: int = 20, height: int = 10, rng: random.Random = None):
        self.width = width
        self.height = height
        self.rng = rng or random.Random()
        self.state = init_state(width, height, self.rng)
        self.input_buffer = InputBuffer()

    def step(self, direction: Direction | None) -> GameState:
        """
        Advance the game by one tick.
        Uses the input buffer to determine the effective direction.
        """
        # Get direction from buffer
        if direction is not None:
            self.input_buffer.push(direction, self.state.direction)

        effective_dir = self.input_buffer.pop(self.state.direction)
        self.state = step(self.state, effective_dir, self.rng)
        return self.state

    def push_input(self, direction: Direction) -> None:
        """Queue a direction input."""
        self.input_buffer.push(direction, self.state.direction)


# Mapping of key inputs to directions
KEY_MAP = {
    '\x1b[A': Direction.UP,    # Up arrow
    '\x1b[B': Direction.DOWN,  # Down arrow
    '\x1b[C': Direction.RIGHT, # Right arrow
    '\x1b[D': Direction.LEFT,  # Left arrow
    'w': Direction.UP,
    'W': Direction.UP,
    's': Direction.DOWN,
    'S': Direction.DOWN,
    'a': Direction.LEFT,
    'A': Direction.LEFT,
    'd': Direction.RIGHT,
    'D': Direction.RIGHT,
}


def read_key() -> str | None:
    """
    Non-blocking read of a single keypress.
    Returns the character(s) read, or None if no input available.
    """
    if select.select([sys.stdin], [], [], 0)[0]:
        return sys.stdin.read(1)
    return None


def read_arrow_key(first_char: str) -> str:
    """
    Read a potential escape sequence for arrow keys.
    Called when first_char is '\x1b' (escape).
    """
    # Try to read the next characters with a short timeout
    if select.select([sys.stdin], [], [], 0.01)[0]:
        second = sys.stdin.read(1)
        if second == '[':
            if select.select([sys.stdin], [], [], 0.01)[0]:
                third = sys.stdin.read(1)
                return '\x1b[' + third
    return first_char  # Just escape alone


def main():
    parser = argparse.ArgumentParser(description='Snake Game - Console Edition')
    parser.add_argument('--width', type=int, default=20, help='Field width')
    parser.add_argument('--height', type=int, default=10, help='Field height')
    args = parser.parse_args()

    rng = random.Random()
    game = Game(width=args.width, height=args.height, rng=rng)

    # Save terminal settings
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)

        # Clear screen and hide cursor
        sys.stdout.write('\033[2J\033[H\033[?25l')
        sys.stdout.flush()

        tick_duration = 0.15  # 150 ms

        while not game.state.game_over:
            # Move cursor to home position
            sys.stdout.write('\033[H')
            sys.stdout.flush()

            # Render and print frame
            frame = render(game.state)
            for line in frame:
                sys.stdout.write(line + '\r\n')
            sys.stdout.flush()

            # Wait for input with timeout
            ready, _, _ = select.select([sys.stdin], [], [], tick_duration)

            if ready:
                char = sys.stdin.read(1)
                if char == 'q' or char == 'Q':
                    break
                elif char == '\x1b':
                    # Escape sequence (arrow keys)
                    seq = read_arrow_key(char)
                    direction = KEY_MAP.get(seq)
                    if direction:
                        game.push_input(direction)
                else:
                    direction = KEY_MAP.get(char)
                    if direction:
                        game.push_input(direction)

            # Advance game state
            game.step(None)

    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # Show cursor
        sys.stdout.write('\033[?25h')
        sys.stdout.flush()

    # Print game over message
    print(f'Game Over! Score: {game.state.score}')
    sys.exit(0)


if __name__ == '__main__':
    main()
