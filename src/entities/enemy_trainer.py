from __future__ import annotations
import pygame
from enum import Enum
from dataclasses import dataclass
from typing import override
import copy

from .entity import Entity
from src.sprites import Sprite
from src.core import GameManager
from src.core.services import input_manager, scene_manager
from src.utils import GameSettings, Direction, Position, PositionCamera
from src.utils.definition import Monster


class EnemyTrainerClassification(Enum):
    STATIONARY = "stationary"


@dataclass
class IdleMovement:
    def update(self, enemy: "EnemyTrainer", dt: float) -> None:
        return


class EnemyTrainer(Entity):
    classification: EnemyTrainerClassification
    max_tiles: int | None
    _movement: IdleMovement
    warning_sign: Sprite
    detected: bool
    los_direction: Direction
    is_corrupted: bool
    is_gym_leader: bool
    aura_pulse_timer: float

    # Cooldown settings (2 minutes = 120 seconds)
    COOLDOWN_DURATION = 120.0

    @override
    def __init__(
        self,
        x: float,
        y: float,
        game_manager: GameManager,
        classification: EnemyTrainerClassification = EnemyTrainerClassification.STATIONARY,
        max_tiles: int | None = 2,
        facing: Direction | None = None,
        monsters: Monster | None = None,
        is_corrupted: bool = False,
        is_gym_leader: bool = False,
    ) -> None:
        
        super().__init__(x, y, game_manager)
        self.classification = classification
        self.max_tiles = max_tiles
        self.monsters = monsters
        self.is_corrupted = is_corrupted
        self.is_gym_leader = is_gym_leader
        self.aura_pulse_timer = 0.0
        
        # Store original monster data for HP restoration after cooldown
        self.original_monster_data = copy.deepcopy(monsters) if monsters else None
        
        # Cooldown system
        self.cooldown_timer = 0.0
        self.on_cooldown = False

        if classification == EnemyTrainerClassification.STATIONARY:
            self._movement = IdleMovement()
            if facing is None:
                raise ValueError("Idle EnemyTrainer requires a 'facing' Direction at instantiation")
            self._set_direction(facing)
        else:
            raise ValueError("Invalid classification")
        
        self.warning_sign = Sprite("exclamation.png", (GameSettings.TILE_SIZE // 2, GameSettings.TILE_SIZE // 2))
        self.warning_sign.update_pos(Position(x + GameSettings.TILE_SIZE // 4, y - GameSettings.TILE_SIZE // 2))
        self.detected = False

    def start_cooldown(self):
        """Start the cooldown timer after being defeated."""
        self.on_cooldown = True
        self.cooldown_timer = self.COOLDOWN_DURATION
        self.detected = False
        print(f"Trainer at ({self.position.x // GameSettings.TILE_SIZE}, {self.position.y // GameSettings.TILE_SIZE}) is now on cooldown for {self.COOLDOWN_DURATION} seconds")

    def _reset_monster(self):
        """Reset monster to full HP after cooldown ends."""
        if self.original_monster_data:
            # Restore HP to max from original data
            if isinstance(self.monsters, dict) and isinstance(self.original_monster_data, dict):
                max_hp = self.original_monster_data.get("max_hp", self.original_monster_data.get("hp", 100))
                self.monsters["hp"] = max_hp
        print(f"Trainer at ({self.position.x // GameSettings.TILE_SIZE}, {self.position.y // GameSettings.TILE_SIZE}) is ready to battle again!")

    def is_on_cooldown(self) -> bool:
        """Check if trainer is on cooldown."""
        return self.on_cooldown

    def get_cooldown_remaining(self) -> float:
        """Get remaining cooldown time in seconds."""
        return self.cooldown_timer if self.on_cooldown else 0.0

    def get_cooldown_remaining_formatted(self) -> str:
        """Get remaining cooldown time as formatted string (MM:SS)."""
        if not self.on_cooldown:
            return "Ready"
        minutes = int(self.cooldown_timer // 60)
        seconds = int(self.cooldown_timer % 60)
        return f"{minutes}:{seconds:02d}"

    @override
    def update(self, dt: float) -> None:
        # Update aura pulse timer for corrupted trainers
        if self.is_corrupted:
            self.aura_pulse_timer += dt
        
        # Update cooldown timer
        if self.on_cooldown:
            self.cooldown_timer -= dt
            if self.cooldown_timer <= 0:
                self.cooldown_timer = 0
                self.on_cooldown = False
                self._reset_monster()
            # Don't detect player while on cooldown
            self.detected = False
            self.animation.update_pos(self.position)
            return
        
        self._movement.update(self, dt)
        self._has_los_to_player()
        
        # If THIS enemy detected the player and space is pressed, start battle with THIS enemy
        if self.detected and input_manager.key_pressed(pygame.K_SPACE):
            print(f"Battle initiated with enemy at position: ({self.position.x // GameSettings.TILE_SIZE}, {self.position.y // GameSettings.TILE_SIZE})")
            print(f"Enemy monsters: {self.monsters}")
            scene_manager.change_scene("battle", self)
        
        self.animation.update_pos(self.position)

    @override
    def draw(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        # Draw purple aura for corrupted trainers (behind the sprite)
        if self.is_corrupted:
            self._draw_corrupted_aura(screen, camera)
        
        super().draw(screen, camera)
        
        if self.on_cooldown:
            # Draw cooldown timer above trainer
            font = pygame.font.Font(None, 18)
            timer_text = self.get_cooldown_remaining_formatted()
            text_surf = font.render(timer_text, True, (150, 150, 150))
            
            # Position above the trainer (apply camera offset directly)
            pos_x = self.position.x + GameSettings.TILE_SIZE // 2 - text_surf.get_width() // 2 - camera.x
            pos_y = self.position.y - GameSettings.TILE_SIZE // 2 - camera.y
            
            # Draw background for better visibility
            bg_rect = pygame.Rect(pos_x - 2, pos_y - 2, 
                                  text_surf.get_width() + 4, text_surf.get_height() + 4)
            pygame.draw.rect(screen, (40, 40, 40), bg_rect, border_radius=3)
            pygame.draw.rect(screen, (80, 80, 80), bg_rect, 1, border_radius=3)
            
            screen.blit(text_surf, (pos_x, pos_y))
        elif self.detected:
            self.warning_sign.draw(screen, camera)
            
        if GameSettings.DRAW_HITBOXES:
            los_rect = self._get_los_rect()
            if los_rect is not None:
                pygame.draw.rect(screen, (255, 255, 0), camera.transform_rect(los_rect), 1)

    def _draw_corrupted_aura(self, screen: pygame.Surface, camera: PositionCamera) -> None:
        """Draw a pulsing purple aura around corrupted trainers."""
        import math
        
        # Calculate screen position
        screen_x = self.position.x - camera.x
        screen_y = self.position.y - camera.y
        
        # Pulsing effect using sine wave
        pulse = (math.sin(self.aura_pulse_timer * 3) + 1) / 2  # 0 to 1
        
        # Base aura properties
        base_alpha = 80 + int(40 * pulse)  # 80-120 alpha
        base_size = GameSettings.TILE_SIZE + 8 + int(4 * pulse)  # Pulsing size
        
        # Create aura surface with transparency
        aura_surface = pygame.Surface((base_size + 16, base_size + 16), pygame.SRCALPHA)
        
        # Draw multiple layers of purple circles for glow effect
        center_x = (base_size + 16) // 2
        center_y = (base_size + 16) // 2
        
        # Outer glow (more transparent)
        for i in range(3):
            radius = base_size // 2 + 8 - i * 3
            alpha = base_alpha // (i + 2)
            color = (148, 0, 211, alpha)  # Dark violet with varying alpha
            pygame.draw.circle(aura_surface, color, (center_x, center_y), radius)
        
        # Inner glow (brighter)
        inner_color = (180, 50, 255, base_alpha)  # Lighter purple
        pygame.draw.circle(aura_surface, inner_color, (center_x, center_y), base_size // 2 + 2)
        
        # Draw particles floating around
        num_particles = 6
        for i in range(num_particles):
            angle = (self.aura_pulse_timer * 2 + i * (math.pi * 2 / num_particles))
            particle_dist = base_size // 2 + 4 + int(3 * math.sin(self.aura_pulse_timer * 4 + i))
            px = center_x + int(math.cos(angle) * particle_dist)
            py = center_y + int(math.sin(angle) * particle_dist)
            particle_alpha = int(150 + 50 * math.sin(self.aura_pulse_timer * 5 + i * 2))
            pygame.draw.circle(aura_surface, (200, 100, 255, particle_alpha), (px, py), 2)
        
        # Blit aura behind trainer
        aura_x = screen_x - 8 - (base_size - GameSettings.TILE_SIZE) // 2
        aura_y = screen_y - 8 - (base_size - GameSettings.TILE_SIZE) // 2
        screen.blit(aura_surface, (aura_x, aura_y))

    def _set_direction(self, direction: Direction) -> None:
        self.direction = direction
        if direction == Direction.RIGHT:
            self.animation.switch("right")
        elif direction == Direction.LEFT:
            self.animation.switch("left")
        elif direction == Direction.DOWN:
            self.animation.switch("down")
        else:
            self.animation.switch("up")
        self.los_direction = self.direction

    def _get_los_rect(self) -> pygame.Rect | None:
        tile = GameSettings.TILE_SIZE
        length = self.max_tiles * tile
        x = self.position.x
        y = self.position.y

        if self.direction == Direction.UP:
            return pygame.Rect(x, y - length, tile, length)
        if self.direction == Direction.DOWN:
            return pygame.Rect(x, y + tile, tile, length)
        if self.direction == Direction.RIGHT:
            return pygame.Rect(x + tile, y, length, tile)
        if self.direction == Direction.LEFT:
            return pygame.Rect(x - length, y, length, tile)
        return None

    def _has_los_to_player(self) -> bool:
        # Don't detect player if on cooldown
        if self.on_cooldown:
            self.detected = False
            return False
            
        player = self.game_manager.player
        if player is None:
            self.detected = False
            return False
        los_rect = self._get_los_rect()
        if los_rect is None:
            self.detected = False
            return False
        player_rect = player.animation.rect
        self.detected = los_rect.colliderect(player_rect)
        return self.detected

    def _distance_to_player(self) -> float:
        player = self.game_manager.player
        if player is None:
            return float('inf')
        ex, ey = self.position.x, self.position.y
        px, py = player.position.x, player.position.y
        return ((px - ex) ** 2 + (py - ey) ** 2) ** 0.5
    
    @classmethod
    @override
    def from_dict(cls, data: dict, game_manager: GameManager) -> "EnemyTrainer":
        classification = EnemyTrainerClassification(data.get("classification", "stationary"))
        max_tiles = data.get("max_tiles")
        facing_val = data.get("facing")
        facing: Direction | None = None
        if facing_val is not None:
            if isinstance(facing_val, str):
                facing = Direction[facing_val]
            elif isinstance(facing_val, Direction):
                facing = facing_val
        if facing is None and classification == EnemyTrainerClassification.STATIONARY:
            facing = Direction.DOWN

        monsters: Monster | None = data.get("monsters")
        is_corrupted: bool = data.get("is_corrupted", False)
        is_gym_leader: bool = data.get("is_gym_leader", False)

        trainer = cls(
            data["x"] * GameSettings.TILE_SIZE,
            data["y"] * GameSettings.TILE_SIZE,
            game_manager,
            classification,
            max_tiles,
            facing,
            monsters,
            is_corrupted,
            is_gym_leader
        )

        return trainer

    @override
    def to_dict(self) -> dict[str, object]:
        base: dict[str, object] = super().to_dict()
        base["classification"] = self.classification.value
        base["facing"] = self.direction.name
        base["max_tiles"] = self.max_tiles
        base["monsters"] = self.monsters
        base["is_corrupted"] = self.is_corrupted
        base["is_gym_leader"] = self.is_gym_leader
        return base