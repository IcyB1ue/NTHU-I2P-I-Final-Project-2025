import pygame as pg
import json
from src.utils import GameSettings, Logger
from src.utils.definition import Monster, Item
from src.sprites import Sprite, Text
from src.interface.components.button import Button
from src.core.services import input_manager


# Monster sprite size in bag
BAG_MONSTER_SPRITE_SIZE = 80

# Healing item definitions
HEALING_ITEMS = {
    "Potion": {"heal": 50, "description": "Restores 50 HP"},
    "Super Potion": {"heal": 100, "description": "Restores 100 HP"},
    "Hyper Potion": {"heal": 200, "description": "Restores 200 HP"},
    "Max Potion": {"heal": 9999, "description": "Fully restores HP"},
    "Full Restore": {"heal": 9999, "description": "Fully restores HP"},
}


class Bag:
    _monsters_data: list[Monster]
    _items_data: list[Item]

    # Maximum Pokemon in party
    MAX_PARTY_SIZE = 6

    def __init__(self, monsters_data: list[Monster] | None = None, items_data: list[Item] | None = None):
        self._monsters_data = monsters_data if monsters_data else []
        self._items_data = items_data if items_data else []

        # Panel dimensions
        self.panel_width = 800
        self.panel_height = 550
        self.panel_x = (GameSettings.SCREEN_WIDTH - self.panel_width) // 2
        self.panel_y = (GameSettings.SCREEN_HEIGHT - self.panel_height) // 2

        # Visual elements
        self.monsters_sprite = []
        self.monsters_data = []
        self.item_sprite = []
        self.item_data = []
        
        # Item buttons for using items
        self.item_buttons: list[Button | None] = []
        
        # Monster selection for healing
        self.selecting_monster_for_item: str | None = None
        self.monster_buttons: list[Button | None] = []

        # Darken background
        self.darken = pg.Surface((GameSettings.SCREEN_WIDTH, GameSettings.SCREEN_HEIGHT))
        self.darken.fill((0, 0, 0))
        self.darken.set_alpha(180)

        self.overlay_show = False
        self.boxes_show = False  # Keep for compatibility
        
        # Message display
        self.message = ""
        self.message_timer = 0.0
        
        # Fonts
        try:
            self.title_font = pg.font.Font("assets/fonts/Minecraft.ttf", 28)
            self.name_font = pg.font.Font("assets/fonts/Minecraft.ttf", 18)
            self.stat_font = pg.font.Font("assets/fonts/Minecraft.ttf", 14)
            self.item_font = pg.font.Font("assets/fonts/Minecraft.ttf", 16)
        except:
            self.title_font = pg.font.Font(None, 32)
            self.name_font = pg.font.Font(None, 22)
            self.stat_font = pg.font.Font(None, 18)
            self.item_font = pg.font.Font(None, 20)
        
        # Scroll for items
        self.item_scroll = 0
        self.max_visible_items = 5

    def _on_back_pressed(self):
        """Handle back button press."""
        if self.selecting_monster_for_item:
            self.selecting_monster_for_item = None
            self.message = ""
        else:
            self.close()

    # ---------------------------
    # Monster utilities
    # ---------------------------
    @property
    def monsters(self) -> list[Monster]:
        return self._monsters_data

    def get_first_alive_monster(self) -> Monster | None:
        for monster in self._monsters_data:
            if monster["hp"] > 0:
                return monster
        return None

    def get_all_alive_monsters(self) -> list[Monster]:
        return [monster for monster in self._monsters_data if monster["hp"] > 0]

    def get_monster_count(self) -> int:
        return len(self._monsters_data)

    def get_alive_monster_count(self) -> int:
        return len(self.get_all_alive_monsters())

    # ---------------------------
    # Item utilities
    # ---------------------------
    @property
    def items(self) -> list[Item]:
        return self._items_data

    def add_item(self, name: str, count: int = 1, sprite_path: str = "ingame_ui/potion.png"):
        """Add an item to the bag."""
        for item in self._items_data:
            if item["name"] == name:
                item["count"] += count
                self.reload_bag()
                Logger.info(f"Added {count}x {name} to bag (now have {item['count']})")
                return
        
        self._items_data.append({
            "name": name,
            "count": count,
            "sprite_path": sprite_path
        })
        self.reload_bag()
        Logger.info(f"Added new item {count}x {name} to bag")

    def remove_item(self, name: str, count: int = 1) -> bool:
        """Remove an item from the bag."""
        for item in self._items_data:
            if item["name"] == name:
                if item["count"] >= count:
                    item["count"] -= count
                    if item["count"] <= 0:
                        self._items_data.remove(item)
                    self.reload_bag()
                    Logger.info(f"Removed {count}x {name} from bag")
                    return True
                return False
        return False

    def has_item(self, name: str, count: int = 1) -> bool:
        for item in self._items_data:
            if item["name"] == name and item["count"] >= count:
                return True
        return False

    def get_item_count(self, name: str) -> int:
        for item in self._items_data:
            if item["name"] == name:
                return item["count"]
        return 0

    # ---------------------------
    # Healing functionality
    # ---------------------------
    def _is_healing_item(self, item_name: str) -> bool:
        return item_name in HEALING_ITEMS
    
    def _use_item_on_monster(self, item_name: str, monster: Monster):
        """Use a healing item on a monster."""
        if item_name not in HEALING_ITEMS:
            self.message = f"{item_name} cannot be used!"
            self.message_timer = 2.0
            return
        
        heal_info = HEALING_ITEMS[item_name]
        heal_amount = heal_info["heal"]
        
        if monster["hp"] >= monster["max_hp"]:
            self.message = f"{monster['name']} is already at full HP!"
            self.message_timer = 2.0
            return
        
        if not self.remove_item(item_name):
            self.message = f"No {item_name} left!"
            self.message_timer = 2.0
            return
        
        old_hp = monster["hp"]
        monster["hp"] = min(monster["hp"] + heal_amount, monster["max_hp"])
        actual_heal = monster["hp"] - old_hp
        
        self.message = f"{monster['name']} recovered {actual_heal} HP!"
        self.message_timer = 2.0
        self.selecting_monster_for_item = None
        
        Logger.info(f"Used {item_name} on {monster['name']}: +{actual_heal} HP")
        self.reload_bag()
    
    def _on_use_item(self, item_name: str):
        """Called when user clicks 'Use' on an item."""
        if self._is_healing_item(item_name):
            needs_healing = False
            for monster in self._monsters_data:
                if monster["hp"] < monster["max_hp"]:
                    needs_healing = True
                    break
            
            if not needs_healing:
                self.message = "All Pokemon are at full HP!"
                self.message_timer = 2.0
                return
            
            self.selecting_monster_for_item = item_name
            self.message = f"Select a Pokemon to use {item_name} on:"
        else:
            self.message = f"{item_name} cannot be used here."
            self.message_timer = 2.0

    # ---------------------------
    # Monster management
    # ---------------------------
    def is_party_full(self) -> bool:
        return len(self._monsters_data) >= self.MAX_PARTY_SIZE

    def add_monster(self, monster: Monster) -> bool:
        if self.is_party_full():
            Logger.warning(f"Party is full! Cannot add {monster.get('name', 'Unknown')} to party.")
            return False
        
        self._monsters_data.append(monster)
        self.reload_bag()
        Logger.info(f"Added monster {monster.get('name', 'Unknown')} to party")
        return True

    # ---------------------------
    # Open / close
    # ---------------------------
    def open(self, reload_from_memory: bool = True, reload_from_disk: bool = False):
        input_manager.reset()

        if reload_from_disk:
            self._reload_from_disk()

        if reload_from_memory or reload_from_disk:
            self.reload_bag()

        self.overlay_show = True
        self.boxes_show = True
        self.selecting_monster_for_item = None
        self.message = ""
        self.item_scroll = 0

    def close(self):
        input_manager.reset()
        self.overlay_show = False
        self.boxes_show = False
        self.selecting_monster_for_item = None
        self.message = ""

    # ---------------------------
    # Update / draw
    # ---------------------------
    def update(self, dt: float):
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                if not self.selecting_monster_for_item:
                    self.message = ""
        
        if not self.overlay_show:
            return
        
        mouse_pos = pg.mouse.get_pos()
        
        # Handle back button / escape
        if input_manager.key_pressed(pg.K_ESCAPE):
            self._on_back_pressed()
            return
        
        # Handle mouse click
        if input_manager.mouse_pressed(1):
            # Check close button
            close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
            if close_btn_rect.collidepoint(mouse_pos):
                self._on_back_pressed()
                return
            
            if self.selecting_monster_for_item:
                # Check monster selection
                for i, monster in enumerate(self._monsters_data):
                    if i >= 6:
                        break
                    card_rect = pg.Rect(self.panel_x + 20, self.panel_y + 80 + i * 78, 360, 72)
                    if card_rect.collidepoint(mouse_pos):
                        if monster["hp"] < monster["max_hp"]:
                            self._use_item_on_monster(self.selecting_monster_for_item, monster)
                        return
            else:
                # Check item use buttons
                for i, item in enumerate(self._items_data):
                    if i < self.item_scroll or i >= self.item_scroll + self.max_visible_items:
                        continue
                    
                    display_i = i - self.item_scroll
                    item_x = self.panel_x + 420
                    item_y = self.panel_y + 80 + display_i * 85
                    item_width = 360
                    use_btn_rect = pg.Rect(item_x + item_width - 70, item_y + 25, 60, 28)
                    
                    if use_btn_rect.collidepoint(mouse_pos) and self._is_healing_item(item["name"]):
                        self._on_use_item(item["name"])
                        return
        
        # Handle scroll for items
        if len(self._items_data) > self.max_visible_items:
            if input_manager.key_pressed(pg.K_DOWN):
                self.item_scroll = min(self.item_scroll + 1, len(self._items_data) - self.max_visible_items)
            if input_manager.key_pressed(pg.K_UP):
                self.item_scroll = max(0, self.item_scroll - 1)

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
        title_text = self.title_font.render("BAG", True, (255, 255, 255))
        screen.blit(title_text, (self.panel_x + 20, self.panel_y + 12))
        
        # Close button
        close_btn_rect = pg.Rect(self.panel_x + self.panel_width - 40, self.panel_y + 10, 30, 30)
        close_color = (200, 80, 80) if close_btn_rect.collidepoint(mouse_pos) else (150, 60, 60)
        pg.draw.rect(screen, close_color, close_btn_rect, border_radius=5)
        x_text = self.name_font.render("X", True, (255, 255, 255))
        screen.blit(x_text, (close_btn_rect.centerx - x_text.get_width() // 2, 
                            close_btn_rect.centery - x_text.get_height() // 2))
        
        # Divider line
        divider_x = self.panel_x + 400
        pg.draw.line(screen, (80, 90, 110), 
                     (divider_x, self.panel_y + 55), 
                     (divider_x, self.panel_y + self.panel_height - 15), 2)
        
        # Section headers
        pokemon_header = self.name_font.render(f"POKEMON ({len(self._monsters_data)}/6)", True, (150, 200, 255))
        screen.blit(pokemon_header, (self.panel_x + 20, self.panel_y + 55))
        
        items_header = self.name_font.render(f"ITEMS ({len(self._items_data)})", True, (255, 200, 150))
        screen.blit(items_header, (self.panel_x + 420, self.panel_y + 55))
        
        # Draw Pokemon cards
        self._draw_pokemon_cards(screen, mouse_pos)
        
        # Draw Items
        self._draw_items(screen, mouse_pos)
        
        # Draw message
        if self.message:
            self._draw_message(screen)
    
    def _draw_pokemon_cards(self, screen: pg.Surface, mouse_pos: tuple):
        """Draw Pokemon cards on the left side."""
        for i, monster in enumerate(self._monsters_data):
            if i >= 6:
                break
            
            card_x = self.panel_x + 20
            card_y = self.panel_y + 80 + i * 78
            card_width = 360
            card_height = 72
            card_rect = pg.Rect(card_x, card_y, card_width, card_height)
            
            # Card background
            is_hovered = card_rect.collidepoint(mouse_pos)
            is_fainted = monster["hp"] <= 0
            can_heal = monster["hp"] < monster["max_hp"]
            
            if self.selecting_monster_for_item:
                if can_heal and is_hovered:
                    card_color = (60, 100, 60)
                elif can_heal:
                    card_color = (50, 70, 50)
                else:
                    card_color = (40, 40, 45)
            elif is_fainted:
                card_color = (60, 40, 40)
            elif is_hovered:
                card_color = (55, 60, 75)
            else:
                card_color = (50, 55, 70)
            
            pg.draw.rect(screen, card_color, card_rect, border_radius=8)
            
            # Card border
            if self.selecting_monster_for_item and can_heal:
                border_color = (100, 200, 100)
            elif is_fainted:
                border_color = (150, 80, 80)
            else:
                border_color = (70, 80, 100)
            pg.draw.rect(screen, border_color, card_rect, 2, border_radius=8)
            
            # Monster sprite
            try:
                sprite_path = monster.get("sprite_path") or monster.get("sprite", "")
                if sprite_path:
                    img = pg.image.load(f"assets/images/{sprite_path}").convert_alpha()
                    img = pg.transform.scale(img, (60, 60))
                    screen.blit(img, (card_x + 8, card_y + 6))
            except:
                # Draw placeholder
                pg.draw.rect(screen, (80, 80, 100), (card_x + 8, card_y + 6, 60, 60), border_radius=5)
            
            # Monster name
            name_text = self.name_font.render(monster["name"], True, (255, 255, 255))
            screen.blit(name_text, (card_x + 75, card_y + 8))
            
            # Level
            level_text = self.stat_font.render(f"Lv.{monster['level']}", True, (180, 180, 180))
            screen.blit(level_text, (card_x + 75, card_y + 30))
            
            # HP bar background
            hp_bar_x = card_x + 75
            hp_bar_y = card_y + 50
            hp_bar_width = 180
            hp_bar_height = 14
            pg.draw.rect(screen, (30, 30, 35), (hp_bar_x, hp_bar_y, hp_bar_width, hp_bar_height), border_radius=3)
            
            # HP bar fill
            hp_ratio = monster["hp"] / monster["max_hp"]
            if hp_ratio > 0.5:
                hp_color = (80, 200, 80)
            elif hp_ratio > 0.25:
                hp_color = (220, 180, 50)
            else:
                hp_color = (200, 60, 60)
            
            fill_width = int(hp_bar_width * hp_ratio)
            if fill_width > 0:
                pg.draw.rect(screen, hp_color, (hp_bar_x, hp_bar_y, fill_width, hp_bar_height), border_radius=3)
            
            # HP text
            hp_text = self.stat_font.render(f"{monster['hp']}/{monster['max_hp']}", True, (255, 255, 255))
            screen.blit(hp_text, (hp_bar_x + hp_bar_width + 10, hp_bar_y))
            
            # Type indicator (small colored dot)
            element_type = monster.get("element_type", "Normal")
            type_colors = {
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
            type_color = type_colors.get(element_type, (150, 150, 150))
            pg.draw.circle(screen, type_color, (card_x + card_width - 20, card_y + 15), 8)
    
    def _draw_items(self, screen: pg.Surface, mouse_pos: tuple):
        """Draw items on the right side."""
        if not self._items_data:
            empty_text = self.stat_font.render("No items", True, (120, 120, 120))
            screen.blit(empty_text, (self.panel_x + 500, self.panel_y + 150))
            return
        
        # Draw visible items
        for i in range(self.item_scroll, min(len(self._items_data), self.item_scroll + self.max_visible_items)):
            item = self._items_data[i]
            display_i = i - self.item_scroll
            
            item_x = self.panel_x + 420
            item_y = self.panel_y + 80 + display_i * 85
            item_width = 360
            item_height = 78
            item_rect = pg.Rect(item_x, item_y, item_width, item_height)
            
            # Item card background
            is_hovered = item_rect.collidepoint(mouse_pos)
            card_color = (55, 60, 75) if is_hovered else (50, 55, 70)
            pg.draw.rect(screen, card_color, item_rect, border_radius=8)
            pg.draw.rect(screen, (70, 80, 100), item_rect, 2, border_radius=8)
            
            # Item sprite
            try:
                img = pg.image.load(f"assets/images/{item['sprite_path']}").convert_alpha()
                img = pg.transform.scale(img, (50, 50))
                screen.blit(img, (item_x + 10, item_y + 14))
            except:
                pg.draw.rect(screen, (80, 80, 100), (item_x + 10, item_y + 14, 50, 50), border_radius=5)
            
            # Item name
            name_text = self.item_font.render(item["name"], True, (255, 255, 255))
            screen.blit(name_text, (item_x + 70, item_y + 12))
            
            # Item count
            count_text = self.stat_font.render(f"x{item['count']}", True, (180, 200, 180))
            screen.blit(count_text, (item_x + 70, item_y + 35))
            
            # Description for healing items
            if item["name"] in HEALING_ITEMS:
                desc = HEALING_ITEMS[item["name"]]["description"]
                desc_text = self.stat_font.render(desc, True, (140, 140, 140))
                screen.blit(desc_text, (item_x + 70, item_y + 55))
            
            # Use button for healing items
            if self._is_healing_item(item["name"]) and not self.selecting_monster_for_item:
                use_btn_rect = pg.Rect(item_x + item_width - 70, item_y + 25, 60, 28)
                btn_hovered = use_btn_rect.collidepoint(mouse_pos)
                btn_color = (80, 140, 80) if btn_hovered else (60, 110, 60)
                pg.draw.rect(screen, btn_color, use_btn_rect, border_radius=5)
                pg.draw.rect(screen, (100, 160, 100), use_btn_rect, 1, border_radius=5)
                
                use_text = self.stat_font.render("USE", True, (255, 255, 255))
                screen.blit(use_text, (use_btn_rect.centerx - use_text.get_width() // 2,
                                       use_btn_rect.centery - use_text.get_height() // 2))
        
        # Scroll indicators
        if self.item_scroll > 0:
            up_text = self.stat_font.render("▲ Scroll Up", True, (150, 150, 150))
            screen.blit(up_text, (self.panel_x + 550, self.panel_y + 510))
        
        if self.item_scroll + self.max_visible_items < len(self._items_data):
            down_text = self.stat_font.render("▼ Scroll Down", True, (150, 150, 150))
            screen.blit(down_text, (self.panel_x + 550, self.panel_y + 525))
    
    def _draw_message(self, screen: pg.Surface):
        """Draw message at bottom of panel."""
        msg_rect = pg.Rect(self.panel_x + 20, self.panel_y + self.panel_height - 45, 
                          self.panel_width - 40, 35)
        
        # Message background
        if self.selecting_monster_for_item:
            bg_color = (50, 80, 50)
            border_color = (100, 150, 100)
        else:
            bg_color = (60, 60, 70)
            border_color = (100, 100, 120)
        
        pg.draw.rect(screen, bg_color, msg_rect, border_radius=5)
        pg.draw.rect(screen, border_color, msg_rect, 2, border_radius=5)
        
        # Message text
        msg_text = self.stat_font.render(self.message, True, (255, 255, 255))
        screen.blit(msg_text, (msg_rect.centerx - msg_text.get_width() // 2,
                              msg_rect.centery - msg_text.get_height() // 2))

    # ---------------------------
    # Serialization
    # ---------------------------
    def to_dict(self) -> dict[str, object]:
        return {
            "monsters": [dict(m) for m in self._monsters_data],
            "items": [dict(i) for i in self._items_data]
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Bag":
        monsters_raw = data.get("monsters") or []
        monsters: list[Monster] = [dict(m) for m in monsters_raw]

        items_raw = data.get("items") or []
        items: list[Item] = [dict(i) for i in items_raw]

        bag = cls(monsters, items)
        bag.reload_bag()
        return bag

    # ---------------------------
    # Visual helpers
    # ---------------------------
    def _clear_visuals(self):
        self.monsters_sprite = []
        self.monsters_data = []
        self.item_sprite = []
        self.item_data = []
        self.item_buttons = []

    def reload_bag(self):
        """Rebuild visual elements - now mostly handled in draw()."""
        self._clear_visuals()
        # Most rendering is now done directly in draw() for better control

    # ---------------------------
    # Disk reload
    # ---------------------------
    def _reload_from_disk(self):
        """Reload Bag data from 'game0.json'."""
        try:
            with open("game0.json", "r") as f:
                data = json.load(f)
            bag_data = data.get("bag", {})
            self._monsters_data = [dict(m) for m in bag_data.get("monsters", [])]
            self._items_data = [dict(i) for i in bag_data.get("items", [])]
        except Exception as e:
            Logger.warning(f"Failed to reload Bag from disk: {e}")