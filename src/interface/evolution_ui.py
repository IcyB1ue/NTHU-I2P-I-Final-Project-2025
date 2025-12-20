"""
Evolution UI - Beautiful animation overlay for Pokemon evolution.
Shows dramatic animation when a Pokemon evolves after battle.
"""
import pygame as pg
import math
import random
from typing import Callable

from src.utils import GameSettings, Logger
from src.core.services import input_manager, sound_manager


class Particle:
    """A sparkle particle for the evolution effect."""
    
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(50, 150)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.uniform(0.5, 1.5)
        self.max_life = self.life
        self.size = random.randint(3, 8)
        self.color = random.choice([
            (255, 255, 255),
            (200, 220, 255),
            (180, 200, 255),
            (255, 255, 200),
            (200, 255, 220),
        ])
    
    def update(self, dt: float) -> bool:
        """Update particle. Returns False if dead."""
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 100 * dt  # Gravity
        self.life -= dt
        return self.life > 0
    
    def draw(self, screen: pg.Surface):
        """Draw the particle."""
        alpha = int(255 * (self.life / self.max_life))
        size = int(self.size * (self.life / self.max_life))
        if size > 0:
            surf = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
            color_with_alpha = (*self.color, alpha)
            pg.draw.circle(surf, color_with_alpha, (size, size), size)
            screen.blit(surf, (int(self.x) - size, int(self.y) - size))


