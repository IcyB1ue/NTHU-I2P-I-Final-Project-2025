import pygame as pg

from src.utils import GameSettings
from src.sprites import BackgroundSprite
from src.scenes.scene import Scene
from src.interface.components import Button
from src.core.services import scene_manager, sound_manager, input_manager
from typing import override, Any


class MenuSettings:
    """Settings overlay for menu - audio only (no save/load)."""
    
    def __init__(self):
        self.overlay_show = False
        
        # Panel dimensions
        self.panel_width = 500
        self.panel_height = 280
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill((0, 0, 0))
        self.darken.set_alpha(180)
        
        # Fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
            self.label_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
            self.small_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        except:
            self.title_font = pg.font.Font(None, 32)
            self.label_font = pg.font.Font(None, 22)
            self.small_font = pg.font.Font(None, 18)
        
        # Audio settings
        self.volume = GameSettings.AUDIO_VOLUME
        self.is_muted = False
        
        # Slider dragging
        self.dragging_slider = False
        
    def open(self): 
        self.overlay_show = True
        
    def close(self): 
        self.overlay_show = False
        self.dragging_slider = False
        
    def update(self, dt: float):
        if not self.overlay_show:
            return
        
        mouse_pos = pg.mouse.get_pos()
        mouse_pressed = pg.mouse.get_pressed()[0]
        
        # Handle slider dragging
        slider_x = self.panel_x + 50
        slider_y = self.panel_y + 130
        slider_width = 300
        slider_height = 20
        slider_rect = pg.Rect(slider_x, slider_y, slider_width, slider_height)
        
        if mouse_pressed:
            if slider_rect.collidepoint(mouse_pos) or self.dragging_slider:
                self.dragging_slider = True
                # Calculate new volume
                rel_x = mouse_pos[0] - slider_x
                self.volume = max(0.0, min(1.0, rel_x / slider_width))
                sound_manager.set_master_volume(self.volume)
        else:
            self.dragging_slider = False
        
        # Handle clicks
        if input_manager.mouse_pressed(1):
            # Close button
            close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
            if close_btn_rect.collidepoint(mouse_pos):
                self.close()
                return
            
            # Mute toggle
            mute_btn_rect = pg.Rect(self.panel_x + 420, self.panel_y + 125, 60, 30)
            if mute_btn_rect.collidepoint(mouse_pos):
                self.is_muted = not self.is_muted
                if self.is_muted:
                    sound_manager.pause_all()
                else:
                    sound_manager.resume_all()
                return
        
        # Handle escape
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            
    def draw(self, screen: pg.Surface):
        if not self.overlay_show:
            return
        
        mouse_pos = pg.mouse.get_pos()
        
        # Darken background
        screen.blit(self.darken, (0, 0))
        
        # Main panel
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        
        # Panel shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5
        pg.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=15)
        
        # Panel background
        pg.draw.rect(screen, (40, 45, 60), panel_rect, border_radius=12)
        
        # Panel border
        pg.draw.rect(screen, (80, 90, 110), panel_rect, 3, border_radius=12)
        
        # Title bar
        title_bar = pg.Rect(self.panel_x, self.panel_y, self.panel_width, 50)
        pg.draw.rect(screen, (60, 70, 90), title_bar, 
                     border_top_left_radius=12, border_top_right_radius=12)
        
        # Title
        title_text = self.title_font.render("SETTINGS", True, (255, 255, 255))
        screen.blit(title_text, (self.panel_x + 20, self.panel_y + 12))
        
        # Close button
        close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
        close_color = (200, 80, 80) if close_btn_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_btn_rect, border_radius=5)
        x_text = self.label_font.render("X", True, (255, 255, 255))
        screen.blit(x_text, (close_btn_rect.centerx - x_text.get_width() // 2, 
                            close_btn_rect.centery - x_text.get_height() // 2))
        
        # === AUDIO SECTION ===
        section_y = self.panel_y + 70
        
        # Section header
        audio_header = self.label_font.render("AUDIO", True, (150, 200, 255))
        screen.blit(audio_header, (self.panel_x + 20, section_y))
        
        # Divider
        pg.draw.line(screen, (80, 90, 110), 
                     (self.panel_x + 20, section_y + 25), 
                     (self.panel_x + self.panel_width - 20, section_y + 25), 2)
        
        # Volume label
        vol_label = self.small_font.render("Master Volume", True, (180, 180, 180))
        screen.blit(vol_label, (self.panel_x + 50, section_y + 40))
        
        # Volume slider background
        slider_x = self.panel_x + 50
        slider_y = section_y + 60
        slider_width = 300
        slider_height = 20
        
        pg.draw.rect(screen, (30, 30, 35), (slider_x, slider_y, slider_width, slider_height), border_radius=5)
        
        # Volume slider fill
        fill_width = int(slider_width * self.volume)
        if fill_width > 0:
            pg.draw.rect(screen, (80, 150, 220), (slider_x, slider_y, fill_width, slider_height), border_radius=5)
        
        # Slider handle
        handle_x = slider_x + fill_width - 8
        handle_rect = pg.Rect(handle_x, slider_y - 3, 16, slider_height + 6)
        handle_color = (120, 180, 255) if self.dragging_slider else (100, 160, 230)
        pg.draw.rect(screen, handle_color, handle_rect, border_radius=3)
        pg.draw.rect(screen, (150, 200, 255), handle_rect, 2, border_radius=3)
        
        # Volume percentage
        vol_pct = self.small_font.render(f"{int(self.volume * 100)}%", True, (255, 255, 255))
        screen.blit(vol_pct, (slider_x + slider_width + 15, slider_y + 2))
        
        # Mute button
        mute_btn_rect = pg.Rect(self.panel_x + 420, section_y + 55, 60, 30)
        mute_hovered = mute_btn_rect.collidepoint(mouse_pos)
        
        if self.is_muted:
            mute_color = (180, 80, 80) if mute_hovered else (150, 60, 60)
            mute_text = "MUTED"
        else:
            mute_color = (80, 140, 80) if mute_hovered else (60, 110, 60)
            mute_text = "SOUND"
        
        pg.draw.rect(screen, mute_color, mute_btn_rect, border_radius=5)
        pg.draw.rect(screen, (100, 100, 120), mute_btn_rect, 2, border_radius=5)
        
        mute_label = self.small_font.render(mute_text, True, (255, 255, 255))
        screen.blit(mute_label, (mute_btn_rect.centerx - mute_label.get_width() // 2,
                                 mute_btn_rect.centery - mute_label.get_height() // 2))
        
        # === FOOTER INFO ===
        footer_text = self.small_font.render("Press ESC to close", True, (100, 100, 110))
        screen.blit(footer_text, (self.panel_x + self.panel_width // 2 - footer_text.get_width() // 2,
                                  self.panel_y + self.panel_height - 25))


class MenuScene(Scene):
    # Background Image
    background: BackgroundSprite
    # Buttons
    play_button: Button
    
    def __init__(self):
        super().__init__()
        self.background = BackgroundSprite("backgrounds/menu_background.png")

        px, py = GameSettings.SCREEN_WIDTH // 2, GameSettings.SCREEN_HEIGHT * 3 // 4
        self.play_button = Button(
            "UI/button_play.png", "UI/button_play_hover.png",
            px + 50, py, 100, 100,
            lambda: scene_manager.change_scene("intro")
        )

        self.settings_button = Button(
            "UI/button_setting.png", "UI/button_setting_hover.png",
            px - 150, py, 100, 100,
            self._open_settings
        )

        # Settings overlay
        self.settings = MenuSettings()

    def _open_settings(self):
        """Open the settings overlay."""
        self.settings.open()
        
    @override
    def enter(self, data: Any = None) -> None:
        sound_manager.play_bgm("RBY 101 Opening (Part 1).ogg")
        pass

    @override
    def exit(self) -> None:
        pass

    @override
    def update(self, dt: float) -> None:
        # Update settings first
        self.settings.update(dt)
        
        # Block other input if settings is open
        if self.settings.overlay_show:
            return
        
        if input_manager.key_pressed(pg.K_SPACE):
            scene_manager.change_scene("intro")
            return
        self.play_button.update(dt)
        self.settings_button.update(dt)

    @override
    def draw(self, screen: pg.Surface) -> None:
        self.background.draw(screen)
        self.play_button.draw(screen)
        self.settings_button.draw(screen)
        
        # Draw settings overlay on top
        self.settings.draw(screen)