import time

from sx1262_constants import *


class SX1262Modem:
    # MODEM, MODULATION PARAMETER, AND PACKET PARAMETER SETUP METHODS

    def set_modem(self, modem):
        self._modem = modem
        self.set_standby(STANDBY_RC)
        self.set_packet_type(modem)

    def set_frequency(self, frequency: int):
        # perform image calibration before set frequency
        if frequency < 446000000:
            cal_freq_min = CAL_IMG_430
            cal_freq_max = CAL_IMG_440
        elif frequency < 734000000:
            cal_freq_min = CAL_IMG_470
            cal_freq_max = CAL_IMG_510
        elif frequency < 828000000:
            cal_freq_min = CAL_IMG_779
            cal_freq_max = CAL_IMG_787
        elif frequency < 877000000:
            cal_freq_min = CAL_IMG_863
            cal_freq_max = CAL_IMG_870
        else:
            cal_freq_min = CAL_IMG_902
            cal_freq_max = CAL_IMG_928

        self.calibrate_image(cal_freq_min, cal_freq_max)

        # calculate frequency and set frequency setting
        rf_freq = int(frequency * RF_FREQUENCY_NOM / RF_FREQUENCY_XTAL)
        self.set_rf_frequency(rf_freq)

    def set_tx_power(self, tx_power: int, version=TX_POWER_SX1262):
        # maximum TX power is 22 dBm and 15 dBm for SX1261
        if tx_power > 22:
            tx_power = 22
        elif tx_power > 15 and version == TX_POWER_SX1261:
            tx_power = 15

        pa_duty_cycle = 0x00
        hp_max = 0x00
        device_sel = 0x00
        power = 0x0E

        if version == TX_POWER_SX1261:
            device_sel = 0x01

        if tx_power == 22:
            pa_duty_cycle = 0x04
            hp_max = 0x07
            power = 0x16
        elif tx_power >= 20:
            pa_duty_cycle = 0x03
            hp_max = 0x05
            power = 0x16
        elif tx_power >= 17:
            pa_duty_cycle = 0x02
            hp_max = 0x03
            power = 0x16
        elif tx_power >= 14 and version == TX_POWER_SX1261:
            pa_duty_cycle = 0x04
            hp_max = 0x00
            power = 0x0E
        elif tx_power >= 14 and version == TX_POWER_SX1262:
            pa_duty_cycle = 0x02
            hp_max = 0x02
            power = 0x16
        elif tx_power >= 14 and version == TX_POWER_SX1268:
            pa_duty_cycle = 0x04
            hp_max = 0x06
            power = 0x0F
        elif tx_power >= 10 and version == TX_POWER_SX1261:
            pa_duty_cycle = 0x01
            hp_max = 0x00
            power = 0x0D
        elif tx_power >= 10 and version == TX_POWER_SX1268:
            pa_duty_cycle = 0x00
            hp_max = 0x03
            power = 0x0F
        else:
            return

        self.set_pa_config(pa_duty_cycle, hp_max, device_sel, 0x01)
        self.set_tx_params(power, PA_RAMP_800U)

    def set_rx_gain(self, rx_gain):
        gain = POWER_SAVING_GAIN
        if rx_gain == RX_GAIN_BOOSTED:
            gain = BOOSTED_GAIN
            self.write_register(REG_RX_GAIN, (gain,), 1)
            self.write_register(0x029F, (0x01, 0x08, 0xAC), 3)
        else:
            self.write_register(REG_RX_GAIN, (gain,), 1)

    def set_lora_modulation(self, sf: int, bw: int, cr: int, ldro: bool = False):
        self._sf = sf
        self._bw = bw
        self._cr = cr
        self._ldro = ldro

        if sf > 12:
            sf = 12
        elif sf < 5:
            sf = 5

        if bw < 9100:
            bw = BW_7800
        elif bw < 13000:
            bw = BW_10400
        elif bw < 18200:
            bw = BW_15600
        elif bw < 26000:
            bw = BW_20800
        elif bw < 36500:
            bw = BW_31250
        elif bw < 52100:
            bw = BW_41700
        elif bw < 93800:
            bw = BW_62500
        elif bw < 187500:
            bw = BW_125000
        elif bw < 375000:
            bw = BW_250000
        else:
            bw = BW_500000

        cr = cr - 4
        if cr > 4:
            cr = 0

        if ldro:
            ldro = LDRO_ON
        else:
            ldro = LDRO_OFF

        self.set_modulation_params_lora(sf, bw, cr, ldro)

    def set_lora_packet(
        self,
        header_type,
        preamble_length: int,
        payload_length: int,
        crc_type: bool = False,
        invert_iq: bool = False,
    ):
        self._header_type = header_type
        self._preamble_length = preamble_length
        self._payload_length = payload_length
        self._crc_type = crc_type
        self._invert_iq = invert_iq

        if header_type != HEADER_IMPLICIT:
            header_type = HEADER_EXPLICIT

        if crc_type:
            crc_type_val = CRC_ON
        else:
            crc_type_val = CRC_OFF

        if invert_iq:
            invert_iq_val = IQ_INVERTED
        else:
            invert_iq_val = IQ_STANDARD

        self.set_packet_params_lora(
            preamble_length, header_type, payload_length, crc_type_val, invert_iq_val
        )
        self._fix_inverted_iq(invert_iq_val)

    def set_spreading_factor(self, sf: int):
        self.set_lora_modulation(sf, self._bw, self._cr, self._ldro)

    def set_bandwidth(self, bw: int):
        self.set_lora_modulation(self._sf, bw, self._cr, self._ldro)

    def set_code_rate(self, cr: int):
        self.set_lora_modulation(self._sf, self._bw, cr, self._ldro)

    def set_ldro_enable(self, ldro: bool = True):
        self.set_lora_modulation(self._sf, self._bw, self._cr, ldro)

    def set_header_type(self, header_type):
        self.set_lora_packet(
            header_type,
            self._preamble_length,
            self._payload_length,
            self._crc_type,
            self._invert_iq,
        )

    def set_preamble_length(self, preamble_length: int):
        self.set_lora_packet(
            self._header_type,
            preamble_length,
            self._payload_length,
            self._crc_type,
            self._invert_iq,
        )

    def set_payload_length(self, payload_length: int):
        self.set_lora_packet(
            self._header_type,
            self._preamble_length,
            payload_length,
            self._crc_type,
            self._invert_iq,
        )

    def set_crc_enable(self, crc_type: bool = True):
        self.set_lora_packet(
            self._header_type,
            self._preamble_length,
            self._payload_length,
            crc_type,
            self._invert_iq,
        )

    def set_invert_iq(self, invert_iq: bool = True):
        self.set_lora_packet(
            self._header_type,
            self._preamble_length,
            self._payload_length,
            self._crc_type,
            invert_iq,
        )

    def set_sync_word(self, sync_word: int):
        buf = (
            (sync_word >> 8) & 0xFF,
            sync_word & 0xFF,
        )
        if sync_word <= 0xFF:
            buf = (
                (sync_word & 0xF0) | 0x04,
                (sync_word << 4) | 0x04,
            )
        self.write_register(REG_LORA_SYNC_WORD_MSB, buf, 2)

    def set_fsk_modulation(self, br: int, pulse_shape: int, bandwidth: int, fdev: int):
        self.set_modulation_params_fsk(br, pulse_shape, bandwidth, fdev)

    def set_fsk_packet(
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
        self.set_packet_params_fsk(
            preamble_length,
            preamble_detector,
            sync_word_length,
            addr_comp,
            packet_type,
            payload_length,
            crc_type,
            whitening,
        )

    def set_fsk_sync_word(self, sw: tuple, sw_len: int):
        self.write_register(REG_FSK_SYNC_WORD_0, sw, sw_len)

    def set_fsk_address(self, node_addr: int, broadcast_addr: int):
        self.write_register(REG_FSK_NODE_ADDRESS, (node_addr, broadcast_addr), 2)

    def set_fsk_crc(self, crc_init: int, crc_polynom: int):
        buf = (
            crc_init >> 8,
            crc_init & 0xFF,
            crc_polynom >> 8,
            crc_polynom & 0xFF,
        )
        self.write_register(REG_FSK_CRC_INITIAL_MSB, buf, 4)

    def set_fsk_whitening(self, whitening: int):
        self.write_register(
            REG_FSK_WHITENING_INITIAL_MSB, (whitening >> 8, whitening & 0xFF), 2
        )
