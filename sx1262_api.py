import lgpio
from sx1262_constants import *


class SX1262Api:
    # OPERATIONAL MODES COMMANDS

    def set_sleep(self, sleep_config: int):
        self._write_bytes(0x84, (sleep_config,), 1)

    def set_standby(self, stby_config: int):
        self._write_bytes(0x80, (stby_config,), 1)

    def set_fs(self):
        self._write_bytes(0xC1, (), 0)

    def set_tx(self, timeout: int):
        buf = (
            (timeout >> 16) & 0xFF,
            (timeout >> 8) & 0xFF,
            timeout & 0xFF,
        )
        self._write_bytes(0x83, buf, 3)

    def set_rx(self, timeout: int):
        buf = (
            (timeout >> 16) & 0xFF,
            (timeout >> 8) & 0xFF,
            timeout & 0xFF,
        )
        self._write_bytes(0x82, buf, 3)

    def set_timer_on_preamble(self, enable: int):
        self._write_bytes(0x9F, (enable,), 1)

    def set_rx_duty_cycle(self, rx_period: int, sleep_period: int):
        buf = (
            (rx_period >> 16) & 0xFF,
            (rx_period >> 8) & 0xFF,
            rx_period & 0xFF,
            (sleep_period >> 16) & 0xFF,
            (sleep_period >> 8) & 0xFF,
            sleep_period & 0xFF,
        )
        self._write_bytes(0x94, buf, 6)

    def set_cad(self):
        self._write_bytes(0xC5, (), 0)

    def set_tx_continuous_wave(self):
        self._write_bytes(0xD1, (), 0)

    def set_tx_infinite_preamble(self):
        self._write_bytes(0xD2, (), 0)

    def set_regulator_mode(self, mode_param: int):
        self._write_bytes(0x96, (mode_param,), 1)

    def calibrate(self, calib_param: int):
        self._write_bytes(0x89, (calib_param,), 1)

    def calibrate_image(self, freq1: int, freq2: int):
        buf = (freq1, freq2)
        self._write_bytes(0x98, buf, 2)

    def set_pa_config(
        self, pa_duty_cycle: int, hp_max: int, device_sel: int, pa_lut: int
    ):
        buf = (pa_duty_cycle, hp_max, device_sel, pa_lut)
        self._write_bytes(0x95, buf, 4)

    def set_rx_tx_fallback_mode(self, fallback_mode: int):
        self._write_bytes(0x93, (fallback_mode,), 1)

    # REGISTER AND BUFFER ACCESS COMMANDS

    def write_register(self, address: int, data: tuple, n_data: int):
        buf = (
            (address >> 8) & 0xFF,
            address & 0xFF,
        ) + tuple(data)
        self._write_bytes(0x0D, buf, n_data + 2)

    def read_register(self, address: int, n_data: int) -> tuple:
        addr = (
            (address >> 8) & 0xFF,
            address & 0xFF,
        )
        buf = self._read_bytes(0x1D, n_data + 1, addr, 2)
        return buf[1:]

    def write_buffer(self, offset: int, data: tuple, n_data: int):
        buf = (offset,) + tuple(data)
        self._write_bytes(0x0E, buf, n_data + 1)

    def read_buffer(self, offset: int, n_data: int) -> tuple:
        buf = self._read_bytes(0x1E, n_data + 1, (offset,), 1)
        return buf[1:]

    # DIO AND IRQ CONTROL

    def set_dio_irq_params(
        self, irq_mask: int, dio1_mask: int, dio2_mask: int, dio3_mask: int
    ):
        buf = (
            (irq_mask >> 8) & 0xFF,
            irq_mask & 0xFF,
            (dio1_mask >> 8) & 0xFF,
            dio1_mask & 0xFF,
            (dio2_mask >> 8) & 0xFF,
            dio2_mask & 0xFF,
            (dio3_mask >> 8) & 0xFF,
            dio3_mask & 0xFF,
        )
        self._write_bytes(0x08, buf, 8)

    def get_irq_status(self) -> int:
        buf = self._read_bytes(0x12, 3)
        return (buf[1] << 8) | buf[2]

    def clear_irq_status(self, clear_irq_param: int):
        buf = (
            (clear_irq_param >> 8) & 0xFF,
            clear_irq_param & 0xFF,
        )
        self._write_bytes(0x02, buf, 2)

    def set_dio2_as_rf_switch_ctrl(self, enable: int):
        self._write_bytes(0x9D, (enable,), 1)

    def set_dio3_as_tcxo_ctrl(self, tcxo_voltage: int, delay: int):
        buf = (
            tcxo_voltage & 0xFF,
            (delay >> 16) & 0xFF,
            (delay >> 8) & 0xFF,
            delay & 0xFF,
        )
        self._write_bytes(0x97, buf, 4)

    # RF, MODULATION, PACKET COMMANDS

    def set_rf_frequency(self, rf_freq: int):
        buf = (
            (rf_freq >> 24) & 0xFF,
            (rf_freq >> 16) & 0xFF,
            (rf_freq >> 8) & 0xFF,
            rf_freq & 0xFF,
        )
        self._write_bytes(0x86, buf, 4)

    def set_packet_type(self, packet_type: int):
        self._write_bytes(0x8A, (packet_type,), 1)

    def get_packet_type(self) -> int:
        buf = self._read_bytes(0x11, 2)
        return buf[1]

    def set_tx_params(self, power: int, ramp_time: int):
        buf = (power, ramp_time)
        self._write_bytes(0x8E, buf, 2)

    def set_modulation_params_lora(self, sf: int, bw: int, cr: int, ldro: int):
        buf = (sf, bw, cr, ldro, 0, 0, 0, 0)
        self._write_bytes(0x8B, buf, 8)

    def set_modulation_params_fsk(
        self, br: int, pulse_shape: int, bandwidth: int, fdev: int
    ):
        buf = (
            (br >> 16) & 0xFF,
            (br >> 8) & 0xFF,
            br & 0xFF,
            pulse_shape,
            bandwidth,
            (br >> 16) & 0xFF,
            (br >> 8) & 0xFF,
            fdev & 0xFF,
        )
        self._write_bytes(0x8B, buf, 8)

    def set_packet_params_lora(
        self,
        preamble_length: int,
        header_type: int,
        payload_length: int,
        crc_type: int,
        invert_iq: int,
    ):
        buf = (
            (preamble_length >> 8) & 0xFF,
            preamble_length & 0xFF,
            header_type,
            payload_length,
            crc_type,
            invert_iq,
            0,
            0,
            0,
        )
        self._write_bytes(0x8C, buf, 9)

    def set_packet_params_fsk(
        self,
        preamble_length: int,
        preamble_detector: int,
        sync_word_length: int,
        addr_comp: int,
        packet_type: int,
        payload_length: int,
        crc_type: int,
        whitening: int,
    ):
        buf = (
            (preamble_length >> 8) & 0xFF,
            preamble_length & 0xFF,
            preamble_detector,
            sync_word_length,
            addr_comp,
            packet_type,
            payload_length,
            crc_type,
            whitening,
        )
        self._write_bytes(0x8C, buf, 9)

    def set_cad_params(
        self,
        cad_symbol_num: int,
        cad_det_peak: int,
        cad_det_min: int,
        cad_exit_mode: int,
        cad_timeout: int,
    ):
        buf = (
            cad_symbol_num,
            cad_det_peak,
            cad_det_min,
            cad_exit_mode,
            (cad_timeout >> 16) & 0xFF,
            (cad_timeout >> 8) & 0xFF,
            cad_timeout & 0xFF,
        )
        self._write_bytes(0x88, buf, 7)

    def set_buffer_base_address(self, tx_base_address: int, rx_base_address: int):
        buf = (tx_base_address, rx_base_address)
        self._write_bytes(0x8F, buf, 2)

    def set_lora_symb_num_timeout(self, symbnum: int):
        self._write_bytes(0xA0, (symbnum,), 1)

    # STATUS COMMANDS

    def get_status_byte(self) -> int:
        buf = self._read_bytes(0xC0, 1)
        return buf[0]

    def get_chip_status(self):
        if self.busy_check():
            return None

        lgpio.gpio_write(self.gpio_chip, self._cs_define, 0)
        resp = self.spi.xfer2([0xC0, 0])
        lgpio.gpio_write(self.gpio_chip, self._cs_define, 1)
        return resp

    def get_rx_buffer_status(self) -> tuple:
        buf = self._read_bytes(0x13, 3)
        return buf[1:3]

    def get_packet_status(self) -> tuple:
        buf = self._read_bytes(0x14, 4)
        return buf[1:4]

    def get_rssi_inst(self) -> int:
        buf = self._read_bytes(0x15, 2)
        return buf[1]

    def get_full_rssi_inst(self):
        resp = self._read_bytes(0x15, 4)
        status = resp[0]
        rssi_raw = resp[1]
        rssi_dbm = -rssi_raw / 2.0
        return status, rssi_dbm

    def decode_status(self, status):
        mode = status & 0x07
        modes = {
            1: "STBY_RC",
            2: "STBY_XOSC",
            3: "FS",
            4: "RX",
            5: "TX",
        }
        return modes.get(mode, "UNKNOWN")

    def get_stats(self) -> tuple:
        buf = self._read_bytes(0x10, 7)
        return (
            (buf[1] >> 8) | buf[2],
            (buf[3] >> 8) | buf[4],
            (buf[5] >> 8) | buf[6],
        )

    def reset_stats(self):
        buf = (0, 0, 0, 0, 0, 0)
        self._write_bytes(0x00, buf, 6)

    def get_device_errors(self) -> int:
        buf = self._read_bytes(0x17, 2)
        return buf[1]

    def clear_device_errors(self):
        buf = (0, 0)
        self._write_bytes(0x07, buf, 2)

    # WORKAROUND FUNCTIONS

    def _fix_lora_bw500(self, bw: int):
        packet_type = self.get_packet_type()
        buf = self.read_register(REG_TX_MODULATION, 1)
        value = buf[0] | 0x04
        if packet_type == LORA_MODEM and bw == BW_500000:
            value = buf[0] & 0xFB
        self.write_register(REG_TX_MODULATION, (value,), 1)

    def _fix_resistance_antenna(self):
        buf = self.read_register(REG_TX_CLAMP_CONFIG, 1)
        value = buf[0] | 0x1E
        self.write_register(REG_TX_CLAMP_CONFIG, (value,), 1)

    def _fix_rx_timeout(self):
        self.write_register(REG_RTC_CONTROL, (0,), 1)
        buf = self.read_register(REG_EVENT_MASK, 1)
        value = buf[0] | 0x02
        self.write_register(REG_EVENT_MASK, (value,), 1)

    def _fix_inverted_iq(self, invert_iq: bool):
        buf = self.read_register(REG_IQ_POLARITY_SETUP, 1)
        value = buf[0] & 0xFB
        if invert_iq:
            value = buf[0] | 0x04
        self.write_register(REG_IQ_POLARITY_SETUP, (value,), 1)

    # UTILITIES

    def _write_bytes(self, opcode: int, data: tuple, n_bytes: int):
        if self.busy_check():
            return
        lgpio.gpio_write(self.gpio_chip, self._cs_define, 0)
        buf = [opcode]
        for i in range(n_bytes):
            buf.append(data[i])
        self.spi.xfer2(buf)
        lgpio.gpio_write(self.gpio_chip, self._cs_define, 1)

    def _read_bytes(
        self,
        opcode: int,
        n_bytes: int,
        address: tuple = (),
        n_address: int = 0,
    ) -> tuple:
        if self.busy_check():
            return ()
        lgpio.gpio_write(self.gpio_chip, self._cs_define, 0)
        buf = [opcode]
        for i in range(n_address):
            buf.append(address[i])
        for _ in range(n_bytes):
            buf.append(0x00)
        feedback = self.spi.xfer2(buf)
        lgpio.gpio_write(self.gpio_chip, self._cs_define, 1)
        return tuple(feedback[n_address + 1 :])
