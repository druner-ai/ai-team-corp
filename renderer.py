"""Renderer module: renders game state as a list of strings."""


def render(state):
    """Render the game state as a list of strings (frame).

    Each string is one row of the field. Borders are '#', empty cells are ' ',
    snake body segments are 'O', head is '@', food is '*'.
    """
    width = state.width
    height = state.height

    grid = [[' ' for _ in range(width)] for _ in range(height)]

    fx, fy = state.food
    grid[fy][fx] = '*'

    for i, (sx, sy) in enumerate(state.snake):
        if i == 0:
            grid[sy][sx] = '@'
        else:
            grid[sy][sx] = 'O'

    frame = []
    frame.append('#' * (width + 2))
    for row in grid:
        frame.append('#' + ''.join(row) + '#')
    frame.append('#' * (width + 2))

    return frame
