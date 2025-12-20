from __future__ import annotations
from typing import TYPE_CHECKING
import pygame as pg
from src.sprites import Sprite
from src.utils import Position, PositionCamera, Direction, GameSettings
from src.core import GameManager

if TYPE_CHECKING:
    from .player import Player
    from src.data.bag import Bag


class ShopItem:
    """Represents an item available for purchase in a shop."""
    
    def __init__(
        self, 
        name: str, 
        price: int, 
        sprite_path: str,
        description: str = "",
        stock: int | None = None  # None = unlimited
    ) -> None:
        self.name = name
        self.price = price
        self.sprite_path = sprite_path
        self.description = description
        self.stock = stock
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "price": self.price,
            "sprite_path": self.sprite_path,
            "description": self.description,
            "stock": self.stock
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> ShopItem:
        return cls(
            name=data["name"],
            price=data["price"],
            sprite_path=data["sprite_path"],
            description=data.get("description", ""),
            stock=data.get("stock")
        )
    
    def __repr__(self) -> str:
        return f"ShopItem({self.name}, {self.price} coins)"


class ShopEntity:
    """An NPC shopkeeper that sells items to the player (static sprite, no animation)."""
    
    CURRENCY_NAME = "Coins"  # The item name used as currency in the bag
    
    def __init__(
        self, 
        x: float, 
        y: float, 
        game_manager: GameManager,
        name: str = "Merchant",
        inventory: list[ShopItem] | None = None,
        sprite_path: str = "character/shopkeeper.png",
        sprite_scale: float = 2.0  # Default 2x size
    ) -> None:
        self.position = Position(x, y)
        self.game_manager = game_manager
        self.name = name
        self.inventory: list[ShopItem] = inventory or []
        self.is_shop_open = False
        self.interaction_range = GameSettings.TILE_SIZE * 2.5  # Larger interaction range
        self.sprite_path = sprite_path
        self.sprite_scale = sprite_scale
        
        # Static sprite with configurable size
        self.sprite_size = int(GameSettings.TILE_SIZE * sprite_scale)
        self.sprite = Sprite(sprite_path, (self.sprite_size, self.sprite_size))
        self.sprite.rect.topleft = (int(self.position.x), int(self.position.y))
    
    # ---------------------------
    # Inventory management
    # ---------------------------
    def add_item(self, item: ShopItem) -> None:
        """Add an item to the shop's inventory."""
        self.inventory.append(item)
    
    def remove_item(self, name: str) -> bool:
        """Remove an item from the shop by name."""
        for i, item in enumerate(self.inventory):
            if item.name == name:
                self.inventory.pop(i)
                return True
        return False
    
    def get_item(self, name: str) -> ShopItem | None:
        """Get an item by name."""
        for item in self.inventory:
            if item.name == name:
                return item
        return None
    
    # ---------------------------
    # Interaction
    # ---------------------------
    def can_interact(self, player_position: Position) -> bool:
        """Check if the player is close enough to interact."""
        # Use center of sprite for distance calculation
        center_x = self.position.x + GameSettings.TILE_SIZE // 2
        center_y = self.position.y + GameSettings.TILE_SIZE // 2
        dx = center_x - player_position.x
        dy = center_y - player_position.y
        distance = (dx ** 2 + dy ** 2) ** 0.5
        return distance <= self.interaction_range
    
    def interact(self, player: Player) -> bool:
        """Called when player interacts with the shop."""
        if not self.can_interact(player.position):
            return False
        
        self.is_shop_open = True
        return True
    
    def close_shop(self) -> None:
        """Close the shop interface."""
        self.is_shop_open = False
    
    # ---------------------------
    # Currency helpers (using Bag)
    # ---------------------------
    def _get_player_coins(self, bag: Bag) -> int:
        """Get the player's coin count from their bag."""
        for item in bag._items_data:
            if item["name"] == self.CURRENCY_NAME:
                return item["count"]
        return 0
    
    def _set_player_coins(self, bag: Bag, amount: int) -> None:
        """Set the player's coin count in their bag."""
        for item in bag._items_data:
            if item["name"] == self.CURRENCY_NAME:
                item["count"] = amount
                return
        # If coins don't exist, create them
        bag._items_data.append({
            "name": self.CURRENCY_NAME,
            "count": amount,
            "sprite_path": "ingame_ui/coin.png"
        })
    
    def _add_item_to_bag(self, bag: Bag, shop_item: ShopItem, quantity: int = 1) -> None:
        """Add a purchased item to the player's bag."""
        # Check if item already exists in bag
        for item in bag._items_data:
            if item["name"] == shop_item.name:
                item["count"] += quantity
                return
        
        # Add new item
        bag._items_data.append({
            "name": shop_item.name,
            "count": quantity,
            "sprite_path": shop_item.sprite_path
        })
    
    # ---------------------------
    # Purchase logic
    # ---------------------------
    def purchase_item(self, item_name: str, bag: Bag, quantity: int = 1) -> tuple[bool, str]:
        """
        Attempt to purchase an item.
        Returns (success, message).
        """
        shop_item = self.get_item(item_name)
        
        if shop_item is None:
            return False, "Item not found."
        
        total_cost = shop_item.price * quantity
        
        # Check stock
        if shop_item.stock is not None:
            if shop_item.stock < quantity:
                return False, f"Not enough stock. Only {shop_item.stock} left."
        
        # Check player has enough coins
        player_coins = self._get_player_coins(bag)
        if player_coins < total_cost:
            return False, f"Not enough coins. Need {total_cost}, have {player_coins}."
        
        # Process transaction
        self._set_player_coins(bag, player_coins - total_cost)
        self._add_item_to_bag(bag, shop_item, quantity)
        
        # Decrease stock if limited
        if shop_item.stock is not None:
            shop_item.stock -= quantity
            if shop_item.stock <= 0:
                self.remove_item(item_name)
        
        # Refresh bag visuals
        bag.reload_bag()
        
        return True, f"Purchased {quantity}x {shop_item.name} for {total_cost} coins!"
    
    def sell_item(self, item_name: str, bag: Bag, quantity: int = 1, sell_ratio: float = 0.5) -> tuple[bool, str]:
        """
        Sell an item from the player's bag.
        sell_ratio: fraction of buy price the player receives (default 50%)
        """
        # Find item in player's bag
        bag_item = None
        for item in bag._items_data:
            if item["name"] == item_name:
                bag_item = item
                break
        
        if bag_item is None:
            return False, "You don't have that item."
        
        if bag_item["count"] < quantity:
            return False, f"You only have {bag_item['count']}."
        
        # Determine sell price (check if we sell this item, otherwise use default)
        shop_item = self.get_item(item_name)
        if shop_item:
            sell_price = int(shop_item.price * sell_ratio) * quantity
        else:
            sell_price = quantity  # Default 1 coin per item if not in shop
        
        # Process transaction
        bag_item["count"] -= quantity
        if bag_item["count"] <= 0:
            bag._items_data.remove(bag_item)
        
        player_coins = self._get_player_coins(bag)
        self._set_player_coins(bag, player_coins + sell_price)
        
        # Refresh bag visuals
        bag.reload_bag()
        
        return True, f"Sold {quantity}x {item_name} for {sell_price} coins!"
    
    # ---------------------------
    # Update / Draw
    # ---------------------------
    def update(self, dt: float) -> None:
        """Update the shop entity."""
        # Static sprite, nothing to update
        pass
    
    def draw(self, screen: pg.Surface, camera: PositionCamera) -> None:
        """Draw the shopkeeper."""
        # Calculate screen position - center the sprite on the tile position
        # Offset by half the difference between sprite size and tile size
        offset = (self.sprite_size - GameSettings.TILE_SIZE) // 2
        screen_x = int(self.position.x - camera.x) - offset
        screen_y = int(self.position.y - camera.y) - offset
        self.sprite.rect.topleft = (screen_x, screen_y)
        self.sprite.draw(screen)
        
        # Debug: draw interaction range
        if GameSettings.DRAW_HITBOXES:
            center_x = screen_x + self.sprite_size // 2
            center_y = screen_y + self.sprite_size // 2
            pg.draw.circle(
                screen, (0, 255, 0), 
                (center_x, center_y), 
                int(self.interaction_range), 
                1
            )
    
    # ---------------------------
    # Serialization
    # ---------------------------
    def to_dict(self) -> dict:
        return {
            "x": self.position.x / GameSettings.TILE_SIZE,
            "y": self.position.y / GameSettings.TILE_SIZE,
            "name": self.name,
            "sprite_path": self.sprite_path,
            "sprite_scale": self.sprite_scale,
            "inventory": [item.to_dict() for item in self.inventory]
        }
    
    @classmethod
    def from_dict(cls, data: dict, game_manager: GameManager) -> ShopEntity:
        x = float(data["x"])
        y = float(data["y"])
        name = data.get("name", "Merchant")
        sprite_path = data.get("sprite_path", "character/shopkeeper.png")
        sprite_scale = data.get("sprite_scale", 2.0)  # Default 2x
        
        shop = cls(
            x * GameSettings.TILE_SIZE, 
            y * GameSettings.TILE_SIZE, 
            game_manager, 
            name,
            sprite_path=sprite_path,
            sprite_scale=sprite_scale
        )
        
        for item_data in data.get("inventory", []):
            shop.add_item(ShopItem.from_dict(item_data))
        
        return shop