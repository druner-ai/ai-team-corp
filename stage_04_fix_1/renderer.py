from game import GameState


def render(state: GameState) -> list[str]:
    width, height = state.width, state.height
    # Create empty grid
    grid = [[' ' for _ in range(width)] for _ in range(height)]

    # Draw food
    fx, fy = state.food
    if 0 <= fx < width and 0 <= fy < height:
        grid[fy][fx] = '*'

    # Draw snake
    for i, (x, y) in enumerate(state.snake):
        if 0 <= x < width and 0 <= y < height:
            # Fixed: head is '@', body is 'O'
            grid[y][x] = '@' if i == 0 else 'O'

    # Add borders
    border = '#' * (width + 2)
    lines = [border]
    for row in grid:
        lines.append('#' + ''.join(row) + '#')
    lines.append(border)

    return lines
