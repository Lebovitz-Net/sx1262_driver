import time
import lgpio

from sx1262_constants import *


class SX1262Transmit:
    # ---------------------------------------------------------------------
    # TRANSMIT RELATED METHODS
    # ---------------------------------------------------------------------

    def begin_packet(self):
        """
        Prepare the TX buffer for a new packet.
        No callbacks or IRQ logic here — TX completion will be emitted
        asynchronously by the internal recv_loop via _handle_irq().
        """
        # Reset payload counter
        self._payload_tx_rx = 0

        # Set TX and RX base addresses (TX at current index)
        self.set_buffer_base_address(
            self._buffer_index,
            (self._buffer_index + 0xFF) % 0xFF
        )

        # Handle TXEN pin if present
        if self._txen != -1:
            self._tx_state = lgpio.gpio_read(self.gpio_chip, self._txen)
            lgpio.gpio_write(self.gpio_chip, self._txen, 0)

        # Apply Semtech BW500 workaround if needed
        self._fix_lora_bw500(self._bw)

    def end_packet(self, timeout: int = TX_SINGLE) -> bool:
        """
        Finalize the packet and start transmission.
        TX completion will be delivered via the 'tx_done' event.
        """
        # If already transmitting, reject
        if self.get_mode() == STATUS_MODE_TX:
            return False

        # Configure IRQ mask for TX_DONE and TIMEOUT
        self._irq_setup(IRQ_TX_DONE | IRQ_TIMEOUT)

        # Update packet parameters (payload length, CRC, IQ, etc.)
        self.set_packet_params_lora(
            self._preamble_length,
            self._header_type,
            self._payload_tx_rx,
            self._crc_type,
            self._invert_iq,
        )

        # Update internal state
        self._status_wait = STATUS_TX_WAIT
        self._status_irq = 0x0000

        # Convert timeout to SX1262 units
        tx_timeout = timeout << 6
        if tx_timeout > 0x00FFFFFF:
            tx_timeout = TX_SINGLE

        # Start TX
        self.set_tx(tx_timeout)
        self._transmit_time = time.time()

        # No callbacks here — events will be emitted by _handle_irq()
        return True

    # ---------------------------------------------------------------------
    # BUFFER WRITE HELPERS
    # ---------------------------------------------------------------------

    def write(self, data, length: int = 0):
        """
        Write raw integers or tuples/lists of integers into the TX buffer.
        """
        if isinstance(data, (list, tuple)):
            if length == 0 or length > len(data):
                length = len(data)
        elif isinstance(data, (int, float)):
            length = 1
            data = (int(data),)
        else:
            raise TypeError("input data must be list, tuple, integer or float")

        self.write_buffer(self._buffer_index, data, length)
        self._buffer_index = (self._buffer_index + length) % 256
        self._payload_tx_rx += length

    def put(self, data):
        """
        Write a bytes or bytearray object into the TX buffer.
        """
        if isinstance(data, (bytes, bytearray)):
            data_list = tuple(data)
            length = len(data_list)
        else:
            raise TypeError("input data must be bytes or bytearray")

        self.write_buffer(self._buffer_index, data_list, length)
        self._buffer_index = (self._buffer_index + length) % 256
        self._payload_tx_rx += length
