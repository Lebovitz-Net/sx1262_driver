from sx1262_constants import *


class SX1262Vars:
    def __init__(self):
        # SPI and GPIO pin setting
        self._bus = BUS
        self._cs = CS
        self._reset = RESET
        self._busy = BUSY
        self._cs_define = CS_DEFINE
        self._irq = IRQ
        self._txen = TXEN
        self._rxen = RXEN
        self._wake = WAKE
        self._busy_timeout = BUSY_TIMEOUT
        self._spi_speed = SPI_SPEED
        self._tx_state = TX_STATE
        self._rx_state = RX_STATE

        # LoRa setting
        self._dio = DIO
        self._modem = MODEM
        self._sf = SF
        self._bw = BW
        self._cr = CR
        self._ldro = LDRO
        self._header_type = HEADER_TYPE
        self._preamble_length = PREAMBLE_LENGTH
        self._payload_length = PAYLOAD_LENGTH
        self._crc_type = CRC_TYPE
        self._invert_iq = INVERT_IQ

        # Operation properties
        self._buffer_index = BUFFER_INDEX
        self._payload_tx_rx = PAYLOAD_TX_RX
        self._status_wait = STATUS_WAIT
        self._status_irq = STATUS_IRQ
        self._transmit_time = TRANSMIT_TIME

        # callback functions
        self._on_transmit = ON_TRANSMIT
        self._on_receive = ON_RECEIVE
