import time
import traceback

from .sx1262_constants import *

import lgpio # type: ignore - pi only


class SX1262Common:
    def __init__(self):
        super().__init__()

    def begin(
        self,
        bus: int = BUS,
        cs: int = CS,
        reset: int = RESET,
        busy: int = BUSY,
        irq: int = IRQ,
        txen: int = TXEN,
        rxen: int = RXEN,
        wake: int = WAKE,
    ) -> bool:
        print(f"pins: bus: {bus} cs:{cs} reset:{reset} irq:{irq} busy:{busy}")

        self.set_spi(bus, cs)
        self.set_pins(reset, busy, irq, txen, rxen, wake)

        self.reset()

        self.set_standby(STANDBY_RC)
        if self.get_mode() != STATUS_MODE_STDBY_RC:
            return False

        self.set_packet_type(LORA_MODEM)
        self._fix_resistance_antenna()
        self._start_recv_loop()
        return True

    def end(self):
        self.sleep(SLEEP_COLD_START)
        self._stop_recv_loop()
        self.spi.close()
        # close gpio chip handle
        lgpio.gpiochip_close(self.gpio_chip)

    def get_status(self):
        resp = self._read_bytes(0xC0, 1)
        if not resp:
            return None
        return resp[0]

    def reset(self) -> bool:
        lgpio.gpio_write(self.gpio_chip, self._reset, 0)
        time.sleep(0.001)
        lgpio.gpio_write(self.gpio_chip, self._reset, 1)
        return not self.busy_check()

    def sleep(self, option=SLEEP_WARM_START):
        self.standby()
        self.set_sleep(option)
        time.sleep(0.0005)

    def wake(self):
        if self._wake != -1:
            lgpio.gpio_claim_output(self.gpio_chip, self._wake)
            lgpio.gpio_write(self.gpio_chip, self._wake, 0)
            time.sleep(0.0005)

        self.set_standby(STANDBY_RC)
        self._fix_resistance_antenna()

    def standby(self, option=STANDBY_RC):
        self.set_standby(option)

    def busy_check(self, timeout: int = BUSY_TIMEOUT) -> bool:
        start = time.time()
        while lgpio.gpio_read(self.gpio_chip, self._busy) == 1:
            if (time.time() - start) > (timeout / 1000.0):
                print(f"busy_check return ... {self._busy} == 1")
                traceback.print_exc()
                return True
        return False

    def set_fallback_mode(self, fallback_mode):
        self.set_rx_tx_fallback_mode(fallback_mode)

    def get_mode(self) -> int:
        status = self.get_status()
        if status is None:
            return 0
        return status & 0x70

    def get_mode_and_status(self) -> int:
        status = self.get_status()
        if status is None:
            return 0
        return status & 0x7E
    
    def start(self, rx_timeout, interval=0.01):
        print(f"starting radio receive {hex(rx_timeout)} ms")
        # self._start_recv_loop(interval)
        ok = self.request(rx_timeout)
        if not ok:
            raise RuntimeError("Failed to enter RX mode.")
        return True

    def _fix_rx_timeout(self):
        # SX1262 errata §15.3 — RX timeout with implicit header mode.
        # After a timed-out RX in implicit header mode, the chip may fail to
        # return to its fallback state. The fix stops the internal RTC timer
        # and masks the RTC event immediately after the timeout IRQ fires.
        #
        # CONDITIONS REQUIRED before enabling:
        #   1. Using implicit header mode (set via set_packet_params with header=1)
        #   2. Using a finite SetRx timeout (not RX_CONTINUOUS = 0xFFFFFF)
        #
        # Currently not applicable — driver uses explicit header mode and
        # continuous RX. Implement when either condition above is added:
        #
        # self.write_register(0x0902, bytes([0x00]), 1)         # stop RTC timer
        # val = self.read_register(0x0944, 1)[0]
        # self.write_register(0x0944, bytes([val | 0x02]), 1)   # mask RTC event
        pass
    