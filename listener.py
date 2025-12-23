#!/usr/bin/env python3
import time
from SX126x import SX126x   # adjust if your driver file has a different name

# ------------------------------------------------------------
# Pin mapping (BCM) — confirmed by your continuity testing
# ------------------------------------------------------------
BUSY_PIN  = 20   # Physical Pin 38
IRQ_PIN   = 16   # Physical Pin 36 (DIO1)
RESET_PIN = 18   # Physical Pin 12
NSS_PIN   = 21   # Physical Pin 40 (manual CS)
SPI_BUS   = 0
SPI_DEV   = 0

# ------------------------------------------------------------
# Radio parameters
# ------------------------------------------------------------
FREQUENCY_HZ = 910_525_000   # 910.525 MHz
BANDWIDTH_HZ = 62_500        # 62.5 kHz
SPREADING_FACTOR = 7
CODING_RATE = 5              # 4/5
PREAMBLE_LENGTH = 12
PAYLOAD_LENGTH = 32
CRC_ENABLED = True
INVERT_IQ = False


def on_rx():
    """
    IRQ callback invoked by the driver when a packet is received.
    """
    status = lora.status()

    if status == lora.STATUS_RX_DONE:
        available = lora.available()
        data = lora.get(available)

        rssi = lora.packetRssi()
        snr = lora.snr()

        print("\n--- PACKET RECEIVED ---")
        print(f"Bytes: {available}")
        print(f"Data:  {data.hex(' ')}")
        print(f"RSSI:  {rssi:.1f} dBm")
        print(f"SNR:   {snr:.1f} dB")
        print("------------------------")

    elif status == lora.STATUS_CRC_ERR:
        print("CRC error")

    elif status == lora.STATUS_HEADER_ERR:
        print("Header error")

    elif status == lora.STATUS_RX_TIMEOUT:
        print("RX timeout (unexpected in continuous mode)")


def main():
    global lora

    print("Initializing SX1262…")

    lora = SX126x()

    ok = lora.begin(
        bus=SPI_BUS,
        cs=SPI_DEV,
        reset=RESET_PIN,
        busy=BUSY_PIN,
        irq=IRQ_PIN,
        txen=-1,
        rxen=-1,
        wake=-1
    )

    if not ok:
        raise RuntimeError("SX1262 failed to enter STDBY_RC. Check BUSY, RESET, NSS wiring.")

    print("Configuring radio…")

    # Frequency
    lora.setFrequency(FREQUENCY_HZ)

    # LoRa modulation
    lora.setLoRaModulation(
        sf=SPREADING_FACTOR,
        bw=BANDWIDTH_HZ,
        cr=CODING_RATE,
        ldro=False
    )

    # Packet parameters
    lora.setLoRaPacket(
        headerType=lora.HEADER_EXPLICIT,
        preambleLength=PREAMBLE_LENGTH,
        payloadLength=PAYLOAD_LENGTH,
        crcType=CRC_ENABLED,
        invertIq=INVERT_IQ
    )

    # Optional: boosted gain
    lora.setRxGain(lora.RX_GAIN_BOOSTED)

    # Register callback
    lora.onReceive(on_rx)

    print(f"Starting continuous receive at {FREQUENCY_HZ/1e6:.6f} MHz…")
    print("Waiting for packets…")

    ok = lora.request(lora.RX_CONTINUOUS)
    if not ok:
        raise RuntimeError("Failed to enter RX_CONTINUOUS mode.")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down…")
        lora.end()


if __name__ == "__main__":
    main()
