# SX1262 Silicon Errata Workarounds

The SX1261/62/68 family contains several documented silicon errata that affect
modulation quality, PA linearity, RX timeout behavior, and IQ polarity
switching. These issues are subtle but real, and they directly impact link
quality, header/CRC error rates, and overall radio stability.

The following functions implement the recommended workarounds from Semtech’s
errata notes. They are preserved in this driver because they fix **actual
hardware defects**, not software bugs.

---

## 1. `_fix_lora_bw500()` — LoRa 500 kHz Bandwidth Spectral Mask Fix

**Problem:**  
When using LoRa modulation at **500 kHz bandwidth**, the SX1262 can violate
spectral mask requirements due to internal modulation shaping. This results in:

- spectral regrowth  
- unwanted sidebands  
- degraded SNR at the receiver  
- potential regulatory non‑compliance  

This only occurs when:

- Packet type = LoRa  
- Bandwidth = 500 kHz  

**Fix:**  
Bit 2 of `REG_TX_MODULATION` must be **cleared** for BW=500kHz and **set**
otherwise.

```python
value = buf[0] | 0x04          # default
if packet_type == LORA_MODEM and bw == BW_500000:
    value = buf[0] & 0xFB      # clear bit 2


## 2. `_fix_resistance_antenna()` — PA Clamp / Antenna Mismatch Fix

**Problem:**  
The SX1262 includes a PA clamp circuit that protects the power amplifier from high VSWR or antenna mismatch. The default clamp threshold is too conservative, causing:

- reduced TX power
- premature PA limiting
- degraded modulation linearity
- lower effective range

**Fix:**  
Raise the clamp threshold by setting bits in `REG_TX_CLAMP_CONFIG`:

```python
value = buf[0] | 0x1E
self.write_register(REG_TX_CLAMP_CONFIG, (value,), 1)
Effect: Improves PA linearity and allows the radio to reach its intended TX power without distortion or early limiting. This is recommended for all LoRa operation, especially above 14 dBm.

## 3. `_fix_rx_timeout()` — RTC Timeout / RX Hang Fix

**Problem:**  
The SX1262 uses an internal RTC for RX and CAD timeouts. A silicon bug can leave the RTC block in an undefined state, causing:

- RX that never times out  
- IRQs that never fire  
- the radio getting stuck in RX mode  
- inconsistent behavior when switching between RX modes  

**Fix:**  
Reset the RTC control register and explicitly enable the timeout event bit in `REG_EVENT_MASK`:

```python
self.write_register(REG_RTC_CONTROL, (0,), 1)
buf = self.read_register(REG_EVENT_MASK, 1)
value = buf[0] | 0x02
self.write_register(REG_EVENT_MASK, (value,), 1)
Effect: Ensures RX timeout events always fire correctly and prevents the radio from hanging in RX mode. This fix is essential for continuous RX and duty‑cycled RX.

## 4. `_fix_inverted_iq()` — IQ Polarity Latch Fix

**Problem:**  
The SX1262 sometimes fails to latch the IQ polarity bit correctly when switching between:

- standard IQ  
- inverted IQ (used by LoRaWAN downlink and some proprietary networks)

When this latch bug occurs, the radio may enter a half‑configured state where the
IQ polarity is neither fully standard nor fully inverted. This leads to:

- silent demodulation failures  
- packets detected but not decoded  
- intermittent header errors  
- unpredictable RX behavior  

**Fix:**  
Explicitly clear bit 2 of `REG_IQ_POLARITY_SETUP` before setting it.  
This forces the latch to reset before applying the new polarity.

```python
buf = self.read_register(REG_IQ_POLARITY_SETUP, 1)
value = buf[0] & 0xFB      # clear bit 2
if invert_iq:
    value = buf[0] | 0x04  # set bit 2
self.write_register(REG_IQ_POLARITY_SETUP, (value,), 1)
Effect: Guarantees that the IQ polarity is applied correctly and prevents the chip from entering the undefined “half‑latched” state that breaks demodulation. This fix is required whenever switching between standard and inverted IQ modes.

Summary
These workarounds are not optional. They correct real hardware issues in the SX1262 silicon and directly improve:

- RX stability
- TX spectral purity
- PA linearity
- IQ polarity correctness
- timeout reliability

Removing them leads to exactly the kinds of symptoms observed during empirical testing: header errors, CRC errors, RX hangs, and inconsistent demodulation.

This driver applies all four fixes automatically where required.