"""
Puzzle UI Component for Water Gym Colored Tile Puzzles

This handles rendering the puzzle tiles as an overlay on top of the map
and managing player movement through the puzzle.
"""

import pygame as pg
from typing import Optional, Callable
from src.utils import GameSettings, Logger
from src.core.services import input_manager, sound_manager

# Import the puzzle system using relative imports
from .colored_tile_puzzle import (
    ColoredTilePuzzle, PuzzleConfig, TileColor, 
    TILE_COLORS_RGB, WATER_GYM_PUZZLES, create_water_gym_puzzles
)


class PuzzleUI:
    """
    UI Component for rendering and interacting with colored tile puzzles.
    
    This renders the puzzle as an overlay when the player enters a puzzle zone.
    The actual game player moves with the puzzle dot.
    """
    
    def __init__(self, game_manager=None):
        self.active = False
        self.current_puzzle: Optional[ColoredTilePuzzle] = None
        self.current_puzzle_id: int = 0
        self.game_manager = game_manager  # Reference to game manager for player sync
        
        # Player position within the puzzle grid
        self.player_x: int = 0
        self.player_y: int = 0
        
        # World position where puzzle starts (for rendering offset)
        self.world_start_x: int = 0
        self.world_start_y: int = 0
        
        # Callbacks
        self.on_puzzle_complete: Optional[Callable[[int], None]] = None
        self.on_puzzle_fail: Optional[Callable[[int, str], None]] = None
        self.on_encounter: Optional[Callable[[], None]] = None
        self.on_damage: Optional[Callable[[int], None]] = None  # Damage to lead Pokemon
        
        # Animation state
        self.slide_animation_active = False
        self.slide_start_pos: tuple[int, int] = (0, 0)
        self.slide_end_pos: tuple[int, int] = (0, 0)
        self.slide_progress: float = 0.0
        self.slide_speed: float = 8.0  # Tiles per second
        
        # Visual effects
        self.tile_pulse_timer: float = 0.0
        self.show_hint: bool = False
        self.message: str = ""
        self.message_timer: float = 0.0
        
        # Direction player is facing
        self.facing_direction: str = "up"
        
        # Movement cooldown
        self.move_cooldown: float = 0.0
        self.move_cooldown_time: float = 0.15  # Seconds between moves
        
        # Fonts
        try:
            self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        except:
            self.font = pg.font.Font(None, 20)
            self.title_font = pg.font.Font(None, 28)
    
    def start_puzzle(self, puzzle_id: int, world_x: int, world_y: int):
        """Start a puzzle at the given world position."""
        if puzzle_id not in WATER_GYM_PUZZLES:
            Logger.warning(f"Unknown puzzle ID: {puzzle_id}")
            return
        
        config = WATER_GYM_PUZZLES[puzzle_id]
        self.current_puzzle = ColoredTilePuzzle(config)
        self.current_puzzle_id = puzzle_id
        
        # Set player to start position
        self.player_x = config.start_x
        self.player_y = config.start_y
        
        # Store world position for rendering
        self.world_start_x = world_x
        self.world_start_y = world_y
        
        self.active = True
        self.facing_direction = "up"
        
        # Sync game player to puzzle start position
        self._sync_player_position()
        
        # Show intro message
        difficulty_names = {1: "Easy", 2: "Medium", 3: "Hard"}
        self._show_message(f"Puzzle {puzzle_id} - {difficulty_names[config.difficulty]}")
        
        Logger.info(f"Started puzzle {puzzle_id} at world pos ({world_x}, {world_y})")
    
    def end_puzzle(self, success: bool = False):
        """End the current puzzle."""
        Logger.info(f"end_puzzle called with success={success}")
        
        if success and self.on_puzzle_complete:
            Logger.info("Calling on_puzzle_complete callback...")
            self.on_puzzle_complete(self.current_puzzle_id)
        elif success:
            Logger.warning("Puzzle success but on_puzzle_complete callback not set!")
        
        self.active = False
        self.current_puzzle = None
        self.current_puzzle_id = 0
        
        Logger.info(f"Puzzle ended, active={self.active}")
    
    def reset_puzzle(self):
        """Reset the current puzzle (regenerate and return to start)."""
        if not self.current_puzzle:
            return
        
        config = self.current_puzzle.config
        self.current_puzzle = ColoredTilePuzzle(config)
        self.player_x = config.start_x
        self.player_y = config.start_y
        
        # Sync player position back to start
        self._sync_player_position()
        
        self._show_message("Puzzle Reset!")
        Logger.info("Puzzle reset")
    
    def _show_message(self, text: str, duration: float = 2.0):
        """Show a temporary message."""
        self.message = text
        self.message_timer = duration
    
    def _handle_tile_effect(self, x: int, y: int):
        """Handle the effect of the tile the player stepped on."""
        if not self.current_puzzle:
            Logger.warning("_handle_tile_effect called but no current_puzzle!")
            return
        
        effect = self.current_puzzle.get_tile_effect(x, y, self.facing_direction)
        Logger.info(f"Tile effect at ({x}, {y}): {effect['effect']}")
        
        if effect['effect'] == 'reset':
            self._show_message("Wrong tile! Back to start!")
            self.reset_puzzle()
            if self.on_puzzle_fail:
                self.on_puzzle_fail(self.current_puzzle_id, 'reset')
            return  # Don't check end after reset
        
        elif effect['effect'] == 'shock':
            self._show_message("ZAP! Your Pokemon took damage!")
            # Deal 20 damage to lead Pokemon
            if self.on_damage:
                self.on_damage(20)
            else:
                Logger.warning("on_damage callback not set!")
            if self.on_puzzle_fail:
                self.on_puzzle_fail(self.current_puzzle_id, 'shock')
        
        elif effect['effect'] == 'encounter':
            self._show_message("Wild Pokemon appeared!")
            if self.on_encounter:
                self.on_encounter()
            else:
                Logger.warning("on_encounter callback not set!")
            return  # Don't check end after encounter (puzzle will resume)
        
        elif effect['effect'] in ('slide', 'slide_facing'):
            # Start sliding
            direction = effect['slide_direction']
            if direction and direction != (0, 0):
                end_x, end_y = self.current_puzzle.calculate_slide(x, y, direction)
                if (end_x, end_y) != (x, y):
                    self._start_slide(x, y, end_x, end_y)
            return  # Don't check end during slide (will be checked after slide)
        
        # Check if reached the end (only for safe tiles)
        if self.current_puzzle and self.current_puzzle.is_at_end(x, y):
            Logger.info(f"Player reached end at ({x}, {y})! Completing puzzle...")
            self._show_message("Puzzle Complete!")
            self.end_puzzle(success=True)
    
    def _start_slide(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Start a sliding animation."""
        self.slide_animation_active = True
        self.slide_start_pos = (start_x, start_y)
        self.slide_end_pos = (end_x, end_y)
        self.slide_progress = 0.0
        Logger.info(f"Starting slide from ({start_x}, {start_y}) to ({end_x}, {end_y})")
    
    def _try_move(self, dx: int, dy: int):
        """Try to move the player in the given direction."""
        if not self.current_puzzle or self.slide_animation_active:
            return
        
        if self.move_cooldown > 0:
            return
        
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        
        # Update facing direction
        if dy < 0:
            self.facing_direction = "up"
        elif dy > 0:
            self.facing_direction = "down"
        elif dx < 0:
            self.facing_direction = "left"
        elif dx > 0:
            self.facing_direction = "right"
        
        # Check bounds
        if not (0 <= new_x < self.current_puzzle.width and 
                0 <= new_y < self.current_puzzle.height):
            return
        
        # Move player
        self.player_x = new_x
        self.player_y = new_y
        self.move_cooldown = self.move_cooldown_time
        
        # Sync actual game player position
        self._sync_player_position()
        
        # Handle tile effect
        self._handle_tile_effect(new_x, new_y)
    
    def _sync_player_position(self):
        """Sync the game player's position with the puzzle player position."""
        if self.game_manager and self.game_manager.player:
            from src.utils import GameSettings, Direction, Position
            # Calculate world position from puzzle position
            world_x = (self.world_start_x + self.player_x) * GameSettings.TILE_SIZE
            world_y = (self.world_start_y + self.player_y) * GameSettings.TILE_SIZE
            
            # Update player position
            self.game_manager.player.position.x = world_x
            self.game_manager.player.position.y = world_y
            
            # Update player facing direction
            direction_map = {
                "up": Direction.UP,
                "down": Direction.DOWN,
                "left": Direction.LEFT,
                "right": Direction.RIGHT
            }
            if self.facing_direction in direction_map:
                self.game_manager.player.direction = direction_map[self.facing_direction]
            
            # Update animation position so sprite follows
            if hasattr(self.game_manager.player, 'animation'):
                self.game_manager.player.animation.update_pos(Position(world_x, world_y))
            
            # Directly set camera position to center on player
            if hasattr(self.game_manager.player, 'camera'):
                self.game_manager.player.camera.x = int(world_x - GameSettings.SCREEN_WIDTH // 2)
                self.game_manager.player.camera.y = int(world_y - GameSettings.SCREEN_HEIGHT // 2)
    
    def _sync_player_position_during_slide(self):
        """Sync the game player's position during a slide animation."""
        if self.game_manager and self.game_manager.player and self.slide_animation_active:
            from src.utils import GameSettings, Position
            # Interpolate position during slide
            px = self.slide_start_pos[0] + (self.slide_end_pos[0] - self.slide_start_pos[0]) * min(1.0, self.slide_progress)
            py = self.slide_start_pos[1] + (self.slide_end_pos[1] - self.slide_start_pos[1]) * min(1.0, self.slide_progress)
            world_x = (self.world_start_x + px) * GameSettings.TILE_SIZE
            world_y = (self.world_start_y + py) * GameSettings.TILE_SIZE
            
            # Update player position
            self.game_manager.player.position.x = world_x
            self.game_manager.player.position.y = world_y
            
            # Update animation position so sprite follows
            if hasattr(self.game_manager.player, 'animation'):
                self.game_manager.player.animation.update_pos(Position(world_x, world_y))
            
            # Directly set camera position to center on player
            if hasattr(self.game_manager.player, 'camera'):
                self.game_manager.player.camera.x = int(world_x - GameSettings.SCREEN_WIDTH // 2)
                self.game_manager.player.camera.y = int(world_y - GameSettings.SCREEN_HEIGHT // 2)
    
    def update(self, dt: float):
        """Update the puzzle UI state."""
        if not self.active:
            return
        
        # Update timers
        self.tile_pulse_timer += dt
        
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""
        
        if self.move_cooldown > 0:
            self.move_cooldown -= dt
        
        # Handle slide animation
        if self.slide_animation_active:
            self.slide_progress += self.slide_speed * dt
            
            # Sync player position during slide
            self._sync_player_position_during_slide()
            
            if self.slide_progress >= 1.0:
                # End slide
                self.player_x, self.player_y = self.slide_end_pos
                self.slide_animation_active = False
                
                # Sync final position
                self._sync_player_position()
                
                # Handle tile at end of slide
                self._handle_tile_effect(self.player_x, self.player_y)
            return  # Don't process input during slide
        
        # Handle input
        if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
            self._try_move(0, -1)
        elif input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
            self._try_move(0, 1)
        elif input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
            self._try_move(-1, 0)
        elif input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
            self._try_move(1, 0)
        
        # Toggle hint
        if input_manager.key_pressed(pg.K_h):
            self.show_hint = not self.show_hint
        
        # Exit puzzle (for testing - remove in production)
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.end_puzzle(success=False)
    
    def draw(self, screen: pg.Surface, camera_x: int = 0, camera_y: int = 0):
        """Draw the puzzle overlay."""
        if not self.active or not self.current_puzzle:
            return
        
        puzzle = self.current_puzzle
        tile_size = GameSettings.TILE_SIZE
        
        # Calculate screen position based on world position and camera
        base_x = self.world_start_x * tile_size - camera_x
        base_y = self.world_start_y * tile_size - camera_y
        
        # Draw puzzle tiles
        for py in range(puzzle.height):
            for px in range(puzzle.width):
                tile = puzzle.get_tile(px, py)
                if tile is None:
                    continue
                
                screen_x = base_x + px * tile_size
                screen_y = base_y + py * tile_size
                
                # Get tile color with pulse effect
                color = list(TILE_COLORS_RGB[tile])
                
                # Add subtle pulse for safe tiles
                if tile in (TileColor.PINK, TileColor.ORANGE):
                    pulse = int(20 * abs(pg.math.Vector2(1, 0).rotate(self.tile_pulse_timer * 100).x))
                    color = [min(255, c + pulse) for c in color]
                
                # Draw tile
                pg.draw.rect(screen, color, (screen_x, screen_y, tile_size, tile_size))
                
                # Draw tile border
                border_color = tuple(max(0, c - 40) for c in TILE_COLORS_RGB[tile])
                pg.draw.rect(screen, border_color, (screen_x, screen_y, tile_size, tile_size), 2)
                
                # Draw hint (show solution path)
                if self.show_hint and (px, py) in puzzle.solution_path:
                    hint_surface = pg.Surface((tile_size - 4, tile_size - 4), pg.SRCALPHA)
                    hint_surface.fill((255, 255, 255, 100))
                    screen.blit(hint_surface, (screen_x + 2, screen_y + 2))
        
        # Draw start marker
        start_x = base_x + puzzle.start[0] * tile_size
        start_y = base_y + puzzle.start[1] * tile_size
        pg.draw.rect(screen, (0, 255, 0), (start_x, start_y, tile_size, tile_size), 3)
        start_text = self.font.render("S", True, (0, 100, 0))
        screen.blit(start_text, (start_x + tile_size//2 - start_text.get_width()//2, 
                                  start_y + tile_size//2 - start_text.get_height()//2))
        
        # Draw end marker
        end_x = base_x + puzzle.end[0] * tile_size
        end_y = base_y + puzzle.end[1] * tile_size
        pg.draw.rect(screen, (255, 215, 0), (end_x, end_y, tile_size, tile_size), 3)
        end_text = self.font.render("E", True, (139, 119, 0))
        screen.blit(end_text, (end_x + tile_size//2 - end_text.get_width()//2, 
                                end_y + tile_size//2 - end_text.get_height()//2))
        
        # Draw player
        if self.slide_animation_active:
            # Interpolate position during slide
            px = self.slide_start_pos[0] + (self.slide_end_pos[0] - self.slide_start_pos[0]) * self.slide_progress
            py = self.slide_start_pos[1] + (self.slide_end_pos[1] - self.slide_start_pos[1]) * self.slide_progress
            player_screen_x = base_x + px * tile_size
            player_screen_y = base_y + py * tile_size
        else:
            player_screen_x = base_x + self.player_x * tile_size
            player_screen_y = base_y + self.player_y * tile_size
        
        # Draw player circle
        player_center = (int(player_screen_x + tile_size//2), int(player_screen_y + tile_size//2))
        pg.draw.circle(screen, (50, 50, 200), player_center, tile_size//3)
        pg.draw.circle(screen, (100, 100, 255), player_center, tile_size//3, 2)
        
        # Draw direction indicator
        dir_offsets = {
            "up": (0, -tile_size//4),
            "down": (0, tile_size//4),
            "left": (-tile_size//4, 0),
            "right": (tile_size//4, 0),
        }
        dx, dy = dir_offsets.get(self.facing_direction, (0, 0))
        indicator_pos = (player_center[0] + dx, player_center[1] + dy)
        pg.draw.circle(screen, (255, 255, 255), indicator_pos, 3)
        
        # Draw UI panel
        self._draw_ui_panel(screen)
        
        # Draw message
        if self.message:
            self._draw_message(screen)
    
    def _draw_ui_panel(self, screen: pg.Surface):
        """Draw the puzzle info panel."""
        panel_width = 250
        panel_height = 120
        panel_x = GameSettings.SCREEN_WIDTH - panel_width - 10
        panel_y = 10
        
        # Panel background
        panel_surface = pg.Surface((panel_width, panel_height), pg.SRCALPHA)
        panel_surface.fill((30, 30, 50, 220))
        screen.blit(panel_surface, (panel_x, panel_y))
        
        # Panel border
        pg.draw.rect(screen, (100, 100, 150), (panel_x, panel_y, panel_width, panel_height), 2)
        
        # Title
        title = self.title_font.render(f"Puzzle {self.current_puzzle_id}", True, (200, 200, 255))
        screen.blit(title, (panel_x + 10, panel_y + 5))
        
        # Legend
        legend_y = panel_y + 35
        legend_items = [
            (TileColor.PINK, "Pink/Orange: Safe"),
            (TileColor.RED, "Red: Back to start"),
            (TileColor.BLUE, "Blue: Slide"),
        ]
        
        for i, (color, text) in enumerate(legend_items):
            # Color box
            pg.draw.rect(screen, TILE_COLORS_RGB[color], 
                        (panel_x + 10, legend_y + i * 18, 12, 12))
            pg.draw.rect(screen, (0, 0, 0), 
                        (panel_x + 10, legend_y + i * 18, 12, 12), 1)
            
            # Text
            legend_text = self.font.render(text, True, (200, 200, 200))
            screen.blit(legend_text, (panel_x + 28, legend_y + i * 18 - 2))
        
        # Hint toggle
        hint_text = self.font.render("Press H for hint", True, (150, 150, 150))
        screen.blit(hint_text, (panel_x + 10, panel_y + panel_height - 25))
    
    def _draw_message(self, screen: pg.Surface):
        """Draw the current message."""
        if not self.message:
            return
        
        # Create message surface
        msg_text = self.title_font.render(self.message, True, (255, 255, 255))
        
        # Background
        padding = 20
        bg_width = msg_text.get_width() + padding * 2
        bg_height = msg_text.get_height() + padding
        bg_x = (GameSettings.SCREEN_WIDTH - bg_width) // 2
        bg_y = GameSettings.SCREEN_HEIGHT // 2 - 100
        
        bg_surface = pg.Surface((bg_width, bg_height), pg.SRCALPHA)
        bg_surface.fill((0, 0, 0, 200))
        screen.blit(bg_surface, (bg_x, bg_y))
        
        pg.draw.rect(screen, (255, 200, 100), (bg_x, bg_y, bg_width, bg_height), 3)
        
        screen.blit(msg_text, (bg_x + padding, bg_y + padding // 2))


# Singleton instance for easy access
_puzzle_ui_instance: Optional[PuzzleUI] = None

def get_puzzle_ui() -> PuzzleUI:
    """Get the global PuzzleUI instance."""
    global _puzzle_ui_instance
    if _puzzle_ui_instance is None:
        _puzzle_ui_instance = PuzzleUI()
    return _puzzle_ui_instance