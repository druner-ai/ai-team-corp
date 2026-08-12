"""Integration tests for main.py: exit codes, game over message, quit key."""
import pytest
import sys
import io
from unittest.mock import patch, MagicMock
import main


class TestMain:
    def test_quit_key_exits_with_code_0(self):
        """ASSERT-01: Pressing 'q' exits with code 0."""
        # Simulate input: first 'q' then nothing
        with patch('sys.stdin', io.StringIO('q\n')), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('select.select', return_value=([sys.stdin], [], [])), \
             patch('termios.tcgetattr'), \
             patch('termios.tcsetattr'), \
             patch('tty.setraw'), \
             patch('random.Random') as mock_random:
            # Mock Random to return a fixed seed instance
            mock_random.return_value = __import__('random').Random(42)
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0

    def test_game_over_exits_with_code_0(self):
        """ASSERT-02: Game over (collision) exits with code 0."""
        # We need to simulate a game that immediately ends.
        # We can mock the game.step to return game_over=True after first step.
        with patch('main.Game') as MockGame, \
             patch('sys.stdin', io.StringIO('')), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('select.select', return_value=([], [], [])), \
             patch('termios.tcgetattr'), \
             patch('termios.tcsetattr'), \
             patch('tty.setraw'), \
             patch('random.Random') as mock_random:
            mock_random.return_value = __import__('random').Random(42)
            # Configure the mock game to be over after one step
            mock_game_instance = MockGame.return_value
            mock_game_instance.step.return_value.game_over = True
            mock_game_instance.step.return_value.score = 0
            with pytest.raises(SystemExit) as exc_info:
                main.main()
            assert exc_info.value.code == 0

    def test_prints_game_over_score_on_quit(self):
        """ASSERT-03: On quit, prints 'Game Over! Score: <score>'."""
        with patch('sys.stdin', io.StringIO('q\n')), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('select.select', return_value=([sys.stdin], [], [])), \
             patch('termios.tcgetattr'), \
             patch('termios.tcsetattr'), \
             patch('tty.setraw'), \
             patch('random.Random') as mock_random:
            mock_random.return_value = __import__('random').Random(42)
            with pytest.raises(SystemExit):
                main.main()
            output = mock_stdout.getvalue()
            assert 'Game Over! Score:' in output

    def test_prints_game_over_score_on_collision(self):
        """ASSERT-03: On game over, prints 'Game Over! Score: <score>'."""
        with patch('main.Game') as MockGame, \
             patch('sys.stdin', io.StringIO('')), \
             patch('sys.stdout', new_callable=io.StringIO) as mock_stdout, \
             patch('select.select', return_value=([], [], [])), \
             patch('termios.tcgetattr'), \
             patch('termios.tcsetattr'), \
             patch('tty.setraw'), \
             patch('random.Random') as mock_random:
            mock_random.return_value = __import__('random').Random(42)
            mock_game_instance = MockGame.return_value
            mock_game_instance.step.return_value.game_over = True
            mock_game_instance.step.return_value.score = 30
            with pytest.raises(SystemExit):
                main.main()
            output = mock_stdout.getvalue()
            assert 'Game Over! Score: 30' in output
