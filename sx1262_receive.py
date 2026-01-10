import time
import lgpio

from sx1262_constants import *


class SX1262Receive:
    # RECEIVE RELATED METHODS

    def request(self, timeout: int = RX_SINGLE) -> bool:
        if self.get_mode() == STATUS_MODE_RX:
            return False

        self._irq_setup(IRQ_RX_DONE | IRQ_TIMEOUT | IRQ_HEADER_ERR | IRQ_CRC_ERR)

        self._status_wait = STATUS_RX_WAIT
        self._status_irq = 0x0000

        rx_timeout = timeout << 6
        if rx_timeout > 0x00FFFFFF:
            rx_timeout = RX_SINGLE
        if timeout == RX_CONTINUOUS:
            rx_timeout = RX_CONTINUOUS
            self._status_wait = STATUS_RX_CONTINUOUS

        if self._txen != -1:
            self._tx_state = lgpio.gpio_read(self.gpio_chip, self._txen)
            lgpio.gpio_write(self.gpio_chip, self._txen, 1)

        self.set_rx(rx_timeout)

        # NOTE: RPi.GPIO event callbacks removed; if you want
        # lgpio alert-based handling, we can add a small helper
        # thread to poll gpio_read_event() and call _interrupt_rx*
        return True

    def listen(self, rx_period: int, sleep_period: int) -> bool:
        if self.get_mode() == STATUS_MODE_RX:
            return False

        self._irq_setup(IRQ_RX_DONE | IRQ_TIMEOUT | IRQ_HEADER_ERR | IRQ_CRC_ERR)

        self._status_wait = STATUS_RX_WAIT
        self._status_irq = 0x0000

        rx_period = rx_period << 6
        sleep_period = sleep_period << 6

        if rx_period > 0x00FFFFFF:
            rx_period = 0x00FFFFFF
        if sleep_period > 0x00FFFFFF:
            sleep_period = 0x00FFFFFF

        if self._txen != -1:
            self._tx_state = lgpio.gpio_read(self.gpio_chip, self._txen)
            lgpio.gpio_write(self.gpio_chip, self._txen, 1)

        self.set_rx_duty_cycle(rx_period, sleep_period)

        return True

    def available(self) -> int:
        return self._payload_tx_rx

    def read(self, length: int = 0):
        single = False
        if length == 0:
            length = 1
            single = True

        buf = self.read_buffer(self._buffer_index, length)
        self._buffer_index = (self._buffer_index + length) % 256

        if self._payload_tx_rx > length:
            self._payload_tx_rx -= length
        else:
            self._payload_tx_rx = 0

        if single:
            return buf[0]
        return buf

    def get(self, length: int = 1) -> bytes:
        buf = self.read_buffer(self._buffer_index, length)
        self._buffer_index = (self._buffer_index + length) % 256

        if self._payload_tx_rx > length:
            self._payload_tx_rx -= length
        else:
            self._payload_tx_rx = 0

        return bytes(buf)

    def purge(self, length: int = 0):
        if self._buffer_index > length:
            self._payload_tx_rx = self._payload_tx_rx - length
        else:
            self._payload_tx_rx = 0
        self._buffer_index += self._payload_tx_rx
