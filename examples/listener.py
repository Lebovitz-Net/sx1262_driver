#!/usr/bin/env python3
import time

from ..sx1262_driver import SX1262
from ..sx1262_driver import *   # brings in LORA_SYNC_WORD_PUBLIC, HEADER_EXPLICIT, TX_SINGLE, etc.

# ------------------------------------------------------------
# Pin mapping (BCM)
# ------------------------------------------------------------
BUSY_PIN = 20
IRQ_PIN = 16     # unused (driver uses internal polling)
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

async def handle_rx_done(payload_length=None, buffer_index=None, irq_status=None):
    data = radio.get(payload_length)
    rssi = radio.packet_rssi()
    snr = radio.snr()

    print("\n--- PACKET RECEIVED ---")
    print(f"Bytes: {payload_length}")
    print(f"Data:  {data.hex(' ')}")
    print(f"RSSI:  {rssi:.1f} dBm")
    print(f"SNR:   {snr:.1f} dB")
    print("------------------------")


async def handle_crc_error(irq_status=None):
    print("CRC error")


async def handle_header_error(irq_status=None):
    print("Header error")


async def handle_timeout(irq_status=None):
    print("RX timeout (unexpected in continuous mode)")


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    global radio

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

    # Sync word
    radio.set_sync_word(LORA_SYNC_WORD_PUBLIC)

    # Frequency
    radio.set_frequency(FREQUENCY_HZ)

    # LoRa modulation
    radio.set_lora_modulation(
        sf=SPREADING_FACTOR,
        bw=BANDWIDTH_HZ,
        cr=CODING_RATE,
        ldro=False,
    )

    # Packet parameters
    radio.set_lora_packet(
        header_type=HEADER_EXPLICIT,
        preamble_length=PREAMBLE_LENGTH,
        payload_length=PAYLOAD_LENGTH,
        crc_type=CRC_ENABLED,
        invert_iq=INVERT_IQ,
    )

    # Optional: boosted gain
    radio.set_rx_gain(RX_GAIN_BOOSTED)

    # --------------------------------------------------------
    # Register event handlers
    # --------------------------------------------------------
    radio.on("rx_done", handle_rx_done)
    radio.on("crc_error", handle_crc_error)
    radio.on("header_error", handle_header_error)
    radio.on("timeout", handle_timeout)

    print(f"Starting continuous receive at {FREQUENCY_HZ/1e6:.6f} MHz BW {BANDWIDTH_HZ} SF {SPREADING_FACTOR} CR {CODING_RATE}")
    print("Waiting for packets…")

    ok = radio.request(RX_CONTINUOUS)
    if not ok:
        raise RuntimeError("Failed to enter RX_CONTINUOUS mode.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down…")
        radio.end()


if __name__ == "__main__":
    main()
