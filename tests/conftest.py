"""Fixtures for Snake game tests."""
import pytest
import random


@pytest.fixture
def fixed_rng():
    """Return a Random instance with a fixed seed for deterministic tests."""
    return random.Random(42)
