import pygame as pg
import math
from typing import Callable

from src.utils import GameSettings
from src.sprites import Sprite


class ProfessorDialog:
    """Shows speaker's face in a circle with dialogue text."""
    
    def __init__(self):
        self.is_active = False
        self.dialogues: list[str] = []
        self.current_dialogue_index = 0
        self.displayed_text = ""
        self.text_index = 0
        self.text_timer = 0.0
        self.text_speed = 0.03
        
        # Speaker sprites
        try:
            self.professor_sprite = Sprite("professor/professor_neutral.png", (150, 150))
        except:
            self.professor_sprite = None
        
        try:
            self.misty_sprite = Sprite("misty/misty_neutral.png", (150, 150))
        except:
            # Fallback - try alternative path
            try:
                self.misty_sprite = Sprite("trainers/misty.png", (150, 150))
            except:
                self.misty_sprite = None
        
        # Current speaker sprite (changes based on dialogue)
        self.current_sprite = self.professor_sprite
        
        # Animation
        self.animation_timer = 0.0
        self.fade_alpha = 0
        self.is_fading_in = False
        self.is_fading_out = False
        
        # Position
        self.circle_x = 120
        self.circle_y = GameSettings.SCREEN_HEIGHT // 2 - 50
        self.circle_radius = 80
        
        # Dialogue box
        self.box_rect = pg.Rect(
            220,
            GameSettings.SCREEN_HEIGHT // 2 - 100,
            GameSettings.SCREEN_WIDTH - 260,
            150
        )
        
        # Fonts
        try:
            self.font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 24)
            self.continue_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
        except:
            self.font = pg.font.Font(None, 28)
            self.continue_font = pg.font.Font(None, 20)
        
        # Callback when dialogue is complete
        self.on_complete: Callable[[], None] | None = None
        
        # Click state tracking for proper click detection
        self.was_mouse_pressed = False
        self.was_key_pressed = False
        self.input_cooldown = 0.0
    
    def _get_speaker_from_text(self, text: str) -> tuple[Sprite | None, str]:
        """Determine speaker sprite and clean text based on dialogue prefix."""
        if text.startswith("Misty:"):
            return self.misty_sprite if self.misty_sprite else self.professor_sprite, text
        elif text.startswith("Professor:"):
            return self.professor_sprite, text
        else:
            # Default to professor for unmarked dialogue
            return self.professor_sprite, text
    
    def _update_current_speaker(self):
        """Update the current speaker sprite based on current dialogue."""
        if self.current_dialogue_index < len(self.dialogues):
            current_text = self.dialogues[self.current_dialogue_index]
            self.current_sprite, _ = self._get_speaker_from_text(current_text)
    
    def show(self, dialogues: list[str], on_complete: Callable[[], None] | None = None):
        """Show dialogue with appropriate speaker."""
        self.dialogues = dialogues
        self.current_dialogue_index = 0
        self.displayed_text = ""
        self.text_index = 0
        self.text_timer = 0.0
        self.is_active = True
        self.is_fading_in = True
        self.is_fading_out = False
        self.fade_alpha = 0
        self.on_complete = on_complete
        self.input_cooldown = 0.5  # Initial cooldown to prevent instant skip
        self.was_mouse_pressed = True  # Assume pressed to prevent immediate trigger
        self.was_key_pressed = True
        
        # Set initial speaker
        self._update_current_speaker()
    
    def _advance_dialogue(self):
        """Advance to next dialogue or close."""
        current_text = self.dialogues[self.current_dialogue_index] if self.current_dialogue_index < len(self.dialogues) else ""
        
        if self.text_index < len(current_text):
            # Complete current text instantly
            self.displayed_text = current_text
            self.text_index = len(current_text)
        else:
            # Move to next dialogue
            self.current_dialogue_index += 1
            if self.current_dialogue_index >= len(self.dialogues):
                self._close()
            else:
                self.displayed_text = ""
                self.text_index = 0
                self.text_timer = 0.0
                # Update speaker for new dialogue
                self._update_current_speaker()
    
    def _close(self):
        """Start closing the dialogue."""
        self.is_fading_out = True
        self.is_fading_in = False
    
    def update(self, dt: float):
        """Update dialogue state."""
        if not self.is_active:
            return
        
        self.animation_timer += dt
        
        # Update input cooldown
        if self.input_cooldown > 0:
            self.input_cooldown -= dt
        
        # Handle fading
        if self.is_fading_in:
            self.fade_alpha = min(255, self.fade_alpha + 500 * dt)
            if self.fade_alpha >= 255:
                self.is_fading_in = False
        elif self.is_fading_out:
            self.fade_alpha = max(0, self.fade_alpha - 500 * dt)
            if self.fade_alpha <= 0:
                self.is_active = False
                self.is_fading_out = False
                if self.on_complete:
                    self.on_complete()
                return
        
        # Handle input for advancing dialogue (only when not fading)
        if not self.is_fading_in and not self.is_fading_out and self.input_cooldown <= 0:
            mouse_pressed = pg.mouse.get_pressed()[0]
            key_pressed = pg.key.get_pressed()[pg.K_SPACE] or pg.key.get_pressed()[pg.K_RETURN]
            
            # Detect release-to-press transition (click)
            mouse_clicked = mouse_pressed and not self.was_mouse_pressed
            key_clicked = key_pressed and not self.was_key_pressed
            
            if mouse_clicked or key_clicked:
                self._advance_dialogue()
                self.input_cooldown = 0.2  # Small cooldown after advancing
            
            self.was_mouse_pressed = mouse_pressed
            self.was_key_pressed = key_pressed
        
        # Typewriter effect
        if not self.is_fading_in and not self.is_fading_out:
            if self.current_dialogue_index < len(self.dialogues):
                current_text = self.dialogues[self.current_dialogue_index]
                if self.text_index < len(current_text):
                    self.text_timer += dt
                    if self.text_timer >= self.text_speed:
                        self.text_timer = 0.0
                        self.text_index += 1
                        self.displayed_text = current_text[:self.text_index]
    
    def draw(self, screen: pg.Surface):
        """Draw the speaker dialogue."""
        if not self.is_active:
            return
        
        # Semi-transparent background
        overlay = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT), pg.SRCALPHA)
        overlay.fill((0, 0, 0, int(150 * (self.fade_alpha / 255))))
        screen.blit(overlay, (0, 0))
        
        # Draw dialogue box
        box_surface = pg.Surface((self.box_rect.width, self.box_rect.height), pg.SRCALPHA)
        pg.draw.rect(box_surface, (255, 255, 255, int(240 * (self.fade_alpha / 255))), 
                     (0, 0, self.box_rect.width, self.box_rect.height), border_radius=15)
        
        # Use different border color based on speaker
        if self.current_sprite == self.misty_sprite:
            border_color = (50, 150, 200, int(self.fade_alpha))  # Blue for Misty
        else:
            border_color = (50, 50, 150, int(self.fade_alpha))  # Purple for Professor
        
        pg.draw.rect(box_surface, border_color, 
                     (0, 0, self.box_rect.width, self.box_rect.height), 4, border_radius=15)
        screen.blit(box_surface, self.box_rect.topleft)
        
        # Draw speaker circle
        circle_surface = pg.Surface((self.circle_radius * 2 + 10, self.circle_radius * 2 + 10), pg.SRCALPHA)
        
        # Outer glow/border - match speaker color
        if self.current_sprite == self.misty_sprite:
            glow_color = (100, 200, 255, int(self.fade_alpha * 0.8))  # Cyan for Misty
        else:
            glow_color = (100, 150, 255, int(self.fade_alpha * 0.8))  # Blue for Professor
        
        pg.draw.circle(circle_surface, glow_color, 
                       (self.circle_radius + 5, self.circle_radius + 5), self.circle_radius + 5)
        
        # White background circle
        pg.draw.circle(circle_surface, (255, 255, 255, int(self.fade_alpha)), 
                       (self.circle_radius + 5, self.circle_radius + 5), self.circle_radius)
        
        # Draw current speaker sprite inside circle
        if self.current_sprite:
            # Create circular mask
            mask_surface = pg.Surface((self.circle_radius * 2, self.circle_radius * 2), pg.SRCALPHA)
            pg.draw.circle(mask_surface, (255, 255, 255), (self.circle_radius, self.circle_radius), self.circle_radius)
            
            # Scale and position speaker sprite
            speaker_img = pg.transform.scale(self.current_sprite.image, (self.circle_radius * 2, self.circle_radius * 2))
            speaker_img.set_alpha(int(self.fade_alpha))
            
            # Apply mask
            masked = pg.Surface((self.circle_radius * 2, self.circle_radius * 2), pg.SRCALPHA)
            masked.blit(speaker_img, (0, 0))
            masked.blit(mask_surface, (0, 0), special_flags=pg.BLEND_RGBA_MIN)
            
            circle_surface.blit(masked, (5, 5))
        
        # Add bobbing animation
        bob_offset = math.sin(self.animation_timer * 3) * 5
        screen.blit(circle_surface, (self.circle_x - self.circle_radius - 5, 
                                      self.circle_y - self.circle_radius - 5 + bob_offset))
        
        # Draw text with word wrapping
        if self.displayed_text:
            self._draw_wrapped_text(screen, self.displayed_text, 
                                    self.box_rect.inflate(-30, -30))
        
        # Draw continue prompt
        if not self.is_fading_in and not self.is_fading_out:
            current_text = self.dialogues[self.current_dialogue_index] if self.current_dialogue_index < len(self.dialogues) else ""
            if self.text_index >= len(current_text):
                if (int(self.animation_timer * 2) % 2) == 0:
                    continue_text = self.continue_font.render("Click or press SPACE to continue ▶", True, (100, 100, 100))
                    continue_text.set_alpha(int(self.fade_alpha))
                    screen.blit(continue_text, (self.box_rect.right - 280, self.box_rect.bottom - 25))
    
    def _draw_wrapped_text(self, screen: pg.Surface, text: str, rect: pg.Rect):
        """Draw text with word wrapping."""
        words = text.split(" ")
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            if self.font.size(test_line)[0] <= rect.width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())
        
        y = rect.y + 15
        for line in lines:
            text_surface = self.font.render(line, True, (0, 0, 0))
            text_surface.set_alpha(int(self.fade_alpha))
            screen.blit(text_surface, (rect.x + 15, y))
            y += text_surface.get_height() + 5