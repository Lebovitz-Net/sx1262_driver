#!/usr/bin/env python3
import time
import threading
import time
from sx1262_constants import *
from sx1262 import SX1262 as SX126x # adjust if your driver file has a different name

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



def start_background_rssi(driver, interval=5):
    """
    driver.get_rssi_inst() must return instantaneous RSSI in dBm.
    Runs forever in a daemon thread.
    """
    def loop():
        while True:
            try:
                rssi = driver.rssiInst()
                print("RSSI:", rssi)
                # Flush the SPI bus with a dummy transaction
                resp = driver.getMode()
                print("Raw GET_STATUS bytes:", hex(resp))


            except Exception as e:
                print("RSSI monitor error:", e)
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()

def start_irq_polling(driver, interval=0.01):
    def loop():
        while True:
            irq = driver.getIrqStatus()

            if irq:
                # Let the driver decode the IRQ and call on_rx()
                driver._interruptRx(None)

            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()


def on_rx():
    """
    IRQ callback invoked by the driver when a packet is received.
    """
    status = radio.status()

    if status == STATUS_RX_DONE:
        available = radio.available()
        data = radio.get(available)

        rssi = radio.packetRssi()
        snr = radio.snr()

        print("\n--- PACKET RECEIVED ---")
        print(f"Bytes: {available}")
        print(f"Data:  {data.hex(' ')}")
        print(f"RSSI:  {rssi:.1f} dBm")
        print(f"SNR:   {snr:.1f} dB")
        print("------------------------")

    elif status == STATUS_CRC_ERR:
        print("CRC error")

    elif status == STATUS_HEADER_ERR:
        print("Header error")

    elif status == STATUS_RX_TIMEOUT:
        print("RX timeout (unexpected in continuous mode)")
    else:
        print("Nada")
    irq = radio.getIrqStatus()
    radio.clearIrqStatus(irq)



def main():
    global radio

    print("Initializing SX1262…")

    radio = SX126x()

    ok = radio.begin(
        bus=SPI_BUS,
        cs=SPI_DEV,
        reset=RESET_PIN,
        busy=BUSY_PIN,
        irq=-1,
        txen=-1,
        rxen=-1,
        wake=-1
    )

    if not ok:
        raise RuntimeError("SX1262 failed to enter STDBY_RC. Check BUSY, RESET, NSS wiring.")

    print("Configuring radio…")

    radio = lora  # or whatever the reference driver class is called

    # start_background_rssi(radio, interval=5)
    start_irq_polling(lora)



    # Frequency
    radio.setFrequency(FREQUENCY_HZ)

    # LoRa modulation
    radio.setLoRaModulation(
        sf=SPREADING_FACTOR,
        bw=BANDWIDTH_HZ,
        cr=CODING_RATE,
        ldro=False
    )

    # Packet parameters
    radio.setLoRaPacket(
        headerType=HEADER_EXPLICIT,
        preambleLength=PREAMBLE_LENGTH,
        payloadLength=PAYLOAD_LENGTH,
        crcType=CRC_ENABLED,
        invertIq=INVERT_IQ
    )

    # Optional: boosted gain
    radio.setRxGain(RX_GAIN_BOOSTED)

    # Register callback
    radio.onReceive(on_rx)

    print(f"Starting continuous receive at {FREQUENCY_HZ/1e6:.6f} MHz…")
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
