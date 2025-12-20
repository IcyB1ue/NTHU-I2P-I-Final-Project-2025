"""
Water Gym Manager

Handles all Water Gym specific mechanics including:
- Corrupted trainer encounter (day/night)
- Colored tile puzzles
- Prison room and real gym leader
- Teleportation between water_map and water_gym
"""

import pygame as pg
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum, auto

from src.utils import GameSettings, Logger, Position
from src.core.services import input_manager


class WaterGymState(Enum):
    """States of the Water Gym quest."""
    NOT_STARTED = auto()      # Haven't entered gym yet
    BLOCKED_BY_TRAINER = auto()  # Corrupted trainer blocks path (day)
    SNEAK_MODE = auto()       # Night time, can sneak past
    PUZZLE_1 = auto()         # In puzzle 1
    PUZZLE_1_COMPLETE = auto()
    PUZZLE_2 = auto()         # In puzzle 2
    PUZZLE_2_COMPLETE = auto()
    PUZZLE_3 = auto()         # In puzzle 3
    PUZZLE_3_COMPLETE = auto()
    PRISON_ROOM = auto()      # Found the real gym leader
    LEADER_RESCUED = auto()   # Rescued the leader
    COMPLETED = auto()        # Quest complete


@dataclass
class PuzzleZone:
    """Defines a puzzle zone in the gym."""
    puzzle_id: int
    x_start: int
    y_start: int
    x_end: int
    y_end: int
    puzzle_grid_x: int  # Where puzzle grid starts in world coords
    puzzle_grid_y: int


