"""
Achievements & Badges UI - Shows player badges and achievements.
Left side: Gym/Story Badges
Right side: Various achievements
"""
import pygame as pg
import math
from typing import Callable

from src.utils import GameSettings, Logger
from src.core.services import input_manager


# Badge data: (id, name, description, icon_color, requirement_desc)
BADGES_DATA = [
    ("fire_gym", "Fire Badge", "Defeated the Fire Gym", (255, 100, 50), "Defeat Fire Gym Leader"),
    ("night_survivor", "Night Survivor", "Survived the night", (100, 50, 150), "Survive until dawn"),
    ("water_master", "Water Master", "Mastered water travel", (80, 150, 255), "Unlock water walking"),
]

# Achievement data: (id, name, description, icon_color, check_func_name)
ACHIEVEMENTS_DATA = [
    ("tutorial_complete", "Getting Started", "Complete the tutorial", (100, 200, 100)),
    ("first_catch", "Pokemon Trainer", "Catch your first Pokemon", (200, 150, 50)),
    ("catch_10", "Collector", "Catch 10 Pokemon", (180, 130, 60)),
    ("catch_20", "Pokemon Master", "Catch 20 Pokemon", (220, 180, 50)),
    ("first_battle", "Challenger", "Win your first trainer battle", (200, 80, 80)),
    ("win_5_battles", "Battle Expert", "Win 5 trainer battles", (220, 60, 60)),
    ("first_evolution", "Evolution!", "Evolve a Pokemon", (150, 100, 200)),
    ("earn_100_coins", "Coin Collector", "Earn 100 coins total", (255, 200, 50)),
    ("earn_500_coins", "Rich Trainer", "Earn 500 coins total", (255, 220, 100)),
    ("quiz_master", "Quiz Master", "Answer 10 quiz questions correctly", (100, 150, 200)),
    ("pokedex_50", "Researcher", "Fill 50% of the Pokedex", (200, 100, 150)),
    ("full_party", "Full Team", "Have 6 Pokemon in your party", (150, 180, 100)),
]


