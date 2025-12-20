"""
PC Storage System - Stores Pokemon that don't fit in the party.
"""
from src.utils import Logger
from src.utils.definition import Monster


# Maximum Pokemon in party
MAX_PARTY_SIZE = 6

# Maximum Pokemon in PC (can be expanded)
MAX_PC_STORAGE = 120  # 4 boxes of 30


class PCStorage:
    """Manages Pokemon storage in the PC."""
    
    def __init__(self):
        self._stored_pokemon: list[Monster] = []
    
    @property
    def pokemon(self) -> list[Monster]:
        """Get all stored Pokemon."""
        return self._stored_pokemon
    
    def get_count(self) -> int:
        """Get number of Pokemon in storage."""
        return len(self._stored_pokemon)
    
    def is_full(self) -> bool:
        """Check if PC storage is full."""
        return len(self._stored_pokemon) >= MAX_PC_STORAGE
    
    def deposit(self, monster: Monster) -> bool:
        """
        Deposit a Pokemon into the PC.
        Returns True if successful, False if PC is full.
        """
        if self.is_full():
            Logger.warning("PC storage is full!")
            return False
        
        self._stored_pokemon.append(monster)
        Logger.info(f"Deposited {monster.get('name', 'Unknown')} to PC")
        return True
    
    def withdraw(self, index: int) -> Monster | None:
        """
        Withdraw a Pokemon from the PC by index.
        Returns the Pokemon if successful, None if index is invalid.
        """
        if index < 0 or index >= len(self._stored_pokemon):
            Logger.warning(f"Invalid PC index: {index}")
            return None
        
        monster = self._stored_pokemon.pop(index)
        Logger.info(f"Withdrew {monster.get('name', 'Unknown')} from PC")
        return monster
    
    def get_pokemon(self, index: int) -> Monster | None:
        """Get a Pokemon at index without removing it."""
        if index < 0 or index >= len(self._stored_pokemon):
            return None
        return self._stored_pokemon[index]
    
    def to_dict(self) -> dict:
        """Serialize PC storage."""
        return {
            "stored_pokemon": [dict(m) for m in self._stored_pokemon]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "PCStorage":
        """Deserialize PC storage."""
        storage = cls()
        stored = data.get("stored_pokemon", [])
        storage._stored_pokemon = [dict(m) for m in stored]
        return storage