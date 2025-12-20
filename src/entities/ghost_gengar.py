import pygame as pg
import math
import random
from src.utils import GameSettings, Logger
from src.utils.definition import Position
from src.sprites import Sprite


class GhostGengar:
    """A ghost Gengar that chases the player at night."""
    
    def __init__(self, x: float, y: float):
        self.position = Position(x * GameSettings.TILE_SIZE, y * GameSettings.TILE_SIZE)
        self.speed = 150  # Faster base speed
        
        # Sprite (bigger size)
        self.sprite_size = 128
        try:
            self.sprite = Sprite("menu_sprites/gengar.png", (self.sprite_size, self.sprite_size))
        except:
            self.sprite = None
        
        # Ghost effect
        self.alpha = 180
        self.alpha_timer = random.random() * 6.28
        self.bob_timer = random.random() * 6.28
        
        # Chase behavior
        self.is_chasing = False
        self.detection_range = 350  # Pixels
        self.catch_range = 40  # Pixels
        
        # More active wander behavior
        self.wander_target: Position | None = None
        self.wander_timer = 0.0
        self.wander_change_timer = 0.0  # Change direction more frequently
        self.movement_style = random.choice(["patrol", "erratic", "circle", "zigzag"])
        self.circle_angle = random.random() * 6.28
        self.circle_center: Position | None = None
        self.zigzag_direction = 1
        
        # Immunity
        self.catch_cooldown = 2.0
    
    def reset_catch_cooldown(self, duration: float = 3.0):
        """Reset the catch cooldown (gives player immunity)."""
        self.catch_cooldown = duration
    
    def update(self, dt: float, player_pos: Position, is_night: bool) -> dict:
        """Update Gengar. Returns events dict."""
        events = {}
        
        if not is_night:
            return events
        
        # Update catch cooldown
        if self.catch_cooldown > 0:
            self.catch_cooldown -= dt
        
        # Ghost effect animation
        self.alpha_timer += dt * 2
        self.bob_timer += dt * 3
        self.alpha = 150 + int(30 * math.sin(self.alpha_timer))
        
        # Calculate distance to player
        dx = player_pos.x - self.position.x
        dy = player_pos.y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Check if caught player (only if cooldown is done)
        if distance < self.catch_range and self.catch_cooldown <= 0:
            events["caught_player"] = True
            self.catch_cooldown = 3.0
            return events
        
        # Chase or wander
        if distance < self.detection_range:
            self.is_chasing = True
            # Move towards player (faster when chasing)
            if distance > 0:
                chase_speed = self.speed * 1.3
                self.position.x += (dx / distance) * chase_speed * dt
                self.position.y += (dy / distance) * chase_speed * dt
        else:
            self.is_chasing = False
            self._wander_actively(dt, player_pos)
        
        return events
    
    def _wander_actively(self, dt: float, player_pos: Position):
        """More active wandering behavior based on movement style."""
        self.wander_change_timer -= dt
        
        if self.movement_style == "patrol":
            self._patrol_movement(dt)
        elif self.movement_style == "erratic":
            self._erratic_movement(dt)
        elif self.movement_style == "circle":
            self._circle_movement(dt, player_pos)
        elif self.movement_style == "zigzag":
            self._zigzag_movement(dt, player_pos)
    
    def _patrol_movement(self, dt: float):
        """Patrol back and forth."""
        self.wander_timer -= dt
        
        if self.wander_timer <= 0 or self.wander_target is None:
            # Pick new patrol target
            angle = random.random() * 6.28
            dist = random.randint(100, 250)
            self.wander_target = Position(
                self.position.x + math.cos(angle) * dist,
                self.position.y + math.sin(angle) * dist
            )
            self.wander_timer = random.uniform(1.5, 3.0)
        
        # Move towards target
        dx = self.wander_target.x - self.position.x
        dy = self.wander_target.y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 5:
            move_speed = self.speed * 0.7
            self.position.x += (dx / distance) * move_speed * dt
            self.position.y += (dy / distance) * move_speed * dt
    
    def _erratic_movement(self, dt: float):
        """Erratic, unpredictable movement."""
        self.wander_timer -= dt
        
        if self.wander_timer <= 0:
            # Change direction frequently
            angle = random.random() * 6.28
            dist = random.randint(30, 80)
            self.wander_target = Position(
                self.position.x + math.cos(angle) * dist,
                self.position.y + math.sin(angle) * dist
            )
            self.wander_timer = random.uniform(0.3, 0.8)  # Very frequent changes
        
        if self.wander_target:
            dx = self.wander_target.x - self.position.x
            dy = self.wander_target.y - self.position.y
            distance = math.sqrt(dx * dx + dy * dy)
            
            if distance > 3:
                move_speed = self.speed * 0.9
                self.position.x += (dx / distance) * move_speed * dt
                self.position.y += (dy / distance) * move_speed * dt
    
    def _circle_movement(self, dt: float, player_pos: Position):
        """Circle around a point (often near player)."""
        if self.circle_center is None:
            # Set circle center near player but offset
            offset_x = random.randint(-200, 200)
            offset_y = random.randint(-200, 200)
            self.circle_center = Position(
                player_pos.x + offset_x,
                player_pos.y + offset_y
            )
        
        # Update circle angle
        self.circle_angle += dt * 1.5  # Circle speed
        
        # Calculate position on circle
        radius = 150 + math.sin(self.alpha_timer) * 50  # Varying radius
        target_x = self.circle_center.x + math.cos(self.circle_angle) * radius
        target_y = self.circle_center.y + math.sin(self.circle_angle) * radius
        
        # Move towards circle position
        dx = target_x - self.position.x
        dy = target_y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 3:
            move_speed = self.speed * 0.8
            self.position.x += (dx / distance) * move_speed * dt
            self.position.y += (dy / distance) * move_speed * dt
        
        # Occasionally reset circle center to keep near player
        self.wander_timer -= dt
        if self.wander_timer <= 0:
            self.circle_center = Position(
                player_pos.x + random.randint(-250, 250),
                player_pos.y + random.randint(-250, 250)
            )
            self.wander_timer = random.uniform(4.0, 8.0)
    
    def _zigzag_movement(self, dt: float, player_pos: Position):
        """Zigzag movement pattern, generally moving towards player area."""
        self.wander_timer -= dt
        
        if self.wander_timer <= 0:
            self.zigzag_direction *= -1  # Flip direction
            self.wander_timer = random.uniform(0.5, 1.2)
        
        # General direction towards player but with zigzag
        dx = player_pos.x - self.position.x
        dy = player_pos.y - self.position.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        if distance > 0:
            # Normalize direction
            dir_x = dx / distance
            dir_y = dy / distance
            
            # Add perpendicular zigzag
            perp_x = -dir_y * self.zigzag_direction
            perp_y = dir_x * self.zigzag_direction
            
            # Combine forward movement with zigzag
            move_speed = self.speed * 0.6
            zigzag_strength = 0.7
            
            self.position.x += (dir_x * 0.3 + perp_x * zigzag_strength) * move_speed * dt
            self.position.y += (dir_y * 0.3 + perp_y * zigzag_strength) * move_speed * dt
    
    def draw(self, screen: pg.Surface, camera):
        """Draw the Gengar."""
        # Transform position with camera
        screen_pos = camera.transform_position(self.position)
        
        if self.sprite:
            # Apply ghost effect
            img = self.sprite.image.copy()
            img.set_alpha(self.alpha)
            
            # Bob up and down
            bob_offset = math.sin(self.bob_timer) * 8
            
            rect = img.get_rect(center=(screen_pos[0], screen_pos[1] + bob_offset))
            screen.blit(img, rect)
        else:
            # Fallback: draw a purple circle if no sprite
            bob_offset = math.sin(self.bob_timer) * 8
            
            # Draw glow effect
            glow_surface = pg.Surface((self.sprite_size + 20, self.sprite_size + 20), pg.SRCALPHA)
            pg.draw.circle(glow_surface, (100, 50, 150, 50), 
                          (self.sprite_size // 2 + 10, self.sprite_size // 2 + 10), 
                          self.sprite_size // 2 + 10)
            screen.blit(glow_surface, (screen_pos[0] - self.sprite_size // 2 - 10, 
                                        screen_pos[1] - self.sprite_size // 2 - 10 + bob_offset))
            
            # Draw main circle
            pg.draw.circle(screen, (128, 0, 128), 
                          (int(screen_pos[0]), int(screen_pos[1] + bob_offset)), 
                          self.sprite_size // 2)
            
            # Draw eyes
            eye_y = int(screen_pos[1] + bob_offset - 10)
            pg.draw.circle(screen, (255, 0, 0), (int(screen_pos[0] - 15), eye_y), 8)
            pg.draw.circle(screen, (255, 0, 0), (int(screen_pos[0] + 15), eye_y), 8)
            pg.draw.circle(screen, (255, 255, 255), (int(screen_pos[0] - 15), eye_y), 4)
            pg.draw.circle(screen, (255, 255, 255), (int(screen_pos[0] + 15), eye_y), 4)