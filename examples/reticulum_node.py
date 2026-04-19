"""
Reticulum node using the SX1262 LoRa interface.

Run this script on your Raspberry Pi instead of `rnsd` to start a Reticulum
node with the SX1262 radio as the transport interface.

Usage:
    python3 examples/reticulum_node.py

Adjust the pin and radio parameters below to match your hardware.
"""

import time
import RNS
from sx1262_driver.reticulum_interface import SX1262ReticulumInterface

# ---- Radio and GPIO configuration ----
# Adjust these to match your hardware wiring (BCM pin numbering)
CONFIG = {
    "name": "sx1262_lora",

    # LoRa radio parameters
    "frequency":        "910525000",    # Hz
    "bandwidth":        "62500",        # Hz
    "spreading_factor": "7",            # 7-12
    "coding_rate":      "5",            # 5-8 (meaning 4/5 ... 4/8)
    "sync_word":        "0x1424",       # 0x1424 = private/MeshCore, 0x3444 = public LoRaWAN

    # SPI
    "spi_bus":    "0",
    "spi_device": "0",

    # GPIO pins (BCM numbering)
    "reset_pin": "18",
    "busy_pin":  "20",
    "irq_pin":   "-1",   # -1 = polling mode; set to DIO1 BCM pin to enable IRQ
    "nss_pin":   "21",

    # Set use_irq = true and irq_pin to your DIO1 BCM pin to enable interrupt-driven RX
    "use_irq": "false",
}

def main():
    # Start Reticulum (reads ~/.reticulum/config for other interfaces if present)
    r = RNS.Reticulum()

    RNS.log("Starting SX1262 Reticulum node...", RNS.LOG_INFO)

    # Instantiate and register the SX1262 interface
    iface = SX1262ReticulumInterface(
        owner=RNS.Transport,
        configuration=CONFIG,
    )
    RNS.Transport.interfaces.append(iface)

    RNS.log(f"Interface online: {iface}", RNS.LOG_INFO)

    # Create a destination and announce to verify TX is working.
    # If TX succeeds you will see "SX1262 Interface: TX complete" in the log.
    identity = RNS.Identity()
    destination = RNS.Destination(
        identity,
        RNS.Destination.IN,
        RNS.Destination.SINGLE,
        "sx1262test",
        "node",
    )
    destination.announce()
    RNS.log(f"Announced as {RNS.prettyhexrep(destination.hash)}", RNS.LOG_INFO)

    RNS.log("Node running. Press Ctrl+C to stop.", RNS.LOG_INFO)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        RNS.log("Shutting down...", RNS.LOG_INFO)
        iface.detach()

if __name__ == "__main__":
    main()
