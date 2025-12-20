"""
Professor NPC - Gives coding quiz for coins.
"""
import pygame as pg

from src.utils import GameSettings, Logger, Position, PositionCamera
from src.sprites import Sprite


class ProfessorNPC:
    """Professor NPC that gives coding quizzes for coins."""
    
    def __init__(self, x: int, y: int):
        """
        Initialize professor at tile position (x, y).
        """
        self.tile_x = x
        self.tile_y = y
        self.position = Position(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE)
        
        # Sprites
        try:
            self.sprite_neutral = Sprite("professor/professor_neutral.png", 
                                         (GameSettings.TILE_SIZE * 2, GameSettings.TILE_SIZE * 2))
            self.sprite_happy = Sprite("professor/professor_happy.png",
                                       (GameSettings.TILE_SIZE * 2, GameSettings.TILE_SIZE * 2))
            self.current_sprite = self.sprite_neutral
        except Exception as e:
            Logger.error(f"Failed to load professor sprites: {e}")
            self.sprite_neutral = None
            self.sprite_happy = None
            self.current_sprite = None
        
        # Interaction state
        self.is_player_nearby = False
        self.interaction_distance = GameSettings.TILE_SIZE * 2  # 2 tiles
        
    def update(self, dt: float, player_position: Position | None = None):
        """Update professor state based on player proximity."""
        if not player_position:
            self.is_player_nearby = False
            self.current_sprite = self.sprite_neutral
            return
        
        # Calculate distance to player
        dx = player_position.x - self.position.x
        dy = player_position.y - self.position.y
        distance = (dx * dx + dy * dy) ** 0.5
        
        self.is_player_nearby = distance < self.interaction_distance
        
        # Change sprite based on proximity
        if self.is_player_nearby:
            self.current_sprite = self.sprite_happy
        else:
            self.current_sprite = self.sprite_neutral
    
    def can_interact(self, player_position: Position) -> bool:
        """Check if player can interact with professor."""
        dx = player_position.x - self.position.x
        dy = player_position.y - self.position.y
        distance = (dx * dx + dy * dy) ** 0.5
        return distance < self.interaction_distance
    
    def draw(self, screen: pg.Surface, camera: PositionCamera):
        """Draw the professor."""
        if not self.current_sprite:
            return
        
        # Calculate screen position
        screen_x = self.position.x - camera.x
        screen_y = self.position.y - camera.y
        
        self.current_sprite.rect.topleft = (screen_x, screen_y)
        self.current_sprite.draw(screen)
        
        # Draw interaction prompt if nearby
        if self.is_player_nearby:
            font = pg.font.Font(None, 20)
            prompt_text = font.render("Press E to play quiz!", True, (255, 255, 255))
            prompt_rect = prompt_text.get_rect(centerx=screen_x + GameSettings.TILE_SIZE, 
                                                y=screen_y - 25)
            
            # Background for text
            bg_rect = prompt_rect.inflate(10, 6)
            bg_surface = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
            bg_surface.fill((0, 0, 0, 180))
            screen.blit(bg_surface, bg_rect)
            screen.blit(prompt_text, prompt_rect)