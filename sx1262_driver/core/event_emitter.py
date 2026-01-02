# src/core/event_emitter.py

import asyncio
import threading
from collections import defaultdict
from typing import Callable, Dict, List

class EventEmitter:
    def __init__(self):
        super().__init__()
class EventEmitter:
    def __init__(self):
        self._loop = None
        self._loop_thread_id = None
        self._event_listeners = defaultdict(list)
        self._lock = threading.Lock()

    def attach_loop(self, loop):
        self._loop = loop
        self._loop_thread_id = getattr(loop, "_thread_id", threading.get_ident())

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

        current_thread_id = threading.get_ident()

        for entry in listeners:
            coro = self._safe_invoke(entry["callback"], *args, **kwargs)

            if current_thread_id != self._loop_thread_id:
                # print(f"[EventEmitter] Cross-thread emit detected for '{event}'")
                self._loop.call_soon_threadsafe(asyncio.create_task, coro)
            else:
                self._loop.create_task(coro)

            if entry["type"] == "once":
                self.off(event, entry["callback"])

    async def _safe_invoke(self, callback: Callable, *args, **kwargs):
        try:
            result = callback(*args, **kwargs)
            if asyncio.iscoroutine(result):
                await result
        except Exception as e:
            print(f"[EventEmitter] Error in event callback: {e}")
