# pyright: reportMissingImports=false, reportMissingModuleSource=false

"""
Reticulum Interface for SX1262 LoRa Transceiver

This module implements a Reticulum-compatible interface for the SX1262 LoRa radio,
enabling mesh networking capabilities using the sx1262_driver module.

Configuration example (in ~/.reticulum/config):

    [[SX1262 LoRa Interface]]
      type = SX1262ReticulumInterface
      enabled = yes
      name = sx1262_lora
      
      # Radio Parameters
      frequency = 914875000
      bandwidth = 125000
      spreading_factor = 9
      coding_rate = 5
      sync_word = 0x1424
      preamble_length = 18
      
      # GPIO/SPI Configuration (BCM numbering)
      spi_bus = 0
      spi_device = 0
      reset_pin = 18
      busy_pin = 20
      irq_pin = -1
      nss_pin = 21
      use_irq = false
"""

import time
import threading
import logging

import RNS
from RNS.Interfaces.Interface import Interface

from .sx1262 import SX1262
from .sx1262_constants import (
    LORA_SYNC_WORD_PUBLIC,
    LORA_SYNC_WORD_PRIVATE,
    RX_CONTINUOUS,
    HEADER_EXPLICIT,
    PREAMBLE_LENGTH,
    PAYLOAD_LENGTH,
    CRC_ON,
    IQ_STANDARD,
    RX_GAIN_BOOSTED,
    IRQ_ALL,
    BUSY_TIMEOUT,
    STANDBY_RC,
)


