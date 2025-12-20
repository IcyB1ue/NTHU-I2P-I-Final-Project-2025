from __future__ import annotations
import pygame as pg
from .entity import Entity
from src.core.services import input_manager, scene_manager, resource_manager
from src.utils import Position, PositionCamera, GameSettings, Logger
from src.core import GameManager
import math
from typing import override
import random

class Player(Entity):
    speed: float = 4.0 * GameSettings.TILE_SIZE
    game_manager: GameManager
    bush_encounter_cooldown: float
    position_log_timer: float
    allow_wild_encounters: bool
    
    # Water riding
    is_on_water: bool
    water_pokemon_sprite: pg.Surface | None
    riding_bob_timer: float
    just_entered_water: bool  # Flag for tutorial detection

    def __init__(self, x: float, y: float, game_manager: GameManager) -> None:
        super().__init__(x, y, game_manager)
        self.bush_encounter_cooldown = 0.0
        self.position_log_timer = 0.0
        self.allow_wild_encounters = True
        
        # Water riding state
        self.is_on_water = False
        self.water_pokemon_sprite = None
        self.riding_bob_timer = 0.0
        self.just_entered_water = False
        self._load_default_water_sprite()
    
    def _load_default_water_sprite(self):
        """Load a default water Pokemon sprite for riding."""
        # Create a simple blue oval as fallback
        self.water_pokemon_sprite = pg.Surface((GameSettings.TILE_SIZE * 2, GameSettings.TILE_SIZE * 2), pg.SRCALPHA)
        pg.draw.ellipse(self.water_pokemon_sprite, (50, 150, 255, 200), 
                       (0, GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE * 2, GameSettings.TILE_SIZE))

    def _has_water_pokemon(self) -> bool:
        """Check if player has a water type Pokemon."""
        for monster in self.game_manager.bag._monsters_data:
            if monster.get("element") == "Water":
                return True
        return False
    
    def _get_water_pokemon_sprite_path(self) -> str | None:
        """Get the sprite path of the first water Pokemon."""
        for monster in self.game_manager.bag._monsters_data:
            if monster.get("element") == "Water":
                return monster.get("sprite_path")
        return None
    
    def _update_water_pokemon_sprite(self):
        """Update the water Pokemon sprite based on what player has."""
        sprite_path = self._get_water_pokemon_sprite_path()
        if sprite_path:
            try:
                img = resource_manager.get_image(sprite_path)
                self.water_pokemon_sprite = pg.transform.scale(img, (GameSettings.TILE_SIZE * 2, GameSettings.TILE_SIZE * 2))
            except Exception as e:
                Logger.warning(f"Failed to load water Pokemon sprite: {e}")

    def _check_bush_encounter(self) -> bool:
        """Check if player is in a bush and trigger encounter."""
        if not self.allow_wild_encounters:
            return False
        
        if self.bush_encounter_cooldown > 0:
            return False
        
        # No encounters while on water
        if self.is_on_water:
            return False
            
        player_rect = self.animation.rect
        for bush_rect in self.game_manager.current_map._bush_map:
            if player_rect.colliderect(bush_rect):
                if random.random() < 0.001:
                    self.bush_encounter_cooldown = 3.0
                    return True
        return False

    def _check_water_tile(self) -> bool:
        """Check if player is on a water tile."""
        if not hasattr(self.game_manager.current_map, '_water_map'):
            return False
        
        player_rect = self.animation.rect
        for water_rect in self.game_manager.current_map._water_map:
            if player_rect.colliderect(water_rect):
                return True
        return False
    
    def _is_water_at_rect(self, rect: pg.Rect) -> bool:
        """Check if a rect overlaps with water tiles."""
        if not hasattr(self.game_manager.current_map, '_water_map'):
            return False
        
        for water_rect in self.game_manager.current_map._water_map:
            if rect.colliderect(water_rect):
                return True
        return False

    def _log_position(self) -> None:
        """Log player position in both pixels and tiles."""
        tile_x = self.position.x // GameSettings.TILE_SIZE
        tile_y = self.position.y // GameSettings.TILE_SIZE
        print(f"[PLAYER POSITION] Pixels: ({self.position.x:.2f}, {self.position.y:.2f}) | Tiles: ({tile_x}, {tile_y})")
    
    def _get_current_animation_frame(self) -> pg.Surface:
        """Get the current animation frame surface."""
        frames = self.animation.animations[self.animation.cur_row]
        idx = int((self.animation.accumulator / self.animation.loop) * self.animation.n_keyframes)
        # Clamp index to valid range
        idx = min(idx, len(frames) - 1)
        return frames[idx]

    @override
    def update(self, dt: float, allow_wild_encounter: bool = True) -> None:
        self.allow_wild_encounters = allow_wild_encounter
        self.just_entered_water = False  # Reset flag each frame
        
        if self.bush_encounter_cooldown > 0:
            self.bush_encounter_cooldown -= dt
        
        self.position_log_timer += dt
        if self.position_log_timer >= 3.0:
            self._log_position()
            self.position_log_timer = 0.0
        
        # Update riding bob animation
        self.riding_bob_timer += dt * 4
        
        dis = Position(0, 0)
        
        if input_manager.key_down(pg.K_LEFT) or input_manager.key_down(pg.K_a):
            self.direction = "left"
            dis.x -= 1
        
        if input_manager.key_down(pg.K_RIGHT) or input_manager.key_down(pg.K_d):
            self.direction = "right"
            dis.x += 1

        if input_manager.key_down(pg.K_UP) or input_manager.key_down(pg.K_w):
            self.direction = "up"
            dis.y -= 1

        if input_manager.key_down(pg.K_DOWN) or input_manager.key_down(pg.K_s):
            self.direction = "down"
            dis.y += 1

        hyp = math.hypot(dis.x, dis.y)
        if hyp:
            dis.x /= hyp
            dis.y /= hyp

        # Movement speed (slightly slower on water)
        current_speed = self.speed * (0.8 if self.is_on_water else 1.0)

        # Check collision for X movement
        to_check_x = self.animation.rect.copy()
        to_check_x.x += int(dis.x * current_speed * dt)
        
        x_blocked = False
        if self.game_manager.check_collision(to_check_x):
            # Check if it's water collision
            if self._is_water_at_rect(to_check_x):
                if self._has_water_pokemon():
                    # Allow movement into water
                    x_blocked = False
                else:
                    x_blocked = True
            else:
                x_blocked = True
        
        if x_blocked:
            self.position.x = self._snap_to_grid(self.position.x)
        else:
            self.position.x += dis.x * current_speed * dt
        
        # Check collision for Y movement
        to_check_y = self.animation.rect.copy()
        to_check_y.y += int(dis.y * current_speed * dt)
        
        y_blocked = False
        if self.game_manager.check_collision(to_check_y):
            if self._is_water_at_rect(to_check_y):
                if self._has_water_pokemon():
                    y_blocked = False
                else:
                    y_blocked = True
            else:
                y_blocked = True
        
        if y_blocked:
            self.position.y = self._snap_to_grid(self.position.y)
        else:
            self.position.y += dis.y * current_speed * dt
        
        # Update water state after movement
        was_on_water = self.is_on_water
        self.is_on_water = self._check_water_tile() and self._has_water_pokemon()
        
        # Detect entering water (for tutorial)
        if self.is_on_water and not was_on_water:
            self._update_water_pokemon_sprite()
            self.just_entered_water = True
            Logger.info("Player entered water with Water Pokemon!")
        
        # Check for bush encounter
        if self._check_bush_encounter():
            scene_manager.change_scene("wild_pokemon", self.game_manager)
            return
        
        # Check teleportation
        tp = self.game_manager.current_map.check_teleport(self.position)
        if tp:
            dest = tp.destination
            if isinstance(dest, dict):
                map_path = dest["path"]
                dest_x = dest.get("x", self.position.x // GameSettings.TILE_SIZE)
                dest_y = dest.get("y", self.position.y // GameSettings.TILE_SIZE)
                self.game_manager.switch_map(map_path)
                self.position.x = dest_x * GameSettings.TILE_SIZE
                self.position.y = dest_y * GameSettings.TILE_SIZE
                self.is_on_water = False
            else:
                self.game_manager.switch_map(dest)
                self.is_on_water = False

        if self.direction == "left":
            self.animation.switch("left")
        elif self.direction == "right":
            self.animation.switch("right")
        elif self.direction == "up":
            self.animation.switch("up")
        elif self.direction == "down":
            self.animation.switch("down")
                
        # Update animation position
        self.animation.update_pos(self.position)
        self.animation.update(dt)
    
    @override
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        if self.is_on_water and self.water_pokemon_sprite:
            # Draw water Pokemon sprite under the player with bobbing effect
            bob_offset = math.sin(self.riding_bob_timer) * 3
            
            # Get screen position
            screen_x = self.position.x - camera.x
            screen_y = self.position.y - camera.y
            
            # Draw water Pokemon centered under player
            pokemon_rect = self.water_pokemon_sprite.get_rect()
            pokemon_rect.centerx = int(screen_x + GameSettings.TILE_SIZE // 2)
            pokemon_rect.centery = int(screen_y + GameSettings.TILE_SIZE // 2 + 10 + bob_offset)
            screen.blit(self.water_pokemon_sprite, pokemon_rect)
            
            # Get the current animation frame properly
            current_frame = self._get_current_animation_frame()
            
            # Draw player on top (slightly raised, bobbing)
            player_screen_x = int(screen_x)
            player_screen_y = int(screen_y - 15 + bob_offset)
            screen.blit(current_frame, (player_screen_x, player_screen_y))
        else:
            # Normal drawing
            self.animation.draw(screen, camera)
            if GameSettings.DRAW_HITBOXES:
                self.animation.draw_hitbox(screen, camera)
        
    @override
    def to_dict(self) -> dict[str, object]:
        return super().to_dict()
    
    @classmethod
    @override
    def from_dict(cls, data: dict[str, object], game_manager: GameManager) -> Player:
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, game_manager)