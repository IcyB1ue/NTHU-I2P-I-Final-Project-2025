import requests
import threading
import time
from collections import deque
from src.utils import Logger, GameSettings


class RemotePlayer:
    """Represents another player - follows their path smoothly."""
    
    def __init__(self, data: dict):
        self.id = data.get("id", -1)
        self.map = data.get("map", "")
        self.direction = data.get("direction", "down")
        self.is_moving = data.get("is_moving", False)
        
        initial_x = float(data.get("x", 0))
        initial_y = float(data.get("y", 0))
        self.x = initial_x
        self.y = initial_y
        
        self.path: deque[tuple[float, float]] = deque(maxlen=50)
        
        # Movement speed (pixels per second) - adjust to match your game
        self.speed = 200.0
        
        self.last_received_x = initial_x
        self.last_received_y = initial_y
        
        self.currently_moving = False
        self.current_direction = "down"
        
    def update_from_server(self, data: dict):
        """Called when we receive new data from server."""
        new_x = float(data.get("x", self.x))
        new_y = float(data.get("y", self.y))
        
        dist_sq = (new_x - self.last_received_x) ** 2 + (new_y - self.last_received_y) ** 2
        if dist_sq > 1.0:
            self.path.append((new_x, new_y))
            self.last_received_x = new_x
            self.last_received_y = new_y
        
        self.map = data.get("map", self.map)
    
    def interpolate(self, dt: float):
        """Move along the path at consistent speed."""
        if len(self.path) == 0:
            self.currently_moving = False
            return
        
        self.currently_moving = True
        
        remaining_distance = self.speed * dt
        
        while remaining_distance > 0 and len(self.path) > 0:
            target_x, target_y = self.path[0]
            
            dx = target_x - self.x
            dy = target_y - self.y
            dist = (dx * dx + dy * dy) ** 0.5
            
            self._update_direction(dx, dy)
            
            if dist <= remaining_distance:
                self.x = target_x
                self.y = target_y
                remaining_distance -= dist
                self.path.popleft()
            else:
                ratio = remaining_distance / dist
                self.x += dx * ratio
                self.y += dy * ratio
                remaining_distance = 0
        
        if len(self.path) == 0:
            self.currently_moving = False
    
    def _update_direction(self, dx: float, dy: float):
        """Update direction based on movement delta."""
        if abs(dx) < 0.1 and abs(dy) < 0.1:
            return
        
        if abs(dx) > abs(dy):
            self.current_direction = "right" if dx > 0 else "left"
        else:
            self.current_direction = "down" if dy > 0 else "up"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "map": self.map,
            "direction": self.current_direction,
            "is_moving": self.currently_moving
        }