class SX1262ReticulumInterface(Interface):
    """
    Reticulum interface for SX1262 LoRa transceiver.
    
    Implements bidirectional packet exchange between Reticulum and the SX1262 radio,
    with full support for LoRa modulation parameters and error handling.
    """
    
    DEFAULT_IFAC_SIZE = 8
    HW_MTU = 564
    BITRATE_GUESS = 62500  # LoRa bitrate estimate
    
    def __init__(self, owner, configuration):
        """
        Initialize the SX1262 Reticulum interface.
        
        Args:
            owner: The Reticulum transport instance
            configuration: Configuration object from Reticulum config file
        """
        super().__init__()
        
        self.supports_discovery = True
        self.logger = RNS.log
        self.owner = owner
        self.online = False
        # Aliases expected by RNS Discovery for RNodeInterface-style announce data
        self.sf = None  # set after config parse
        self.cr = None  # set after config parse
        self.radio = None
        self.irq_thread = None
        
        # Parse configuration
        try:
            c = Interface.get_config_obj(configuration)
            
            # Interface name
            self.name = c.get("name", "SX1262Interface")
            
            # Radio parameters
            self.frequency = int(c.get("frequency", "914875000"))
            self.bandwidth = int(c.get("bandwidth", "125000"))
            self.spreading_factor = int(c.get("spreading_factor", "9"))
            self.coding_rate = int(c.get("coding_rate", "5"))
            
            # LDRO handling: auto-calculate for SF11/SF12 and narrow bandwidths
            ldro_cfg = c.get("ldro", "auto").strip().lower()
            if ldro_cfg in ("true", "1", "yes", "on"):
                self.ldro = True
            elif ldro_cfg in ("false", "0", "no", "off"):
                self.ldro = False
            else:
                self.ldro = self._compute_ldro(self.spreading_factor, self.bandwidth)
            
            # Sync word handling
            sync_word_str = c.get("sync_word", "0x1424")
            if sync_word_str.startswith("0x"):
                self.sync_word = int(sync_word_str, 16)
            elif sync_word_str.upper() == "PUBLIC":
                self.sync_word = LORA_SYNC_WORD_PUBLIC
            elif sync_word_str.upper() == "PRIVATE":
                self.sync_word = LORA_SYNC_WORD_PRIVATE
            else:
                self.sync_word = int(sync_word_str)
            
            # SPI configuration
            self.spi_bus = int(c.get("spi_bus", "0"))
            self.spi_device = int(c.get("spi_device", "0"))
            
            # GPIO pins (BCM numbering)
            self.reset_pin = int(c.get("reset_pin", "18"))
            self.busy_pin = int(c.get("busy_pin", "20"))
            self.irq_pin = int(c.get("irq_pin", "-1"))
            self.nss_pin = int(c.get("nss_pin", "21"))
            
            # Preamble length — must be >= 18 to be received by RNode firmware devices
            self.preamble_length = int(c.get("preamble_length", str(PREAMBLE_LENGTH)))

            # RNS Discovery aliases (used by Discovery.py for RNodeInterface-style announce)
            self.sf = self.spreading_factor
            self.cr = self.coding_rate

            # Hardware watchdogs
            self.busy_timeout = int(c.get("busy_timeout", str(BUSY_TIMEOUT)))
            
            # IRQ mode
            self.use_irq = c.get("use_irq", "false").strip().lower() in ("true", "1", "yes", "on")
            
        except Exception as e:
            self.logger(f"SX1262 Interface: Configuration error: {e}", RNS.LOG_ERROR)
            raise e
        
        # Initialize radio
        try:
            self.logger(f"SX1262 Interface: Initializing radio on SPI bus {self.spi_bus}, device {self.spi_device}")
            self._init_radio()
        except Exception as e:
            self.logger(f"SX1262 Interface: Failed to initialize radio: {e}", RNS.LOG_ERROR)
            raise e
        
        # Start receive thread
        self.read_thread = None
        self._should_run = True
        self._start_read_thread()
        
        self.logger(f"SX1262 Interface: {self.name} initialized successfully", RNS.LOG_INFO)
    
    def _init_radio(self):
        """Initialize and configure the SX1262 radio."""
        self.radio = SX1262()
        
        # Begin radio operation
        ok = self.radio.begin(
            bus=self.spi_bus,
            cs=self.spi_device,
            reset=self.reset_pin,
            busy=self.busy_pin,
            irq=self.irq_pin,
            txen=-1,
            rxen=-1,
            wake=-1,
        )
        
        if not ok:
            raise RuntimeError("SX1262 failed to enter STDBY_RC. Check BUSY, RESET, NSS wiring.")

        if self.use_irq and self.irq_pin != -1:
            # Ensure the driver uses DIO1 for IRQ mapping when physical IRQ pin is configured
            self.radio.set_rf_irq_pin(1)
            self.radio._stop_recv_loop()

        # Register event handlers
        self.radio.on("rx_done", self._handle_rx_done)
        self.radio.on("rx_error", self._handle_rx_error)
        self.radio.on("timeout", self._handle_timeout)
        self.radio.on_transmit(self._handle_tx_done)
        
        # Configure radio parameters
        self.radio.set_sync_word(self.sync_word)
        self.radio.set_frequency(self.frequency)
        
        self.radio.set_lora_modulation(
            sf=self.spreading_factor,
            bw=self.bandwidth,
            cr=self.coding_rate,
            ldro=int(self.ldro),
        )
        
        self.radio.set_lora_packet(
            header_type=HEADER_EXPLICIT,
            preamble_length=self.preamble_length,
            payload_length=PAYLOAD_LENGTH,
            crc_type=CRC_ON,
            invert_iq=IQ_STANDARD
        )
        
        self.radio.set_rx_gain(RX_GAIN_BOOSTED)
        
        # Start continuous receive
        self.radio.request(RX_CONTINUOUS)
        self.online = True

        if self.use_irq and self.irq_pin != -1:
            self._start_irq_monitor()
        
        self.logger(
            f"SX1262 Interface: Radio configured:\n"
            f"  Frequency  : {self.frequency/1e6:.3f} MHz\n"
            f"  Bandwidth  : {self.bandwidth/1e3:.1f} kHz\n"
            f"  Spreading  : SF{self.spreading_factor}\n"
            f"  Coding Rate: 4/{self.coding_rate}\n"
            f"  LDRO       : {self.ldro}\n"
            f"  Preamble   : {self.preamble_length} symbols\n"
            f"  Sync Word  : 0x{self.sync_word:04x}",
            RNS.LOG_NOTICE
        )
    
    def _compute_ldro(self, sf: int, bw: int) -> bool:
        """Return True when low data rate optimization is required."""
        symbol_duration = (2 ** sf) / float(bw)
        return symbol_duration > 0.016

    def _wait_for_idle(self):
        """Wait for BUSY to clear, or raise if stuck."""
        if self.radio.busy_check(timeout=self.busy_timeout):
            raise RuntimeError(f"SX1262 BUSY stuck high for {self.busy_timeout} ms")

    def _restart_receive(self):
        """Clear IRQs and re-enter continuous receive mode."""
        if not self.online or self.radio is None:
            return
        try:
            self.radio.clear_irq_status(IRQ_ALL)
            self.radio.request(RX_CONTINUOUS)
            self.logger("SX1262 Interface: restarted RX continuous", RNS.LOG_DEBUG)
        except Exception as e:
            self.logger(f"SX1262 Interface: failed to restart RX: {e}", RNS.LOG_ERROR)
    
    def _start_irq_monitor(self):
        """Start an optional DIO1 IRQ monitor thread."""
        if self.irq_thread is not None:
            return

        self.irq_thread = threading.Thread(target=self._irq_monitor_loop, daemon=True)
        self.irq_thread.start()

    def _irq_monitor_loop(self):
        """Monitor the physical IRQ pin and dispatch radio IRQ events."""
        try:
            import lgpio  # type: ignore - pi only
        except ImportError:
            self.logger("SX1262 Interface: lgpio not available for IRQ monitoring", RNS.LOG_WARNING)
            return

        if self.radio is None or self.radio.gpio_chip is None or self.radio._irq == -1:
            self.logger("SX1262 Interface: IRQ monitor not started due to missing IRQ pin", RNS.LOG_WARNING)
            return

        self.logger("SX1262 Interface: starting DIO1 IRQ monitor", RNS.LOG_INFO)
        use_event = hasattr(lgpio, "gpio_wait_event")
        last_state = None

        while self._should_run and self.online:
            try:
                if use_event:
                    event = lgpio.gpio_wait_event(self.radio.gpio_chip, self.radio._irq, 1000)
                    if not event:
                        continue
                else:
                    state = lgpio.gpio_read(self.radio.gpio_chip, self.radio._irq)
                    if last_state is None:
                        last_state = state
                        continue
                    if state == last_state:
                        time.sleep(0.001)
                        continue
                    last_state = state
                    if state == 0:
                        continue

                self._handle_irq_pin()
            except Exception as e:
                self.logger(f"SX1262 Interface: IRQ monitor error: {e}", RNS.LOG_ERROR)
                time.sleep(0.1)

        self.logger("SX1262 Interface: DIO1 IRQ monitor stopped", RNS.LOG_DEBUG)

    def _handle_irq_pin(self):
        """Process a physical IRQ pin event by reading and dispatching chip IRQ status."""
        if self.radio is None:
            return

        try:
            irq = self.radio.get_irq_status()
            if irq and irq <= 0x3FF:
                self.radio.clear_irq_status(irq)
                if hasattr(self.radio, "_handle_irq"):
                    self.radio._handle_irq(irq, None)
                else:
                    self.logger("SX1262 Interface: radio has no internal IRQ handler", RNS.LOG_WARNING)
        except Exception as e:
            self.logger(f"SX1262 Interface: failed to handle IRQ pin event: {e}", RNS.LOG_ERROR)

    def _handle_tx_done(self):
        """Called when transmit has completed; re-enter receive mode."""
        self.logger("SX1262 Interface: TX complete, restarting RX", RNS.LOG_NOTICE)
        self._restart_receive()

    def _handle_rx_done(self, data, payload_length, irq_status):
        """
        Handle received packet from radio.
        
        Called when a complete LoRa packet is received with valid CRC.
        """
        try:
            self.logger(
                f"SX1262 Interface: RX_DONE - {payload_length} bytes, "
                f"RSSI={self.radio.packet_rssi():.1f}dBm, "
                f"SNR={self.radio.snr():.1f}dB",
                RNS.LOG_INFO
            )
            self.process_incoming(data)
        except Exception as e:
            self.logger(f"SX1262 Interface: RX_DONE handler error: {e}", RNS.LOG_ERROR)
    
    def _handle_rx_error(self, irq_status):
        """Handle RX errors (CRC, header errors)."""
        self.logger(
            f"SX1262 Interface: RX error - "
            f"RSSI={self.radio.packet_rssi():.1f}dBm, "
            f"SNR={self.radio.snr():.1f}dB",
            RNS.LOG_INFO
        )
        self._restart_receive()
    
    def _handle_timeout(self, irq_status):
        """Handle RX timeout (no packet received in expected time)."""
        self.logger("SX1262 Interface: RX timeout", RNS.LOG_WARNING)
        self._restart_receive()
    
    def _start_read_thread(self):
        """Start background thread for radio event polling."""
        self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.read_thread.start()
    
    def _read_loop(self):
        """
        Background thread that monitors radio state.
        
        The actual packet reception is handled asynchronously via event callbacks.
        This thread mainly keeps the radio alive and handles reconnection if needed.
        """
        try:
            while self._should_run and self.online:
                time.sleep(0.5)
        except Exception as e:
            self.logger(f"SX1262 Interface: Read loop error: {e}", RNS.LOG_ERROR)
            self.online = False
    
    def process_incoming(self, data):
        """
        Process received packet and pass to Reticulum.
        
        Args:
            data: Raw packet bytes from radio
        """
        if self.online:
            self.rxb += len(data)
            self.owner.inbound(data, self)
    
    def process_outgoing(self, data):
        """
        Send packet via radio.
        
        Args:
            data: Packet bytes to transmit
        """
        if self.online and self.radio:
            try:
                import lgpio  # type: ignore - pi only

                # Stop the recv loop to avoid SPI bus contention during TX
                self.radio._stop_recv_loop()
                self.logger("SX1262 Interface: recv loop stopped for TX", RNS.LOG_DEBUG)

                # Exit RX mode — SX1262 must be in STDBY before switching to TX
                self._wait_for_idle()
                self.radio.set_standby(STANDBY_RC)
                self._wait_for_idle()
                self.logger("SX1262 Interface: radio in STDBY, starting TX", RNS.LOG_NOTICE)

                self.radio.begin_packet()
                self.radio.write(list(data))
                self.radio.end_packet()

                # Wait for BUSY to assert (TX started), then wait for it to drop (TX done)
                time.sleep(0.002)  # give chip time to assert BUSY
                deadline = time.time() + (self.busy_timeout / 1000.0)
                while time.time() < deadline:
                    if lgpio.gpio_read(self.radio.gpio_chip, self.radio._busy) == 0:
                        break
                    time.sleep(0.001)
                else:
                    self.logger("SX1262 Interface: TX timeout waiting for BUSY to clear", RNS.LOG_ERROR)

                self.txb += len(data)
                self.logger(f"SX1262 Interface: TX complete - {len(data)} bytes sent", RNS.LOG_NOTICE)
                self._restart_receive()
                self.radio._start_recv_loop()
            except Exception as e:
                self.logger(f"SX1262 Interface: TX error: {e}", RNS.LOG_ERROR)
                try:
                    self._restart_receive()
                    self.radio._start_recv_loop()
                except Exception:
                    pass
                raise e
    
    def should_ingress_limit(self):
        """
        Indicate whether ingress limiting should be applied.
        
        Returns:
            False - LoRa is already rate-limited by modulation parameters
        """
        return False
    
    def detach(self):
        """Clean up and shut down the interface."""
        self.logger(f"SX1262 Interface: Detaching {self.name}", RNS.LOG_INFO)
        self.online = False
        self._should_run = False

        if self.irq_thread is not None and self.irq_thread.is_alive():
            self.irq_thread.join(timeout=1.0)

        if self.radio:
            try:
                self.radio.end()
            except Exception as e:
                self.logger(f"SX1262 Interface: Error shutting down radio: {e}", RNS.LOG_WARNING)
    
    def __str__(self):
        """String representation for logging."""
        return f"SX1262ReticulumInterface[{self.name}]"
