import time
import lgpio

from sx1262_constants import *


class SX1262Receive:
    # ---------------------------------------------------------------------
    # RECEIVE REQUESTS
    # ---------------------------------------------------------------------

    def request(self, timeout: int = RX_SINGLE) -> bool:
        """
        Begin a receive operation (single-shot or continuous).
        IRQ events (rx_done, timeout, crc_error, header_error) will be emitted
        asynchronously by the internal recv_loop via _handle_irq().
        """
        # If already in RX mode, reject
        if self.get_mode() == STATUS_MODE_RX:
            return False

        # Configure IRQ mask for RX events
        self._irq_setup(IRQ_RX_DONE | IRQ_TIMEOUT | IRQ_HEADER_ERR | IRQ_CRC_ERR)

        # Update internal state
        self._status_wait = STATUS_RX_WAIT
        self._status_irq = 0x0000

        # Convert timeout to SX1262 units (timeout << 6)
        rx_timeout = timeout << 6

        # Clamp timeout to 24-bit range
        if rx_timeout > 0x00FFFFFF:
            rx_timeout = RX_SINGLE

        # Continuous RX mode
        if timeout == RX_CONTINUOUS:
            rx_timeout = RX_CONTINUOUS
            self._status_wait = STATUS_RX_CONTINUOUS

        # Handle TXEN pin if present
        if self._txen != -1:
            self._tx_state = lgpio.gpio_read(self.gpio_chip, self._txen)
            lgpio.gpio_write(self.gpio_chip, self._txen, 1)

        # Issue the RX command
        self.set_rx(rx_timeout)

        # No callbacks here — events will be emitted by _handle_irq()
        return True

    # ---------------------------------------------------------------------
    # DUTY-CYCLED LISTEN MODE
    # ---------------------------------------------------------------------

    def listen(self, rx_period: int, sleep_period: int) -> bool:
        """
        Begin duty-cycled RX (listen mode).
        IRQ events will be emitted asynchronously by the recv_loop.
        """
        if self.get_mode() == STATUS_MODE_RX:
            return False

        # Configure IRQ mask for RX events
        self._irq_setup(IRQ_RX_DONE | IRQ_TIMEOUT | IRQ_HEADER_ERR | IRQ_CRC_ERR)

        # Update internal state
        self._status_wait = STATUS_RX_WAIT
        self._status_irq = 0x0000

        # Convert to SX1262 units
        rx_period = rx_period << 6
        sleep_period = sleep_period << 6

        # Clamp to 24-bit range
        if rx_period > 0x00FFFFFF:
            rx_period = 0x00FFFFFF
        if sleep_period > 0x00FFFFFF:
            sleep_period = 0x00FFFFFF

        # Handle TXEN pin if present
        if self._txen != -1:
            self._tx_state = lgpio.gpio_read(self.gpio_chip, self._txen)
            lgpio.gpio_write(self.gpio_chip, self._txen, 1)

        # Issue the duty-cycle RX command
        self.set_rx_duty_cycle(rx_period, sleep_period)

        return True

    # ---------------------------------------------------------------------
    # BUFFER ACCESS HELPERS
    # ---------------------------------------------------------------------

    def available(self) -> int:
        """
        Return number of bytes available in the RX buffer.
        """
        return self._payload_tx_rx

    def read(self, length: int = 0):
        """
        Read 'length' bytes from the RX buffer.
        If length == 0, read a single byte.
        """
        single = False
        if length == 0:
            length = 1
            single = True

        buf = self.read_buffer(self._buffer_index, length)
        self._buffer_index = (self._buffer_index + length) % 256

        # Update remaining payload count
        if self._payload_tx_rx > length:
            self._payload_tx_rx -= length
        else:
            self._payload_tx_rx = 0

        return buf[0] if single else buf

    def get(self, length: int = 1) -> bytes:
        """
        Read 'length' bytes and return them as a bytes object.
        """
        buf = self.read_buffer(self._buffer_index, length)
        self._buffer_index = (self._buffer_index + length) % 256

        # Update remaining payload count
        if self._payload_tx_rx > length:
            self._payload_tx_rx -= length
        else:
            self._payload_tx_rx = 0

        return bytes(buf)

    def purge(self, length: int = 0):
        """
        Discard 'length' bytes from the RX buffer.
        """
        if self._buffer_index > length:
            self._payload_tx_rx -= length
        else:
            self._payload_tx_rx = 0

        self._buffer_index += self._payload_tx_rx
