"""
Undertale-style Colored Tile Puzzle System for Water Gym

Tile Colors and Effects:
- PINK (0): Safe to walk on
- RED (1): Sends player back to puzzle start
- YELLOW (2): Electric shock - damages lead Pokemon
- GREEN (3): Triggers wild Pokemon encounter
- BLUE (4): Slippery ice - slides player forward until hitting wall/other tile
- PURPLE (5): Slides player in the direction they're facing
- ORANGE (6): Safe (smells like oranges!)

The puzzle generates a guaranteed solvable path while filling
remaining tiles with hazards based on difficulty.
"""

import random
from enum import IntEnum
from typing import Optional
from dataclasses import dataclass


class TileColor(IntEnum):
    PINK = 0      # Safe
    RED = 1       # Back to start
    YELLOW = 2    # Damage
    GREEN = 3     # Encounter
    BLUE = 4      # Slide forward
    PURPLE = 5    # Slide facing direction
    ORANGE = 6    # Safe


# RGB colors for rendering
TILE_COLORS_RGB = {
    TileColor.PINK: (255, 182, 193),      # Light pink
    TileColor.RED: (220, 20, 60),          # Crimson red
    TileColor.YELLOW: (255, 215, 0),       # Gold yellow
    TileColor.GREEN: (50, 205, 50),        # Lime green
    TileColor.BLUE: (100, 149, 237),       # Cornflower blue
    TileColor.PURPLE: (148, 0, 211),       # Dark violet
    TileColor.ORANGE: (255, 165, 0),       # Orange
}

# Safe tiles that don't harm the player
SAFE_TILES = {TileColor.PINK, TileColor.ORANGE}

# Hazard tiles
HAZARD_TILES = {TileColor.RED, TileColor.YELLOW, TileColor.GREEN}

# Movement tiles
SLIDE_TILES = {TileColor.BLUE, TileColor.PURPLE}


@dataclass
class PuzzleConfig:
    """Configuration for puzzle generation."""
    width: int
    height: int
    difficulty: int  # 1 = Easy, 2 = Medium, 3 = Hard
    start_x: int
    start_y: int
    end_x: int
    end_y: int


