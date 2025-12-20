"""
Game Menu UI - A beautiful menu with Navigation and Pokedex options.
"""
import pygame as pg
import math
from typing import Callable

from src.utils import GameSettings, Logger
from src.core.services import input_manager


class MenuOption:
    """A single menu option with icon and hover effects."""
    
    def __init__(self, x: int, y: int, width: int, height: int, 
                 icon_path: str, label: str, description: str,
                 color: tuple, on_click: Callable[[], None], disabled: bool = False):
        self.rect = pg.Rect(x, y, width, height)
        self.icon_path = icon_path
        self.label = label
        self.description = description
        self.color = color
        self.on_click = on_click
        self.hovered = False
        self.hover_scale = 1.0
        self.icon = None
        self.disabled = disabled
        self._load_icon()
        
        # Load fonts
        try:
            self.label_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
            self.desc_font = pg.font.Font("assets/fonts/Minecraft.ttf", 11)
        except:
            self.label_font = pg.font.Font(None, 24)
            self.desc_font = pg.font.Font(None, 16)
    
    def _load_icon(self):
        """Load the menu icon."""
        try:
            full_path = f"assets/images/{self.icon_path}"
            original = pg.image.load(full_path).convert_alpha()
            self.icon = pg.transform.scale(original, (48, 48))
        except Exception as e:
            Logger.warning(f"Failed to load icon {self.icon_path}: {e}")
            # Create placeholder
            self.icon = pg.Surface((48, 48), pg.SRCALPHA)
            pg.draw.rect(self.icon, self.color, (0, 0, 48, 48), border_radius=8)
    
    def update(self, dt: float, mouse_pos: tuple):
        """Update hover state and animation."""
        # Don't respond to hover/click if disabled
        if self.disabled:
            self.hovered = False
            self.hover_scale = 1.0
            return False
        
        was_hovered = self.hovered
        self.hovered = self.rect.collidepoint(mouse_pos)
        
        # Smooth scale animation
        target_scale = 1.05 if self.hovered else 1.0
        self.hover_scale += (target_scale - self.hover_scale) * 10 * dt
        
        # Check click
        if self.hovered and input_manager.mouse_pressed(1):
            self.on_click()
            return True
        return False
    
    def draw(self, screen: pg.Surface, animation_offset: float = 0):
        """Draw the menu option."""
        # Calculate animated position
        y_offset = math.sin(animation_offset) * 3 if self.hovered else 0
        
        # Scale rect for hover effect
        scaled_rect = self.rect.copy()
        if self.hover_scale != 1.0:
            width_diff = int(self.rect.width * (self.hover_scale - 1))
            height_diff = int(self.rect.height * (self.hover_scale - 1))
            scaled_rect.inflate_ip(width_diff, height_diff)
        scaled_rect.y += int(y_offset)
        
        # Disabled state - darker colors
        if self.disabled:
            bg_color = (30, 30, 35)
            border_color = (50, 50, 55)
            border_width = 2
            label_color = (80, 80, 90)
            desc_color = (60, 60, 70)
            icon_alpha = 80
        elif self.hovered:
            # Brighter when hovered
            bg_color = tuple(min(255, c + 30) for c in self.color)
            border_color = (255, 255, 255)
            border_width = 3
            label_color = (255, 255, 255)
            desc_color = (200, 200, 220)
            icon_alpha = 255
        else:
            bg_color = self.color
            border_color = tuple(min(255, c + 50) for c in self.color)
            border_width = 2
            label_color = (255, 255, 255)
            desc_color = (200, 200, 220)
            icon_alpha = 255
        
        # Draw shadow
        shadow_rect = scaled_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pg.draw.rect(screen, (0, 0, 0, 100), shadow_rect, border_radius=12)
        
        # Draw main background
        pg.draw.rect(screen, bg_color, scaled_rect, border_radius=12)
        
        # Inner highlight (skip if disabled)
        if not self.disabled:
            highlight_rect = scaled_rect.inflate(-4, -4)
            highlight_color = tuple(min(255, c + 20) for c in bg_color)
            pg.draw.rect(screen, highlight_color, highlight_rect, border_radius=10)
        
        # Border
        pg.draw.rect(screen, border_color, scaled_rect, border_width, border_radius=12)
        
        # Icon
        if self.icon:
            icon_to_draw = self.icon.copy()
            if self.disabled:
                icon_to_draw.set_alpha(icon_alpha)
            icon_rect = icon_to_draw.get_rect(
                centerx=scaled_rect.x + 45,
                centery=scaled_rect.centery + int(y_offset)
            )
            screen.blit(icon_to_draw, icon_rect)
        
        # Label
        label_text = self.label_font.render(self.label, True, label_color)
        label_rect = label_text.get_rect(
            x=scaled_rect.x + 85,
            centery=scaled_rect.centery - 10 + int(y_offset)
        )
        screen.blit(label_text, label_rect)
        
        # Description
        desc_text = self.desc_font.render(self.description, True, desc_color)
        desc_rect = desc_text.get_rect(
            x=scaled_rect.x + 85,
            centery=scaled_rect.centery + 12 + int(y_offset)
        )
        screen.blit(desc_text, desc_rect)
        
        # Draw "Not available" text if disabled
        if self.disabled:
            try:
                unavail_font = pg.font.Font("assets/fonts/Minecraft.ttf", 9)
            except:
                unavail_font = pg.font.Font(None, 12)
            unavail_text = unavail_font.render("(Main map only)", True, (100, 70, 70))
            unavail_rect = unavail_text.get_rect(
                x=scaled_rect.x + 85,
                centery=scaled_rect.centery + 26 + int(y_offset)
            )
            screen.blit(unavail_text, unavail_rect)


