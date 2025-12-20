"""
Puzzles module for Water Gym and other puzzle mechanics.
"""

from .colored_tile_puzzle import ColoredTilePuzzle, TileColor, PuzzleConfig, WATER_GYM_PUZZLES
from .puzzle_ui import PuzzleUI
from .water_gym_manager import WaterGymManager, WaterGymState

__all__ = [
    'ColoredTilePuzzle',
    'TileColor',
    'PuzzleConfig',
    'WATER_GYM_PUZZLES',
    'PuzzleUI',
    'WaterGymManager',
    'WaterGymState'
]