class ColoredTilePuzzle:
    """
    Generates and manages a colored tile puzzle.
    
    The puzzle guarantees:
    1. A solvable path from start to end
    2. Difficulty-appropriate hazard distribution
    3. Randomized layout each generation
    """
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.width = config.width
        self.height = config.height
        self.difficulty = config.difficulty
        self.start = (config.start_x, config.start_y)
        self.end = (config.end_x, config.end_y)
        
        # The puzzle grid
        self.grid: list[list[TileColor]] = []
        
        # The solution path (for debugging/hints)
        self.solution_path: list[tuple[int, int]] = []
        
        # Generate the puzzle
        self._generate()
    
    def _generate(self):
        """Generate a new puzzle with guaranteed solution."""
        # Initialize grid with None (will be filled)
        self.grid = [[None for _ in range(self.width)] for _ in range(self.height)]
        
        # Step 1: Generate a solvable path
        self._generate_solution_path()
        
        # Step 2: Mark solution path as safe tiles
        for x, y in self.solution_path:
            # Mix of pink and orange for safe path
            self.grid[y][x] = random.choice([TileColor.PINK, TileColor.ORANGE])
        
        # Step 3: Fill remaining tiles based on difficulty
        self._fill_hazards()
        
        # Step 4: Ensure start and end are always safe
        self.grid[self.start[1]][self.start[0]] = TileColor.PINK
        self.grid[self.end[1]][self.end[0]] = TileColor.PINK
    
    def _generate_solution_path(self):
        """Generate a guaranteed solvable path using modified A* with randomization."""
        self.solution_path = []
        
        # Use a randomized path finding that prefers interesting routes
        current = self.start
        visited = {current}
        self.solution_path.append(current)
        
        while current != self.end:
            x, y = current
            
            # Get valid neighbors (within bounds, not visited)
            neighbors = []
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in visited:
                        # Calculate distance to end for heuristic
                        dist = abs(nx - self.end[0]) + abs(ny - self.end[1])
                        neighbors.append((nx, ny, dist))
            
            if not neighbors:
                # Dead end - backtrack
                if len(self.solution_path) > 1:
                    self.solution_path.pop()
                    current = self.solution_path[-1]
                    continue
                else:
                    # Can't find path - use direct path
                    self._generate_direct_path()
                    return
            
            # Sort by distance but add randomness
            neighbors.sort(key=lambda n: n[2] + random.randint(0, 3))
            
            # Pick one of the better options (not always the best for variety)
            if len(neighbors) > 1 and random.random() < 0.3:
                next_pos = neighbors[1][:2]
            else:
                next_pos = neighbors[0][:2]
            
            visited.add(next_pos)
            self.solution_path.append(next_pos)
            current = next_pos
        
        # Add some extra safe tiles adjacent to path for easier navigation
        self._add_buffer_tiles()
    
    def _generate_direct_path(self):
        """Fallback: generate a simple direct path."""
        self.solution_path = [self.start]
        x, y = self.start
        
        while (x, y) != self.end:
            if x < self.end[0]:
                x += 1
            elif x > self.end[0]:
                x -= 1
            elif y < self.end[1]:
                y += 1
            elif y > self.end[1]:
                y -= 1
            self.solution_path.append((x, y))
    
    def _add_buffer_tiles(self):
        """Add some safe buffer tiles adjacent to the solution path."""
        buffer_tiles = set()
        
        # Based on difficulty, add fewer or more buffer tiles
        buffer_chance = {1: 0.5, 2: 0.3, 3: 0.15}[self.difficulty]
        
        for x, y in self.solution_path:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.width and 0 <= ny < self.height:
                    if (nx, ny) not in self.solution_path:
                        if random.random() < buffer_chance:
                            buffer_tiles.add((nx, ny))
        
        # Add buffer tiles to solution path for marking as safe
        for tile in buffer_tiles:
            if tile not in self.solution_path:
                self.solution_path.append(tile)
    
    def _fill_hazards(self):
        """Fill non-path tiles with hazards based on difficulty."""
        # Difficulty settings
        hazard_weights = {
            1: {  # Easy
                TileColor.PINK: 40,
                TileColor.ORANGE: 30,
                TileColor.RED: 10,
                TileColor.YELLOW: 5,
                TileColor.GREEN: 5,
                TileColor.BLUE: 5,
                TileColor.PURPLE: 5,
            },
            2: {  # Medium
                TileColor.PINK: 25,
                TileColor.ORANGE: 15,
                TileColor.RED: 20,
                TileColor.YELLOW: 10,
                TileColor.GREEN: 10,
                TileColor.BLUE: 10,
                TileColor.PURPLE: 10,
            },
            3: {  # Hard
                TileColor.PINK: 10,
                TileColor.ORANGE: 10,
                TileColor.RED: 25,
                TileColor.YELLOW: 15,
                TileColor.GREEN: 15,
                TileColor.BLUE: 15,
                TileColor.PURPLE: 10,
            },
        }
        
        weights = hazard_weights[self.difficulty]
        tile_choices = list(weights.keys())
        tile_weights = list(weights.values())
        
        for y in range(self.height):
            for x in range(self.width):
                if self.grid[y][x] is None:
                    self.grid[y][x] = random.choices(tile_choices, tile_weights)[0]
    
    def get_tile(self, x: int, y: int) -> Optional[TileColor]:
        """Get the tile color at position."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return None
    
    def get_tile_effect(self, x: int, y: int, facing_direction: str) -> dict:
        """
        Get the effect of stepping on a tile.
        
        Returns a dict with:
        - 'safe': bool - whether the tile is safe
        - 'effect': str - the effect type
        - 'slide_direction': tuple - direction to slide (if applicable)
        - 'damage': int - damage to deal (if applicable)
        """
        tile = self.get_tile(x, y)
        if tile is None:
            return {'safe': False, 'effect': 'out_of_bounds'}
        
        result = {'safe': True, 'effect': 'none', 'slide_direction': None, 'damage': 0}
        
        if tile == TileColor.PINK or tile == TileColor.ORANGE:
            result['effect'] = 'safe'
            
        elif tile == TileColor.RED:
            result['safe'] = False
            result['effect'] = 'reset'
            
        elif tile == TileColor.YELLOW:
            result['safe'] = False
            result['effect'] = 'shock'
            result['damage'] = 10  # 10% HP damage
            
        elif tile == TileColor.GREEN:
            result['safe'] = False
            result['effect'] = 'encounter'
            
        elif tile == TileColor.BLUE:
            result['effect'] = 'slide'
            # Slide in the direction player was moving
            result['slide_direction'] = self._get_direction_vector(facing_direction)
            
        elif tile == TileColor.PURPLE:
            result['effect'] = 'slide_facing'
            # Slide in the direction player is facing
            result['slide_direction'] = self._get_direction_vector(facing_direction)
        
        return result
    
    def _get_direction_vector(self, direction: str) -> tuple[int, int]:
        """Convert direction string to vector."""
        directions = {
            'up': (0, -1),
            'down': (0, 1),
            'left': (-1, 0),
            'right': (1, 0),
        }
        return directions.get(direction, (0, 0))
    
    def calculate_slide(self, start_x: int, start_y: int, direction: tuple[int, int]) -> tuple[int, int]:
        """Calculate where a slide ends."""
        x, y = start_x, start_y
        dx, dy = direction
        
        # Slide until hitting a wall or non-slide tile
        while True:
            next_x, next_y = x + dx, y + dy
            
            # Check bounds
            if not (0 <= next_x < self.width and 0 <= next_y < self.height):
                break
            
            next_tile = self.grid[next_y][next_x]
            
            # Stop at certain tiles
            if next_tile in {TileColor.RED, TileColor.PINK, TileColor.ORANGE}:
                x, y = next_x, next_y
                break
            
            # Continue sliding on blue/purple
            if next_tile in {TileColor.BLUE, TileColor.PURPLE}:
                x, y = next_x, next_y
                continue
            
            # Stop at hazards but land on them
            x, y = next_x, next_y
            break
        
        return x, y
    
    def is_at_end(self, x: int, y: int) -> bool:
        """Check if position is at the puzzle end."""
        return (x, y) == self.end
    
    def to_string(self) -> str:
        """Convert puzzle to string for debugging."""
        symbols = {
            TileColor.PINK: 'P',
            TileColor.RED: 'R',
            TileColor.YELLOW: 'Y',
            TileColor.GREEN: 'G',
            TileColor.BLUE: 'B',
            TileColor.PURPLE: 'V',
            TileColor.ORANGE: 'O',
        }
        
        lines = []
        for y in range(self.height):
            row = ''
            for x in range(self.width):
                if (x, y) == self.start:
                    row += 'S'
                elif (x, y) == self.end:
                    row += 'E'
                else:
                    row += symbols.get(self.grid[y][x], '?')
            lines.append(row)
        return '\n'.join(lines)


class PuzzleManager:
    """
    Manages multiple puzzles in the Water Gym.
    """
    
    def __init__(self):
        self.puzzles: dict[int, ColoredTilePuzzle] = {}
        self.current_puzzle_id: int = 0
        self.player_puzzle_position: tuple[int, int] = (0, 0)
        
    def create_puzzle(self, puzzle_id: int, config: PuzzleConfig) -> ColoredTilePuzzle:
        """Create a new puzzle with given config."""
        puzzle = ColoredTilePuzzle(config)
        self.puzzles[puzzle_id] = puzzle
        return puzzle
    
    def get_puzzle(self, puzzle_id: int) -> Optional[ColoredTilePuzzle]:
        """Get a puzzle by ID."""
        return self.puzzles.get(puzzle_id)
    
    def regenerate_puzzle(self, puzzle_id: int) -> Optional[ColoredTilePuzzle]:
        """Regenerate a puzzle (e.g., after stepping on red tile)."""
        if puzzle_id in self.puzzles:
            old_puzzle = self.puzzles[puzzle_id]
            new_puzzle = ColoredTilePuzzle(old_puzzle.config)
            self.puzzles[puzzle_id] = new_puzzle
            return new_puzzle
        return None
    
    def enter_puzzle(self, puzzle_id: int):
        """Enter a puzzle area."""
        self.current_puzzle_id = puzzle_id
        puzzle = self.get_puzzle(puzzle_id)
        if puzzle:
            self.player_puzzle_position = puzzle.start
    
    def is_in_puzzle(self) -> bool:
        """Check if player is currently in a puzzle."""
        return self.current_puzzle_id > 0
    
    def exit_puzzle(self):
        """Exit current puzzle."""
        self.current_puzzle_id = 0


# Pre-defined puzzle configurations for the Water Gym
# One large puzzle covering (2,14) to (24,41) = 23x28 tiles
WATER_GYM_PUZZLES = {
    1: PuzzleConfig(
        width=23,      # x: 2 to 24 inclusive
        height=28,     # y: 14 to 41 inclusive
        difficulty=2,  # Medium difficulty for large puzzle
        start_x=11,    # Bottom center (middle of width)
        start_y=27,    # Bottom row (0-indexed)
        end_x=11,      # Top center
        end_y=0,       # Top row
    ),
}


def create_water_gym_puzzles() -> PuzzleManager:
    """Create all puzzles for the Water Gym."""
    manager = PuzzleManager()
    
    for puzzle_id, config in WATER_GYM_PUZZLES.items():
        manager.create_puzzle(puzzle_id, config)
    
    return manager


# Test the puzzle generation
if __name__ == "__main__":
    print("Testing Colored Tile Puzzle Generation")
    print("=" * 50)
    
    for puzzle_id, config in WATER_GYM_PUZZLES.items():
        print(f"\nPuzzle {puzzle_id} (Difficulty: {config.difficulty})")
        print(f"Size: {config.width}x{config.height}")
        puzzle = ColoredTilePuzzle(config)
        print(puzzle.to_string())
        print(f"Solution path length: {len(puzzle.solution_path)}")