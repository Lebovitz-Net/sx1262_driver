import time

from sx1262_constants import *

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

    def _interrupt_tx(self, _channel=None):
        self._transmit_time = time.time() - self._transmit_time

        # restore TXEN
        if self._txen != -1:
            from lgpio import gpio_write

            gpio_write(self.gpio_chip, self._txen, self._tx_state)

        self._status_irq = self.get_irq_status()

        if callable(self._on_transmit):
            self._on_transmit()

    def _interrupt_rx(self, _channel=None):
        if self._txen != -1:
            from lgpio import gpio_write

            gpio_write(self.gpio_chip, self._txen, self._tx_state)

        self._fix_rx_timeout()
        self._status_irq = self.get_irq_status()
        (self._payload_tx_rx, self._buffer_index) = self.get_rx_buffer_status()

        if callable(self._on_receive):
            self._on_receive()

    def _interrupt_rx_continuous(self, _channel=None):
        self._status_irq = self.get_irq_status()
        self.clear_irq_status(IRQ_ALL)
        (self._payload_tx_rx, self._buffer_index) = self.get_rx_buffer_status()

        if callable(self._on_receive):
            self._on_receive()

    def on_transmit(self, callback):
        self._on_transmit = callback

    def on_receive(self, callback):
        self._on_receive = callback

    # -------------------------------------------------------------------------
    # Internal IRQ polling loop -> emits events via SX1262Interrupt._handle_irq
    # -------------------------------------------------------------------------

    def _start_recv_loop (self, interval=0.01):
        """
        Poll the IRQ status register and, if non-zero, invoke
        the driver's internal RX interrupt handler.
        """

        if self._recv_thread and self._recv_running:
            return
        
        self._recv_running = True

        def loop():
            while self._recv_running:
                irq = self.get_irq_status()
                if irq:
                    if self._status_wait == STATUS_RX_CONTINUOUS:
                        self._interrupt_rx_continuous(None)
                    else:
                        self._interrupt_rx(None)
                time.sleep(interval)

        self._recv_thread = threading.Thread(target=loop, daemon=True)
        self._recv_thread.start()

    def _stop_recv_loop(self):
        """
        Stop the background IRQ polling loop.
        """

        if not self._recv_running:
            return

        self._recv_running = False
        self._recv_thread = None