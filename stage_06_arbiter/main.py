"""Main entry point for the Snake game."""
import sys
import tty
import termios
import select
import random
import argparse
from game import Direction, init_state, step as game_step
from input_buffer import InputBuffer
from renderer import render


class Game:
    """Wrapper for game logic."""

    def __init__(self, width=20, height=10, rng=None):
        if rng is None:
            rng = random.Random()
        self.width = width
        self.height = height
        self.rng = rng
        self.state = init_state(width, height, rng)

    def step(self, direction):
        """Advance the game by one step in the given direction."""
        self.state = game_step(self.state, direction, self.rng)
        return self.state


def main():
    """Run the Snake game."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--width', type=int, default=20)
    parser.add_argument('--height', type=int, default=10)
    args, _ = parser.parse_known_args()

    rng = random.Random()
    game = Game(args.width, args.height, rng)
    buf = InputBuffer()

    old_settings = None
    try:
        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            tty.setraw(fd)
        except Exception:
            pass

        while True:
            rlist, _, _ = select.select([sys.stdin], [], [], 0.1)

            if rlist:
                key = sys.stdin.read(1)
                if key == 'q':
                    print(f'Game Over! Score: {game.state.score}')
                    sys.exit(0)

                direction = None
                if key in ('\x1b[A', 'w'):
                    direction = Direction.UP
                elif key in ('\x1b[B', 's'):
                    direction = Direction.DOWN
                elif key in ('\x1b[D', 'a'):
                    direction = Direction.LEFT
                elif key in ('\x1b[C', 'd'):
                    direction = Direction.RIGHT

                if direction is not None:
                    buf.push(direction, game.state.direction)

            direction = buf.pop(game.state.direction)
            new_state = game.step(direction)

            if new_state.game_over:
                print(f'Game Over! Score: {new_state.score}')
                sys.exit(0)

            frame = render(new_state)
            print('\n'.join(frame))
    finally:
        if old_settings is not None:
            try:
                fd = sys.stdin.fileno()
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass


if __name__ == '__main__':
    main()
