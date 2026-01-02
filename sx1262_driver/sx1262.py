from base import BaseLoRa
import spidev
import lgpio
import time

from core.event_emitter import EventEmitter

from sx1262_vars import SX1262Vars
from sx1262_api import SX1262Api
from sx1262_common import SX1262Common
from sx1262_hardware import SX1262Hardware
from sx1262_modem import SX1262Modem
from sx1262_receive import SX1262Receive
from sx1262_transmit import SX1262Transmit
from sx1262_status import SX1262Status
from sx1262_interrupt import SX1262Interrupt


class SX1262(
    EventEmitter,
    SX1262Vars,
    SX1262Api,
    SX1262Common,
    SX1262Hardware,
    SX1262Modem,
    SX1262Receive,
    SX1262Transmit,
    SX1262Status,
    SX1262Interrupt,
    BaseLoRa,
):
    def __init__(self):
        # Initialize EventEmitter first so it's ready before we emit anything
        EventEmitter.__init__(self)
        # Initialize all mixins / BaseLoRa as before
        super().__init__()

        self.spi = spidev.SpiDev()

        # lgpio: open /dev/gpiochip0 explicitly and keep a handle
        self.gpio_chip = lgpio.gpiochip_open(0)