class OnlineManager:
    player_id: int
    
    _stop_event: threading.Event
    _lock: threading.Lock
    
    _remote_players: dict[int, RemotePlayer]
    
    _chat_messages: list[dict]
    _chat_lock: threading.Lock
    
    _pending_update: dict | None
    _update_lock: threading.Lock
    
    def __init__(self):
        self.base: str = GameSettings.ONLINE_SERVER_URL
        self.player_id = -1
        
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        
        self._remote_players = {}
        
        self._chat_messages = []
        self._chat_lock = threading.Lock()
        
        self._pending_update = None
        self._update_lock = threading.Lock()
        
        self._session = requests.Session()
        
        Logger.info("OnlineManager initialized")
        
    def enter(self):
        self.register()
        if self.player_id != -1:
            self.start()
        else:
            Logger.warning("OnlineManager: Failed to register, not starting polling")
            
    def exit(self):
        self._unregister()
        self.stop()
        self._session.close()
    
    def _unregister(self):
        """Tell the server we're disconnecting."""
        if self.player_id == -1:
            return
        
        try:
            url = f"{self.base}/unregister"
            body = {"id": self.player_id}
            self._session.post(url, json=body, timeout=1)
            Logger.info(f"Unregistered player {self.player_id}")
        except Exception as e:
            Logger.warning(f"Failed to unregister: {e}")
    
    def tick(self, dt: float):
        """Call this every frame to update movement."""
        # Copy player list to avoid holding lock during interpolation
        with self._lock:
            players = list(self._remote_players.values())
        
        for player in players:
            player.interpolate(dt)
        
    def get_list_players(self) -> list[dict]:
        with self._lock:
            return [p.to_dict() for p in self._remote_players.values()]

    def get_chat_messages(self, count: int = 20) -> list[dict]:
        with self._chat_lock:
            return list(self._chat_messages[-count:])

    def send_chat(self, text: str) -> bool:
        if self.player_id == -1:
            return False
        
        url = f"{self.base}/chat"
        body = {"id": self.player_id, "text": text}
        try:
            resp = self._session.post(url, json=body, timeout=1)
            if resp.status_code == 200:
                return True
            Logger.warning(f"Chat send failed: {resp.status_code} {resp.text}")
        except Exception as e:
            Logger.warning(f"Chat send error: {e}")
        return False

    def register(self):
        try:
            url = f"{self.base}/register"
            resp = self._session.get(url, timeout=5)
            resp.raise_for_status()
            data = resp.json()
            if resp.status_code == 200:
                self.player_id = data["id"]
                Logger.info(f"OnlineManager registered with id={self.player_id}")
            else:
                Logger.error(f"Registration failed: {data}")
        except Exception as e:
            Logger.warning(f"OnlineManager registration error: {e}")
            self.player_id = -1

    def update(self, x: float, y: float, map_name: str, 
               direction: str = "down", is_moving: bool = False) -> bool:
        if self.player_id == -1:
            return False
        
        with self._update_lock:
            self._pending_update = {
                "id": self.player_id,
                "x": x,
                "y": y,
                "map": map_name,
                "direction": direction,
                "is_moving": is_moving
            }
        return True

    def start(self) -> None:
        self._stop_event.clear()
        
        self._player_thread = threading.Thread(
            target=self._player_loop,
            name="OnlineManagerPlayers",
            daemon=True
        )
        self._send_thread = threading.Thread(
            target=self._send_loop,
            name="OnlineManagerSend",
            daemon=True
        )
        self._chat_thread = threading.Thread(
            target=self._chat_loop,
            name="OnlineManagerChat",
            daemon=True
        )
        
        self._player_thread.start()
        self._send_thread.start()
        self._chat_thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def _player_loop(self) -> None:
        while not self._stop_event.is_set():
            self._fetch_players()
            time.sleep(0.15)  # ~7 requests/second (was 0.05 = 20/s)

    def _send_loop(self) -> None:
        while not self._stop_event.is_set():
            self._send_pending_update()
            time.sleep(0.15)  # ~7 requests/second (was 0.05 = 20/s)

    def _chat_loop(self) -> None:
        while not self._stop_event.is_set():
            self._fetch_chat()
            time.sleep(1.0)

    def _send_pending_update(self) -> None:
        with self._update_lock:
            if self._pending_update is None:
                return
            body = self._pending_update
            self._pending_update = None
        
        try:
            url = f"{self.base}/players"
            resp = self._session.post(url, json=body, timeout=0.5)
            if resp.status_code == 404:
                Logger.warning("Player not found on server, re-registering...")
                self.register()
        except requests.exceptions.Timeout:
            pass  # Timeouts are expected, don't log
        except Exception as e:
            Logger.debug(f"Send update error: {e}")
            
    def _fetch_players(self) -> None:
        if self.player_id == -1:
            return
            
        try:
            url = f"{self.base}/players"
            resp = self._session.get(url, timeout=0.5)
            resp.raise_for_status()
            all_players = resp.json().get("players", {})

            pid = self.player_id
            
            with self._lock:
                seen_ids = set()
                for key, data in all_players.items():
                    player_id = int(key)
                    if player_id == pid:
                        continue
                    
                    seen_ids.add(player_id)
                    
                    if player_id in self._remote_players:
                        self._remote_players[player_id].update_from_server(data)
                    else:
                        self._remote_players[player_id] = RemotePlayer(data)
                
                to_remove = [p for p in self._remote_players if p not in seen_ids]
                for p in to_remove:
                    del self._remote_players[p]
                    
        except requests.exceptions.Timeout:
            pass  # Timeouts are expected, don't log
        except Exception as e:
            Logger.debug(f"Fetch players error: {e}")

    def _fetch_chat(self) -> None:
        if self.player_id == -1:
            return
        
        try:
            url = f"{self.base}/chat?count=20"
            resp = self._session.get(url, timeout=1)
            resp.raise_for_status()
            messages = resp.json().get("messages", [])
            with self._chat_lock:
                self._chat_messages = messages
        except requests.exceptions.Timeout:
            pass  # Timeouts are expected, don't log
        except Exception as e:
            Logger.debug(f"Fetch chat error: {e}")