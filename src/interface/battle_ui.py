"""
Modern Battle UI Module
Provides styled UI components for battle scenes (trainer and wild battles)
"""
import pygame as pg
import math
from src.utils import GameSettings
from src.utils.definition import Monster, Move

# Element type colors
ELEMENT_COLORS = {
    "Normal": (168, 168, 120),
    "Fire": (240, 128, 48),
    "Water": (104, 144, 240),
    "Electric": (248, 208, 48),
    "Grass": (120, 200, 80),
    "Ice": (152, 216, 216),
    "Fighting": (192, 48, 40),
    "Poison": (160, 64, 160),
    "Ground": (224, 192, 104),
    "Flying": (168, 144, 240),
    "Psychic": (248, 88, 136),
    "Bug": (168, 184, 32),
    "Rock": (184, 160, 56),
    "Ghost": (112, 88, 152),
    "Dragon": (112, 56, 248),
    "Dark": (112, 88, 72),
    "Steel": (184, 184, 208),
    "Fairy": (238, 153, 172),
}


class ModernHealthBar:
    """A stylish health bar with gradient and smooth animations."""
    
    def __init__(self, x: int, y: int, width: int = 200, height: int = 16, is_player: bool = True):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.is_player = is_player
        self.current_hp = 100
        self.max_hp = 100
        self.display_hp = 100  # For smooth animation
        self.animation_speed = 100  # HP per second
        
    def set_hp(self, current: int, maximum: int):
        self.current_hp = max(0, current)
        self.max_hp = max(1, maximum)
        
    def update(self, dt: float):
        # Smooth HP bar animation
        if self.display_hp != self.current_hp:
            diff = self.current_hp - self.display_hp
            change = self.animation_speed * dt
            if abs(diff) < change:
                self.display_hp = self.current_hp
            else:
                self.display_hp += change if diff > 0 else -change
        
    def draw(self, screen: pg.Surface):
        # Background (dark)
        bg_rect = pg.Rect(self.x - 2, self.y - 2, self.width + 4, self.height + 4)
        pg.draw.rect(screen, (20, 20, 25), bg_rect, border_radius=4)
        
        # Inner background
        inner_rect = pg.Rect(self.x, self.y, self.width, self.height)
        pg.draw.rect(screen, (40, 40, 50), inner_rect, border_radius=3)
        
        # HP fill
        hp_percentage = max(0, self.display_hp) / self.max_hp
        current_width = int(self.width * hp_percentage)
        
        if hp_percentage > 0.5:
            color = (80, 200, 80)
            color_dark = (50, 150, 50)
        elif hp_percentage > 0.25:
            color = (230, 200, 50)
            color_dark = (180, 150, 30)
        else:
            color = (220, 60, 60)
            color_dark = (170, 40, 40)
        
        if current_width > 0:
            # Main fill
            fill_rect = pg.Rect(self.x, self.y, current_width, self.height)
            pg.draw.rect(screen, color, fill_rect, border_radius=3)
            
            # Gradient effect (darker at bottom)
            gradient_rect = pg.Rect(self.x, self.y + self.height // 2, current_width, self.height // 2)
            pg.draw.rect(screen, color_dark, gradient_rect, 
                        border_bottom_left_radius=3, border_bottom_right_radius=3)
        
        # Border
        pg.draw.rect(screen, (60, 60, 70), inner_rect, 2, border_radius=3)


class PokemonInfoCard:
    """A styled card showing Pokemon info (name, level, HP, type)."""
    
    def __init__(self, x: int, y: int, width: int = 250, is_player: bool = True):
        self.x = x
        self.y = y
        self.width = width
        self.height = 90
        self.is_player = is_player
        self.health_bar = ModernHealthBar(x + 15, y + 55, width - 30, 14, is_player)
        
        # Pokemon data
        self.name = ""
        self.level = 1
        self.hp = 100
        self.max_hp = 100
        self.element = "Normal"
        
        # Fonts
        try:
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
            self.level_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
            self.hp_font = pg.font.Font("assets/fonts/Minecraft.ttf", 12)
        except:
            self.name_font = pg.font.Font(None, 22)
            self.level_font = pg.font.Font(None, 18)
            self.hp_font = pg.font.Font(None, 16)
    
    def set_pokemon(self, monster: Monster):
        if not monster:
            return
        self.name = monster.get("name", "???")
        self.level = monster.get("level", 1)
        self.hp = monster.get("hp", 0)
        self.max_hp = monster.get("max_hp", 1)
        self.element = monster.get("element", "Normal")
        self.health_bar.set_hp(self.hp, self.max_hp)
    
    def update_hp(self, hp: int, max_hp: int):
        self.hp = hp
        self.max_hp = max_hp
        self.health_bar.set_hp(hp, max_hp)
    
    def update(self, dt: float):
        self.health_bar.update(dt)
    
    def draw(self, screen: pg.Surface):
        # Card background
        card_rect = pg.Rect(self.x, self.y, self.width, self.height)
        
        # Shadow
        shadow_rect = card_rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pg.draw.rect(screen, (15, 15, 20), shadow_rect, border_radius=10)
        
        # Main card
        pg.draw.rect(screen, (45, 50, 65), card_rect, border_radius=8)
        pg.draw.rect(screen, (70, 80, 100), card_rect, 2, border_radius=8)
        
        # Type indicator bar at top
        type_color = ELEMENT_COLORS.get(self.element, (128, 128, 128))
        type_bar = pg.Rect(self.x, self.y, self.width, 6)
        pg.draw.rect(screen, type_color, type_bar, 
                    border_top_left_radius=8, border_top_right_radius=8)
        
        # Name
        name_text = self.name_font.render(self.name, True, (255, 255, 255))
        screen.blit(name_text, (self.x + 15, self.y + 12))
        
        # Level
        level_text = self.level_font.render(f"Lv.{self.level}", True, (180, 180, 190))
        screen.blit(level_text, (self.x + self.width - level_text.get_width() - 15, self.y + 14))
        
        # Type badge
        type_badge_rect = pg.Rect(self.x + 15, self.y + 34, 60, 18)
        pg.draw.rect(screen, type_color, type_badge_rect, border_radius=4)
        type_text = self.hp_font.render(self.element, True, (255, 255, 255))
        screen.blit(type_text, (type_badge_rect.centerx - type_text.get_width() // 2,
                               type_badge_rect.centery - type_text.get_height() // 2))
        
        # HP text
        hp_text = self.hp_font.render(f"{max(0, self.hp)}/{self.max_hp}", True, (200, 200, 200))
        screen.blit(hp_text, (self.x + self.width - hp_text.get_width() - 15, self.y + 36))
        
        # Health bar
        self.health_bar.draw(screen)


class ModernMoveButton:
    """A styled button for selecting moves."""
    
    def __init__(self, x: int, y: int, width: int, height: int, callback):
        self.rect = pg.Rect(x, y, width, height)
        self.move = None
        self.callback = callback
        self.hovered = False
        self.enabled = True
        
        try:
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
            self.info_font = pg.font.Font("assets/fonts/Minecraft.ttf", 11)
        except:
            self.name_font = pg.font.Font(None, 20)
            self.info_font = pg.font.Font(None, 14)
    
    def update_move(self, move: Move | None):
        self.move = move
        self.enabled = move is not None and move.get("pp", 0) > 0
    
    def update(self, dt: float):
        mouse_pos = pg.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled
    
    def handle_click(self, mouse_pos: tuple) -> bool:
        if self.rect.collidepoint(mouse_pos) and self.move and self.enabled:
            self.callback(self.move)
            return True
        return False
    
    def draw(self, screen: pg.Surface):
        if not self.move:
            # Empty slot
            pg.draw.rect(screen, (35, 40, 50), self.rect, border_radius=8)
            pg.draw.rect(screen, (50, 55, 65), self.rect, 2, border_radius=8)
            return
        
        move_type = self.move.get("type", "Normal")
        base_color = ELEMENT_COLORS.get(move_type, (168, 168, 120))
        
        if not self.enabled:
            # Disabled (no PP)
            color = (60, 60, 65)
            border_color = (80, 80, 85)
        elif self.hovered:
            # Brighten on hover
            color = tuple(min(255, c + 30) for c in base_color)
            border_color = (255, 255, 255)
        else:
            color = base_color
            border_color = tuple(min(255, c + 50) for c in base_color)
        
        # Button background
        pg.draw.rect(screen, color, self.rect, border_radius=8)
        
        # Gradient overlay (darker at bottom)
        dark_color = tuple(max(0, c - 40) for c in color)
        bottom_rect = pg.Rect(self.rect.x, self.rect.y + self.rect.height // 2,
                             self.rect.width, self.rect.height // 2)
        pg.draw.rect(screen, dark_color, bottom_rect,
                    border_bottom_left_radius=8, border_bottom_right_radius=8)
        
        # Border
        pg.draw.rect(screen, border_color, self.rect, 2, border_radius=8)
        
        # Move name
        name_text = self.name_font.render(self.move.get("name", "???"), True, (255, 255, 255))
        screen.blit(name_text, (self.rect.centerx - name_text.get_width() // 2,
                               self.rect.y + 8))
        
        # PP
        pp = self.move.get("pp", 0)
        max_pp = self.move.get("max_pp", 0)
        pp_color = (255, 255, 255) if pp > 0 else (255, 100, 100)
        pp_text = self.info_font.render(f"PP: {pp}/{max_pp}", True, pp_color)
        screen.blit(pp_text, (self.rect.centerx - pp_text.get_width() // 2,
                             self.rect.y + 28))
        
        # Power
        power = self.move.get("power", 0)
        if power > 0:
            power_text = self.info_font.render(f"PWR: {power}", True, (220, 220, 220))
            screen.blit(power_text, (self.rect.centerx - power_text.get_width() // 2,
                                    self.rect.y + 43))


class ModernActionButton:
    """A styled action button (Fight, Run, Catch, etc.)."""
    
    def __init__(self, x: int, y: int, width: int, height: int, text: str, 
                 color: tuple, callback, icon: str = None):
        self.rect = pg.Rect(x, y, width, height)
        self.text = text
        self.base_color = color
        self.callback = callback
        self.icon = icon
        self.hovered = False
        self.enabled = True
        
        try:
            self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
        except:
            self.font = pg.font.Font(None, 22)
    
    def update(self, dt: float):
        mouse_pos = pg.mouse.get_pos()
        self.hovered = self.rect.collidepoint(mouse_pos) and self.enabled
    
    def handle_click(self, mouse_pos: tuple) -> bool:
        if self.rect.collidepoint(mouse_pos) and self.enabled:
            self.callback()
            return True
        return False
    
    def draw(self, screen: pg.Surface):
        if self.hovered:
            color = tuple(min(255, c + 25) for c in self.base_color)
            border_color = (255, 255, 255)
        else:
            color = self.base_color
            border_color = tuple(min(255, c + 40) for c in self.base_color)
        
        # Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.x += 2
        shadow_rect.y += 2
        pg.draw.rect(screen, (20, 20, 25), shadow_rect, border_radius=10)
        
        # Button background
        pg.draw.rect(screen, color, self.rect, border_radius=8)
        
        # Gradient (darker bottom)
        dark_color = tuple(max(0, c - 30) for c in color)
        bottom_rect = pg.Rect(self.rect.x, self.rect.y + self.rect.height // 2,
                             self.rect.width, self.rect.height // 2)
        pg.draw.rect(screen, dark_color, bottom_rect,
                    border_bottom_left_radius=8, border_bottom_right_radius=8)
        
        # Border
        pg.draw.rect(screen, border_color, self.rect, 2, border_radius=8)
        
        # Text
        text_surface = self.font.render(self.text, True, (255, 255, 255))
        text_x = self.rect.centerx - text_surface.get_width() // 2
        text_y = self.rect.centery - text_surface.get_height() // 2
        screen.blit(text_surface, (text_x, text_y))


class MessageBox:
    """A styled message box for battle messages with text wrapping."""
    
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pg.Rect(x, y, width, height)
        self.message = ""
        self.sub_message = ""
        
        try:
            self.font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
            self.sub_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        except:
            self.font = pg.font.Font(None, 22)
            self.sub_font = pg.font.Font(None, 18)
        
        self.padding = 15
        self.max_text_width = width - (self.padding * 2)
    
    def set_message(self, message: str, sub_message: str = ""):
        self.message = message
        self.sub_message = sub_message
    
    def _wrap_text(self, text: str, font, max_width: int) -> list[str]:
        """Wrap text to fit within max_width. Returns list of lines."""
        if not text:
            return []
        
        words = text.split(' ')
        lines = []
        current_line = ""
        
        for word in words:
            # Test if adding this word exceeds max width
            test_line = current_line + (" " if current_line else "") + word
            test_width = font.size(test_line)[0]
            
            if test_width <= max_width:
                current_line = test_line
            else:
                # Current line is full, start new line
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        # Don't forget the last line
        if current_line:
            lines.append(current_line)
        
        return lines
    
    def draw(self, screen: pg.Surface):
        # Shadow
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pg.draw.rect(screen, (15, 15, 20), shadow_rect, border_radius=12)
        
        # Background
        pg.draw.rect(screen, (40, 45, 55), self.rect, border_radius=10)
        
        # Inner highlight
        inner_rect = pg.Rect(self.rect.x + 3, self.rect.y + 3, 
                            self.rect.width - 6, self.rect.height // 2 - 3)
        pg.draw.rect(screen, (50, 55, 70), inner_rect,
                    border_top_left_radius=8, border_top_right_radius=8)
        
        # Border
        pg.draw.rect(screen, (70, 80, 100), self.rect, 3, border_radius=10)
        
        # Wrap and render main message
        if self.message:
            lines = self._wrap_text(self.message, self.font, self.max_text_width)
            line_height = self.font.get_height() + 2
            
            # Calculate starting Y to center text vertically
            total_height = len(lines) * line_height
            if self.sub_message:
                total_height += self.sub_font.get_height() + 5
            
            start_y = self.rect.y + (self.rect.height - total_height) // 2
            
            for i, line in enumerate(lines):
                text_surface = self.font.render(line, True, (255, 255, 255))
                screen.blit(text_surface, (self.rect.x + self.padding, start_y + i * line_height))
            
            # Sub message below main message
            if self.sub_message:
                sub_y = start_y + len(lines) * line_height + 3
                sub_text = self.sub_font.render(self.sub_message, True, (180, 180, 190))
                screen.blit(sub_text, (self.rect.x + self.padding, sub_y))
        elif self.sub_message:
            # Only sub message
            sub_text = self.sub_font.render(self.sub_message, True, (180, 180, 190))
            y_pos = self.rect.centery - sub_text.get_height() // 2
            screen.blit(sub_text, (self.rect.x + self.padding, y_pos))


class BattleUI:
    """
    Complete modern battle UI system.
    Manages all UI elements for battle scenes.
    """
    
    def __init__(self, is_trainer_battle: bool = False):
        self.is_trainer_battle = is_trainer_battle
        
        # Screen dimensions
        self.screen_width = GameSettings.SCREEN_WIDTH
        self.screen_height = GameSettings.SCREEN_HEIGHT
        
        # Pokemon info cards
        # Enemy/Wild card (top right)
        self.enemy_card = PokemonInfoCard(
            self.screen_width - 280, 20, 260, False
        )
        
        # Player card (bottom left, above controls)
        self.player_card = PokemonInfoCard(
            20, self.screen_height - 220, 260, True
        )
        
        # Message box (top left) - taller to fit wrapped text
        self.message_box = MessageBox(20, 20, 450, 100)
        
        # Control panel dimensions - positioned on right side
        self.panel_width = 280
        self.panel_height = 170
        self.panel_x = self.screen_width - self.panel_width - 20
        self.panel_y = self.screen_height - 180
        
        # Action buttons
        btn_width = 115
        btn_height = 55
        btn_spacing = 10
        start_x = self.panel_x + 20
        start_y = self.panel_y + 20
        
        self.action_buttons = {}
        
        # Fight button (red/orange)
        self.action_buttons["fight"] = ModernActionButton(
            start_x, start_y, btn_width, btn_height,
            "FIGHT", (180, 80, 60), None
        )
        
        if is_trainer_battle:
            # Run button (gray) - for trainer battles
            self.action_buttons["run"] = ModernActionButton(
                start_x + btn_width + btn_spacing, start_y, btn_width, btn_height,
                "RUN", (100, 100, 110), None
            )
        else:
            # Catch button (blue) - for wild battles
            self.action_buttons["catch"] = ModernActionButton(
                start_x + btn_width + btn_spacing, start_y, btn_width, btn_height,
                "CATCH", (70, 130, 180), None
            )
        
        # Switch button (green)
        self.action_buttons["switch"] = ModernActionButton(
            start_x, start_y + btn_height + btn_spacing, btn_width, btn_height,
            "SWITCH", (70, 140, 70), None
        )
        
        if is_trainer_battle:
            # Items button (yellow) - for trainer battles
            self.action_buttons["items"] = ModernActionButton(
                start_x + btn_width + btn_spacing, start_y + btn_height + btn_spacing,
                btn_width, btn_height,
                "ITEMS", (180, 160, 60), None
            )
        else:
            # Run button (gray) - for wild battles
            self.action_buttons["run"] = ModernActionButton(
                start_x + btn_width + btn_spacing, start_y + btn_height + btn_spacing,
                btn_width, btn_height,
                "RUN", (100, 100, 110), None
            )
        
        # Move buttons (2x2 grid) - sized to fit panel
        self.move_buttons = []
        move_width = 115
        move_height = 55
        move_spacing = 8
        move_start_x = self.panel_x + 20
        move_start_y = self.panel_y + 15
        
        for i in range(4):
            row = i // 2
            col = i % 2
            x = move_start_x + col * (move_width + move_spacing)
            y = move_start_y + row * (move_height + move_spacing)
            self.move_buttons.append(ModernMoveButton(x, y, move_width, move_height, None))
        
        # Back button for move selection - positioned below moves
        self.back_button = ModernActionButton(
            self.panel_x + self.panel_width // 2 - 50,
            self.panel_y + self.panel_height - 45,
            100, 35,
            "BACK", (80, 80, 90), None
        )
        
        # State
        self.show_moves = False
        
        # Fonts for victory/defeat screens
        try:
            self.big_font = pg.font.Font("assets/fonts/Pokemon Solid.ttf", 48)
            self.medium_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
        except:
            self.big_font = pg.font.Font(None, 52)
            self.medium_font = pg.font.Font(None, 28)
    
    def set_callbacks(self, fight_cb, run_cb, switch_cb, items_cb=None, catch_cb=None, 
                      back_cb=None, move_cb=None):
        """Set button callbacks."""
        self.action_buttons["fight"].callback = fight_cb
        self.action_buttons["run"].callback = run_cb
        self.action_buttons["switch"].callback = switch_cb
        
        if self.is_trainer_battle and items_cb:
            self.action_buttons["items"].callback = items_cb
        elif not self.is_trainer_battle and catch_cb:
            self.action_buttons["catch"].callback = catch_cb
        
        if back_cb:
            self.back_button.callback = back_cb
        
        if move_cb:
            for btn in self.move_buttons:
                btn.callback = move_cb
    
    def set_player_pokemon(self, monster: Monster):
        """Update player Pokemon info."""
        self.player_card.set_pokemon(monster)
    
    def set_enemy_pokemon(self, monster: Monster):
        """Update enemy/wild Pokemon info."""
        self.enemy_card.set_pokemon(monster)
    
    def update_player_hp(self, hp: int, max_hp: int):
        """Update player Pokemon HP."""
        self.player_card.update_hp(hp, max_hp)
    
    def update_enemy_hp(self, hp: int, max_hp: int):
        """Update enemy Pokemon HP."""
        self.enemy_card.update_hp(hp, max_hp)
    
    def set_message(self, message: str, sub_message: str = ""):
        """Set the battle message."""
        self.message_box.set_message(message, sub_message)
    
    def setup_moves(self, moves: list[Move]):
        """Setup move buttons with Pokemon moves."""
        for i, btn in enumerate(self.move_buttons):
            if i < len(moves):
                btn.update_move(moves[i])
            else:
                btn.update_move(None)
    
    def update(self, dt: float):
        """Update UI elements."""
        self.player_card.update(dt)
        self.enemy_card.update(dt)
        
        if self.show_moves:
            for btn in self.move_buttons:
                btn.update(dt)
            self.back_button.update(dt)
        else:
            for btn in self.action_buttons.values():
                btn.update(dt)
    
    def handle_click(self, mouse_pos: tuple) -> bool:
        """Handle mouse click. Returns True if a button was clicked."""
        if self.show_moves:
            for btn in self.move_buttons:
                if btn.handle_click(mouse_pos):
                    return True
            if self.back_button.handle_click(mouse_pos):
                return True
        else:
            for btn in self.action_buttons.values():
                if btn.handle_click(mouse_pos):
                    return True
        return False
    
    def draw(self, screen: pg.Surface):
        """Draw all UI elements."""
        # Draw Pokemon info cards
        self.enemy_card.draw(screen)
        self.player_card.draw(screen)
        
        # Draw message box
        self.message_box.draw(screen)
        
        # Draw control panel background
        panel_rect = pg.Rect(self.panel_x, self.panel_y, self.panel_width, self.panel_height)
        
        # Panel shadow
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 4
        shadow_rect.y += 4
        pg.draw.rect(screen, (15, 15, 20), shadow_rect, border_radius=15)
        
        # Panel background
        pg.draw.rect(screen, (35, 40, 50), panel_rect, border_radius=12)
        pg.draw.rect(screen, (60, 70, 85), panel_rect, 3, border_radius=12)
        
        # Draw buttons
        if self.show_moves:
            for btn in self.move_buttons:
                btn.draw(screen)
            self.back_button.draw(screen)
        else:
            for btn in self.action_buttons.values():
                btn.draw(screen)
    
    def draw_victory_screen(self, screen: pg.Surface, message: str, 
                           xp_gained: int = 0, leveled_up: bool = False,
                           coins_gained: int = 0):
        """Draw victory overlay."""
        # Dark overlay
        overlay = pg.Surface((self.screen_width, self.screen_height), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Victory panel
        panel_width = 450
        panel_height = 250
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = (self.screen_height - panel_height) // 2
        
        panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)
        pg.draw.rect(screen, (40, 50, 40), panel_rect, border_radius=15)
        pg.draw.rect(screen, (100, 180, 100), panel_rect, 4, border_radius=15)
        
        # Victory text
        victory_text = self.big_font.render("VICTORY!", True, (100, 255, 100))
        screen.blit(victory_text, (self.screen_width // 2 - victory_text.get_width() // 2,
                                   panel_y + 30))
        
        # Message
        msg_text = self.medium_font.render(message, True, (255, 255, 255))
        screen.blit(msg_text, (self.screen_width // 2 - msg_text.get_width() // 2,
                              panel_y + 100))
        
        # XP gained
        if xp_gained > 0:
            xp_text = self.medium_font.render(f"+{xp_gained} XP", True, (255, 220, 100))
            screen.blit(xp_text, (self.screen_width // 2 - xp_text.get_width() // 2,
                                 panel_y + 140))
        
        # Level up
        if leveled_up:
            level_text = self.medium_font.render("LEVEL UP!", True, (255, 200, 50))
            screen.blit(level_text, (self.screen_width // 2 - level_text.get_width() // 2,
                                    panel_y + 175))
        
        # Coins gained
        if coins_gained > 0:
            coin_text = self.medium_font.render(f"+{coins_gained} Coins", True, (255, 215, 0))
            screen.blit(coin_text, (self.screen_width // 2 - coin_text.get_width() // 2,
                                   panel_y + 210))
    
    def draw_defeat_screen(self, screen: pg.Surface, message: str):
        """Draw defeat overlay."""
        # Dark overlay
        overlay = pg.Surface((self.screen_width, self.screen_height), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Defeat panel
        panel_width = 450
        panel_height = 200
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = (self.screen_height - panel_height) // 2
        
        panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)
        pg.draw.rect(screen, (50, 40, 40), panel_rect, border_radius=15)
        pg.draw.rect(screen, (180, 100, 100), panel_rect, 4, border_radius=15)
        
        # Defeat text
        defeat_text = self.big_font.render("DEFEATED", True, (255, 100, 100))
        screen.blit(defeat_text, (self.screen_width // 2 - defeat_text.get_width() // 2,
                                  panel_y + 40))
        
        # Message
        msg_text = self.medium_font.render(message, True, (255, 255, 255))
        screen.blit(msg_text, (self.screen_width // 2 - msg_text.get_width() // 2,
                              panel_y + 120))
    
    def draw_catch_result(self, screen: pg.Surface, success: bool, pokemon_name: str):
        """Draw catch result overlay."""
        # Dark overlay
        overlay = pg.Surface((self.screen_width, self.screen_height), pg.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Result panel
        panel_width = 450
        panel_height = 180
        panel_x = (self.screen_width - panel_width) // 2
        panel_y = (self.screen_height - panel_height) // 2
        
        if success:
            panel_color = (40, 50, 60)
            border_color = (100, 180, 255)
            title = "GOTCHA!"
            title_color = (100, 200, 255)
            message = f"{pokemon_name} was caught!"
        else:
            panel_color = (50, 45, 40)
            border_color = (180, 150, 100)
            title = "OH NO!"
            title_color = (255, 180, 100)
            message = f"{pokemon_name} broke free!"
        
        panel_rect = pg.Rect(panel_x, panel_y, panel_width, panel_height)
        pg.draw.rect(screen, panel_color, panel_rect, border_radius=15)
        pg.draw.rect(screen, border_color, panel_rect, 4, border_radius=15)
        
        # Title
        title_text = self.big_font.render(title, True, title_color)
        screen.blit(title_text, (self.screen_width // 2 - title_text.get_width() // 2,
                                 panel_y + 35))
        
        # Message
        msg_text = self.medium_font.render(message, True, (255, 255, 255))
        screen.blit(msg_text, (self.screen_width // 2 - msg_text.get_width() // 2,
                              panel_y + 110))