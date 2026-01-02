import lgpio

from sx1262_constants import *


class SX1262Hardware:
    def set_spi(self, bus: int, cs: int, speed: int = SPI_SPEED):
        self._bus = bus
        self._cs = cs
        self._spi_speed = speed

        self.spi.open(bus, cs)
        self.spi.max_speed_hz = speed
        self.spi.lsbfirst = False
        self.spi.mode = 0

    def set_pins(
        self,
        reset: int,
        busy: int,
        irq: int = -1,
        txen: int = -1,
        rxen: int = -1,
        wake: int = -1,
    ):
        self._reset = reset
        self._busy = busy
        self._irq = irq
        self._txen = txen
        self._rxen = rxen
        self._wake = wake

        lgpio.gpio_claim_output(self.gpio_chip, reset)
        lgpio.gpio_claim_input(self.gpio_chip, busy)

        lgpio.gpio_claim_output(self.gpio_chip, self._cs_define)

        if irq != -1:
            lgpio.gpio_claim_input(self.gpio_chip, irq)
        if txen != -1:
            lgpio.gpio_claim_output(self.gpio_chip, txen)
        if rxen != -1:
            lgpio.gpio_claim_output(self.gpio_chip, rxen)

    def set_rf_irq_pin(self, dio_pin_select: int):
        if dio_pin_select in (2, 3):
            self._dio = dio_pin_select
        else:
            self._dio = 1

    def set_dio2_rf_switch(self, enable: bool = True):
        if enable:
            self.set_dio2_as_rf_switch_ctrl(DIO2_AS_RF_SWITCH)
        else:
            self.set_dio2_as_rf_switch_ctrl(DIO2_AS_IRQ)

    def set_dio3_tcxo_ctrl(self, tcxo_voltage, delay_time):
        self.set_dio3_as_tcxo_ctrl(tcxo_voltage, delay_time)
        self.set_standby(STANDBY_RC)
        self.calibrate(0xFF)

    def set_xtal_cap(self, xtal_a, xtal_b):
        self.set_standby(STANDBY_XOSC)
        self.write_register(REG_XTA_TRIM, (xtal_a, xtal_b), 2)
        self.set_standby(STANDBY_RC)
        self.calibrate(0xFF)

    def set_regulator(self, reg_mode):
        self.set_regulator_mode(reg_mode)

    def set_current_protection(self, level):
        if level > 63:
            level = 63
        self.write_register(REG_OCP_CONFIGURATION, (level,), 1)
