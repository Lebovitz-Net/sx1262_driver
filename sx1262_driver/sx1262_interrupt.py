import time
import threading

from .sx1262_constants import *

class SX1262Interrupt:
    def __init__(self):
        super().__init__()
        self._recv_thread =  None
        self._recv_running = False
        
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

    def _interrupt_tx(self, irq, _channel=None):
        """
        Internal TX-done handler. Called from _handle_irq().
        Restores TXEN and emits a 'tx_done' event.
        """
        self._transmit_time = time.time() - self._transmit_time

        # restore TXEN
        if self._txen != -1:
            from lgpio import gpio_write
            gpio_write(self.gpio_chip, self._txen, self._tx_state)

        # EventEmitter: notify listeners
        # Transmit time in seconds, plus raw IRQ status for those who care.
        self.emit(
            "tx_done",
            transmit_time=self._transmit_time,
            irq_status=irq,
        )

    def _interrupt_rx(self, irq, _channel=None):
        """
        Internal RX handler for single-shot and timeout cases.
        Restores TXEN (if used), applies _fix_rx_timeout(), reads RX buffer
        status, and emits 'rx_done' (or error events via _handle_irq()).
        """
        if self._status_wait == STATUS_RX_CONTINUOUS:
            if self._txen != -1:
                from lgpio import gpio_write
                gpio_write(self.gpio_chip, self._txen, self._tx_state)

            # Apply RTC / timeout errata workaround
            self._fix_rx_timeout()

        (payload_length, buffer_index) = self.get_rx_buffer_status()
        print(f"got rx_done, buffer status payload lenght is {payload_length} buffer offset is {buffer_index} irq is {irq}")

        # EventEmitter: notify listeners of RX completion
        self.emit(
            "rx_done",
            payload_length,
            buffer_index,
            irq_status=irq
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
        print(".../handle_irq IRQ", hex(irq))
        self._status_irq = irq

        if (irq & 0x2000) and self._status_wait == STATUS_RX_CONTINUOUS:
            # (length, _) = self.get_rx_buffer_status()
            # _  = self.get(length)
            # self.clear_irq_status(irq)
            print(f".../handle_irq got startup IRQ, mode is {hex(self.get_mode_and_control())}")
            return
        
        # TX done
        if irq & IRQ_TX_DONE:
            self._interrupt_tx(irq)

        # RX done (single or continuous)
        if irq & IRQ_RX_DONE:
            self._interrupt_rx(irq)

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

   # -------------------------------------------------------------------------
    # Internal IRQ polling loop -> emits events via SX1262Interrupt._handle_irq
    # -------------------------------------------------------------------------

    def start_recv_loop(self, interval: float = 0.01):
        """
        Start a background thread that polls get_irq_status() and dispatches
        events via _handle_irq(). Safe to call multiple times.
        """
        if self._recv_thread and self._recv_running:
            return
        print("Initiating Recv Loop")
        self._recv_interval = interval
        self._recv_running = True


        def loop():
            print(f"Recv Loop Started {self._recv_running}")
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
        if not self._recv_running:
            return

        self._recv_running = False
        # Thread is daemon=True; we don't strictly need to join here.
        self._recv_thread = None
