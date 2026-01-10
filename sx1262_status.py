import time

from sx1262_constants import *


class SX1262Status:
    # WAIT, OPERATION STATUS, AND PACKET STATUS METHODS

    def wait(self, timeout: int = 0) -> bool:
        if self._status_irq:
            return True

        irq_stat = 0x0000
        start = time.time()

        while irq_stat == 0x0000 and self._status_irq == 0x0000:
            if self._irq == -1:
                irq_stat = self.get_irq_status()

            if timeout > 0 and (time.time() - start) > timeout:
                return False

        if self._status_irq:
            return True
        elif self._status_wait == STATUS_TX_WAIT:
            self._transmit_time = time.time() - self._transmit_time
            if self._txen != -1:
                # restore TXEN pin
                # value already in self._tx_state
                from lgpio import gpio_write

                gpio_write(self.gpio_chip, self._txen, self._tx_state)

        elif self._status_wait == STATUS_RX_WAIT:
            (self._payload_tx_rx, self._buffer_index) = self.get_rx_buffer_status()
            if self._txen != -1:
                from lgpio import gpio_write

                gpio_write(self.gpio_chip, self._txen, self._tx_state)
            self._fix_rx_timeout()

        elif self._status_wait == STATUS_RX_CONTINUOUS:
            (self._payload_tx_rx, self._buffer_index) = self.get_rx_buffer_status()
            self.clear_irq_status(IRQ_ALL)

        self._status_irq = irq_stat
        return True

    def status(self) -> int:
        status_irq = self._status_irq
        if self._status_wait == STATUS_RX_CONTINUOUS:
            self._status_irq = 0x0000

        if status_irq & IRQ_TIMEOUT:
            if self._status_wait == STATUS_TX_WAIT:
                return STATUS_TX_TIMEOUT
            else:
                return STATUS_RX_TIMEOUT
        elif status_irq & IRQ_HEADER_ERR:
            return STATUS_HEADER_ERR
        elif status_irq & IRQ_CRC_ERR:
            return STATUS_CRC_ERR
        elif status_irq & IRQ_TX_DONE:
            return STATUS_TX_DONE
        elif status_irq & IRQ_RX_DONE:
            return STATUS_RX_DONE

        return self._status_wait

    def transmit_time(self) -> float:
        return self._transmit_time * 1000

    def data_rate(self) -> float:
        if self._transmit_time == 0:
            return 0.0
        return self._payload_tx_rx / self._transmit_time

    def packet_rssi(self) -> float:
        (rssi_pkt, snr_pkt, signal_rssi_pkt) = self.get_packet_status()
        return rssi_pkt / -2.0

    def snr(self) -> float:
        (rssi_pkt, snr_pkt, signal_rssi_pkt) = self.get_packet_status()
        if snr_pkt > 127:
            snr_pkt = snr_pkt - 256
        return snr_pkt / 4.0

    def signal_rssi(self) -> float:
        (rssi_pkt, snr_pkt, signal_rssi_pkt) = self.get_packet_status()
        return signal_rssi_pkt / -2.0

    def rssi_inst(self) -> float:
        return self.get_rssi_inst() / -2.0

    def get_error(self) -> int:
        error = self.get_device_errors()
        self.clear_device_errors()
        return error
