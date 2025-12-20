from pygame import Rect
from .settings import GameSettings
from dataclasses import dataclass
from enum import Enum
from typing import overload, TypedDict, Protocol

MouseBtn = int
Key = int

Direction = Enum('Direction', ['UP', 'DOWN', 'LEFT', 'RIGHT', 'NONE'])

# Pokemon Element Types
class ElementType(Enum):
    NORMAL = "Normal"
    FIRE = "Fire"
    WATER = "Water"
    ELECTRIC = "Electric"
    GRASS = "Grass"
    ICE = "Ice"
    FIGHTING = "Fighting"
    POISON = "Poison"
    GROUND = "Ground"
    FLYING = "Flying"
    PSYCHIC = "Psychic"
    BUG = "Bug"
    ROCK = "Rock"
    GHOST = "Ghost"
    DRAGON = "Dragon"


# Type effectiveness chart (attacker -> defender -> multiplier)
# 2.0 = super effective, 0.5 = not very effective, 0.0 = no effect
TYPE_CHART: dict[ElementType, dict[ElementType, float]] = {
    ElementType.NORMAL: {
        ElementType.ROCK: 0.5,
        ElementType.GHOST: 0.0,
    },
    ElementType.FIRE: {
        ElementType.FIRE: 0.5,
        ElementType.WATER: 0.5,
        ElementType.GRASS: 2.0,
        ElementType.ICE: 2.0,
        ElementType.BUG: 2.0,
        ElementType.ROCK: 0.5,
        ElementType.DRAGON: 0.5,
    },
    ElementType.WATER: {
        ElementType.FIRE: 2.0,
        ElementType.WATER: 0.5,
        ElementType.GRASS: 0.5,
        ElementType.GROUND: 2.0,
        ElementType.ROCK: 2.0,
        ElementType.DRAGON: 0.5,
    },
    ElementType.ELECTRIC: {
        ElementType.WATER: 2.0,
        ElementType.ELECTRIC: 0.5,
        ElementType.GRASS: 0.5,
        ElementType.GROUND: 0.0,
        ElementType.FLYING: 2.0,
        ElementType.DRAGON: 0.5,
    },
    ElementType.GRASS: {
        ElementType.FIRE: 0.5,
        ElementType.WATER: 2.0,
        ElementType.GRASS: 0.5,
        ElementType.POISON: 0.5,
        ElementType.GROUND: 2.0,
        ElementType.FLYING: 0.5,
        ElementType.BUG: 0.5,
        ElementType.ROCK: 2.0,
        ElementType.DRAGON: 0.5,
    },
    ElementType.ICE: {
        ElementType.FIRE: 0.5,
        ElementType.WATER: 0.5,
        ElementType.GRASS: 2.0,
        ElementType.ICE: 0.5,
        ElementType.GROUND: 2.0,
        ElementType.FLYING: 2.0,
        ElementType.DRAGON: 2.0,
    },
    ElementType.FIGHTING: {
        ElementType.NORMAL: 2.0,
        ElementType.ICE: 2.0,
        ElementType.POISON: 0.5,
        ElementType.FLYING: 0.5,
        ElementType.PSYCHIC: 0.5,
        ElementType.BUG: 0.5,
        ElementType.ROCK: 2.0,
        ElementType.GHOST: 0.0,
    },
    ElementType.POISON: {
        ElementType.GRASS: 2.0,
        ElementType.POISON: 0.5,
        ElementType.GROUND: 0.5,
        ElementType.BUG: 2.0,
        ElementType.ROCK: 0.5,
        ElementType.GHOST: 0.5,
    },
    ElementType.GROUND: {
        ElementType.FIRE: 2.0,
        ElementType.ELECTRIC: 2.0,
        ElementType.GRASS: 0.5,
        ElementType.POISON: 2.0,
        ElementType.FLYING: 0.0,
        ElementType.BUG: 0.5,
        ElementType.ROCK: 2.0,
    },
    ElementType.FLYING: {
        ElementType.ELECTRIC: 0.5,
        ElementType.GRASS: 2.0,
        ElementType.FIGHTING: 2.0,
        ElementType.BUG: 2.0,
        ElementType.ROCK: 0.5,
    },
    ElementType.PSYCHIC: {
        ElementType.FIGHTING: 2.0,
        ElementType.POISON: 2.0,
        ElementType.PSYCHIC: 0.5,
    },
    ElementType.BUG: {
        ElementType.FIRE: 0.5,
        ElementType.GRASS: 2.0,
        ElementType.FIGHTING: 0.5,
        ElementType.POISON: 2.0,
        ElementType.FLYING: 0.5,
        ElementType.PSYCHIC: 2.0,
        ElementType.GHOST: 0.5,
    },
    ElementType.ROCK: {
        ElementType.FIRE: 2.0,
        ElementType.ICE: 2.0,
        ElementType.FIGHTING: 0.5,
        ElementType.GROUND: 0.5,
        ElementType.FLYING: 2.0,
        ElementType.BUG: 2.0,
    },
    ElementType.GHOST: {
        ElementType.NORMAL: 0.0,
        ElementType.PSYCHIC: 0.0,
        ElementType.GHOST: 2.0,
    },
    ElementType.DRAGON: {
        ElementType.DRAGON: 2.0,
    },
}


