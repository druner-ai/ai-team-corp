import sys
import select
import termios
import tty
import random
import argparse
from game import Game
from renderer import render


def main():
    # Fixed: use parse_known_args() to ignore pytest's command-line arguments
    # that would otherwise cause argparse to exit with code 2.
    parser = argparse.ArgumentParser()
    parser.add_argument('--width', type=int, default=20)
    parser.add_argument('--height', type=int, default=10)
    args, _ = parser.parse_known_args()

    rng = random.Random()
    game = Game(args.width, args.height, rng)

    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        while True:
            frame = render(game.state)
            sys.stdout.write('\n'.join(frame) + '\n')
            sys.stdout.flush()

            if game.state.game_over:
                break

            # Non-blocking input with a small timeout
            ready, _, _ = select.select([sys.stdin], [], [], 0.1)
            if ready:
                ch = sys.stdin.read(1)
                if ch == 'q':
                    break
                # Map wasd to directions (not strictly required by these tests
                # but keeps the game playable)
                direction = None
                if ch == 'w':
                    direction = game.Direction.UP
                elif ch == 's':
                    direction = game.Direction.DOWN
                elif ch == 'a':
                    direction = game.Direction.LEFT
                elif ch == 'd':
                    direction = game.Direction.RIGHT
                if direction is not None:
                    game.step(direction)
                else:
                    game.step()
            else:
                game.step()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

    print(f'Game Over! Score: {game.state.score}')
    sys.exit(0)


if __name__ == '__main__':
    main()
