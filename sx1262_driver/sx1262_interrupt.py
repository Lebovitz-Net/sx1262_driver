import time

from sx1262_constants import *


class SX1262Interrupt:
    # INTERRUPT HANDLER METHODS

    def _irq_setup(self, irq_mask):
        self.clear_irq_status(IRQ_ALL)

        dio1_mask = 0x0000
        dio2_mask = 0x0000
        dio3_mask = 0x0000

        if self._dio == 2:
            dio2_mask = irq_mask
        elif self._dio == 3:
            dio3_mask = irq_mask
        else:
            dio1_mask = irq_mask

        self.set_dio_irq_params(irq_mask, dio1_mask, dio2_mask, dio3_mask)

    def _interrupt_tx(self, _channel=None):
        """
        Internal TX-done handler. Called from _handle_irq().
        Restores TXEN and emits a 'tx_done' event.
        """
        self._transmit_time = time.time() - self._transmit_time

        # restore TXEN
        if self._txen != -1:
            from lgpio import gpio_write

            gpio_write(self.gpio_chip, self._txen, self._tx_state)

        # Cache IRQ status for legacy .status() path
        self._status_irq = self.get_irq_status()

        # EventEmitter: notify listeners
        # Transmit time in seconds, plus raw IRQ status for those who care.
        self.emit(
            "tx_done",
            transmit_time=self._transmit_time,
            irq_status=self._status_irq,
        )

    def _interrupt_rx(self, _channel=None):
        """
        Internal RX handler for single-shot and timeout cases.
        Restores TXEN (if used), applies _fix_rx_timeout(), reads RX buffer
        status, and emits 'rx_done' (or error events via _handle_irq()).
        """
        if self._txen != -1:
            from lgpio import gpio_write

            gpio_write(self.gpio_chip, self._txen, self._tx_state)

        # Apply RTC / timeout errata workaround
        self._fix_rx_timeout()

        # Cache IRQ status and RX buffer status
        self._status_irq = self.get_irq_status()
        (self._payload_tx_rx, self._buffer_index) = self.get_rx_buffer_status()

        # EventEmitter: notify listeners of RX completion
        self.emit(
            "rx_done",
            payload_length=self._payload_tx_rx,
            buffer_index=self._buffer_index,
            irq_status=self._status_irq,
        )

    def _interrupt_rx_continuous(self, _channel=None):
        """
        Internal RX handler for continuous mode; does not restore TXEN.
        """
        self._status_irq = self.get_irq_status()
        self.clear_irq_status(IRQ_ALL)
        (self._payload_tx_rx, self._buffer_index) = self.get_rx_buffer_status()

        self.emit(
            "rx_done",
            payload_length=self._payload_tx_rx,
            buffer_index=self._buffer_index,
            irq_status=self._status_irq,
        )

    # -------------------------------------------------------------------------
    # Central IRQ decoder used by the recv_loop in SX1262Common
    # -------------------------------------------------------------------------

    def _handle_irq(self, irq: int):
        """
        Decode IRQ bits and invoke internal handlers and/or emit events.
        This is called by the internal recv_loop.
        """
        # Keep legacy status() path in sync
        self._status_irq = irq

        # TX done
        if irq & IRQ_TX_DONE:
            self._interrupt_tx()

        # RX done (single or continuous)
        if irq & IRQ_RX_DONE:
            # Decide which RX path to use based on current status_wait
            if self._status_wait == STATUS_RX_CONTINUOUS:
                self._interrupt_rx_continuous()
            else:
                self._interrupt_rx()

        # Timeout
        if irq & IRQ_TIMEOUT:
            # Emit an explicit timeout event
            self.emit("timeout", irq_status=irq)

        # Header error
        if irq & IRQ_HEADER_ERR:
            self.emit("header_error", irq_status=irq)

        # CRC error
        if irq & IRQ_CRC_ERR:
            self.emit("crc_error", irq_status=irq)

        # CAD events (if/when you use them)
        if irq & IRQ_CAD_DETECTED:
            self.emit("cad_detected", irq_status=irq)
        if irq & IRQ_CAD_DONE:
            self.emit("cad_done", irq_status=irq)

        # Clear IRQs at the end to release the latch
        self.clear_irq_status(irq)

    # -------------------------------------------------------------------------
    # Back-compat helpers for existing callback-based code
    # -------------------------------------------------------------------------

    def on_transmit(self, callback):
        """
        Legacy callback registration. Internally registers a 'tx_done' listener.
        The callback is invoked with no arguments for back-compat.
        """
        if callback is None:
            return

        async def _wrapper(**kwargs):
            callback()

        self.on("tx_done", _wrapper)

    def on_receive(self, callback):
        """
        Legacy callback registration. Internally registers an 'rx_done' listener.
        The callback is invoked with no arguments for back-compat.
        """
        if callback is None:
            return

        async def _wrapper(**kwargs):
            callback()

        self.on("rx_done", _wrapper)