class GameMenuUI:
    """
    Beautiful game menu with Navigation, Pokedex, and Achievements options.
    """
    
    def __init__(self, on_navigation: Callable[[], None], on_pokedex: Callable[[], None],
                 on_achievements: Callable[[], None] = None,
                 is_on_main_map: Callable[[], bool] = None):
        """
        Initialize the menu.
        on_navigation: Callback when Navigation is selected.
        on_pokedex: Callback when Pokedex is selected.
        on_achievements: Callback when Achievements is selected.
        is_on_main_map: Callback to check if player is on main map (for navigation).
        """
        self.overlay_show = False
        self.on_navigation = on_navigation
        self.on_pokedex = on_pokedex
        self.on_achievements = on_achievements or (lambda: None)
        self.is_on_main_map = is_on_main_map or (lambda: True)
        
        # Animation
        self.animation_time = 0.0
        self.open_animation = 0.0  # 0 to 1 for opening animation
        
        # UI dimensions - taller to fit 3 options
        self.panel_width = 320
        self.panel_height = 360
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Menu options
        self.options: list[MenuOption] = []
        self._create_options()
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        self.darken.set_alpha(180)
        
        # Load fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        except:
            self.title_font = pg.font.Font(None, 32)
    
    def _create_options(self):
        """Create menu options."""
        self.options.clear()
        
        option_width = 260
        option_height = 70
        start_y = self.panel_y + 70
        spacing = 80
        
        # Check if navigation should be disabled
        nav_disabled = not self.is_on_main_map()
        
        # Navigation option
        nav_option = MenuOption(
            x=self.panel_x + (self.panel_width - option_width) // 2,
            y=start_y,
            width=option_width,
            height=option_height,
            icon_path="UI/button_play.png",
            label="Navigation",
            description="Find your way around",
            color=(50, 100, 150),
            on_click=self._select_navigation,
            disabled=nav_disabled
        )
        self.options.append(nav_option)
        
        # Pokedex option
        dex_option = MenuOption(
            x=self.panel_x + (self.panel_width - option_width) // 2,
            y=start_y + spacing,
            width=option_width,
            height=option_height,
            icon_path="ingame_ui/ball.png",
            label="Pokedex",
            description="View all Pokemon",
            color=(180, 60, 60),
            on_click=self._select_pokedex
        )
        self.options.append(dex_option)
        
        # Achievements option
        achievements_option = MenuOption(
            x=self.panel_x + (self.panel_width - option_width) // 2,
            y=start_y + spacing * 2,
            width=option_width,
            height=option_height,
            icon_path="UI/button_setting.png",
            label="Achievements",
            description="Badges & milestones",
            color=(60, 130, 90),
            on_click=self._select_achievements
        )
        self.options.append(achievements_option)
    
    def _select_navigation(self):
        """Handle navigation selection."""
        self.close()
        self.on_navigation()
    
    def _select_pokedex(self):
        """Handle pokedex selection."""
        self.close()
        self.on_pokedex()
    
    def _select_achievements(self):
        """Handle achievements selection."""
        self.close()
        self.on_achievements()
    
    def open(self):
        """Open the menu."""
        self.overlay_show = True
        self.open_animation = 0.0
        self._create_options()  # Refresh options
        input_manager.reset()
        Logger.info("Game menu opened")
    
    def close(self):
        """Close the menu."""
        self.overlay_show = False
        input_manager.reset()
    
    def update(self, dt: float):
        """Update the menu."""
        if not self.overlay_show:
            return
        
        # Update animation
        self.animation_time += dt * 3
        self.open_animation = min(1.0, self.open_animation + dt * 5)
        
        mouse_pos = input_manager.mouse_pos
        
        # Handle close with ESC
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        # Close button
        close_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 28, 28)
        if close_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
            return
        
        # Click outside to close
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        if input_manager.mouse_pressed(1) and not panel_rect.collidepoint(mouse_pos):
            self.close()
            return
        
        # Update options
        for i, option in enumerate(self.options):
            if option.update(dt, mouse_pos):
                break  # Option was clicked
    
    def draw(self, screen: pg.Surface):
        """Draw the menu."""
        if not self.overlay_show:
            return
        
        # Darken background with fade
        darken_alpha = int(180 * self.open_animation)
        self.darken.set_alpha(darken_alpha)
        screen.blit(self.darken, (0, 0))
        
        # Scale animation for panel
        scale = 0.8 + 0.2 * self.open_animation
        
        # Calculate animated panel rect
        panel_width = int(self.panel_width * scale)
        panel_height = int(self.panel_height * scale)
        panel_x = (GameSettings.SCREEN_WIDTH - panel_width) // 2
        panel_y = (GameSettings.SCREEN_HEIGHT - panel_height) // 2
        panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)
        
        # Panel shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 8
        shadow_rect.y += 8
        pg.draw.rect(screen, (0, 0, 0, 80), shadow_rect, border_radius=18)
        
        # Panel background gradient effect
        pg.draw.rect(screen, (30, 35, 50), panel_rect, border_radius=15)
        
        # Inner panel
        inner_rect = panel_rect.inflate(-8, -8)
        pg.draw.rect(screen, (40, 48, 68), inner_rect, border_radius=12)
        
        # Top accent bar
        accent_rect = pg.Rect(panel_x + 4, panel_y + 4, panel_width - 8, 50)
        pg.draw.rect(screen, (60, 75, 105), accent_rect, 
                     border_top_left_radius=12, border_top_right_radius=12)
        
        # Border
        pg.draw.rect(screen, (80, 100, 140), panel_rect, 3, border_radius=15)
        
        # Title
        title_text = self.title_font.render("MENU", True, (255, 255, 255))
        title_rect = title_text.get_rect(
            centerx=panel_x + panel_width // 2,
            centery=panel_y + 28
        )
        screen.blit(title_text, title_rect)
        
        # Close button
        close_rect = pg.Rect(panel_x + panel_width - 40, panel_y + 10, 28, 28)
        mouse_pos = input_manager.mouse_pos
        close_hovered = close_rect.collidepoint(mouse_pos)
        close_color = (200, 80, 80) if close_hovered else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_rect, border_radius=6)
        
        # X mark
        try:
            close_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        except:
            close_font = pg.font.Font(None, 20)
        close_text = close_font.render("X", True, (255, 255, 255))
        close_text_rect = close_text.get_rect(center=close_rect.center)
        screen.blit(close_text, close_text_rect)
        
        # Draw options with staggered animation
        for i, option in enumerate(self.options):
            # Stagger the animation for each option
            option_animation = max(0, self.open_animation - i * 0.1)
            if option_animation > 0:
                # Apply animation offset to option position
                original_y = option.rect.y
                option.rect.y = original_y + int((1 - option_animation) * 30)
                
                # Set alpha based on animation
                option.draw(screen, self.animation_time + i * 0.5)
                
                option.rect.y = original_y
        
        # Hint text at bottom
        try:
            hint_font = pg.font.Font("assets/fonts/Minecraft.ttf", 10)
        except:
            hint_font = pg.font.Font(None, 14)
        hint_text = hint_font.render("Press ESC to close", True, (120, 130, 150))
        hint_rect = hint_text.get_rect(
            centerx=panel_x + panel_width // 2,
            y=panel_y + panel_height - 20
        )
        screen.blit(hint_text, hint_rect)