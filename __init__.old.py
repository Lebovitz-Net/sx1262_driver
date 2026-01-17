"""
SX1262 LoRa driver (lgpio + spidev, snake_case API)

This package exposes:
- SX1262: the full radio driver class
- Constants from sx1262_constants
"""

from .sx1262 import SX1262

# Re-export constants so users can do:
#   from sx1262 import LORA_SYNC_WORD_PUBLIC, HEADER_EXPLICIT, ...
from .sx1262_constants import (
    # Sync words
    LORA_SYNC_WORD_PUBLIC,
    LORA_SYNC_WORD_PRIVATE,

    # Header modes
    HEADER_EXPLICIT,
    HEADER_IMPLICIT,

    # CRC
    CRC_ON,
    CRC_OFF,

    # IQ inversion
    IQ_STANDARD,
    IQ_INVERTED,

    # Modem types
    LORA_MODEM,
    FSK_MODEM,

    # RX gain
    RX_GAIN_POWER_SAVING,
    RX_GAIN_BOOSTED,

    # IRQ flags
    IRQ_TX_DONE,
    IRQ_RX_DONE,
    IRQ_PREAMBLE_DETECTED,
    IRQ_SYNC_WORD_VALID,
    IRQ_HEADER_VALID,
    IRQ_HEADER_ERR,
    IRQ_CRC_ERR,
    IRQ_CAD_DONE,
    IRQ_CAD_DETECTED,
    IRQ_TIMEOUT,
    IRQ_ALL,
    IRQ_NONE,

    # Status codes
    STATUS_DEFAULT,
    STATUS_TX_WAIT,
    STATUS_TX_TIMEOUT,
    STATUS_TX_DONE,
    STATUS_RX_WAIT,
    STATUS_RX_CONTINUOUS,
    STATUS_RX_TIMEOUT,
    STATUS_RX_DONE,
    STATUS_HEADER_ERR,
    STATUS_CRC_ERR,
    STATUS_CAD_WAIT,
    STATUS_CAD_DETECTED,
    STATUS_CAD_DONE,

    # Fallback modes
    FALLBACK_FS,
    FALLBACK_STDBY_XOSC,
    FALLBACK_STDBY_RC,

    # Power settings
    TX_POWER_SX1261,
    TX_POWER_SX1262,
    TX_POWER_SX1268,
)

__all__ = [
    "SX1262",

    # Constants
    "LORA_SYNC_WORD_PUBLIC",
    "LORA_SYNC_WORD_PRIVATE",
    "HEADER_EXPLICIT",
    "HEADER_IMPLICIT",
    "CRC_ON",
    "CRC_OFF",
    "IQ_STANDARD",
    "IQ_INVERTED",
    "LORA_MODEM",
    "FSK_MODEM",
    "RX_GAIN_POWER_SAVING",
    "RX_GAIN_BOOSTED",
    "IRQ_TX_DONE",
    "IRQ_RX_DONE",
    "IRQ_PREAMBLE_DETECTED",
    "IRQ_SYNC_WORD_VALID",
    "IRQ_HEADER_VALID",
    "IRQ_HEADER_ERR",
    "IRQ_CRC_ERR",
    "IRQ_CAD_DONE",
    "IRQ_CAD_DETECTED",
    "IRQ_TIMEOUT",
    "IRQ_ALL",
    "IRQ_NONE",
    "STATUS_DEFAULT",
    "STATUS_TX_WAIT",
    "STATUS_TX_TIMEOUT",
    "STATUS_TX_DONE",
    "STATUS_RX_WAIT",
    "STATUS_RX_CONTINUOUS",
    "STATUS_RX_TIMEOUT",
    "STATUS_RX_DONE",
    "STATUS_HEADER_ERR",
    "STATUS_CRC_ERR",
    "STATUS_CAD_WAIT",
    "STATUS_CAD_DETECTED",
    "STATUS_CAD_DONE",
    "FALLBACK_FS",
    "FALLBACK_STDBY_XOSC",
    "FALLBACK_STDBY_RC",
    "TX_POWER_SX1261",
    "TX_POWER_SX1262",
    "TX_POWER_SX1268",
]