class BadgeDisplay:
    """Display for a single badge."""
    
    def __init__(self, x: int, y: int, size: int, badge_data: tuple, is_unlocked: bool):
        self.rect = pg.Rect(x, y, size, size)
        self.badge_id, self.name, self.description, self.color, self.requirement = badge_data
        self.is_unlocked = is_unlocked
        self.hovered = False
        
        # Load fonts
        try:
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 11)
        except:
            self.name_font = pg.font.Font(None, 15)
    
    def update(self, mouse_pos: tuple):
        """Update hover state."""
        self.hovered = self.rect.collidepoint(mouse_pos)
    
    def draw(self, screen: pg.Surface):
        """Draw the badge."""
        center_x = self.rect.centerx
        center_y = self.rect.centery - 10
        
        # Badge background
        if self.is_unlocked:
            # Golden glow for unlocked
            if self.hovered:
                glow_surf = pg.Surface((self.rect.width + 20, self.rect.height + 20), pg.SRCALPHA)
                pg.draw.circle(glow_surf, (*self.color, 60), 
                              (self.rect.width // 2 + 10, self.rect.height // 2 + 10), 45)
                screen.blit(glow_surf, (self.rect.x - 10, self.rect.y - 10))
            
            # Badge shape (octagon-ish)
            badge_color = self.color
            outline_color = (255, 215, 0)  # Gold outline
        else:
            # Locked - grey and darker
            badge_color = (40, 40, 50)
            outline_color = (60, 60, 70)
        
        # Draw octagonal badge shape
        points = []
        for i in range(8):
            angle = math.pi / 8 + i * math.pi / 4
            px = center_x + 32 * math.cos(angle)
            py = center_y + 32 * math.sin(angle)
            points.append((px, py))
        
        pg.draw.polygon(screen, badge_color, points)
        pg.draw.polygon(screen, outline_color, points, 3)
        
        # Inner design
        if self.is_unlocked:
            # Star or emblem in center
            inner_points = []
            for i in range(8):
                angle = math.pi / 8 + i * math.pi / 4
                radius = 15 if i % 2 == 0 else 22
                px = center_x + radius * math.cos(angle)
                py = center_y + radius * math.sin(angle)
                inner_points.append((px, py))
            pg.draw.polygon(screen, (255, 255, 200), inner_points)
        else:
            # Question mark for locked
            try:
                q_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
            except:
                q_font = pg.font.Font(None, 32)
            q_text = q_font.render("?", True, (80, 80, 90))
            q_rect = q_text.get_rect(center=(center_x, center_y))
            screen.blit(q_text, q_rect)
        
        # Badge name below
        name_color = (255, 255, 255) if self.is_unlocked else (100, 100, 110)
        name_text = self.name_font.render(self.name, True, name_color)
        name_rect = name_text.get_rect(centerx=center_x, y=self.rect.bottom - 20)
        screen.blit(name_text, name_rect)


class AchievementRow:
    """Display for a single achievement row."""
    
    def __init__(self, x: int, y: int, width: int, height: int, 
                 achievement_data: tuple, is_unlocked: bool):
        self.rect = pg.Rect(x, y, width, height)
        self.achievement_id, self.name, self.description, self.color = achievement_data
        self.is_unlocked = is_unlocked
        self.hovered = False
        
        # Load fonts
        try:
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 12)
            self.desc_font = pg.font.Font("assets/fonts/Minecraft.ttf", 9)
        except:
            self.name_font = pg.font.Font(None, 16)
            self.desc_font = pg.font.Font(None, 12)
    
    def update(self, mouse_pos: tuple):
        """Update hover state."""
        self.hovered = self.rect.collidepoint(mouse_pos)
    
    def draw(self, screen: pg.Surface):
        """Draw the achievement row."""
        # Background
        if self.is_unlocked:
            bg_color = (50, 60, 45) if not self.hovered else (60, 75, 55)
        else:
            bg_color = (35, 35, 40) if not self.hovered else (45, 45, 50)
        
        pg.draw.rect(screen, bg_color, self.rect, border_radius=6)
        
        # Border
        if self.is_unlocked:
            border_color = self.color
        else:
            border_color = (55, 55, 60)
        pg.draw.rect(screen, border_color, self.rect, 2, border_radius=6)
        
        # Checkmark or lock icon
        icon_x = self.rect.x + 20
        icon_y = self.rect.centery
        
        if self.is_unlocked:
            # Green checkmark
            pg.draw.circle(screen, (80, 180, 80), (icon_x, icon_y), 10)
            # Check mark
            pg.draw.lines(screen, (255, 255, 255), False, [
                (icon_x - 5, icon_y),
                (icon_x - 1, icon_y + 4),
                (icon_x + 6, icon_y - 5)
            ], 2)
        else:
            # Grey lock
            pg.draw.circle(screen, (60, 60, 70), (icon_x, icon_y), 10)
            # Lock shape
            pg.draw.rect(screen, (80, 80, 90), (icon_x - 5, icon_y - 2, 10, 8), border_radius=2)
            pg.draw.arc(screen, (80, 80, 90), (icon_x - 4, icon_y - 8, 8, 10), 0, 3.14, 2)
        
        # Name
        name_color = (255, 255, 255) if self.is_unlocked else (120, 120, 130)
        name_text = self.name_font.render(self.name, True, name_color)
        screen.blit(name_text, (self.rect.x + 40, self.rect.y + 8))
        
        # Description
        desc_color = (180, 180, 180) if self.is_unlocked else (80, 80, 90)
        desc_text = self.desc_font.render(self.description, True, desc_color)
        screen.blit(desc_text, (self.rect.x + 40, self.rect.y + 26))


class AchievementsUI:
    """The achievements and badges interface."""
    
    def __init__(self, get_unlocked_badges: Callable[[], list[str]],
                 get_unlocked_achievements: Callable[[], list[str]]):
        """
        Initialize achievements UI.
        get_unlocked_badges: Returns list of unlocked badge IDs.
        get_unlocked_achievements: Returns list of unlocked achievement IDs.
        """
        self.overlay_show = False
        self.get_unlocked_badges = get_unlocked_badges
        self.get_unlocked_achievements = get_unlocked_achievements
        
        # UI dimensions
        self.panel_width = 750
        self.panel_height = 500
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Badges and achievements
        self.badges: list[BadgeDisplay] = []
        self.achievements: list[AchievementRow] = []
        
        # Scrolling for achievements
        self.scroll_offset = 0
        self.max_scroll = 0
        
        # Selected item for tooltip
        self.selected_badge: BadgeDisplay | None = None
        
        # Animation
        self.open_animation = 0.0
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill("Black")
        self.darken.set_alpha(200)
        
        # Load fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
            self.section_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
            self.small_font = pg.font.Font("assets/fonts/Minecraft.ttf", 11)
        except:
            self.title_font = pg.font.Font(None, 32)
            self.section_font = pg.font.Font(None, 22)
            self.small_font = pg.font.Font(None, 15)
    
    def open(self):
        """Open the achievements UI."""
        self.overlay_show = True
        self.open_animation = 0.0
        self.scroll_offset = 0
        self.selected_badge = None
        self._create_displays()
        input_manager.reset()
        Logger.info("Achievements UI opened")
    
    def close(self):
        """Close the achievements UI."""
        self.overlay_show = False
        self.badges.clear()
        self.achievements.clear()
        input_manager.reset()
    
    def _create_displays(self):
        """Create badge and achievement displays."""
        self.badges.clear()
        self.achievements.clear()
        
        unlocked_badges = set(self.get_unlocked_badges())
        unlocked_achievements = set(self.get_unlocked_achievements())
        
        # Create badge displays (left side, centered between panel edge and divider)
        badge_size = 100
        badge_spacing = 110
        # Left section width is 370 (divider at panel_x + 370)
        # Total width of 3 badges = 2 * spacing + badge_size = 320
        # Center: (370 - 320) / 2 = 25
        badge_start_x = self.panel_x + 25
        badge_start_y = self.panel_y + 120
        
        for i, badge_data in enumerate(BADGES_DATA):
            x = badge_start_x + (i % 3) * badge_spacing
            y = badge_start_y + (i // 3) * badge_spacing
            is_unlocked = badge_data[0] in unlocked_badges
            
            badge = BadgeDisplay(x, y, badge_size, badge_data, is_unlocked)
            self.badges.append(badge)
        
        # Create achievement rows (right side)
        achievement_width = 320
        achievement_height = 48
        achievement_start_x = self.panel_x + 390
        achievement_start_y = self.panel_y + 90
        achievement_spacing = 54
        
        for i, achievement_data in enumerate(ACHIEVEMENTS_DATA):
            x = achievement_start_x
            y = achievement_start_y + i * achievement_spacing
            is_unlocked = achievement_data[0] in unlocked_achievements
            
            achievement = AchievementRow(x, y, achievement_width, achievement_height,
                                        achievement_data, is_unlocked)
            self.achievements.append(achievement)
        
        # Calculate max scroll for achievements
        total_height = len(ACHIEVEMENTS_DATA) * achievement_spacing
        visible_height = self.panel_height - 120
        self.max_scroll = max(0, total_height - visible_height)
        
        # Count unlocked
        self.badges_unlocked = len(unlocked_badges & {b[0] for b in BADGES_DATA})
        self.achievements_unlocked = len(unlocked_achievements & {a[0] for a in ACHIEVEMENTS_DATA})
    
    def update(self, dt: float):
        """Update the achievements UI."""
        if not self.overlay_show:
            return
        
        # Update open animation
        self.open_animation = min(1.0, self.open_animation + dt * 6)
        
        mouse_pos = input_manager.mouse_pos
        
        # Handle close
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
            return
        
        # Close button
        close_rect = pg.Rect(self.panel_x + self.panel_width - 45, self.panel_y + 12, 32, 32)
        if close_rect.collidepoint(mouse_pos) and input_manager.mouse_pressed(1):
            self.close()
            return
        
        # Scroll achievements with arrow keys
        if input_manager.key_down(pg.K_DOWN):
            self.scroll_offset = min(self.max_scroll, self.scroll_offset + 150 * dt)
        if input_manager.key_down(pg.K_UP):
            self.scroll_offset = max(0, self.scroll_offset - 150 * dt)
        
        # Update badges
        self.selected_badge = None
        for badge in self.badges:
            badge.update(mouse_pos)
            if badge.hovered:
                self.selected_badge = badge
        
        # Update achievements with scroll
        for i, achievement in enumerate(self.achievements):
            achievement.rect.y = (self.panel_y + 90 + i * 54) - int(self.scroll_offset)
            # Only update if visible
            if self.panel_y + 70 < achievement.rect.centery < self.panel_y + self.panel_height - 30:
                achievement.update(mouse_pos)
            else:
                achievement.hovered = False
    
    def draw(self, screen: pg.Surface):
        """Draw the achievements UI."""
        if not self.overlay_show:
            return
        
        # Darken background
        alpha = int(200 * self.open_animation)
        self.darken.set_alpha(alpha)
        screen.blit(self.darken, (0, 0))
        
        # Animated panel
        scale = 0.9 + 0.1 * self.open_animation
        panel_w = int(self.panel_width * scale)
        panel_h = int(self.panel_height * scale)
        panel_x = (GameSettings.SCREEN_WIDTH - panel_w) // 2
        panel_y = (GameSettings.SCREEN_HEIGHT - panel_h) // 2
        panel_rect = pg.Rect(panel_x, panel_y, panel_w, panel_h)
        
        # Panel shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 6
        shadow_rect.y += 6
        pg.draw.rect(screen, (10, 15, 20), shadow_rect, border_radius=15)
        
        # Panel background
        pg.draw.rect(screen, (30, 35, 48), panel_rect, border_radius=12)
        
        # Inner panel
        inner_rect = panel_rect.inflate(-6, -6)
        pg.draw.rect(screen, (38, 44, 60), inner_rect, border_radius=10)
        
        # Title bar
        title_bar = pg.Rect(panel_rect.x + 3, panel_rect.y + 3, panel_rect.width - 6, 48)
        pg.draw.rect(screen, (60, 130, 90), title_bar,
                     border_top_left_radius=10, border_top_right_radius=10)
        
        # Border
        pg.draw.rect(screen, (80, 160, 110), panel_rect, 2, border_radius=12)
        
        # Title
        title_text = self.title_font.render("Achievements & Badges", True, (255, 255, 255))
        title_rect = title_text.get_rect(centerx=panel_rect.centerx, centery=panel_rect.y + 27)
        screen.blit(title_text, title_rect)
        
        # Close button
        close_rect = pg.Rect(panel_rect.right - 45, panel_rect.y + 12, 32, 32)
        mouse_pos = input_manager.mouse_pos
        close_color = (200, 80, 80) if close_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_rect, border_radius=6)
        close_x = self.small_font.render("X", True, (255, 255, 255))
        close_x_rect = close_x.get_rect(center=close_rect.center)
        screen.blit(close_x, close_x_rect)
        
        # Divider line between badges and achievements
        divider_x = self.panel_x + 370
        pg.draw.line(screen, (60, 70, 85), 
                    (divider_x, self.panel_y + 60),
                    (divider_x, self.panel_y + self.panel_height - 20), 2)
        
        # Badges section header
        badges_header = self.section_font.render(f"Badges ({self.badges_unlocked}/{len(BADGES_DATA)})", 
                                                  True, (255, 220, 100))
        screen.blit(badges_header, (self.panel_x + 30, self.panel_y + 70))
        
        # Draw badges
        for badge in self.badges:
            badge.draw(screen)
        
        # Badge tooltip
        if self.selected_badge:
            self._draw_badge_tooltip(screen, self.selected_badge)
        
        # Achievements section header
        achievements_header = self.section_font.render(
            f"Achievements ({self.achievements_unlocked}/{len(ACHIEVEMENTS_DATA)})",
            True, (100, 200, 255))
        screen.blit(achievements_header, (self.panel_x + 400, self.panel_y + 65))
        
        # Clip achievements area
        clip_rect = pg.Rect(self.panel_x + 380, self.panel_y + 85,
                           360, self.panel_height - 115)
        old_clip = screen.get_clip()
        screen.set_clip(clip_rect)
        
        # Draw achievements
        for achievement in self.achievements:
            if clip_rect.top - 50 < achievement.rect.centery < clip_rect.bottom + 50:
                achievement.draw(screen)
        
        screen.set_clip(old_clip)
        
        # Scroll indicators for achievements
        if self.scroll_offset > 0:
            pg.draw.polygon(screen, (150, 150, 180), [
                (self.panel_x + 550, self.panel_y + 88),
                (self.panel_x + 540, self.panel_y + 98),
                (self.panel_x + 560, self.panel_y + 98),
            ])
        
        if self.scroll_offset < self.max_scroll:
            bottom_y = self.panel_y + self.panel_height - 25
            pg.draw.polygon(screen, (150, 150, 180), [
                (self.panel_x + 550, bottom_y + 5),
                (self.panel_x + 540, bottom_y - 5),
                (self.panel_x + 560, bottom_y - 5),
            ])
    
    def _draw_badge_tooltip(self, screen: pg.Surface, badge: BadgeDisplay):
        """Draw tooltip for hovered badge."""
        tooltip_width = 200
        tooltip_height = 60
        tooltip_x = badge.rect.centerx - tooltip_width // 2
        tooltip_y = badge.rect.bottom + 5
        
        # Keep tooltip in bounds
        if tooltip_x < self.panel_x + 10:
            tooltip_x = self.panel_x + 10
        if tooltip_x + tooltip_width > self.panel_x + 360:
            tooltip_x = self.panel_x + 360 - tooltip_width
        
        tooltip_rect = pg.Rect(tooltip_x, tooltip_y, tooltip_width, tooltip_height)
        
        # Background
        pg.draw.rect(screen, (25, 30, 40), tooltip_rect, border_radius=8)
        pg.draw.rect(screen, badge.color if badge.is_unlocked else (70, 70, 80), 
                    tooltip_rect, 2, border_radius=8)
        
        # Description
        if badge.is_unlocked:
            desc_text = self.small_font.render(badge.description, True, (200, 255, 200))
            status_text = self.small_font.render("UNLOCKED!", True, (100, 255, 100))
        else:
            desc_text = self.small_font.render(badge.requirement, True, (180, 180, 180))
            status_text = self.small_font.render("LOCKED", True, (150, 100, 100))
        
        desc_rect = desc_text.get_rect(centerx=tooltip_rect.centerx, y=tooltip_y + 12)
        status_rect = status_text.get_rect(centerx=tooltip_rect.centerx, y=tooltip_y + 35)
        
        screen.blit(desc_text, desc_rect)
        screen.blit(status_text, status_rect)