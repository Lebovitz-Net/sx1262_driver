"""
Internal utilities for the SX1262 driver.

Currently exposes:
- EventEmitter: async event dispatch system used by SX1262
"""

from .event_emitter import EventEmitter

__all__ = ["EventEmitter"]
