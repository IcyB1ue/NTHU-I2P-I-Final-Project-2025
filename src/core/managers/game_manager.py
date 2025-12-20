from __future__ import annotations
from src.utils import Logger, GameSettings, Position, Teleport
import json, os
import pygame as pg
from typing import TYPE_CHECKING
from src.core.services import input_manager, scene_manager

if TYPE_CHECKING:
    from src.maps.map import Map
    from src.entities.player import Player
    from src.entities.enemy_trainer import EnemyTrainer
    from src.entities.shopkeeper import ShopEntity
    from src.data.bag import Bag
    from src.core.managers.pc_storage import PCStorage

class GameManager:
    # Entities
    player: Player | None
    enemy_trainers: dict[str, list[EnemyTrainer]]
    shops: dict[str, list[ShopEntity]]
    bag: "Bag"
    pc_storage: "PCStorage"
    
    # Map properties
    current_map_key: str
    maps: dict[str, Map]
    
    # Changing Scene properties
    should_change_scene: bool
    next_map: str
    cd: float
    
    def __init__(self, maps: dict[str, Map], start_map: str, 
                 player: Player | None,
                 enemy_trainers: dict[str, list[EnemyTrainer]],
                 shops: dict[str, list[ShopEntity]] | None = None,
                 bag: Bag | None = None,
                 pc_storage: PCStorage | None = None):
                     
        from src.data.bag import Bag
        from src.core.managers.pc_storage import PCStorage
        
        # Game Properties
        self.maps = maps
        self.current_map_key = start_map
        self.player = player
        self.enemy_trainers = enemy_trainers
        self.shops = shops if shops is not None else {}
        self.bag = bag if bag is not None else Bag([], [])
        self.pc_storage = pc_storage if pc_storage is not None else PCStorage()
        
        # Check If you should change scene
        self.should_change_scene = False
        self.next_map = ""
        
        # Track removed collision tiles (e.g., tree at 60,32 after Fire Gym)
        # Format: {map_key: [(x, y), ...]}
        self.removed_collision_tiles: dict[str, list[tuple[int, int]]] = {}
        
        
    @property
    def current_map(self) -> Map:
        return self.maps[self.current_map_key]
        
    @property
    def current_enemy_trainers(self) -> list[EnemyTrainer]:
        return self.enemy_trainers[self.current_map_key]
    
    @property
    def current_shops(self) -> list[ShopEntity]:
        return self.shops.get(self.current_map_key, [])
        
    @property
    def current_teleporter(self) -> list[Teleport]:
        return self.maps[self.current_map_key].teleporters
    
    def switch_map(self, target: str) -> None:
        if target not in self.maps:
            Logger.warning(f"Map '{target}' not loaded; cannot switch.")
            return
        
        self.next_map = target
        self.should_change_scene = True
            
    def try_switch_map(self) -> None:
        if self.should_change_scene:
            self.current_map_key = self.next_map
            self.next_map = ""
            self.should_change_scene = False
            input_manager.reset()

            
    def check_collision(self, rect: pg.Rect) -> bool:
        removed_tiles = self.removed_collision_tiles.get(self.current_map_key, [])
        
        # Get the tile the player's center is on
        center_tile_x = rect.centerx // GameSettings.TILE_SIZE
        center_tile_y = rect.centery // GameSettings.TILE_SIZE
        
        # If player center is on a removed tile, allow passage
        if (center_tile_x, center_tile_y) in removed_tiles:
            return False
        
        # Also check all corners
        tiles_to_check = [
            (rect.left // GameSettings.TILE_SIZE, rect.top // GameSettings.TILE_SIZE),
            ((rect.right - 1) // GameSettings.TILE_SIZE, rect.top // GameSettings.TILE_SIZE),
            (rect.left // GameSettings.TILE_SIZE, (rect.bottom - 1) // GameSettings.TILE_SIZE),
            ((rect.right - 1) // GameSettings.TILE_SIZE, (rect.bottom - 1) // GameSettings.TILE_SIZE),
        ]
        
        for tx, ty in tiles_to_check:
            if (tx, ty) in removed_tiles:
                return False  # Allow passage through removed tiles
        
        # Normal collision checks
        if self.maps[self.current_map_key].check_collision(rect):
            return True
        for entity in self.enemy_trainers[self.current_map_key]:
            if rect.colliderect(entity.animation.rect):
                return True
        for shop in self.current_shops:
            if rect.colliderect(shop.sprite.rect):
                return True
        return False
    
    def remove_collision_tile(self, map_key: str, tile_x: int, tile_y: int):
        """Remove collision from a specific tile (e.g., when a tree disappears)."""
        if map_key not in self.removed_collision_tiles:
            self.removed_collision_tiles[map_key] = []
        if (tile_x, tile_y) not in self.removed_collision_tiles[map_key]:
            self.removed_collision_tiles[map_key].append((tile_x, tile_y))
            Logger.info(f"Removed collision at ({tile_x}, {tile_y}) on {map_key}")
        
    def save(self, path: str) -> None:
        try:
            with open(path, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            Logger.info(f"Game saved to {path}")
        except Exception as e:
            Logger.warning(f"Failed to save game: {e}")
    
    def reload_from_file(self, path: str) -> bool:
        """
        Reload game state from file into THIS GameManager instance.
        Returns True if successful, False otherwise.
        """
        try:
            if not os.path.exists(path):
                Logger.error(f"No save file found: {path}")
                return False

            with open(path, "r") as f:
                data = json.load(f)
            
            Logger.info(f"Reloading game state from {path}")
            
            # Reload bag data
            bag_data = data.get("bag", {})
            from src.data.bag import Bag
            self.bag = Bag.from_dict(bag_data)
            
            # Reload PC storage
            from src.core.managers.pc_storage import PCStorage
            pc_data = data.get("pc_storage", {})
            self.pc_storage = PCStorage.from_dict(pc_data) if pc_data else PCStorage()
            Logger.info(f"PC storage reloaded: {self.pc_storage.get_count()} Pokemon")
            
            # Reload player position (values are in TILES, need to convert to pixels)
            if data.get("player") and self.player:
                player_data = data["player"]
                self.player.position.x = float(player_data["x"]) * GameSettings.TILE_SIZE
                self.player.position.y = float(player_data["y"]) * GameSettings.TILE_SIZE
                Logger.info(f"Player position reloaded: ({self.player.position.x}, {self.player.position.y})")
            
            # Reload current map
            self.current_map_key = data.get("current_map", self.current_map_key)
            
            # Reload enemy trainers
            from src.entities.enemy_trainer import EnemyTrainer
            for map_entry in data.get("map", []):
                map_path = map_entry["path"]
                if map_path in self.enemy_trainers:
                    self.enemy_trainers[map_path] = [
                        EnemyTrainer.from_dict(t, self) 
                        for t in map_entry.get("enemy_trainers", [])
                    ]
            
            # Reload shops
            from src.entities.shopkeeper import ShopEntity
            for map_entry in data.get("map", []):
                map_path = map_entry["path"]
                self.shops[map_path] = [
                    ShopEntity.from_dict(s, self)
                    for s in map_entry.get("shops", [])
                ]
            
            Logger.info("Game state reloaded successfully")
            return True
            
        except Exception as e:
            Logger.error(f"Failed to reload game: {e}")
            return False
             
    @classmethod
    def load(cls, path: str) -> "GameManager | None":
        """Load a NEW GameManager from file (used for initial game load)"""
        if not os.path.exists(path):
            Logger.error(f"No file found: {path}, ignoring load function")
            return None

        with open(path, "r") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> dict[str, object]:
        map_blocks: list[dict[str, object]] = []
        for key, m in self.maps.items():
            block = m.to_dict()
            block["enemy_trainers"] = [t.to_dict() for t in self.enemy_trainers.get(key, [])]
            block["shops"] = [s.to_dict() for s in self.shops.get(key, [])]
            map_blocks.append(block)
        return {
            "map": map_blocks,
            "current_map": self.current_map_key,
            "player": self.player.to_dict() if self.player is not None else None,
            "bag": self.bag.to_dict(),
            "pc_storage": self.pc_storage.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "GameManager":
        from src.maps.map import Map
        from src.entities.player import Player
        from src.entities.enemy_trainer import EnemyTrainer
        from src.entities.shopkeeper import ShopEntity
        from src.data.bag import Bag
        from src.core.managers.pc_storage import PCStorage
        
        Logger.info("Loading maps")
        maps_data = data["map"]
        maps: dict[str, Map] = {}
        player_spawns: dict[str, Position] = {}
        trainers: dict[str, list[EnemyTrainer]] = {}
        shops: dict[str, list[ShopEntity]] = {}

        for entry in maps_data:
            path = entry["path"]
            maps[path] = Map.from_dict(entry)
            sp = entry.get("player")
            if sp:
                player_spawns[path] = Position(
                    sp["x"] * GameSettings.TILE_SIZE,
                    sp["y"] * GameSettings.TILE_SIZE
                )
        current_map = data["current_map"]
        gm = cls(
            maps, current_map,
            None,  # Player
            trainers,
            shops,
            bag=None,
            pc_storage=None
        )
        gm.current_map_key = current_map
        
        Logger.info("Loading enemy trainers")
        for m in data["map"]:
            raw_data = m.get("enemy_trainers", [])
            gm.enemy_trainers[m["path"]] = [EnemyTrainer.from_dict(t, gm) for t in raw_data]
        
        Logger.info("Loading shops")
        for m in data["map"]:
            raw_data = m.get("shops", [])
            gm.shops[m["path"]] = [ShopEntity.from_dict(s, gm) for s in raw_data]
        
        Logger.info("Loading Player")
        if data.get("player"):
            gm.player = Player.from_dict(data["player"], gm)
        
        Logger.info("Loading bag")
        gm.bag = Bag.from_dict(data.get("bag", {})) if data.get("bag") else Bag([], [])
        
        Logger.info("Loading PC storage")
        gm.pc_storage = PCStorage.from_dict(data.get("pc_storage", {})) if data.get("pc_storage") else PCStorage()
        Logger.info(f"PC storage loaded: {gm.pc_storage.get_count()} Pokemon")

        return gm