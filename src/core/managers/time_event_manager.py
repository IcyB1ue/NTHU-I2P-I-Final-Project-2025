import random
from typing import Callable, Optional
from src.utils import Logger

class TimeEvent:
    def __init__(self, event_id: str, 
                 start_hour: int, 
                 end_hour: int, 
                 probability: float,
                 on_start: Callable[[], None],
                 on_end: Optional[Callable[[], None]] = None,
                 on_update: Optional[Callable[[float], None]] = None,
                 description: str = ""):
        self.event_id = event_id
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.probability = probability
        self.on_start = on_start
        self.on_end = on_end
        self.on_update = on_update
        self.description = description
        
        self.is_active = False
        self.was_active_today = False  # Track if it already happened today (or rolled for today)
        self.rolled_today = False      # Track if we already rolled for this window

    def reset_daily(self):
        """Reset daily tracking flags."""
        self.was_active_today = False
        self.rolled_today = False
        self.is_active = False

class TimeEventManager:
    def __init__(self, game_scene):
        self.game_scene = game_scene
        self.events: list[TimeEvent] = []
        self.active_events: set[str] = set()
        self.last_hour = -1.0
        
    def add_event(self, event: TimeEvent):
        self.events.append(event)
        
    def update(self, current_time: float, dt: float):
        current_hour_int = int(current_time)
        
        # Check for daily reset (e.g. at midnight or 6 AM? Let's say midnight 00:00)
        # However, logic: if current time < last time, a new day started
        if current_time < self.last_hour:
             self._on_new_day()
             
        self.last_hour = current_time
        
        for event in self.events:
            # Check window
            in_window = False
            
            # Handle wrapping times (e.g. 22:00 to 02:00)
            if event.start_hour < event.end_hour:
                in_window = event.start_hour <= current_time < event.end_hour
            else:
                in_window = event.start_hour <= current_time or current_time < event.end_hour
                
            if in_window:
                # If entering window and haven't rolled yet
                if not event.rolled_today:
                    event.rolled_today = True
                    if random.random() < event.probability:
                        self._start_event(event)
                    else:
                        Logger.info(f"Event {event.event_id} skipped (rolled failure)")
                
                # Update if active
                if event.is_active and event.on_update:
                    event.on_update(dt)
            else:
                # Left window
                if event.is_active:
                    self._end_event(event)
                
                # If window passed and we never rolled (e.g. time skip), mark rolled so we don't weirdly trigger
                # Actually, wrap logic handles scheduling.
                # If we are strictly outside window, meaningful only if we were inside.
                pass

    def _start_event(self, event: TimeEvent):
        Logger.info(f"Starting Event: {event.event_id}")
        event.is_active = True
        self.active_events.add(event.event_id)
        if event.on_start:
            event.on_start()
            
        # Optional: Show notification via GameScene
        if event.description:
            self.game_scene.quest_ui.show_notification(event.description, duration=5.0)

    def _end_event(self, event: TimeEvent):
        Logger.info(f"Ending Event: {event.event_id}")
        event.is_active = False
        if event.event_id in self.active_events:
            self.active_events.remove(event.event_id)
        if event.on_end:
            event.on_end()

    def _on_new_day(self):
        Logger.info("New Day! Resetting events.")
        for event in self.events:
            event.reset_daily()
