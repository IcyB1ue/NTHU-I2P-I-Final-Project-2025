"""
Modern Battle Items UI
Allows players to use items during battle (potions, stat boosts, etc.)
"""
import pygame as pg
from src.utils import GameSettings
from src.core.services import input_manager


class BattleItemsUI:
    """Modern UI for using items during battle."""
    
    def __init__(self, on_item_used=None):
        self.overlay_show = False
        self.on_item_used = on_item_used
        
        # Panel dimensions - taller to fit 4 items
        self.panel_width = 400
        self.panel_height = 400
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2
        
        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill((0, 0, 0))
        self.darken.set_alpha(180)
        
        # Fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 24)
            self.item_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
            self.desc_font = pg.font.Font("assets/fonts/Minecraft.ttf", 12)
        except:
            self.title_font = pg.font.Font(None, 28)
            self.item_font = pg.font.Font(None, 20)
            self.desc_font = pg.font.Font(None, 16)
        
        # Items data
        self.bag = None
        self.target_monster = None
        self.usable_items = []
        
        # Scrolling - only scroll when 5+ items
        self.scroll_offset = 0
        self.max_visible_items = 4
        self.item_height = 75
        
        # Message
        self.message = ""
        self.message_timer = 0.0
    
    def open(self, bag, target_monster):
        """Open the items UI."""
        self.overlay_show = True
        self.bag = bag
        self.target_monster = target_monster
        self.scroll_offset = 0
        self.message = ""
        self._load_usable_items()
    
    def close(self):
        """Close the items UI."""
        self.overlay_show = False
        self.bag = None
        self.target_monster = None
        self.usable_items = []
    
    def _load_usable_items(self):
        """Load items that can be used in battle."""
        self.usable_items = []
        
        if not self.bag:
            return
        
        # Define battle-usable items with their effects
        battle_items = {
            "Potion": {"type": "heal", "value": 50, "desc": "Restores 50 HP", "color": (255, 100, 150)},
            "Super Potion": {"type": "heal", "value": 100, "desc": "Restores 100 HP", "color": (255, 150, 100)},
            "Hyper Potion": {"type": "heal", "value": 200, "desc": "Restores 200 HP", "color": (255, 200, 100)},
            "Max Potion": {"type": "heal", "value": 9999, "desc": "Fully restores HP", "color": (255, 255, 100)},
            "Full Restore": {"type": "heal", "value": 9999, "desc": "Fully restores HP", "color": (100, 255, 200)},
            "Strength Potion": {"type": "attack_boost", "value": 10, "desc": "+10 Attack in battle", "color": (255, 100, 100)},
            "Defense Potion": {"type": "defense_boost", "value": 10, "desc": "+10 Defense in battle", "color": (100, 150, 255)},
        }
        
        # Check bag for usable items
        for item_name, item_info in battle_items.items():
            count = self.bag.get_item_count(item_name)
            if count > 0:
                self.usable_items.append({
                    "name": item_name,
                    "count": count,
                    "type": item_info["type"],
                    "value": item_info["value"],
                    "desc": item_info["desc"],
                    "color": item_info["color"],
                })
    
    def _use_item(self, item: dict):
        """Use an item on the target monster."""
        if not self.target_monster or not self.bag:
            return
        
        item_name = item["name"]
        item_type = item["type"]
        value = item["value"]
        
        # Handle different item types
        if item_type == "heal":
            current_hp = self.target_monster.get("hp", 0)
            max_hp = self.target_monster.get("max_hp", 100)
            
            if current_hp >= max_hp:
                self.message = f"{self.target_monster.get('name', 'Pokemon')} is already at full HP!"
                self.message_timer = 1.5
                return
            
            if not self.bag.remove_item(item_name):
                self.message = f"No {item_name} left!"
                self.message_timer = 1.5
                return
            
            actual_heal = min(value, max_hp - current_hp)
            self.target_monster["hp"] = min(current_hp + value, max_hp)
            
            if self.on_item_used:
                self.on_item_used(item_name, {"type": "heal", "value": actual_heal})
            
            self.close()
        
        elif item_type == "attack_boost":
            if not self.bag.remove_item(item_name):
                self.message = f"No {item_name} left!"
                self.message_timer = 1.5
                return
            
            current_attack = self.target_monster.get("attack", 10)
            self.target_monster["attack"] = current_attack + value
            
            if self.on_item_used:
                self.on_item_used(item_name, {"type": "attack_boost", "value": value})
            
            self.close()
        
        elif item_type == "defense_boost":
            if not self.bag.remove_item(item_name):
                self.message = f"No {item_name} left!"
                self.message_timer = 1.5
                return
            
            current_defense = self.target_monster.get("defense", 10)
            self.target_monster["defense"] = current_defense + value
            
            if self.on_item_used:
                self.on_item_used(item_name, {"type": "defense_boost", "value": value})
            
            self.close()
    
    def _calculate_panel_geometry(self):
        """Calculate dynamic panel height and position based on item count."""
        num_items = len(self.usable_items)
        if num_items == 0:
            visible_items_count = 1  # Space for "no items" message
        else:
            visible_items_count = min(num_items, self.max_visible_items)
        
        # Dynamic height: title (60) + items + message area (50)
        dynamic_height = 60 + visible_items_count * self.item_height + 50
        panel_height = max(200, dynamic_height)  # Minimum height
        panel_y = (GameSettings.SCREEN_HEIGHT - panel_height) // 2
        
        return panel_height, panel_y
    
    def update(self, dt: float):
        """Update the UI."""
        if not self.overlay_show:
            return
        
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""
        
        mouse_pos = pg.mouse.get_pos()
        
        # Calculate dynamic panel position (same as in draw)
        panel_height, panel_y = self._calculate_panel_geometry()
        
        # Only allow scrolling when more than 4 items
        if len(self.usable_items) > self.max_visible_items:
            keys = pg.key.get_pressed()
            if keys[pg.K_UP] and self.scroll_offset > 0:
                self.scroll_offset -= 1
            max_scroll = len(self.usable_items) - self.max_visible_items
            if keys[pg.K_DOWN] and self.scroll_offset < max_scroll:
                self.scroll_offset += 1
        
        # Handle clicks
        if input_manager.mouse_pressed(1):
            close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, panel_y + 10, 30, 30)
            if close_btn_rect.collidepoint(mouse_pos):
                self.close()
                return
            
            items_start_y = panel_y + 60
            visible_count = min(len(self.usable_items), self.max_visible_items)
            for i, item in enumerate(self.usable_items[self.scroll_offset:self.scroll_offset + visible_count]):
                item_rect = pg.Rect(
                    self.panel_x + 20,
                    items_start_y + i * self.item_height,
                    self.panel_width - 40,
                    self.item_height - 5
                )
                if item_rect.collidepoint(mouse_pos):
                    self._use_item(item)
                    return
            
            # Scroll arrows (only when 5+ items)
            if len(self.usable_items) > self.max_visible_items:
                up_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15, items_start_y - 20, 30, 18)
                down_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15, 
                                   items_start_y + self.max_visible_items * self.item_height, 30, 18)
                
                if up_btn.collidepoint(mouse_pos) and self.scroll_offset > 0:
                    self.scroll_offset -= 1
                max_scroll = len(self.usable_items) - self.max_visible_items
                if down_btn.collidepoint(mouse_pos) and self.scroll_offset < max_scroll:
                    self.scroll_offset += 1
        
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
    
    def draw(self, screen: pg.Surface):
        """Draw the UI."""
        if not self.overlay_show:
            return
        
        mouse_pos = pg.mouse.get_pos()
        
        screen.blit(self.darken, (0, 0))
        
        # Calculate dynamic panel height and position
        panel_height, panel_y = self._calculate_panel_geometry()
        
        panel_rect = pg.Rect(self.panel_x, panel_y, self.panel_width, panel_height)
        
        shadow_rect = panel_rect.copy()
        shadow_rect.x += 5
        shadow_rect.y += 5
        pg.draw.rect(screen, (20, 20, 30), shadow_rect, border_radius=15)
        
        pg.draw.rect(screen, (40, 45, 60), panel_rect, border_radius=12)
        pg.draw.rect(screen, (80, 90, 110), panel_rect, 3, border_radius=12)
        
        title_bar = pg.Rect(self.panel_x, panel_y, self.panel_width, 50)
        pg.draw.rect(screen, (60, 70, 90), title_bar,
                     border_top_left_radius=12, border_top_right_radius=12)
        
        title_text = self.title_font.render("ITEMS", True, (255, 255, 255))
        screen.blit(title_text, (self.panel_x + 20, panel_y + 12))
        
        close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, panel_y + 10, 30, 30)
        close_color = (200, 80, 80) if close_btn_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_btn_rect, border_radius=5)
        x_text = self.item_font.render("X", True, (255, 255, 255))
        screen.blit(x_text, (close_btn_rect.centerx - x_text.get_width() // 2,
                            close_btn_rect.centery - x_text.get_height() // 2))
        
        items_start_y = panel_y + 60
        
        if not self.usable_items:
            no_items_text = self.item_font.render("No usable items!", True, (150, 150, 160))
            screen.blit(no_items_text, (self.panel_x + self.panel_width // 2 - no_items_text.get_width() // 2,
                                        items_start_y + 30))
        else:
            # Scroll up indicator (only when 5+ items and scrolled down)
            if len(self.usable_items) > self.max_visible_items and self.scroll_offset > 0:
                up_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15, items_start_y - 20, 30, 18)
                pg.draw.rect(screen, (70, 80, 100), up_btn, border_radius=3)
                arrow_text = self.desc_font.render("▲", True, (200, 200, 200))
                screen.blit(arrow_text, (up_btn.centerx - arrow_text.get_width() // 2,
                                        up_btn.centery - arrow_text.get_height() // 2))
            
            visible_items = self.usable_items[self.scroll_offset:self.scroll_offset + self.max_visible_items]
            
            for i, item in enumerate(visible_items):
                item_rect = pg.Rect(
                    self.panel_x + 20,
                    items_start_y + i * self.item_height,
                    self.panel_width - 40,
                    self.item_height - 5
                )
                
                is_hovered = item_rect.collidepoint(mouse_pos)
                card_color = (55, 60, 75) if is_hovered else (50, 55, 70)
                pg.draw.rect(screen, card_color, item_rect, border_radius=8)
                pg.draw.rect(screen, (70, 80, 100), item_rect, 2, border_radius=8)
                
                icon_rect = pg.Rect(item_rect.x + 10, item_rect.y + 12, 45, 45)
                item_type = item.get("type", "heal")
                
                if item_type == "heal":
                    pg.draw.rect(screen, (80, 150, 80), icon_rect, border_radius=8)
                    pg.draw.rect(screen, (100, 180, 100), icon_rect, 2, border_radius=8)
                elif item_type == "attack_boost":
                    pg.draw.rect(screen, (150, 80, 80), icon_rect, border_radius=8)
                    pg.draw.rect(screen, (180, 100, 100), icon_rect, 2, border_radius=8)
                elif item_type == "defense_boost":
                    pg.draw.rect(screen, (80, 100, 150), icon_rect, border_radius=8)
                    pg.draw.rect(screen, (100, 130, 180), icon_rect, 2, border_radius=8)
                
                potion_color = item.get("color", (255, 100, 150))
                pg.draw.ellipse(screen, potion_color, 
                               (icon_rect.x + 12, icon_rect.y + 8, 21, 30))
                pg.draw.rect(screen, (200, 200, 200),
                            (icon_rect.x + 15, icon_rect.y + 5, 15, 8))
                
                name_text = self.item_font.render(item["name"], True, (255, 255, 255))
                screen.blit(name_text, (item_rect.x + 65, item_rect.y + 12))
                
                count_text = self.desc_font.render(f"x{item['count']}", True, (180, 180, 180))
                screen.blit(count_text, (item_rect.x + 65, item_rect.y + 38))
                
                if item_type == "heal":
                    desc_color = (150, 200, 150)
                elif item_type == "attack_boost":
                    desc_color = (255, 180, 150)
                elif item_type == "defense_boost":
                    desc_color = (150, 180, 255)
                else:
                    desc_color = (180, 180, 180)
                    
                desc_text = self.desc_font.render(item["desc"], True, desc_color)
                screen.blit(desc_text, (item_rect.x + 120, item_rect.y + 38))
                
                use_btn_rect = pg.Rect(item_rect.right - 70, item_rect.y + 18, 55, 34)
                use_hovered = use_btn_rect.collidepoint(mouse_pos)
                use_color = (80, 140, 80) if use_hovered else (60, 110, 60)
                pg.draw.rect(screen, use_color, use_btn_rect, border_radius=5)
                pg.draw.rect(screen, (100, 160, 100), use_btn_rect, 2, border_radius=5)
                
                use_text = self.desc_font.render("USE", True, (255, 255, 255))
                screen.blit(use_text, (use_btn_rect.centerx - use_text.get_width() // 2,
                                       use_btn_rect.centery - use_text.get_height() // 2))
            
            # Scroll down indicator (only when 5+ items and can scroll more)
            if len(self.usable_items) > self.max_visible_items:
                max_scroll = len(self.usable_items) - self.max_visible_items
                if self.scroll_offset < max_scroll:
                    down_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15, 
                                       items_start_y + self.max_visible_items * self.item_height, 30, 18)
                    pg.draw.rect(screen, (70, 80, 100), down_btn, border_radius=3)
                    arrow_text = self.desc_font.render("▼", True, (200, 200, 200))
                    screen.blit(arrow_text, (down_btn.centerx - arrow_text.get_width() // 2,
                                            down_btn.centery - arrow_text.get_height() // 2))
        
        # Message at bottom of panel
        if self.message:
            msg_rect = pg.Rect(self.panel_x + 20, panel_y + panel_height - 45,
                              self.panel_width - 40, 30)
            pg.draw.rect(screen, (60, 50, 50), msg_rect, border_radius=5)
            pg.draw.rect(screen, (120, 100, 100), msg_rect, 2, border_radius=5)
            
            msg_text = self.desc_font.render(self.message, True, (255, 200, 200))
            screen.blit(msg_text, (msg_rect.centerx - msg_text.get_width() // 2,
                                  msg_rect.centery - msg_text.get_height() // 2))