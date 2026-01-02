import time
import threading

from sx1262_constants import *
import lgpio


class SX1262Common:
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

        # Start internal IRQ polling loop (event-driven interface)
        self._start_recv_loop()

        return True

    def end(self):
        # Stop internal IRQ loop before shutting down hardware
        self._stop_recv_loop()

        self.sleep(SLEEP_COLD_START)
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
                return True
        return False

    def set_fallback_mode(self, fallback_mode):
        self.set_rx_tx_fallback_mode(fallback_mode)

    def get_mode(self) -> int:
        status = self.get_status()
        if status is None:
            return 0
        return status & 0x70

    # -------------------------------------------------------------------------
    # Internal IRQ polling loop -> emits events via SX1262Interrupt._handle_irq
    # -------------------------------------------------------------------------

    def _start_recv_loop(self, interval: float = 0.01):
        """
        Start a background thread that polls get_irq_status() and dispatches
        events via _handle_irq(). Safe to call multiple times.
        """
        if getattr(self, "_recv_thread", None) and getattr(
            self, "_recv_running", False
        ):
            return

        self._recv_interval = interval
        self._recv_running = True

        def loop():
            while self._recv_running:
                irq = self.get_irq_status()
                if irq:
                    # Let SX1262Interrupt decode and emit events
                    self._handle_irq(irq)
                time.sleep(self._recv_interval)

        self._recv_thread = threading.Thread(target=loop, daemon=True)
        self._recv_thread.start()

    def _stop_recv_loop(self):
        """
        Stop the background IRQ polling loop.
        """
        if not getattr(self, "_recv_running", False):
            return

        self._recv_running = False
        # Thread is daemon=True; we don't strictly need to join here.
        self._recv_thread = None
