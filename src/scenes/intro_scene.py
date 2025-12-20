import pygame as pg
from typing import Any, override
import math

from src.scenes.scene import Scene
from src.core.services import input_manager, scene_manager, sound_manager
from src.utils import Logger, GameSettings
from src.sprites import Sprite


class IntroScene(Scene):
    """Pokemon-style intro scene where the professor wakes you up on your 18th birthday."""

    STATE_WAKE_UP = 0
    STATE_BIRTHDAY = 1
    STATE_POKEMON_WORLD = 2
    STATE_ASK_NAME = 3
    STATE_TYPING = 4
    STATE_CONFIRM_NAME = 5
    STATE_ADVENTURE = 6
    STATE_POKEMON_APPEAR = 7
    STATE_FADE_OUT = 8

    def __init__(self):
        super().__init__()

        self.state = self.STATE_WAKE_UP

        # --------------------------------------------------
        # Professor sprites (bigger)
        # --------------------------------------------------
        self.professor_neutral = Sprite("professor/professor_neutral.png", (400, 400))
        self.professor_happy = Sprite("professor/professor_happy.png", (400, 400))

        for sprite in (self.professor_neutral, self.professor_happy):
            sprite.rect.center = (
                GameSettings.SCREEN_WIDTH // 2,
                GameSettings.SCREEN_HEIGHT // 2 - 120
            )

        self.current_professor = self.professor_neutral

        # --------------------------------------------------
        # Pokemon sprites for the final animation
        # --------------------------------------------------
        self.pokemon_sprites: list[dict] = []
        self._setup_pokemon_sprites()
        
        # Animation state
        self.pokemon_animation_timer = 0.0
        self.pokemon_visible = False
        self.can_advance_from_pokemon = False

        # --------------------------------------------------
        # Background
        # --------------------------------------------------
        try:
            self.background = Sprite("backgrounds/introduction_background1.png", 
                                    (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
            Logger.info("Loaded introduction background successfully")
        except Exception as e:
            # Fallback to solid color if no background image
            Logger.error(f"Failed to load introduction background: {e}")
            self.background = None
            self.background_surface = pg.Surface(
                (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
            )
            self.background_surface.fill((180, 140, 100))  # Warm brown for house

        # --------------------------------------------------
        # Dialogue system
        # --------------------------------------------------
        self.current_dialogue = ""
        self.displayed_dialogue = ""
        self.dialogue_index = 0
        self.dialogue_timer = 0.0
        self.dialogue_speed = 0.03

        # --------------------------------------------------
        # Fonts
        # --------------------------------------------------
        try:
            self.dialogue_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 28)
            self.input_font = pg.font.Font("assets/fonts/Minecraft.ttf", 26)
            self.ui_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        except:
            self.dialogue_font = pg.font.Font(None, 32)
            self.input_font = pg.font.Font(None, 30)
            self.ui_font = pg.font.Font(None, 22)

        # --------------------------------------------------
        # Name input
        # --------------------------------------------------
        self.player_name = ""
        self.max_name_length = 12

        self.input_box_rect = pg.Rect(0, 0, 320, 50)
        self.input_box_rect.center = (
            GameSettings.SCREEN_WIDTH // 2,
            GameSettings.SCREEN_HEIGHT // 2 + 140
        )

        self.cursor_visible = True
        self.cursor_timer = 0.0
        self.cursor_blink_rate = 0.5

        # --------------------------------------------------
        # Confirm button (custom styled, not image-based)
        # --------------------------------------------------
        self.confirm_button_rect = pg.Rect(
            GameSettings.SCREEN_WIDTH // 2 - 60,
            self.input_box_rect.bottom + 15,
            120,
            45
        )
        self.confirm_button_hovered = False

        # --------------------------------------------------
        # Fade effect
        # --------------------------------------------------
        self.fade_surface = pg.Surface(
            (GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT)
        )
        self.fade_surface.fill((0, 0, 0))
        self.fade_alpha = 255
        self.fade_speed = 200
        self.fading_in = True

    def _setup_pokemon_sprites(self):
        """Setup Pokemon sprites that will appear around the professor."""
        # Bigger size for Pokemon sprites
        pokemon_size = 180
        
        # Adjusted offsets:
        # Pikachu & Blastoise: +15x, +15y (down and right)
        # Charizard & Venusaur: -15x, +15y (down and left)
        pokemon_data = [
            {"path": "menu_sprites/pikachu.png", "offset": (-235, -65), "delay": 0.0},
            {"path": "menu_sprites/charizard.png", "offset": (235, -65), "delay": 0.3},
            {"path": "menu_sprites/blastoise.png", "offset": (-165, 75), "delay": 0.6},
            {"path": "menu_sprites/venusaur.png", "offset": (165, 75), "delay": 0.9},
        ]
        
        # Center position moved up by 50 pixels (was -150, now -200)
        center_x = GameSettings.SCREEN_WIDTH // 2
        center_y = GameSettings.SCREEN_HEIGHT // 2 - 200
        
        for data in pokemon_data:
            try:
                sprite = Sprite(data["path"], (pokemon_size, pokemon_size))
                target_x = center_x + data["offset"][0]
                target_y = center_y + data["offset"][1]
                
                # Start position (at center/professor)
                start_x = center_x
                start_y = center_y
                
                self.pokemon_sprites.append({
                    "sprite": sprite,
                    "start_x": start_x,
                    "start_y": start_y,
                    "target_x": target_x,
                    "target_y": target_y,
                    "current_x": start_x,
                    "current_y": start_y,
                    "delay": data["delay"],
                    "progress": 0.0,
                    "alpha": 0,
                    "bounce_offset": 0.0,
                })
                Logger.info(f"Loaded Pokemon sprite: {data['path']}")
            except Exception as e:
                Logger.warning(f"Could not load Pokemon sprite {data['path']}: {e}")

    def _reset_pokemon_animation(self):
        """Reset all Pokemon to their starting positions."""
        center_x = GameSettings.SCREEN_WIDTH // 2
        center_y = GameSettings.SCREEN_HEIGHT // 2 - 200  # Moved up 50 pixels
        
        for pokemon in self.pokemon_sprites:
            pokemon["current_x"] = center_x
            pokemon["current_y"] = center_y
            pokemon["progress"] = 0.0
            pokemon["alpha"] = 0
            pokemon["bounce_offset"] = 0.0
        
        self.pokemon_animation_timer = 0.0
        self.pokemon_visible = True
        self.can_advance_from_pokemon = False

    def _update_pokemon_animation(self, dt: float):
        """Update Pokemon animation - they fly out from center and bounce."""
        self.pokemon_animation_timer += dt
        
        for pokemon in self.pokemon_sprites:
            # Wait for delay
            if self.pokemon_animation_timer < pokemon["delay"]:
                continue
            
            # Calculate progress (0 to 1)
            time_since_start = self.pokemon_animation_timer - pokemon["delay"]
            duration = 0.8  # Animation duration in seconds
            
            if pokemon["progress"] < 1.0:
                pokemon["progress"] = min(1.0, time_since_start / duration)
                
                # Ease out cubic for smooth deceleration
                t = pokemon["progress"]
                ease = 1 - (1 - t) ** 3
                
                # Interpolate position
                pokemon["current_x"] = pokemon["start_x"] + (pokemon["target_x"] - pokemon["start_x"]) * ease
                pokemon["current_y"] = pokemon["start_y"] + (pokemon["target_y"] - pokemon["start_y"]) * ease
                
                # Fade in
                pokemon["alpha"] = int(255 * min(1.0, t * 2))
            else:
                # Bounce animation after reaching target
                bounce_time = time_since_start - duration
                pokemon["bounce_offset"] = math.sin(bounce_time * 4) * 8 * max(0, 1 - bounce_time * 0.3)
                pokemon["alpha"] = 255
        
        # Allow advancing after 2 seconds
        if self.pokemon_animation_timer > 2.0:
            self.can_advance_from_pokemon = True

    # ==================================================
    # Button callback
    # ==================================================

    def _on_confirm(self):
        """Handle confirm button press."""
        if self.state == self.STATE_TYPING:
            if self.player_name.strip():
                self._advance_state()

    # ==================================================
    # Dialogue helpers
    # ==================================================

    def _get_dialogue_for_state(self) -> str:
        if self.state == self.STATE_WAKE_UP:
            return "Rise and shine, sleepyhead! Wake up!"
        elif self.state == self.STATE_BIRTHDAY:
            return "Today is a very special day... You've turned 18 years old!"
        elif self.state == self.STATE_POKEMON_WORLD:
            return "You are finally ready to explore the world of Pokemon!"
        elif self.state == self.STATE_ASK_NAME:
            return "But first, remind me... What was your name again?"
        elif self.state == self.STATE_TYPING:
            return "Please enter your name:"
        elif self.state == self.STATE_CONFIRM_NAME:
            return f"Ah yes, {self.player_name}! I remember now. What a wonderful name!"
        elif self.state == self.STATE_ADVENTURE:
            return "The world of Pokemon awaits you! Your adventure starts NOW!"
        elif self.state == self.STATE_POKEMON_APPEAR:
            return "Go out there and become the greatest Pokemon trainer!"
        return ""

    def _advance_state(self):
        self.state += 1
        self.dialogue_index = 0
        self.displayed_dialogue = ""
        self.dialogue_timer = 0.0
        
        # Handle state transitions
        if self.state == self.STATE_CONFIRM_NAME:
            self.current_professor = self.professor_happy
        
        if self.state == self.STATE_POKEMON_APPEAR:
            self._reset_pokemon_animation()

        if self.state > self.STATE_POKEMON_APPEAR:
            self.state = self.STATE_FADE_OUT
            return
        
        self.current_dialogue = self._get_dialogue_for_state()

    def _is_dialogue_complete(self) -> bool:
        return self.dialogue_index >= len(self.current_dialogue)

    def _complete_dialogue(self):
        self.displayed_dialogue = self.current_dialogue
        self.dialogue_index = len(self.current_dialogue)

    # ==================================================
    # Scene lifecycle
    # ==================================================

    @override
    def enter(self, data: Any = None):
        Logger.info("Entering IntroScene")

        self.state = self.STATE_WAKE_UP
        self.player_name = ""
        self.current_professor = self.professor_neutral
        self.current_dialogue = self._get_dialogue_for_state()
        self.displayed_dialogue = ""
        self.dialogue_index = 0
        self.pokemon_visible = False
        self.can_advance_from_pokemon = False
        self.pokemon_animation_timer = 0.0

        self.fade_alpha = 255
        self.fading_in = True

    @override
    def exit(self):
        Logger.info("Exiting IntroScene")

    @override
    def update(self, dt: float):
        # Fade in
        if self.fading_in:
            self.fade_alpha -= self.fade_speed * dt
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fading_in = False
            return

        # Fade out
        if self.state == self.STATE_FADE_OUT:
            self.fade_alpha += self.fade_speed * dt
            if self.fade_alpha >= 255:
                scene_manager.change_scene("game", {"player_name": self.player_name})
            return

        # Update Pokemon animation
        if self.pokemon_visible:
            self._update_pokemon_animation(dt)

        # Typewriter effect
        if not self._is_dialogue_complete():
            self.dialogue_timer += dt
            if self.dialogue_timer >= self.dialogue_speed:
                self.dialogue_timer = 0.0
                self.dialogue_index += 1
                self.displayed_dialogue = self.current_dialogue[:self.dialogue_index]

        # Handle input for state advancement
        clicked = input_manager.key_pressed(pg.K_SPACE) or input_manager.mouse_pressed(0)
        
        if self.state == self.STATE_TYPING:
            # Typing state - handle cursor and button
            self.cursor_timer += dt
            if self.cursor_timer >= self.cursor_blink_rate:
                self.cursor_timer = 0.0
                self.cursor_visible = not self.cursor_visible
            
            # Custom button hover detection
            mouse_pos = pg.mouse.get_pos()
            self.confirm_button_hovered = self.confirm_button_rect.collidepoint(mouse_pos)
            
            # Handle button click
            if input_manager.mouse_pressed(1) and self.confirm_button_hovered:
                if self.player_name.strip():
                    self._advance_state()
            
        elif self.state == self.STATE_POKEMON_APPEAR:
            # Pokemon appear state - wait for animation before allowing advance
            if clicked:
                if self._is_dialogue_complete() and self.can_advance_from_pokemon:
                    self._advance_state()
                elif not self._is_dialogue_complete():
                    self._complete_dialogue()
        else:
            # All other states
            if clicked:
                if self._is_dialogue_complete():
                    self._advance_state()
                else:
                    self._complete_dialogue()

    def handle_event(self, event: pg.event.Event):
        if self.state != self.STATE_TYPING or event.type != pg.KEYDOWN:
            return

        if event.key == pg.K_BACKSPACE:
            self.player_name = self.player_name[:-1]
        elif event.key in (pg.K_RETURN, pg.K_KP_ENTER):
            if self.player_name.strip():
                self._advance_state()
        elif len(self.player_name) < self.max_name_length:
            if event.unicode.isalnum() or event.unicode == " ":
                self.player_name += event.unicode

    # ==================================================
    # Drawing
    # ==================================================

    def _draw_wrapped_text(self, screen, text, rect):
        words = text.split(" ")
        lines = []
        current = ""

        for word in words:
            test = current + word + " "
            if self.dialogue_font.size(test)[0] <= rect.width - 40:
                current = test
            else:
                lines.append(current)
                current = word + " "
        lines.append(current)

        y = rect.y + 18
        for line in lines:
            surf = self.dialogue_font.render(line, True, (0, 0, 0))
            screen.blit(surf, (rect.x + 20, y))
            y += surf.get_height() + 4

    def _draw_dialogue_box(self, screen):
        rect = pg.Rect(
            40,
            GameSettings.SCREEN_HEIGHT - 160,
            GameSettings.SCREEN_WIDTH - 80,
            120
        )

        shadow = rect.move(4, 4)
        pg.draw.rect(screen, (100, 100, 100), shadow, border_radius=12)
        pg.draw.rect(screen, (255, 255, 255), rect, border_radius=12)
        pg.draw.rect(screen, (50, 50, 150), rect, 4, border_radius=12)

        self._draw_wrapped_text(screen, self.displayed_dialogue, rect)

        # Show continue prompt
        if self._is_dialogue_complete() and self.state != self.STATE_TYPING:
            # For Pokemon appear state, only show after animation is ready
            if self.state == self.STATE_POKEMON_APPEAR and not self.can_advance_from_pokemon:
                return
            if (pg.time.get_ticks() // 400) % 2 == 0:
                arrow = self.ui_font.render("▶ Click to continue", True, (100, 100, 100))
                screen.blit(arrow, (rect.right - 160, rect.bottom - 25))

    def _draw_pokemon(self, screen):
        """Draw the Pokemon sprites with animation."""
        if not self.pokemon_visible:
            return
        
        if len(self.pokemon_sprites) == 0:
            # No sprites loaded - draw placeholder circles (bigger)
            center_x = GameSettings.SCREEN_WIDTH // 2
            center_y = GameSettings.SCREEN_HEIGHT // 2 - 200  # Moved up 50 pixels
            offsets = [(-235, -65), (235, -65), (-165, 75), (165, 75)]
            
            for i, (ox, oy) in enumerate(offsets):
                delay = i * 0.3
                if self.pokemon_animation_timer < delay:
                    continue
                
                t = min(1.0, (self.pokemon_animation_timer - delay) / 0.8)
                ease = 1 - (1 - t) ** 3
                
                x = center_x + ox * ease
                y = center_y + oy * ease
                alpha = int(255 * min(1.0, t * 2))
                
                # Draw a colored circle as placeholder (bigger)
                colors = [(255, 255, 0), (255, 100, 0), (0, 150, 255), (0, 200, 100)]
                size = 90  # Bigger placeholder
                surf = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
                pg.draw.circle(surf, (*colors[i], alpha), (size, size), size)
                screen.blit(surf, (x - size, y - size))
            return
        
        for pokemon in self.pokemon_sprites:
            if pokemon["alpha"] <= 0:
                continue
            
            sprite = pokemon["sprite"]
            x = pokemon["current_x"]
            y = pokemon["current_y"] + pokemon["bounce_offset"]
            
            # Create a copy of the image with alpha
            img = sprite.image.copy()
            img.set_alpha(pokemon["alpha"])
            
            rect = img.get_rect(center=(int(x), int(y)))
            screen.blit(img, rect)

    def _draw_sparkles(self, screen):
        """Draw sparkle effects (stay at original position, don't follow Pokemon)."""
        if not self.pokemon_visible or self.pokemon_animation_timer < 1.0:
            return
        
        center_x = GameSettings.SCREEN_WIDTH // 2
        center_y = GameSettings.SCREEN_HEIGHT // 2 - 150  # Original position (sparkles stay here)
        
        # Fixed sparkle positions (original offsets)
        offsets = [(-220, -60), (220, -60), (-160, 60), (160, 60)]
        positions = [(center_x + ox, center_y + oy) for ox, oy in offsets]
        
        sparkle_time = self.pokemon_animation_timer * 3
        
        for i, (x, y) in enumerate(positions):
            # Draw bigger sparkles
            for j in range(5):  # More sparkles
                angle = sparkle_time + i * 2 + j * 1.26
                dist = 80 + math.sin(sparkle_time * 2 + j) * 20  # Bigger orbit
                sx = x + math.cos(angle) * dist
                sy = y + math.sin(angle) * dist
                
                alpha = int(128 + 127 * math.sin(sparkle_time * 4 + j))
                size = int(6 + 4 * math.sin(sparkle_time * 3 + j))  # Bigger sparkles
                
                sparkle_surf = pg.Surface((size * 2, size * 2), pg.SRCALPHA)
                pg.draw.circle(sparkle_surf, (255, 255, 200, alpha), (size, size), size)
                screen.blit(sparkle_surf, (sx - size, sy - size))

    @override
    def draw(self, screen: pg.Surface):
        # Draw background
        if self.background:
            self.background.draw(screen)
        else:
            screen.blit(self.background_surface, (0, 0))

        # Draw professor first
        self.current_professor.draw(screen)
        
        # Draw Pokemon on top of professor
        self._draw_pokemon(screen)
        self._draw_sparkles(screen)

        # Draw dialogue box
        self._draw_dialogue_box(screen)

        # Draw name input if in typing state
        if self.state == self.STATE_TYPING:
            # Draw input box with nice styling
            shadow_rect = self.input_box_rect.move(3, 3)
            pg.draw.rect(screen, (100, 100, 100), shadow_rect, border_radius=8)
            
            border_color = (32, 144, 255) if self.cursor_visible else (50, 50, 150)
            pg.draw.rect(screen, (255, 255, 255), self.input_box_rect, border_radius=8)
            pg.draw.rect(screen, border_color, self.input_box_rect, 3, border_radius=8)

            text = self.player_name + ("|" if self.cursor_visible else "")
            surf = self.input_font.render(text, True, (0, 0, 0))
            screen.blit(
                surf,
                (self.input_box_rect.x + 12, self.input_box_rect.y + 10)
            )

            # Draw custom styled confirm button
            btn_rect = self.confirm_button_rect
            
            # Button shadow
            shadow = btn_rect.move(3, 3)
            pg.draw.rect(screen, (30, 80, 30), shadow, border_radius=10)
            
            # Button colors based on hover state
            if self.confirm_button_hovered:
                btn_color = (80, 180, 80)
                border_color = (120, 220, 120)
            else:
                btn_color = (60, 140, 60)
                border_color = (90, 180, 90)
            
            # Button background
            pg.draw.rect(screen, btn_color, btn_rect, border_radius=8)
            
            # Gradient effect (darker bottom)
            dark_rect = pg.Rect(btn_rect.x, btn_rect.y + btn_rect.height // 2,
                               btn_rect.width, btn_rect.height // 2)
            dark_color = (btn_color[0] - 20, btn_color[1] - 30, btn_color[2] - 20)
            pg.draw.rect(screen, dark_color, dark_rect,
                        border_bottom_left_radius=8, border_bottom_right_radius=8)
            
            # Button border
            pg.draw.rect(screen, border_color, btn_rect, 3, border_radius=8)
            
            # Button text
            btn_text = self.ui_font.render("CONFIRM", True, (255, 255, 255))
            screen.blit(btn_text, (btn_rect.centerx - btn_text.get_width() // 2,
                                   btn_rect.centery - btn_text.get_height() // 2))

        # Draw fade overlay
        if self.fade_alpha > 0:
            self.fade_surface.set_alpha(int(self.fade_alpha))
            screen.blit(self.fade_surface, (0, 0))