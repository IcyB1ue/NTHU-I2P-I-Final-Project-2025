"""
Modern Shop UI for P'Anan's Shop and other shops
"""
import pygame as pg
from src.utils import GameSettings
from src.core.services import input_manager


class ShopUI:
    """Modern UI for shopping."""
    
    def __init__(self):
        self.overlay_show = False
        self.shop = None
        self.bag = None
        
        # Panel dimensions
        self.panel_width = 500
        self.panel_height = 450
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
            self.price_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
        except:
            self.title_font = pg.font.Font(None, 28)
            self.item_font = pg.font.Font(None, 20)
            self.desc_font = pg.font.Font(None, 16)
            self.price_font = pg.font.Font(None, 18)
        
        # Scrolling
        self.scroll_offset = 0
        self.max_visible_items = 5
        self.item_height = 65
        
        # Message
        self.message = ""
        self.message_timer = 0.0
        self.message_success = True
    
    def open(self, shop, bag):
        """Open the shop UI."""
        self.overlay_show = True
        self.shop = shop
        self.bag = bag
        self.scroll_offset = 0
        self.message = ""
    
    def close(self):
        """Close the shop UI."""
        self.overlay_show = False
        self.shop = None
        self.bag = None
    
    def _get_coins(self) -> int:
        """Get current coin count from bag."""
        if not self.bag:
            return 0
        return self.bag.get_item_count("Coins")
    
    def _get_item_attr(self, item, attr, default=None):
        """Safely get attribute from item (works with both dict and object)."""
        if isinstance(item, dict):
            return item.get(attr, default)
        return getattr(item, attr, default)
    
    def _buy_item(self, item):
        """Buy an item from the shop."""
        if not self.bag:
            return
        
        item_name = self._get_item_attr(item, "name", "Unknown")
        price = self._get_item_attr(item, "price", 0)
        sprite_path = self._get_item_attr(item, "sprite_path", "")
        
        # Check if player has enough coins
        coins = self._get_coins()
        if coins < price:
            self.message = "Not enough coins!"
            self.message_success = False
            self.message_timer = 2.0
            return
        
        # Check stock (None means infinite)
        stock = self._get_item_attr(item, "stock", None)
        if stock is not None and stock <= 0:
            self.message = "Out of stock!"
            self.message_success = False
            self.message_timer = 2.0
            return
        
        # Remove coins
        self.bag.remove_item("Coins", price)
        
        # Add item to bag
        self.bag.add_item(item_name, 1, sprite_path)
        
        # Decrease stock if limited
        if stock is not None:
            if isinstance(item, dict):
                item["stock"] = stock - 1
            else:
                item.stock = stock - 1
        
        self.message = f"Bought {item_name}!"
        self.message_success = True
        self.message_timer = 1.5
    
    def update(self, dt: float):
        """Update the UI."""
        if not self.overlay_show:
            return
        
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = ""
        
        mouse_pos = pg.mouse.get_pos()
        
        # Handle scroll with keys
        keys = pg.key.get_pressed()
        if keys[pg.K_UP] and self.scroll_offset > 0:
            self.scroll_offset -= 1
        
        inventory = self.shop.inventory if self.shop else []
        max_scroll = max(0, len(inventory) - self.max_visible_items)
        if keys[pg.K_DOWN] and self.scroll_offset < max_scroll:
            self.scroll_offset += 1
        
        # Handle clicks
        if input_manager.mouse_pressed(1):
            # Close button
            close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
            if close_btn_rect.collidepoint(mouse_pos):
                self.close()
                return
            
            # Buy buttons
            items_start_y = self.panel_y + 100
            visible_items = inventory[self.scroll_offset:self.scroll_offset + self.max_visible_items]
            
            for i, item in enumerate(visible_items):
                buy_btn_rect = pg.Rect(
                    self.panel_x + self.panel_width - 90,
                    items_start_y + i * self.item_height + 15,
                    60, 32
                )
                if buy_btn_rect.collidepoint(mouse_pos):
                    self._buy_item(item)
                    return
            
            # Scroll arrows
            if len(inventory) > self.max_visible_items:
                up_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15, items_start_y - 18, 30, 16)
                down_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15,
                                   items_start_y + self.max_visible_items * self.item_height, 30, 16)
                
                if up_btn.collidepoint(mouse_pos) and self.scroll_offset > 0:
                    self.scroll_offset -= 1
                if down_btn.collidepoint(mouse_pos) and self.scroll_offset < max_scroll:
                    self.scroll_offset += 1
        
        # Handle escape
        if input_manager.key_pressed(pg.K_ESCAPE):
            self.close()
    
    def draw(self, screen: pg.Surface):
        """Draw the UI."""
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
        pg.draw.rect(screen, (80, 90, 110), panel_rect, 3, border_radius=12)
        
        # Title bar
        title_bar = pg.Rect(self.panel_x, self.panel_y, self.panel_width, 50)
        pg.draw.rect(screen, (60, 70, 90), title_bar,
                     border_top_left_radius=12, border_top_right_radius=12)
        
        # Shop name
        shop_name = self.shop.name if self.shop else "Shop"
        title_text = self.title_font.render(shop_name, True, (255, 255, 255))
        screen.blit(title_text, (self.panel_x + 20, self.panel_y + 12))
        
        # Close button
        close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
        close_color = (200, 80, 80) if close_btn_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_btn_rect, border_radius=5)
        x_text = self.item_font.render("X", True, (255, 255, 255))
        screen.blit(x_text, (close_btn_rect.centerx - x_text.get_width() // 2,
                            close_btn_rect.centery - x_text.get_height() // 2))
        
        # Coin display
        coins = self._get_coins()
        coin_bar = pg.Rect(self.panel_x + 20, self.panel_y + 60, 150, 30)
        pg.draw.rect(screen, (50, 55, 70), coin_bar, border_radius=6)
        pg.draw.rect(screen, (70, 80, 100), coin_bar, 2, border_radius=6)
        
        # Coin icon (yellow circle)
        pg.draw.circle(screen, (255, 215, 0), (coin_bar.x + 18, coin_bar.centery), 10)
        pg.draw.circle(screen, (200, 170, 0), (coin_bar.x + 18, coin_bar.centery), 10, 2)
        
        # Coin count
        coin_text = self.price_font.render(f"{coins} Coins", True, (255, 215, 0))
        screen.blit(coin_text, (coin_bar.x + 35, coin_bar.centery - coin_text.get_height() // 2))
        
        # Items list header
        header_y = self.panel_y + 60
        header_text = self.desc_font.render("Available Items", True, (150, 150, 160))
        screen.blit(header_text, (self.panel_x + 190, header_y + 8))
        
        # Items list
        items_start_y = self.panel_y + 100
        inventory = self.shop.inventory if self.shop else []
        
        if not inventory:
            no_items_text = self.item_font.render("No items available!", True, (150, 150, 160))
            screen.blit(no_items_text, (self.panel_x + self.panel_width // 2 - no_items_text.get_width() // 2,
                                        items_start_y + 80))
        else:
            # Scroll up indicator
            if len(inventory) > self.max_visible_items and self.scroll_offset > 0:
                up_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15, items_start_y - 18, 30, 16)
                pg.draw.rect(screen, (70, 80, 100), up_btn, border_radius=3)
                arrow_text = self.desc_font.render("▲", True, (200, 200, 200))
                screen.blit(arrow_text, (up_btn.centerx - arrow_text.get_width() // 2,
                                        up_btn.centery - arrow_text.get_height() // 2))
            
            # Draw items
            visible_items = inventory[self.scroll_offset:self.scroll_offset + self.max_visible_items]
            
            for i, item in enumerate(visible_items):
                item_rect = pg.Rect(
                    self.panel_x + 20,
                    items_start_y + i * self.item_height,
                    self.panel_width - 40,
                    self.item_height - 5
                )
                
                # Item card background
                is_hovered = item_rect.collidepoint(mouse_pos)
                card_color = (55, 60, 75) if is_hovered else (50, 55, 70)
                pg.draw.rect(screen, card_color, item_rect, border_radius=8)
                pg.draw.rect(screen, (70, 80, 100), item_rect, 2, border_radius=8)
                
                # Item icon
                icon_rect = pg.Rect(item_rect.x + 10, item_rect.y + 8, 45, 45)
                
                # Determine icon color based on item type
                item_name = self._get_item_attr(item, "name", "")
                if "Potion" in item_name:
                    if "Strength" in item_name:
                        icon_bg = (150, 80, 80)
                        potion_color = (255, 100, 100)
                    elif "Defense" in item_name:
                        icon_bg = (80, 100, 150)
                        potion_color = (100, 150, 255)
                    elif "Super" in item_name:
                        icon_bg = (100, 140, 80)
                        potion_color = (255, 150, 100)
                    else:
                        icon_bg = (80, 150, 80)
                        potion_color = (255, 100, 150)
                    
                    pg.draw.rect(screen, icon_bg, icon_rect, border_radius=8)
                    pg.draw.rect(screen, (icon_bg[0]+30, icon_bg[1]+30, icon_bg[2]+30), icon_rect, 2, border_radius=8)
                    
                    # Potion shape
                    pg.draw.ellipse(screen, potion_color, 
                                   (icon_rect.x + 12, icon_rect.y + 8, 21, 30))
                    pg.draw.rect(screen, (200, 200, 200),
                                (icon_rect.x + 15, icon_rect.y + 5, 15, 8))
                
                elif "Pokeball" in item_name or "Ball" in item_name:
                    pg.draw.rect(screen, (150, 80, 80), icon_rect, border_radius=8)
                    pg.draw.rect(screen, (180, 100, 100), icon_rect, 2, border_radius=8)
                    
                    # Pokeball shape
                    center = (icon_rect.centerx, icon_rect.centery)
                    pg.draw.circle(screen, (255, 255, 255), center, 16)
                    pg.draw.arc(screen, (255, 50, 50), 
                               (center[0]-16, center[1]-16, 32, 32), 
                               3.14159, 6.28318, 16)
                    pg.draw.line(screen, (30, 30, 30), (center[0]-16, center[1]), (center[0]+16, center[1]), 3)
                    pg.draw.circle(screen, (255, 255, 255), center, 5)
                    pg.draw.circle(screen, (30, 30, 30), center, 5, 2)
                
                else:
                    # Generic item
                    pg.draw.rect(screen, (100, 100, 120), icon_rect, border_radius=8)
                    pg.draw.rect(screen, (130, 130, 150), icon_rect, 2, border_radius=8)
                    
                    q_text = self.desc_font.render("?", True, (200, 200, 200))
                    screen.blit(q_text, (icon_rect.centerx - q_text.get_width() // 2,
                                           icon_rect.centery - q_text.get_height() // 2))
                
                # Item name
                name_text = self.item_font.render(item_name, True, (255, 255, 255))
                screen.blit(name_text, (item_rect.x + 65, item_rect.y + 8))
                
                # Item description
                desc = self._get_item_attr(item, "description", "")
                desc_text = self.desc_font.render(desc, True, (150, 180, 150))
                screen.blit(desc_text, (item_rect.x + 65, item_rect.y + 30))
                
                # Price
                price = self._get_item_attr(item, "price", 0)
                can_afford = coins >= price
                price_color = (255, 215, 0) if can_afford else (200, 100, 100)
                price_text = self.price_font.render(f"{price}", True, price_color)
                screen.blit(price_text, (item_rect.right - 160, item_rect.y + 20))
                
                # Small coin icon next to price
                pg.draw.circle(screen, (255, 215, 0), (item_rect.right - 170, item_rect.y + 27), 6)
                pg.draw.circle(screen, (200, 170, 0), (item_rect.right - 170, item_rect.y + 27), 6, 1)
                
                # Stock indicator
                stock = self._get_item_attr(item, "stock", None)
                if stock is not None:
                    stock_text = self.desc_font.render(f"Stock: {stock}", True, (150, 150, 160))
                    screen.blit(stock_text, (item_rect.x + 65, item_rect.y + 45))
                
                # Buy button
                buy_btn_rect = pg.Rect(item_rect.right - 80, item_rect.y + 15, 60, 32)
                buy_hovered = buy_btn_rect.collidepoint(mouse_pos)
                
                # Check if can buy
                out_of_stock = stock is not None and stock <= 0
                
                if out_of_stock:
                    buy_color = (80, 80, 80)
                    buy_border = (100, 100, 100)
                    buy_text_color = (120, 120, 120)
                    buy_label = "SOLD"
                elif not can_afford:
                    buy_color = (100, 60, 60)
                    buy_border = (130, 80, 80)
                    buy_text_color = (180, 150, 150)
                    buy_label = "BUY"
                else:
                    buy_color = (80, 140, 80) if buy_hovered else (60, 110, 60)
                    buy_border = (100, 160, 100)
                    buy_text_color = (255, 255, 255)
                    buy_label = "BUY"
                
                pg.draw.rect(screen, buy_color, buy_btn_rect, border_radius=5)
                pg.draw.rect(screen, buy_border, buy_btn_rect, 2, border_radius=5)
                
                buy_text = self.desc_font.render(buy_label, True, buy_text_color)
                screen.blit(buy_text, (buy_btn_rect.centerx - buy_text.get_width() // 2,
                                       buy_btn_rect.centery - buy_text.get_height() // 2))
            
            # Scroll down indicator
            max_scroll = max(0, len(inventory) - self.max_visible_items)
            if len(inventory) > self.max_visible_items and self.scroll_offset < max_scroll:
                down_btn = pg.Rect(self.panel_x + self.panel_width // 2 - 15,
                                   items_start_y + self.max_visible_items * self.item_height, 30, 16)
                pg.draw.rect(screen, (70, 80, 100), down_btn, border_radius=3)
                arrow_text = self.desc_font.render("▼", True, (200, 200, 200))
                screen.blit(arrow_text, (down_btn.centerx - arrow_text.get_width() // 2,
                                        down_btn.centery - arrow_text.get_height() // 2))
        
        # Message
        if self.message:
            msg_rect = pg.Rect(self.panel_x + 20, self.panel_y + self.panel_height - 45,
                              self.panel_width - 40, 30)
            
            if self.message_success:
                bg_color = (50, 80, 50)
                border_color = (80, 130, 80)
                text_color = (150, 255, 150)
            else:
                bg_color = (80, 50, 50)
                border_color = (130, 80, 80)
                text_color = (255, 150, 150)
            
            pg.draw.rect(screen, bg_color, msg_rect, border_radius=5)
            pg.draw.rect(screen, border_color, msg_rect, 2, border_radius=5)
            
            msg_text = self.desc_font.render(self.message, True, text_color)
            screen.blit(msg_text, (msg_rect.centerx - msg_text.get_width() // 2,
                                  msg_rect.centery - msg_text.get_height() // 2))