#!/usr/bin/env python3
import threading
import time
import asyncio

from sx1262_driver.sx1262_constants import *
from sx1262_driver.sx1262 import SX1262 as SX126x  # adjust if your driver file has a different name

# ------------------------------------------------------------
# Pin mapping (BCM) — confirmed by your continuity testing
# ------------------------------------------------------------
BUSY_PIN = 20    # Physical Pin 38
IRQ_PIN = 16     # Physical Pin 36 (DIO1)  (unused here; we poll IRQ status)
RESET_PIN = 18   # Physical Pin 12
NSS_PIN = 21     # Physical Pin 40 (manual CS, mapped as CS_DEFINE in constants)
SPI_BUS = 0
SPI_DEV = 0

# ------------------------------------------------------------
# Radio parameters
# ------------------------------------------------------------
FREQUENCY_HZ = 910525000   # 910.525 MHz
BANDWIDTH_HZ = 62500        # 62.5 kHz
SPREADING_FACTOR = 7
CODING_RATE = 5              # 4/5
# PREAMBLE_LENGTH =8 
# PAYLOAD_LENGTH =256 
# CRC_ENABLED = True
# INVERT_IQ = False


def start_background_rssi(driver, interval=5):
    """
    driver.rssi_inst() returns instantaneous RSSI in dBm.
    Runs forever in a daemon thread.
    """

    def loop():
        while True:
            try:
                rssi = driver.rssi_inst()
                print("RSSI:", rssi)

                # Flush the SPI bus / status
                mode = driver.get_mode()
                print("Raw mode bits from GET_STATUS:", hex(mode) if mode is not None else "None")

            except Exception as e:
                print("RSSI monitor error:", e)
            time.sleep(interval)

    t = threading.Thread(target=loop, daemon=True)
    t.start()

_recv_thread = None
_recv_running = False

# def _start_recv_loop (driver, interval=0.01):
#     """
#     Poll the IRQ status register and, if non-zero, invoke
#     the driver's internal RX interrupt handler.
#     """
#     global _recv_thread, _recv_running

#     if _recv_thread and _recv_running:
#         return
    
#     _recv_running = True

#     def loop():
#         while _recv_running:
#             irq = driver.get_irq_status()
#             if irq:
#                 if driver._status_wait == STATUS_RX_CONTINUOUS:
#                     driver._interrupt_rx_continuous(None)
#                 else:
#                     driver._interrupt_rx(None)
#                 print(f"irq status is {hex(irq)} chip status is {driver.get_mode_and_status()}")
#             time.sleep(interval)

#     _recv_thread = threading.Thread(target=loop, daemon=True)
#     _recv_thread.start()

# def _stop_recv_loop(radio):
#     """
#     Stop the background IRQ polling loop.
#     """
#     global _recv_running, _recv_thread

#     if not _recv_running:
#         return

#     _recv_running = False
#     _recv_thread = None

# def on_rx():
#     """
#     RX callback invoked by the driver when a packet is received.
#     """
#     status = radio.status()

#     if status == STATUS_RX_DONE:
#         print("Packet received!")
#         # available = radio.available()
#         # data = radio.get(available)

#         # rssi = radio.packet_rssi()
#         # snr = radio.snr()

#         # print("\n--- PACKET RECEIVED ---")
#         # print(f"Bytes: {available}")
#         # print(f"Data:  {data.hex(' ')}")
#         # print(f"RSSI:  {rssi:.1f} dBm")
#         # print(f"SNR:   {snr:.1f} dB")
#         # print("------------------------")

#     elif status == STATUS_CRC_ERR:
#         print("CRC error")

#     elif status == STATUS_HEADER_ERR:
#         print("Header error")

#     elif status == STATUS_RX_TIMEOUT:
#         print("RX timeout (unexpected in continuous mode)")
#     else:
#         print("Nada")

#     irq = radio.get_irq_status()
#     radio.clear_irq_status(irq)

def handle_header_error(irq_status):
    print(f"Header error event: irq_status={hex(irq_status)}")

def handle_timeout(irq_status):
    print(f"Timeout event: irq_status={hex(irq_status)}")

def handle_crc_error(irq_status):
    print(f"CRC error event: irq_status={hex(irq_status)}")

def handle_rx_done(data, payload_length, buffer_index, irq_status):
    print(f"RX done event: payload_length={payload_length}, buffer_index={buffer_index}, irq_status={hex(irq_status)}")
    # data = radio.get(payload_length)

    rssi = radio.packet_rssi()
    snr = radio.snr()

    print("\n--- PACKET RECEIVED ---")
    print(f"Bytes: {payload_length}")
    print(f"Data:  {data.hex(' ')}")
    print(f"RSSI:  {rssi:.1f} dBm")
    print(f"SNR:   {snr:.1f} dB")
    print("------------------------")

async def main():
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
        wake=-1,
    )

    radio.on("rx_done", handle_rx_done)
    radio.on("header_error", handle_header_error)
    radio.on("timeout", handle_timeout)
    radio.on("crc_error", handle_crc_error)

    if not ok:
        raise RuntimeError("SX1262 failed to enter STDBY_RC. Check BUSY, RESET, NSS wiring.")

    print("Configuring radio…")

    # Optional: background RSSI monitor
    # start_background_rssi(radio, interval=5)

    # Poll IRQ status in a background thread instead of GPIO edge callbacks
    # radio._start_recv_loop()

    # Sync word (public network)
    radio.set_sync_word(LORA_SYNC_WORD_PRIVATE)

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
        crc_type=CRC_ON,
        invert_iq=IQ_STANDARD
    )

    # Optional: boosted gain
    radio.set_rx_gain(RX_GAIN_BOOSTED)

    # Register callback
    # radio.on_receive(on_rx)

    print(f"Starting continuous receive at {FREQUENCY_HZ/1e6:.6f} MHz…")
    print("Waiting for packets…")

    ok = radio.request(RX_CONTINUOUS)
    if not ok:
        raise RuntimeError("Failed to enter RX_CONTINUOUS mode.")

    try:
        print("starting program running")
        await asyncio.Event().wait()
    finally:
        # This ALWAYS runs, even on Ctrl+C
        print("Shutting down…")
        # radio._stop_recv_loop()
        radio.end() 

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Swallow the traceback so it looks clean
        pass
