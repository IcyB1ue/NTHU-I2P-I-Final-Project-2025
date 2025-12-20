from server.playerHandler import PlayerHandler

from http.server import BaseHTTPRequestHandler, HTTPServer
import json

PORT = 8989

PLAYER_HANDLER = PlayerHandler()
PLAYER_HANDLER.start()
    
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        return

    def do_GET(self):
        if self.path == "/":
            self._json(200, {"status": "ok"})
            return
            
        if self.path == "/register":
            pid = PLAYER_HANDLER.register()
            self._json(200, {"message": "registration successful", "id": pid})
            return

        if self.path == "/players":
            self._json(200, {"players": PLAYER_HANDLER.list_players()})
            return

        if self.path.startswith("/chat"):
            count = 20
            if "?" in self.path:
                query = self.path.split("?")[1]
                for param in query.split("&"):
                    if param.startswith("count="):
                        try:
                            count = int(param.split("=")[1])
                        except ValueError:
                            pass
            messages = PLAYER_HANDLER.get_chat_messages(count)
            self._json(200, {"messages": messages})
            return

        self._json(404, {"error": "not_found"})

    def do_POST(self):
        if self.path == "/players":
            self._handle_player_update()
            return
        
        if self.path == "/chat":
            self._handle_chat()
            return
        
        if self.path == "/unregister":
            self._handle_unregister()
            return

        self._json(404, {"error": "not_found"})

    def _handle_player_update(self):
        """Handle player position/state update."""
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid_json"})
            return

        missing = [k for k in ("id", "x", "y", "map") if k not in data]
        if missing:
            self._json(400, {"error": "bad_fields", "missing": missing})
            return

        try:
            pid = int(data["id"])
            x = float(data["x"])
            y = float(data["y"])
            map_name = str(data["map"])
            direction = str(data.get("direction", "down"))
            is_moving = bool(data.get("is_moving", False))
        except (ValueError, TypeError):
            self._json(400, {"error": "bad_fields"})
            return

        ok = PLAYER_HANDLER.update(pid, x, y, map_name, direction, is_moving)
        if not ok:
            self._json(404, {"error": "player_not_found"})
            return

        self._json(200, {"success": True})

    def _handle_chat(self):
        """Handle chat message send."""
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid_json"})
            return

        missing = [k for k in ("id", "text") if k not in data]
        if missing:
            self._json(400, {"error": "bad_fields", "missing": missing})
            return

        try:
            pid = int(data["id"])
            text = str(data["text"])[:200]
        except (ValueError, TypeError):
            self._json(400, {"error": "bad_fields"})
            return

        if not text.strip():
            self._json(400, {"error": "empty_message"})
            return

        ok = PLAYER_HANDLER.send_chat(pid, text.strip())
        if not ok:
            self._json(404, {"error": "player_not_found"})
            return

        self._json(200, {"success": True})

    def _handle_unregister(self):
        """Handle player disconnect."""
        length = int(self.headers.get("Content-Length", "0"))
        try:
            body = self.rfile.read(length)
            data = json.loads(body.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "invalid_json"})
            return

        if "id" not in data:
            self._json(400, {"error": "bad_fields", "missing": ["id"]})
            return

        try:
            pid = int(data["id"])
        except (ValueError, TypeError):
            self._json(400, {"error": "bad_fields"})
            return

        ok = PLAYER_HANDLER.unregister(pid)
        if not ok:
            self._json(404, {"error": "player_not_found"})
            return

        self._json(200, {"success": True})

    def _json(self, code: int, obj: object) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"[Server] Running on localhost with port {PORT}")
    HTTPServer(("0.0.0.0", PORT), Handler).serve_forever()