import threading
import time
import copy
from dataclasses import dataclass, field
from typing import Dict, Optional, List

TIMEOUT_TIME = 60.0
CHECK_INTERVAL_TIME = 5.0  # Reduced from 10.0
MAX_CHAT_MESSAGES = 4


@dataclass
class ChatMessage:
    from_id: int
    from_name: str
    text: str
    timestamp: float


@dataclass
class Player:
    id: int
    x: float
    y: float
    map: str
    last_update: float
    direction: str = "down"
    is_moving: bool = False

    def update(self, x: float, y: float, map: str, direction: str = "down", is_moving: bool = False) -> None:
        if x != self.x or y != self.y or map != self.map:
            self.last_update = time.monotonic()
        self.x = x
        self.y = y
        self.map = map
        self.direction = direction
        self.is_moving = is_moving

    def is_inactive(self) -> bool:
        now = time.monotonic()
        return (now - self.last_update) >= TIMEOUT_TIME


class PlayerHandler:
    _lock: threading.Lock
    _stop_event: threading.Event
    _thread: threading.Thread | None
    
    players: Dict[int, Player]
    _next_id: int
    
    _chat_messages: List[ChatMessage]
    _chat_lock: threading.Lock

    def __init__(self, *, timeout_seconds: float = 120.0, check_interval_seconds: float = 5.0):
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None
        
        self.players = {}
        self._next_id = 0
        
        self._chat_messages = []
        self._chat_lock = threading.Lock()
        
    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._cleaner, name="PlayerCleaner", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def _cleaner(self) -> None:
        while not self._stop_event.wait(CHECK_INTERVAL_TIME):
            now = time.monotonic()
            to_remove: list[int] = []
            with self._lock:
                for pid, p in list(self.players.items()):
                    if now - p.last_update >= TIMEOUT_TIME:
                        to_remove.append(pid)
                for pid in to_remove:
                    _ = self.players.pop(pid, None)
                    print(f"[PlayerHandler] Removed inactive player {pid}")
                    
    def register(self) -> int:
        with self._lock:
            pid = self._next_id
            self._next_id += 1
            self.players[pid] = Player(pid, 0.0, 0.0, "", time.monotonic())
            print(f"[PlayerHandler] Registered player {pid}")
            return pid

    def unregister(self, pid: int) -> bool:
        """Remove a player immediately."""
        with self._lock:
            if pid in self.players:
                del self.players[pid]
                print(f"[PlayerHandler] Unregistered player {pid}")
                return True
            return False

    def update(self, pid: int, x: float, y: float, map_name: str, 
               direction: str = "down", is_moving: bool = False) -> bool:
        with self._lock:
            p = self.players.get(pid)
            if not p:
                return False
            else:
                p.update(float(x), float(y), str(map_name), direction, is_moving)
                return True

    def list_players(self) -> dict:
        with self._lock:
            player_list = {}
            for p in self.players.values():
                player_list[p.id] = {
                    "id": p.id,
                    "x": p.x,
                    "y": p.y,
                    "map": p.map,
                    "direction": p.direction,
                    "is_moving": p.is_moving
                }
            return player_list

    def send_chat(self, pid: int, text: str) -> bool:
        """Send a chat message from a player."""
        with self._lock:
            p = self.players.get(pid)
            if not p:
                return False
            player_name = f"Player{pid}"
        
        with self._chat_lock:
            msg = ChatMessage(
                from_id=pid,
                from_name=player_name,
                text=text,
                timestamp=time.monotonic()
            )
            self._chat_messages.append(msg)
            if len(self._chat_messages) > MAX_CHAT_MESSAGES:
                self._chat_messages = self._chat_messages[-MAX_CHAT_MESSAGES:]
        return True

    def get_chat_messages(self, count: int = 10) -> list:
        """Get the last N chat messages."""
        with self._chat_lock:
            messages = self._chat_messages[-count:]
            return [
                {
                    "from": msg.from_name,
                    "text": msg.text,
                    "timestamp": msg.timestamp
                }
                for msg in messages
            ]