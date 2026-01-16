import time
import lgpio # type: ignore - pi only

from sx1262_constants import *


class SX1262Transmit:
    # TRANSMIT RELATED METHODS

    def send_packet(
        self,
        payload: bytes,
        tx_header_type=HEADER_IMPLICIT,
        tx_preamble_length=None,
        tx_crc_type=CRC_ON,
        tx_invert_iq=IQ_STANDARD,
        tx_payload_length=None,
    ):

        # --- 1. Save current RX/sniffer settings ---
        saved_header_type     = self._header_type
        saved_preamble_length = self._preamble_length
        saved_payload_length  = self._payload_length
        saved_crc_type        = self._crc_type
        saved_invert_iq       = self._invert_iq

        # --- 2. Determine TX parameters ---
        if tx_payload_length is None:
            tx_payload_length = len(payload)

        if tx_preamble_length is None:
            tx_preamble_length = saved_preamble_length  # usually 8 for MeshCore

        # --- 3. Apply TX settings ---
        self.set_lora_packet(
            header_type     = tx_header_type,
            preamble_length = tx_preamble_length,
            payload_length  = tx_payload_length,
            crc_type        = tx_crc_type,
            invert_iq       = tx_invert_iq,
        )

        # --- 4. Transmit ---
        self.begin_packet()
        self.write(payload)
        self.end_packet()

        # --- 5. Restore RX/sniffer settings ---
        self.set_lora_packet(
            header_type     = saved_header_type,
            preamble_length = saved_preamble_length,
            payload_length  = saved_payload_length,
            crc_type        = saved_crc_type,
            invert_iq       = saved_invert_iq,
        )

    def begin_packet(self):
        self._payload_tx_rx = 0
        self.set_buffer_base_address(
            self._buffer_index, (self._buffer_index + 0xFF) % 0xFF
        )

        if self._txen != -1:
            self._tx_state = lgpio.gpio_read(self.gpio_chip, self._txen)
            lgpio.gpio_write(self.gpio_chip, self._txen, 0)

        self._fix_lora_bw500(self._bw)

    def end_packet(self, timeout: int = TX_SINGLE) -> bool:
        if self.get_mode() == STATUS_MODE_TX:
            return False

        self._irq_setup(IRQ_TX_DONE | IRQ_TIMEOUT)

        self.set_packet_params_lora(
            self._preamble_length,
            self._header_type,
            self._payload_tx_rx,
            self._crc_type,
            self._invert_iq,
        )

        self._status_wait = STATUS_TX_WAIT
        self._status_irq = 0x0000

        tx_timeout = timeout << 6
        if tx_timeout > 0x00FFFFFF:
            tx_timeout = TX_SINGLE

        self.set_tx(tx_timeout)
        self._transmit_time = time.time()

        # IRQ callback wiring via lgpio alerts could be added here if desired
        return True

    def write(self, data, length: int = 0):
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
        if isinstance(data, (bytes, bytearray)):
            data_list = tuple(data)
            length = len(data_list)
        else:
            raise TypeError("input data must be bytes or bytearray")

        self.write_buffer(self._buffer_index, data_list, length)
        self._buffer_index = (self._buffer_index + length) % 256
        self._payload_tx_rx += length
