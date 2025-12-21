import pygame as pg
from src.utils import GameSettings


class QuestUI:
    """Displays the current quest at the top of the screen."""
    
    def __init__(self):
        self.quest_text = ""
        self.alpha = 255
        self.is_visible = True
        
        # Font
        try:
            self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 20)
        except:
            self.font = pg.font.Font(None, 24)
        
        # Position
        self.x = GameSettings.SCREEN_WIDTH // 2
        self.y = 30
        
        # Box padding
        self.padding_x = 20
        self.padding_y = 10
        
        # Notification System
        self.notification_text = ""
        self.notification_timer = 0.0
        self.notification_alpha = 0
    
    def set_quest(self, text: str, alpha: int = 255):
        """Set the current quest text and alpha."""
        self.quest_text = text
        self.alpha = alpha
        self.is_visible = alpha > 0 and text != ""
    
    def hide(self):
        """Hide the quest UI."""
        self.is_visible = False
        self.alpha = 0

    def show_notification(self, text: str, duration: float = 3.0):
        """Show a temporary notification."""
        self.notification_text = text
        self.notification_timer = duration
        self.notification_alpha = 255
        
    def update(self, dt: float):
        """Update notification timer."""
        if self.notification_timer > 0:
            self.notification_timer -= dt
            if self.notification_timer <= 0:
                self.notification_timer = 0
            
            # Fade out in last second
            if self.notification_timer < 1.0:
                self.notification_alpha = int(255 * self.notification_timer)
            else:
                self.notification_alpha = 255
        else:
            self.notification_alpha = 0
    
    def draw(self, screen: pg.Surface):
        """Draw the quest UI."""
        if not self.is_visible or not self.quest_text or self.alpha <= 0:
            return
        
        # Render text
        text_surface = self.font.render(self.quest_text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.x, self.y))
        
        # Background box
        bg_rect = text_rect.inflate(self.padding_x * 2, self.padding_y * 2)
        
        # Create surfaces with alpha
        bg_surface = pg.Surface((bg_rect.width, bg_rect.height), pg.SRCALPHA)
        bg_color = (0, 0, 0, int(180 * (self.alpha / 255)))
        border_color = (100, 100, 200, int(self.alpha))
        
        # Draw background
        pg.draw.rect(bg_surface, bg_color, (0, 0, bg_rect.width, bg_rect.height), border_radius=10)
        pg.draw.rect(bg_surface, border_color, (0, 0, bg_rect.width, bg_rect.height), 2, border_radius=10)
        
        screen.blit(bg_surface, bg_rect.topleft)
        
        # Draw text with alpha
        text_surface.set_alpha(self.alpha)
        screen.blit(text_surface, text_rect)
        
        # Draw Notification (below quest)
        if self.notification_timer > 0 and self.notification_text:
            n_font = self.font
            n_text = n_font.render(self.notification_text, True, (255, 255, 100))
            n_rect = n_text.get_rect(center=(self.x, self.y + 60))
            
            # Bg
            n_bg_rect = n_rect.inflate(20, 10)
            n_bg_surf = pg.Surface((n_bg_rect.width, n_bg_rect.height), pg.SRCALPHA)
            n_bg_surf.fill((0, 0, 0, int(150 * (self.notification_alpha / 255))))
            pg.draw.rect(n_bg_surf, (200, 200, 100, self.notification_alpha), (0, 0, n_bg_rect.width, n_bg_rect.height), 2, border_radius=8)
            
            screen.blit(n_bg_surf, n_bg_rect)
            
            n_text.set_alpha(self.notification_alpha)
            screen.blit(n_text, n_rect)