class WaterGymManager:
    """
    Manages all Water Gym mechanics and state.
    """
    
    def __init__(self):
        self.state = WaterGymState.NOT_STARTED
        self.is_night = False
        
        # Corrupted trainer position (in water_gym.tmx)
        self.corrupted_trainer_pos = (3, 49)  # Near entrance, facing left
        
        # Misty (real gym leader) position
        self.real_leader_pos = (1, 4)
        
        # Puzzle zone - one large puzzle covering (2,14) to (24,41)
        self.puzzle_zones = {
            1: PuzzleZone(
                puzzle_id=1,
                x_start=2, y_start=14,
                x_end=24, y_end=41,
                puzzle_grid_x=2, puzzle_grid_y=14  # World position of puzzle top-left
            ),
        }
        
        # Puzzle completion status
        self.puzzles_completed = {1: False}
        
        # Current active puzzle
        self.current_puzzle_id: int = 0
        
        # Real gym leader position (prison room)
        self.real_leader_pos = (12, 5)
        
        # Teleporter positions
        # From water_map.tmx to water_gym.tmx
        self.gym_entrance_water_map = (41, 29)  # In water_map
        self.gym_spawn_position = (12, 48)  # Where player spawns in water_gym
        
        # From water_gym.tmx back to water_map.tmx
        self.gym_exit_position = (12, 49)  # Exit tile in water_gym
        self.water_map_return_position = (41, 30)  # Where to spawn in water_map
        
        # Callbacks
        self.on_state_change: Optional[Callable[[WaterGymState], None]] = None
        self.on_dialogue: Optional[Callable[[list[str]], None]] = None
        self.on_battle_start: Optional[Callable[[str], None]] = None
        
        # Interaction cooldown
        self.interaction_cooldown: float = 0.0
    
    def set_night_mode(self, is_night: bool):
        """Set whether it's night time (affects gym access)."""
        was_night = self.is_night
        self.is_night = is_night
        
        if is_night and not was_night:
            if self.state == WaterGymState.BLOCKED_BY_TRAINER:
                self._set_state(WaterGymState.SNEAK_MODE)
                if self.on_dialogue:
                    self.on_dialogue([
                        "The corrupted trainer seems to be asleep...",
                        "Now's your chance to sneak past!",
                        "Be careful not to make any noise!"
                    ])
    
    def _set_state(self, new_state: WaterGymState):
        """Change the gym state."""
        old_state = self.state
        self.state = new_state
        Logger.info(f"Water Gym state changed: {old_state.name} -> {new_state.name}")
        
        if self.on_state_change:
            self.on_state_change(new_state)
    
    def enter_gym(self):
        """Called when player enters the water gym."""
        if self.state == WaterGymState.NOT_STARTED:
            self._set_state(WaterGymState.BLOCKED_BY_TRAINER)
            
            if self.on_dialogue:
                self.on_dialogue([
                    "You've entered the Water Gym!",
                    "But wait... something feels wrong.",
                    "A corrupted Blastoise trainer blocks the path!",
                    "You'll need to find another way through...",
                    "Perhaps at night, when they're asleep?"
                ])
    
    def check_trainer_collision(self, player_x: int, player_y: int) -> bool:
        """Check if player is trying to walk into the corrupted trainer."""
        if self.state not in (WaterGymState.BLOCKED_BY_TRAINER, WaterGymState.SNEAK_MODE):
            return False
        
        # If it's night (sneak mode), trainer doesn't block
        if self.is_night:
            return False
        
        tx, ty = self.corrupted_trainer_pos
        # Check if player is within 1 tile of trainer
        if abs(player_x - tx) <= 1 and abs(player_y - ty) <= 1:
            return True
        
        return False
    
    def interact_with_trainer(self) -> bool:
        """Interact with the corrupted trainer."""
        if self.state == WaterGymState.BLOCKED_BY_TRAINER and not self.is_night:
            if self.on_dialogue:
                self.on_dialogue([
                    "Corrupted Blastoise Trainer: GRAAAHHH!",
                    "The corruption has taken hold... They won't let you pass!",
                    "Maybe if you wait until nightfall..."
                ])
            return True
        return False
    
    def check_puzzle_zone(self, player_x: int, player_y: int) -> int:
        """Check if player is in a puzzle zone. Returns puzzle ID or 0."""
        for puzzle_id, zone in self.puzzle_zones.items():
            if (zone.x_start <= player_x <= zone.x_end and 
                zone.y_start <= player_y <= zone.y_end):
                return puzzle_id
        return 0
    
    def can_enter_puzzle(self, puzzle_id: int) -> bool:
        """Check if player can enter a puzzle."""
        # Must have passed corrupted trainer first (sneak mode or later)
        if self.state in (WaterGymState.NOT_STARTED, WaterGymState.BLOCKED_BY_TRAINER):
            return False
        
        # Can enter puzzle 1 after sneaking past
        if puzzle_id == 1:
            return True
        
        return False
    
    def start_puzzle(self, puzzle_id: int):
        """Start a puzzle."""
        self.current_puzzle_id = puzzle_id
        
        state_map = {
            1: WaterGymState.PUZZLE_1,
            2: WaterGymState.PUZZLE_2,
            3: WaterGymState.PUZZLE_3,
        }
        
        if puzzle_id in state_map:
            self._set_state(state_map[puzzle_id])
        
        Logger.info(f"Started puzzle {puzzle_id}")
    
    def complete_puzzle(self, puzzle_id: int):
        """Mark a puzzle as complete."""
        self.puzzles_completed[puzzle_id] = True
        self.current_puzzle_id = 0
        
        if puzzle_id == 1:
            self._set_state(WaterGymState.PUZZLE_1_COMPLETE)
        
        # Dialogue is handled by game_scene
        Logger.info(f"Completed puzzle {puzzle_id}")
    
    def fail_puzzle(self, puzzle_id: int, reason: str):
        """Handle puzzle failure."""
        if reason == 'shock':
            if self.on_dialogue:
                self.on_dialogue(["Your Pokemon took damage from the electric tile!"])
        elif reason == 'reset':
            # Just reset, message handled by puzzle UI
            pass
        
        Logger.info(f"Failed puzzle {puzzle_id}: {reason}")
    
    def check_prison_room(self, player_x: int, player_y: int) -> bool:
        """Check if player reached the area where Misty is."""
        if not self.puzzles_completed.get(1, False):
            return False
        
        # Misty is at (1, 4), check if player is near top area (y <= 13)
        if player_y <= 13:
            if self.state == WaterGymState.PUZZLE_1_COMPLETE:
                self._set_state(WaterGymState.PRISON_ROOM)
                return True
        
        return False
    
    def interact_with_real_leader(self) -> bool:
        """Interact with Misty (the real gym leader)."""
        if self.state != WaterGymState.PRISON_ROOM:
            return False
        
        self._set_state(WaterGymState.LEADER_RESCUED)
        
        if self.on_dialogue:
            self.on_dialogue([
                "Misty: You made it through the puzzle!",
                "That corrupted Blastoise trainer took over my gym!",
                "I've been trapped here unable to help anyone.",
                "Please, you have to defeat them!",
                "I'll heal your Pokemon first...",
                "...",
                "There! Now go challenge that impostor!",
                "I believe in you!"
            ])
        
        return True
    
    def is_gym_complete(self) -> bool:
        """Check if the gym quest is complete."""
        return self.state == WaterGymState.COMPLETED
    
    def complete_gym(self):
        """Mark the gym as complete (after final battle)."""
        self._set_state(WaterGymState.COMPLETED)
        
        if self.on_dialogue:
            self.on_dialogue([
                "The corruption has been cleansed!",
                "Water Gym Leader: Thank you so much!",
                "Here, take this Water Badge as proof of your victory!",
                "You've proven yourself a true Pokemon trainer!"
            ])
    
    def update(self, dt: float):
        """Update the gym manager."""
        if self.interaction_cooldown > 0:
            self.interaction_cooldown -= dt
    
    def get_state_description(self) -> str:
        """Get a description of the current state for quest UI."""
        descriptions = {
            WaterGymState.NOT_STARTED: "Enter the Water Gym",
            WaterGymState.BLOCKED_BY_TRAINER: "Find a way past the corrupted trainer",
            WaterGymState.SNEAK_MODE: "Sneak past the sleeping trainer!",
            WaterGymState.PUZZLE_1: "Solve the colored tile puzzle",
            WaterGymState.PUZZLE_1_COMPLETE: "Find Misty",
            WaterGymState.PUZZLE_2: "Solve the colored tile puzzle",
            WaterGymState.PUZZLE_2_COMPLETE: "Find Misty",
            WaterGymState.PUZZLE_3: "Solve the colored tile puzzle",
            WaterGymState.PUZZLE_3_COMPLETE: "Find Misty",
            WaterGymState.PRISON_ROOM: "Talk to Misty",
            WaterGymState.LEADER_RESCUED: "Defeat the corrupted trainer",
            WaterGymState.COMPLETED: "Water Gym Complete!",
        }
        return descriptions.get(self.state, "")


# Singleton instance
_water_gym_manager: Optional[WaterGymManager] = None

def get_water_gym_manager() -> WaterGymManager:
    """Get the global WaterGymManager instance."""
    global _water_gym_manager
    if _water_gym_manager is None:
        _water_gym_manager = WaterGymManager()
    return _water_gym_manager