# src/core/event_emitter.py

import asyncio
import threading
from collections import defaultdict
from typing import Callable, Dict, List
import traceback

class EventEmitter:
    def __init__(self):
        super().__init__()
        self._event_listeners: Dict[str, List[dict]] = defaultdict(list)
        self._lock = threading.Lock()
        self._owned_loop = False

        try:
            # Preferred: running loop if inside async context
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop — create one and run it in a background daemon thread
            self._loop = asyncio.new_event_loop()
            self._owned_loop = True
            t = threading.Thread(target=self._loop.run_forever, daemon=True)
            t.start()

        # Track the thread ID that owns this loop
        self._loop_thread_id = getattr(self._loop, "_thread_id", threading.get_ident())

    def on(self, event: str, callback: Callable):
        with self._lock:
            if not any(cb["callback"] == callback for cb in self._event_listeners[event]):
                self._event_listeners[event].append({"type": "on", "callback": callback})

    def once(self, event: str, callback: Callable):
        with self._lock:
            if not any(cb["callback"] == callback for cb in self._event_listeners[event]):
                self._event_listeners[event].append({"type": "once", "callback": callback})

    def off(self, event: str, callback: Callable):
        with self._lock:
            if event in self._event_listeners:
                self._event_listeners[event] = [
                    entry for entry in self._event_listeners[event]
                    if entry["callback"] != callback
                ]

    def emit(self, event: str, *args, **kwargs):
        with self._lock:
            listeners = list(self._event_listeners.get(event, []))

            # Remove once-listeners BEFORE invoking callbacks
            for entry in listeners:
                if entry["type"] == "once":
                    self._event_listeners[event].remove(entry)

        for entry in listeners:
            coro = self._safe_invoke(entry["callback"], *args, **kwargs)
            asyncio.run_coroutine_threadsafe(coro, self._loop)


    async def _safe_invoke(self, callback: Callable, *args, **kwargs):
        try:
            result = callback(*args, **kwargs)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            print(f"[EventEmitter] Error in event callback: {e} {e.args}")