def get_type_multiplier(attacker_type: str, defender_type: str) -> float:
    """Get the damage multiplier based on types."""
    try:
        atk_type = ElementType(attacker_type)
        def_type = ElementType(defender_type)
        
        if atk_type in TYPE_CHART:
            return TYPE_CHART[atk_type].get(def_type, 1.0)
        return 1.0
    except (ValueError, KeyError):
        return 1.0


def get_effectiveness_message(multiplier: float) -> str:
    """Get a message describing the effectiveness."""
    if multiplier >= 2.0:
        return "It's super effective!"
    elif multiplier == 0.0:
        return "It has no effect..."
    elif multiplier <= 0.5:
        return "It's not very effective..."
    return ""


# ============== MOVE SYSTEM ==============

class Move(TypedDict, total=False):
    name: str
    type: str  # Element type
    power: int  # Base damage (0 for status moves)
    accuracy: int  # 0-100
    pp: int  # Power points (uses)
    max_pp: int
    category: str  # "physical", "special", "status"
    effect: str  # Optional effect description


# All available moves in the game
MOVE_DATABASE: dict[str, Move] = {
    # Normal moves
    "Tackle": {"name": "Tackle", "type": "Normal", "power": 40, "accuracy": 100, "pp": 35, "max_pp": 35, "category": "physical"},
    "Scratch": {"name": "Scratch", "type": "Normal", "power": 40, "accuracy": 100, "pp": 35, "max_pp": 35, "category": "physical"},
    "Pound": {"name": "Pound", "type": "Normal", "power": 40, "accuracy": 100, "pp": 35, "max_pp": 35, "category": "physical"},
    "Quick Attack": {"name": "Quick Attack", "type": "Normal", "power": 40, "accuracy": 100, "pp": 30, "max_pp": 30, "category": "physical"},
    "Slam": {"name": "Slam", "type": "Normal", "power": 80, "accuracy": 75, "pp": 20, "max_pp": 20, "category": "physical"},
    "Hyper Beam": {"name": "Hyper Beam", "type": "Normal", "power": 150, "accuracy": 90, "pp": 5, "max_pp": 5, "category": "special"},
    "Body Slam": {"name": "Body Slam", "type": "Normal", "power": 85, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    
    # Fire moves
    "Ember": {"name": "Ember", "type": "Fire", "power": 40, "accuracy": 100, "pp": 25, "max_pp": 25, "category": "special"},
    "Flamethrower": {"name": "Flamethrower", "type": "Fire", "power": 90, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "special"},
    "Fire Blast": {"name": "Fire Blast", "type": "Fire", "power": 110, "accuracy": 85, "pp": 5, "max_pp": 5, "category": "special"},
    "Fire Punch": {"name": "Fire Punch", "type": "Fire", "power": 75, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    "Fire Spin": {"name": "Fire Spin", "type": "Fire", "power": 35, "accuracy": 85, "pp": 15, "max_pp": 15, "category": "special"},
    
    # Water moves
    "Water Gun": {"name": "Water Gun", "type": "Water", "power": 40, "accuracy": 100, "pp": 25, "max_pp": 25, "category": "special"},
    "Bubble": {"name": "Bubble", "type": "Water", "power": 40, "accuracy": 100, "pp": 30, "max_pp": 30, "category": "special"},
    "Hydro Pump": {"name": "Hydro Pump", "type": "Water", "power": 110, "accuracy": 80, "pp": 5, "max_pp": 5, "category": "special"},
    "Surf": {"name": "Surf", "type": "Water", "power": 90, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "special"},
    "Aqua Tail": {"name": "Aqua Tail", "type": "Water", "power": 90, "accuracy": 90, "pp": 10, "max_pp": 10, "category": "physical"},
    "Withdraw": {"name": "Withdraw", "type": "Water", "power": 0, "accuracy": 100, "pp": 40, "max_pp": 40, "category": "status", "effect": "defense_up"},
    
    # Electric moves
    "Thunder Shock": {"name": "Thunder Shock", "type": "Electric", "power": 40, "accuracy": 100, "pp": 30, "max_pp": 30, "category": "special"},
    "Thunderbolt": {"name": "Thunderbolt", "type": "Electric", "power": 90, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "special"},
    "Thunder": {"name": "Thunder", "type": "Electric", "power": 110, "accuracy": 70, "pp": 10, "max_pp": 10, "category": "special"},
    "Thunder Wave": {"name": "Thunder Wave", "type": "Electric", "power": 0, "accuracy": 90, "pp": 20, "max_pp": 20, "category": "status", "effect": "paralyze"},
    "Volt Tackle": {"name": "Volt Tackle", "type": "Electric", "power": 120, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    
    # Grass moves
    "Vine Whip": {"name": "Vine Whip", "type": "Grass", "power": 45, "accuracy": 100, "pp": 25, "max_pp": 25, "category": "physical"},
    "Razor Leaf": {"name": "Razor Leaf", "type": "Grass", "power": 55, "accuracy": 95, "pp": 25, "max_pp": 25, "category": "physical"},
    "Solar Beam": {"name": "Solar Beam", "type": "Grass", "power": 120, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    "Leaf Storm": {"name": "Leaf Storm", "type": "Grass", "power": 130, "accuracy": 90, "pp": 5, "max_pp": 5, "category": "special"},
    "Leech Seed": {"name": "Leech Seed", "type": "Grass", "power": 0, "accuracy": 90, "pp": 10, "max_pp": 10, "category": "status", "effect": "leech"},
    
    # Ice moves
    "Ice Beam": {"name": "Ice Beam", "type": "Ice", "power": 90, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    "Blizzard": {"name": "Blizzard", "type": "Ice", "power": 110, "accuracy": 70, "pp": 5, "max_pp": 5, "category": "special"},
    "Ice Punch": {"name": "Ice Punch", "type": "Ice", "power": 75, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    
    # Fighting moves
    "Karate Chop": {"name": "Karate Chop", "type": "Fighting", "power": 50, "accuracy": 100, "pp": 25, "max_pp": 25, "category": "physical"},
    "Low Kick": {"name": "Low Kick", "type": "Fighting", "power": 50, "accuracy": 100, "pp": 20, "max_pp": 20, "category": "physical"},
    "Brick Break": {"name": "Brick Break", "type": "Fighting", "power": 75, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    "Close Combat": {"name": "Close Combat", "type": "Fighting", "power": 120, "accuracy": 100, "pp": 5, "max_pp": 5, "category": "physical"},
    
    # Poison moves
    "Poison Sting": {"name": "Poison Sting", "type": "Poison", "power": 15, "accuracy": 100, "pp": 35, "max_pp": 35, "category": "physical"},
    "Sludge Bomb": {"name": "Sludge Bomb", "type": "Poison", "power": 90, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    "Toxic": {"name": "Toxic", "type": "Poison", "power": 0, "accuracy": 90, "pp": 10, "max_pp": 10, "category": "status", "effect": "poison"},
    
    # Ground moves
    "Earthquake": {"name": "Earthquake", "type": "Ground", "power": 100, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "physical"},
    "Dig": {"name": "Dig", "type": "Ground", "power": 80, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "physical"},
    "Mud Slap": {"name": "Mud Slap", "type": "Ground", "power": 20, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    
    # Flying moves
    "Gust": {"name": "Gust", "type": "Flying", "power": 40, "accuracy": 100, "pp": 35, "max_pp": 35, "category": "special"},
    "Wing Attack": {"name": "Wing Attack", "type": "Flying", "power": 60, "accuracy": 100, "pp": 35, "max_pp": 35, "category": "physical"},
    "Fly": {"name": "Fly", "type": "Flying", "power": 90, "accuracy": 95, "pp": 15, "max_pp": 15, "category": "physical"},
    "Hurricane": {"name": "Hurricane", "type": "Flying", "power": 110, "accuracy": 70, "pp": 10, "max_pp": 10, "category": "special"},
    
    # Psychic moves
    "Confusion": {"name": "Confusion", "type": "Psychic", "power": 50, "accuracy": 100, "pp": 25, "max_pp": 25, "category": "special"},
    "Psychic": {"name": "Psychic", "type": "Psychic", "power": 90, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    "Dream Eater": {"name": "Dream Eater", "type": "Psychic", "power": 100, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "special"},
    
    # Ghost moves
    "Lick": {"name": "Lick", "type": "Ghost", "power": 30, "accuracy": 100, "pp": 30, "max_pp": 30, "category": "physical"},
    "Shadow Ball": {"name": "Shadow Ball", "type": "Ghost", "power": 80, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "special"},
    "Night Shade": {"name": "Night Shade", "type": "Ghost", "power": 50, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "special"},
    "Hex": {"name": "Hex", "type": "Ghost", "power": 65, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    
    # Dragon moves
    "Dragon Rage": {"name": "Dragon Rage", "type": "Dragon", "power": 40, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "special"},
    "Dragon Claw": {"name": "Dragon Claw", "type": "Dragon", "power": 80, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    "Outrage": {"name": "Outrage", "type": "Dragon", "power": 120, "accuracy": 100, "pp": 10, "max_pp": 10, "category": "physical"},
    "Draco Meteor": {"name": "Draco Meteor", "type": "Dragon", "power": 130, "accuracy": 90, "pp": 5, "max_pp": 5, "category": "special"},
    
    # Bug moves
    "Bug Bite": {"name": "Bug Bite", "type": "Bug", "power": 60, "accuracy": 100, "pp": 20, "max_pp": 20, "category": "physical"},
    "X-Scissor": {"name": "X-Scissor", "type": "Bug", "power": 80, "accuracy": 100, "pp": 15, "max_pp": 15, "category": "physical"},
    
    # Rock moves
    "Rock Throw": {"name": "Rock Throw", "type": "Rock", "power": 50, "accuracy": 90, "pp": 15, "max_pp": 15, "category": "physical"},
    "Rock Slide": {"name": "Rock Slide", "type": "Rock", "power": 75, "accuracy": 90, "pp": 10, "max_pp": 10, "category": "physical"},
    "Stone Edge": {"name": "Stone Edge", "type": "Rock", "power": 100, "accuracy": 80, "pp": 5, "max_pp": 5, "category": "physical"},
}


# Default moves for each Pokemon (up to 4 moves)
POKEMON_MOVES: dict[str, list[str]] = {
    # Fire starters
    "Charmander": ["Scratch", "Ember", "Tackle", "Fire Spin"],
    "Charmeleon": ["Scratch", "Flamethrower", "Slam", "Fire Spin"],
    "Charizard": ["Flamethrower", "Fire Blast", "Wing Attack", "Slam"],
    
    # Water starters
    "Squirtle": ["Tackle", "Water Gun", "Bubble", "Withdraw"],
    "Wartortle": ["Water Gun", "Aqua Tail", "Tackle", "Withdraw"],
    "Blastoise": ["Hydro Pump", "Surf", "Ice Beam", "Aqua Tail"],
    
    # Grass starters
    "Bulbasaur": ["Tackle", "Vine Whip", "Leech Seed", "Razor Leaf"],
    "Ivysaur": ["Vine Whip", "Razor Leaf", "Leech Seed", "Tackle"],
    "Venusaur": ["Solar Beam", "Leaf Storm", "Sludge Bomb", "Earthquake"],
    
    # Electric
    "Pikachu": ["Thunder Shock", "Quick Attack", "Thunderbolt", "Thunder Wave"],
    "Raichu": ["Thunderbolt", "Thunder", "Quick Attack", "Volt Tackle"],
    
    # Ghost
    "Gastly": ["Lick", "Night Shade", "Confusion", "Hex"],
    "Haunter": ["Shadow Ball", "Night Shade", "Dream Eater", "Hex"],
    "Gengar": ["Shadow Ball", "Sludge Bomb", "Dream Eater", "Psychic"],
    
    # Dragon
    "Dratini": ["Dragon Rage", "Tackle", "Thunder Wave", "Aqua Tail"],
    "Dragonair": ["Dragon Rage", "Slam", "Thunder Wave", "Aqua Tail"],
    "Dragonite": ["Outrage", "Draco Meteor", "Hurricane", "Fire Punch"],
}

# Fallback moves by element type
DEFAULT_MOVES_BY_TYPE: dict[str, list[str]] = {
    "Normal": ["Tackle", "Scratch", "Quick Attack", "Body Slam"],
    "Fire": ["Ember", "Flamethrower", "Tackle", "Fire Spin"],
    "Water": ["Water Gun", "Surf", "Tackle", "Aqua Tail"],
    "Electric": ["Thunder Shock", "Thunderbolt", "Quick Attack", "Thunder Wave"],
    "Grass": ["Vine Whip", "Razor Leaf", "Tackle", "Leech Seed"],
    "Ice": ["Ice Beam", "Blizzard", "Tackle", "Ice Punch"],
    "Fighting": ["Karate Chop", "Brick Break", "Low Kick", "Close Combat"],
    "Poison": ["Poison Sting", "Sludge Bomb", "Tackle", "Toxic"],
    "Ground": ["Earthquake", "Dig", "Tackle", "Mud Slap"],
    "Flying": ["Gust", "Wing Attack", "Fly", "Quick Attack"],
    "Psychic": ["Confusion", "Psychic", "Tackle", "Dream Eater"],
    "Bug": ["Bug Bite", "X-Scissor", "Tackle", "Quick Attack"],
    "Rock": ["Rock Throw", "Rock Slide", "Tackle", "Stone Edge"],
    "Ghost": ["Lick", "Shadow Ball", "Night Shade", "Hex"],
    "Dragon": ["Dragon Rage", "Dragon Claw", "Outrage", "Tackle"],
}


def get_pokemon_moves(monster: "Monster") -> list[Move]:
    """Get the moves for a Pokemon. Returns list of Move dicts with current PP."""
    name = monster.get("name", "")
    element = monster.get("element", "Normal")
    
    # Check if monster already has moves stored
    if "moves" in monster and monster["moves"]:
        return monster["moves"]
    
    # Get move names for this Pokemon
    if name in POKEMON_MOVES:
        move_names = POKEMON_MOVES[name]
    else:
        # Fallback to type-based moves
        move_names = DEFAULT_MOVES_BY_TYPE.get(element, DEFAULT_MOVES_BY_TYPE["Normal"])
    
    # Build move list with PP
    moves = []
    for move_name in move_names[:4]:  # Max 4 moves
        if move_name in MOVE_DATABASE:
            move = MOVE_DATABASE[move_name].copy()
            move["pp"] = move.get("max_pp", 10)  # Start with full PP
            moves.append(move)
    
    # Store moves on monster for persistence
    monster["moves"] = moves
    return moves


def get_move(move_name: str) -> Move | None:
    """Get a move from the database by name."""
    return MOVE_DATABASE.get(move_name)


# ============== END MOVE SYSTEM ==============


# Evolution data: pokemon_name -> (evolution_name, required_level, new_sprite_path)
EVOLUTION_DATA: dict[str, tuple[str, int, str]] = {
    # Fire line
    "Charmander": ("Charmeleon", 16, "menu_sprites/charmeleon.png"),
    "Charmeleon": ("Charizard", 36, "menu_sprites/charizard.png"),
    
    # Water line
    "Squirtle": ("Wartortle", 16, "menu_sprites/wartortle.png"),
    "Wartortle": ("Blastoise", 36, "menu_sprites/blastoise.png"),
    
    # Grass line
    "Bulbasaur": ("Ivysaur", 16, "menu_sprites/ivysaur.png"),
    "Ivysaur": ("Venusaur", 36, "menu_sprites/venusaur.png"),
    
    # Electric line
    "Pikachu": ("Raichu", 25, "menu_sprites/raichu.png"),
    
    # Ghost line
    "Gastly": ("Haunter", 25, "menu_sprites/haunter.png"),
    "Haunter": ("Gengar", 40, "menu_sprites/gengar.png"),
    
    # Dragon line
    "Dratini": ("Dragonair", 30, "menu_sprites/dragonair.png"),
    "Dragonair": ("Dragonite", 55, "menu_sprites/dragonite.png"),
}


def check_evolution(monster: "Monster") -> tuple[str, str] | None:
    """
    Check if a monster can evolve.
    Returns (new_name, new_sprite_path) if can evolve, None otherwise.
    """
    name = monster.get("name", "")
    level = monster.get("level", 1)
    
    if name in EVOLUTION_DATA:
        evolution_name, required_level, new_sprite = EVOLUTION_DATA[name]
        if level >= required_level:
            return (evolution_name, new_sprite)
    
    return None


def evolve_monster(monster: "Monster") -> bool:
    """
    Evolve a monster if possible.
    Returns True if evolution happened, False otherwise.
    """
    evolution = check_evolution(monster)
    if evolution:
        new_name, new_sprite = evolution
        old_name = monster["name"]
        
        # Update monster data
        monster["name"] = new_name
        monster["sprite_path"] = new_sprite
        
        # Boost stats on evolution
        monster["max_hp"] = int(monster["max_hp"] * 1.2)
        monster["hp"] = min(monster["hp"] + 20, monster["max_hp"])
        monster["attack"] = int(monster.get("attack", 10) * 1.15)
        monster["defense"] = int(monster.get("defense", 10) * 1.15)
        
        # Update moves for evolved form
        if new_name in POKEMON_MOVES:
            monster["moves"] = None  # Clear moves so they get reloaded
            get_pokemon_moves(monster)  # Reload with new moves
        
        return True
    return False


@dataclass
class Position:
    x: float
    y: float
    
    def copy(self):
        return Position(self.x, self.y)
        
    def distance_to(self, other: "Position") -> float:
        return ((self.x - other.x) ** 2 + (self.y - other.y) ** 2) ** 0.5
        
@dataclass
class PositionCamera:
    x: int
    y: int
    
    def copy(self):
        return PositionCamera(self.x, self.y)
        
    def to_tuple(self) -> tuple[int, int]:
        return (self.x, self.y)
        
    def transform_position(self, position: Position) -> tuple[int, int]:
        return (int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_position_as_position(self, position: Position) -> Position:
        return Position(int(position.x) - self.x, int(position.y) - self.y)
        
    def transform_rect(self, rect: Rect) -> Rect:
        return Rect(rect.x - self.x, rect.y - self.y, rect.width, rect.height)

@dataclass
class Teleport:
    pos: Position
    destination: str
    
    @overload
    def __init__(self, x: int, y: int, destination: str) -> None: ...
    @overload
    def __init__(self, pos: Position, destination: str) -> None: ...

    def __init__(self, *args, **kwargs):
        if isinstance(args[0], Position):
            self.pos = args[0]
            self.destination = args[1]
        else:
            x, y, dest = args
            self.pos = Position(x, y)
            self.destination = dest
    
    def to_dict(self):
        return {
            "x": self.pos.x // GameSettings.TILE_SIZE,
            "y": self.pos.y // GameSettings.TILE_SIZE,
            "destination": self.destination
        }
    
    @classmethod
    def from_dict(cls, data: dict):
        return cls(data["x"] * GameSettings.TILE_SIZE, data["y"] * GameSettings.TILE_SIZE, data["destination"])
    

class Monster(TypedDict, total=False):
    name: str
    hp: int
    max_hp: int
    level: int
    sprite_path: str
    attack: int
    defense: int
    element: str  # Element type (Fire, Water, Grass, etc.)
    moves: list[Move]  # Pokemon's moves
    xp: int  # Experience points


class Item(TypedDict):
    name: str
    count: int
    sprite_path: str