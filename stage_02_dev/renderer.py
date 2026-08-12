from game import GameState


def render(state: GameState) -> list[str]:
    """
    Render the game state into a list of strings.
    Each string is one row of the field including borders.
    """
    width = state.width
    height = state.height

    # Create a 2D grid of spaces
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Place food
    fx, fy = state.food
    if 0 <= fx < width and 0 <= fy < height:
        grid[fy][fx] = '*'

    # Place snake body (from tail to head, so head overwrites body if overlap)
    for i, (sx, sy) in enumerate(reversed(state.snake)):
        if 0 <= sx < width and 0 <= sy < height:
            if i == 0:  # head (last in reversed order = head)
                grid[sy][sx] = '@'
            else:
                grid[sy][sx] = 'O'

    # Build frame with borders
    border_row = '#' * (width + 2)
    frame = [border_row]
    for row in grid:
        frame.append('#' + ''.join(row) + '#')
    frame.append(border_row)

    return frame
