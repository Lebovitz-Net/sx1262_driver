# SX1262Interface.py
#
# Place this file (or a symlink to it) in ~/.reticulum/interfaces/
# so Reticulum can load the SX1262 interface from the config file.
#
# Symlink setup on Pi:
#   ln -s ~/Projects/sx1262_driver/examples/SX1262Interface.py \
#         ~/.reticulum/interfaces/SX1262Interface.py
#
# Then in ~/.reticulum/config:
#
#   [[SX1262 LoRa Interface]]
#     type = SX1262Interface
#     enabled = yes
#     name = sx1262_lora
#     frequency = 914875000
#     bandwidth = 125000
#     spreading_factor = 9
#     coding_rate = 5
#     sync_word = 0x1424
#     preamble_length = 18
#     spi_bus = 0
#     spi_device = 0
#     reset_pin = 18
#     busy_pin = 20
#     irq_pin = -1
#     nss_pin = 21
#     use_irq = false

import sys
import os

from sx1262_driver.reticulum_interface import SX1262Interface

interface_class = SX1262Interface