class EvolutionUI:
    """
    Evolution animation overlay.
    Shows a dramatic sequence when a Pokemon evolves.
    """
    
    # Evolution phases
    PHASE_INTRO = 0        # "What is happening!?!?"
    PHASE_EVOLVING = 1     # "[Name] is evolving!?!?" + animation
    PHASE_TRANSFORM = 2    # Flash and transform
    PHASE_COMPLETE = 3     # "Congratulations!" + new Pokemon
    PHASE_DONE = 4         # Finished, can close
    
    def __init__(self, on_complete: Callable[[], None] = None):
        """
        Initialize evolution UI.
        on_complete: Callback when evolution animation finishes.
        """
        self.overlay_show = False
        self.on_complete = on_complete
        
        # Evolution data
        self.old_name = ""
        self.new_name = ""
        self.old_sprite = None
        self.new_sprite = None
        self.monster_data = None
        
        # Animation state
        self.phase = self.PHASE_INTRO
        self.phase_timer = 0.0
        self.total_time = 0.0
        
        # Visual effects
        self.flash_alpha = 0
        self.glow_radius = 0
        self.sprite_scale = 1.0
        self.sprite_alpha = 255
        self.shake_offset = (0, 0)
        self.particles: list[Particle] = []
        self.show_new_sprite = False
        
        # Pulse animation
        self.pulse_timer = 0.0
        self.pulse_speed = 3.0  # Starts slow, gets faster
        
        # Screen center
        self.center_x = GameSettings.SCREEN_WIDTH // 2
        self.center_y = GameSettings.SCREEN_HEIGHT // 2
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill((0, 0, 20))
        
        # Load fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 36)
            self.small_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        except:
            self.title_font = pg.font.Font(None, 36)
            self.name_font = pg.font.Font(None, 48)
            self.small_font = pg.font.Font(None, 24)
    
    def start_evolution(self, monster_data: dict, old_name: str, new_name: str, 
                        old_sprite_path: str, new_sprite_path: str):
        """
        Start the evolution animation.
        """
        self.overlay_show = True
        self.monster_data = monster_data
        self.old_name = old_name
        self.new_name = new_name
        
        # Load sprites
        try:
            old_img = pg.image.load(f"assets/images/{old_sprite_path}").convert_alpha()
            self.old_sprite = pg.transform.scale(old_img, (160, 160))
        except Exception as e:
            Logger.error(f"Failed to load old sprite: {e}")
            self.old_sprite = pg.Surface((160, 160), pg.SRCALPHA)
            self.old_sprite.fill((100, 100, 100))
        
        try:
            new_img = pg.image.load(f"assets/images/{new_sprite_path}").convert_alpha()
            self.new_sprite = pg.transform.scale(new_img, (160, 160))
        except Exception as e:
            Logger.error(f"Failed to load new sprite: {e}")
            self.new_sprite = pg.Surface((160, 160), pg.SRCALPHA)
            self.new_sprite.fill((150, 150, 150))
        
        # Reset animation state
        self.phase = self.PHASE_INTRO
        self.phase_timer = 0.0
        self.total_time = 0.0
        self.flash_alpha = 0
        self.glow_radius = 0
        self.sprite_scale = 1.0
        self.sprite_alpha = 255
        self.shake_offset = (0, 0)
        self.particles.clear()
        self.show_new_sprite = False
        self.pulse_timer = 0.0
        self.pulse_speed = 3.0
        
        # Play evolution sound/music if available
        try:
            sound_manager.play_bgm("pokemon_evolution.ogg")
        except:
            pass
        
        input_manager.reset()
        Logger.info(f"Evolution animation started: {old_name} -> {new_name}")
    
    def close(self):
        """Close the evolution UI."""
        self.overlay_show = False
        if self.on_complete:
            self.on_complete()
        input_manager.reset()
    
    def update(self, dt: float):
        """Update the evolution animation."""
        if not self.overlay_show:
            return
        
        self.phase_timer += dt
        self.total_time += dt
        
        # Update particles
        self.particles = [p for p in self.particles if p.update(dt)]
        
        # Phase transitions
        if self.phase == self.PHASE_INTRO:
            # "What is happening!?!?" for 2 seconds
            if self.phase_timer >= 2.0:
                self.phase = self.PHASE_EVOLVING
                self.phase_timer = 0.0
        
        elif self.phase == self.PHASE_EVOLVING:
            # Evolving animation for 4 seconds
            self.pulse_timer += dt * self.pulse_speed
            
            # Speed up pulsing over time
            self.pulse_speed = 3.0 + self.phase_timer * 2.0
            
            # Pulsing glow
            pulse = (math.sin(self.pulse_timer) + 1) / 2
            self.glow_radius = int(120 + pulse * 100)  # Much bigger base glow
            
            # Sprite pulsing (scale between 0.9 and 1.1)
            self.sprite_scale = 1.0 + math.sin(self.pulse_timer * 2) * 0.1
            
            # Add particles periodically (offset to match sprite position at -40)
            if random.random() < 0.3:
                px = self.center_x + random.randint(-100, 100)
                py = self.center_y - 40 + random.randint(-100, 100)
                self.particles.append(Particle(px, py))
            
            # Shake effect increases over time
            shake_intensity = min(self.phase_timer * 2, 8)
            self.shake_offset = (
                random.uniform(-shake_intensity, shake_intensity),
                random.uniform(-shake_intensity, shake_intensity)
            )
            
            if self.phase_timer >= 4.0:
                self.phase = self.PHASE_TRANSFORM
                self.phase_timer = 0.0
                self.flash_alpha = 255
                # Big particle burst (offset to match sprite position at -40)
                for _ in range(50):
                    px = self.center_x + random.randint(-70, 70)
                    py = self.center_y - 40 + random.randint(-70, 70)
                    self.particles.append(Particle(px, py))
        
        elif self.phase == self.PHASE_TRANSFORM:
            # Flash and transform - 1.5 seconds
            # Flash fades out
            self.flash_alpha = max(0, 255 - int(self.phase_timer * 300))
            
            # Switch sprite at peak of flash
            if self.phase_timer >= 0.3 and not self.show_new_sprite:
                self.show_new_sprite = True
                self.sprite_scale = 1.3  # Pop effect
            
            # Scale back to normal
            if self.show_new_sprite:
                self.sprite_scale = max(1.0, self.sprite_scale - dt * 0.5)
            
            self.shake_offset = (0, 0)
            self.glow_radius = max(0, int(140 - self.phase_timer * 100))
            
            if self.phase_timer >= 1.5:
                self.phase = self.PHASE_COMPLETE
                self.phase_timer = 0.0
                self.sprite_scale = 1.0
        
        elif self.phase == self.PHASE_COMPLETE:
            # Show congratulations for 3 seconds, then allow closing
            self.glow_radius = int(40 + math.sin(self.total_time * 2) * 20)
            
            if self.phase_timer >= 2.0:
                self.phase = self.PHASE_DONE
        
        elif self.phase == self.PHASE_DONE:
            # Wait for player input to close
            if input_manager.mouse_pressed(1) or input_manager.key_pressed(pg.K_RETURN) or input_manager.key_pressed(pg.K_SPACE):
                self.close()
    
    def draw(self, screen: pg.Surface):
        """Draw the evolution animation."""
        if not self.overlay_show:
            return
        
        # Darken background
        self.darken.set_alpha(230)
        screen.blit(self.darken, (0, 0))
        
        # Draw glow behind sprite - much bigger glow
        if self.glow_radius > 0:
            glow_size = int(self.glow_radius * 2)  # Much bigger glow
            glow_surf = pg.Surface((glow_size * 4, glow_size * 4), pg.SRCALPHA)
            for r in range(glow_size, 0, -5):
                alpha = int(100 * (r / glow_size))
                color = (180, 200, 255, alpha) if not self.show_new_sprite else (255, 220, 150, alpha)
                pg.draw.circle(glow_surf, color, (glow_size * 2, glow_size * 2), r)
            # Glow centered on sprite (sprite offset is -40)
            screen.blit(glow_surf, (self.center_x - glow_size * 2, 
                                    self.center_y - glow_size * 2 - 40))
        
        # Draw sprite
        current_sprite = self.new_sprite if self.show_new_sprite else self.old_sprite
        if current_sprite:
            # Scale sprite - much bigger size
            base_size = 280
            scaled_size = int(base_size * self.sprite_scale)
            scaled_sprite = pg.transform.scale(current_sprite, (scaled_size, scaled_size))
            
            # Apply shake offset - sprite moved up
            sprite_x = self.center_x - scaled_size // 2 + self.shake_offset[0]
            sprite_y = self.center_y - scaled_size // 2 + self.shake_offset[1] - 100
            
            screen.blit(scaled_sprite, (sprite_x, sprite_y))
        
        # Draw particles
        for particle in self.particles:
            particle.draw(screen)
        
        # Draw flash overlay
        if self.flash_alpha > 0:
            flash_surf = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            flash_surf.fill((255, 255, 255))
            flash_surf.set_alpha(self.flash_alpha)
            screen.blit(flash_surf, (0, 0))
        
        # Draw text based on phase
        if self.phase == self.PHASE_INTRO:
            # "What is happening!?!?"
            text1 = self.title_font.render("What is happening!?!?", True, (255, 255, 100))
            text1_rect = text1.get_rect(centerx=self.center_x, y=60)
            screen.blit(text1, text1_rect)
            
            # Pokemon name (below sprite)
            name_text = self.name_font.render(self.old_name, True, (255, 255, 255))
            name_rect = name_text.get_rect(centerx=self.center_x, y=self.center_y + 120)
            screen.blit(name_text, name_rect)
        
        elif self.phase == self.PHASE_EVOLVING:
            # "[Name] is evolving!?!?"
            evolve_text = self.title_font.render(f"{self.old_name} is evolving!?!?", True, (255, 255, 100))
            evolve_rect = evolve_text.get_rect(centerx=self.center_x, y=60)
            screen.blit(evolve_text, evolve_rect)
            
            # Dots animation (below sprite)
            dots = "." * (int(self.phase_timer * 3) % 4)
            dots_text = self.title_font.render(dots, True, (255, 255, 255))
            dots_rect = dots_text.get_rect(centerx=self.center_x, y=self.center_y + 130)
            screen.blit(dots_text, dots_rect)
        
        elif self.phase == self.PHASE_TRANSFORM:
            # Just show the transformation, minimal text
            pass
        
        elif self.phase >= self.PHASE_COMPLETE:
            # "Congratulations!"
            congrats_text = self.title_font.render("Congratulations!", True, (100, 255, 100))
            congrats_rect = congrats_text.get_rect(centerx=self.center_x, y=50)
            screen.blit(congrats_text, congrats_rect)
            
            # Evolution message
            evolve_msg = self.name_font.render(f"{self.old_name} evolved into", True, (255, 255, 255))
            evolve_rect = evolve_msg.get_rect(centerx=self.center_x, y=90)
            screen.blit(evolve_msg, evolve_rect)
            
            # New name (highlighted)
            new_name_text = self.name_font.render(f"{self.new_name}!", True, (255, 220, 100))
            new_name_rect = new_name_text.get_rect(centerx=self.center_x, y=130)
            screen.blit(new_name_text, new_name_rect)
            
            # Stats boost info
            if self.monster_data:
                stats_text = self.small_font.render(
                    f"HP: {self.monster_data.get('max_hp', '?')}  "
                    f"ATK: {self.monster_data.get('attack', '?')}  "
                    f"DEF: {self.monster_data.get('defense', '?')}", 
                    True, (180, 200, 255)
                )
                stats_rect = stats_text.get_rect(centerx=self.center_x, y=self.center_y + 130)
                screen.blit(stats_text, stats_rect)
            
            # Continue prompt
            if self.phase == self.PHASE_DONE:
                prompt_alpha = int(128 + 127 * math.sin(self.total_time * 4))
                prompt_text = self.small_font.render("Click or press SPACE to continue", True, (200, 200, 200))
                prompt_text.set_alpha(prompt_alpha)
                prompt_rect = prompt_text.get_rect(centerx=self.center_x, y=GameSettings.SCREEN_HEIGHT - 60)
                screen.blit(prompt_text, prompt_rect)