"""Tests for renderer: frame dimensions, symbols, snake and food rendering."""
import pytest
from renderer import render
from game import GameState, Direction


class TestRenderer:
    def test_frame_height(self):
        """ASSERT-12: render returns a list of height+2 lines (including borders)."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        assert len(frame) == 12  # 10 + 2

    def test_line_width(self):
        """ASSERT-13: Each line has length width+2 (including side borders)."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        for line in frame:
            assert len(line) == 22  # 20 + 2

    def test_border_symbols(self):
        """ASSERT-14: Borders are '#' characters."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        # Top and bottom rows are all '#'
        assert frame[0] == '#' * 22
        assert frame[-1] == '#' * 22
        # Side borders on interior rows
        for line in frame[1:-1]:
            assert line[0] == '#'
            assert line[-1] == '#'

    def test_snake_head_symbol(self):
        """ASSERT-14: Head is '@'."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        # Head at (10,5) -> row index 5+1=6 (0-indexed, plus top border), column 10+1=11
        assert frame[6][11] == '@'

    def test_snake_body_symbol(self):
        """ASSERT-14: Body segments are 'O'."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        # Body at (9,5) -> row 6, col 10
        assert frame[6][10] == 'O'
        # Body at (8,5) -> row 6, col 9
        assert frame[6][9] == 'O'

    def test_food_symbol(self):
        """ASSERT-14: Food is '*'."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        # Food at (15,5) -> row 6, col 16
        assert frame[6][16] == '*'

    def test_empty_cell_is_space(self):
        """ASSERT-14: Empty cells are spaces."""
        state = GameState(
            width=20, height=10,
            snake=[(10, 5), (9, 5), (8, 5)],
            food=(15, 5),
            score=0,
            game_over=False,
            direction=Direction.RIGHT
        )
        frame = render(state)
        # An empty cell, e.g., (0,0) -> row 1, col 1
        assert frame[1][1] == ' '
