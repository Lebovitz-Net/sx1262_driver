#!/usr/bin/env python3
import time

from sx1262_driver import SX1262
from sx1262_driver import *   # brings in LORA_SYNC_WORD_PUBLIC, HEADER_EXPLICIT, TX_SINGLE, etc.

# ------------------------------------------------------------
# Pin mapping (BCM)
# ------------------------------------------------------------
BUSY_PIN = 20
RESET_PIN = 18
NSS_PIN = 21
SPI_BUS = 0
SPI_DEV = 0

# ------------------------------------------------------------
# Radio parameters
# ------------------------------------------------------------
FREQUENCY_HZ = 910_525_000
BANDWIDTH_HZ = 62_500
SPREADING_FACTOR = 7
CODING_RATE = 5
PREAMBLE_LENGTH = 12
PAYLOAD_LENGTH = 32
CRC_ENABLED = True
INVERT_IQ = False

# ------------------------------------------------------------
# Event Handlers
# ------------------------------------------------------------

async def handle_tx_done(transmit_time=None, irq_status=None):
    print("\n--- TX COMPLETE ---")
    print(f"Transmit time: {transmit_time*1000:.2f} ms")
    print("-------------------")

async def handle_timeout(irq_status=None):
    print("TX timeout")

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    print("Initializing SX1262…")
    radio = SX1262()

    ok = radio.begin(
        bus=SPI_BUS,
        cs=SPI_DEV,
        reset=RESET_PIN,
        busy=BUSY_PIN,
        irq=-1,
        txen=-1,
        rxen=-1,
        wake=-1,
    )

    if not ok:
        raise RuntimeError("SX1262 failed to enter STDBY_RC. Check wiring.")

    print("Configuring radio…")

    radio.set_sync_word(LORA_SYNC_WORD_PUBLIC)

    radio.set_frequency(FREQUENCY_HZ)

    radio.set_lora_modulation(
        sf=SPREADING_FACTOR,
        bw=BANDWIDTH_HZ,
        cr=CODING_RATE,
        ldro=False,
    )

    radio.set_lora_packet(
        header_type=HEADER_EXPLICIT,
        preamble_length=PREAMBLE_LENGTH,
        payload_length=PAYLOAD_LENGTH,
        crc_type=CRC_ENABLED,
        invert_iq=INVERT_IQ,
    )

    radio.on("tx_done", handle_tx_done)
    radio.on("timeout", handle_timeout)

    print("Transmitting packet…")

    radio.begin_packet()
    radio.put(b"Hello from SX1262!")
    ok = radio.end_packet(TX_SINGLE)

    if not ok:
        raise RuntimeError("Failed to start TX")

    print("Packet sent, waiting for TX_DONE event…")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down…")
        radio.end()

if __name__ == "__main__":
    main()
