import time
import threading

from sx1262_constants import *

class SX1262Interrupt:
    def __init__(self):
        super().__init__()
        self._recv_thread = None
        self._recv_running = False
        self._recv_stopped =  True
        self._recv_interval = None
        self._recv_data = None

    # INTERRUPT HANDLER METHODS
    # These are timing critical functions. Keep them lean.
    # Print statements will affect the timing and may cause missed IRQs.
    # Missed IRQs can lead to lockups in receive mode.

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
        self._transmit_time = time.time() - self._transmit_time

        # restore TXEN
        if self._txen != -1:
            from lgpio import gpio_write # type: ignore - pi only
            gpio_write(self.gpio_chip, self._txen, self._tx_state)

        if callable(self._on_transmit):
            self._on_transmit()

    def _interrupt_rx(self, irq, _channel=None):
        # not in continous mode
        if self._status_wait != STATUS_RX_CONTINUOUS:
            if self._txen != -1:
                from lgpio import gpio_write # type: ignore - pi only
                gpio_write(self.gpio_chip, self._txen, self._tx_state)

            self._fix_rx_timeout()
        
        # if self._status_wait == STATUS_RX_CONTINUOUS:
        #     self.clear_irq_status(IRQ_ALL)

        (payload_length, _) = self.get_rx_buffer_status()

        data = None

        if payload_length > 0:
            data = self.get(payload_length)
            
        self.emit(
            "rx_done",
            data=data,
            payload_length=payload_length,
            irq_status=irq
        )

        if callable(self._on_receive):
            self._on_receive()

    def on_transmit(self, callback):
        self._on_transmit = callback

    def on_receive(self, callback):
        self._on_receive = callback

    # -------------------------------------------------------------------------
    # Internal IRQ polling loop -> emits events via SX1262Interrupt._handle_irq
    # -------------------------------------------------------------------------

    def _start_recv_loop (self, interval=0.005):

        if self._recv_thread and self._recv_running:
            return
        print("starting recv loop")
        self._recv_interval = interval
        
        def loop():
            self._recv_running = True
            self._recv_stopped = False
            start = time.time()
            while self._recv_running:
                irq = self.get_irq_status()
                if irq:
                    self._handle_irq(irq, None)  # handle IRQ STATUS, read FIFO if RX_DONE
                    self.clear_irq_status(IRQ_ALL)
                # time.sleep(interval)
            if (time.time() - start) > (5):
                print(f"tick")
                start =  time.time()
            self._recv_stopped = True
            print("recv loop stopped")

        self._recv_thread = threading.Thread(target=loop, daemon=True)
        self._recv_thread.start()

    def _stop_recv_loop(self):
        """
        Stop the background IRQ polling loop.
        """

        if not self._recv_running:
            return
        
        self._recv_running = False
        
        while not self._recv_stopped:
            time.sleep(0.01)

        self._recv_thread = None

    # -------------------------------------------------------------------------
    # Central IRQ decoder used by the recv_loop in SX1262Common
    # -------------------------------------------------------------------------

    def _handle_irq(self, irq: int, _channel=None):
        """
        Decode IRQ bits and invoke internal handlers and/or emit events.
        This is called by the internal recv_loop.
        """
        # Keep legacy status() path in sync
        self._status_irq = irq

        error_status = (IRQ_HEADER_ERR | IRQ_CRC_ERR | IRQ_TIMEOUT) & 0xFFFF

        #---------------------------------------------------------------------
        # No errors: handle TX done, RX done, CAD events
        #---------------------------------------------------------------------

        if ((irq & error_status) == 0):     # TX done
            if irq & IRQ_TX_DONE:
                self._interrupt_tx(irq, _channel)

            # RX done (single or continuous)
            elif irq & IRQ_RX_DONE:
                self._interrupt_rx(irq, _channel)

            # CAD events (if/when you use them)
            elif irq & IRQ_CAD_DETECTED:
                self.emit("cad_detected", irq_status=irq)

            elif irq & IRQ_CAD_DONE:
                self.emit("cad_done", irq_status=irq)

        #---------------------------------------------------------------------
        # Errors: timeout, header error, CRC error
        #---------------------------------------------------------------------

        else:
            if irq & IRQ_TIMEOUT:
                # Emit an explicit timeout event
                self.emit("timeout", irq_status=irq)
            # Header error
            elif irq & IRQ_HEADER_ERR:
                self.emit("header_error", irq_status=irq)

            # CRC error
            elif irq & IRQ_CRC_ERR:
                self.emit("crc_error", irq_status=irq)

        self._status_irq = 0x0000
