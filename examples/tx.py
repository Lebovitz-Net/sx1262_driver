#!/usr/bin/env python3
import time
from sx1262 import SX1262
from sx1262_constants import *

FREQ = 868_300_000

def main():
    radio = SX1262()

    # begin(bus, cs, reset, busy, irq, txen, rxen, wake)
    ok = radio.begin(
        bus=0,
        cs=0,
        reset=18,
        busy=20,
        irq=16,
        txen=6,
        rxen=-1,
        wake=-1
    )
    assert ok, "Failed to initialize SX1262"

    # RF switch on DIO2
    radio.set_dio2_rf_switch(True)

    # Frequency
    radio.set_frequency(FREQ)

    # TX power (5 dBm here)
    radio.set_tx_power(5, TX_POWER_SX1262)

    # LoRa modulation: SF7, BW 125 kHz, CR 4/5
    radio.set_lora_modulation(
        sf=7,
        bw=125_000,
        cr=5
    )

    # LoRa packet: explicit header, preamble=12, payload=255, CRC on
    radio.set_lora_packet(
        header_type=HEADER_EXPLICIT,
        preamble_length=12,
        payload_length=255,
        crc_type=True
    )

    # Sync word (public network)
    radio.set_sync_word(LORA_SYNC_WORD_PUBLIC)

    i = 0
    while True:
        payload = f"HeLoRa {i}".encode()

        radio.begin_packet()
        radio.put(payload)
        radio.end_packet(5000)
        radio.wait()

        print("TX:", payload)

        i += 1
        time.sleep(1.5)


if __name__ == "__main__":
    main()
