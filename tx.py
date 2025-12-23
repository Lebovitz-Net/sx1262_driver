from SX126x import SX126x
import time
FREQ = 868_300_000
l = SX126x(); assert l.begin(0,0,18,20,16,6,-1)
l.setDio2RfSwitch(True)
l.setFrequency(FREQ)
l.setTxPower(5, l.TX_POWER_SX1262)               # 小功率，先别 22 dBm
l.setLoRaModulation(7, 125_000, 5)
l.setLoRaPacket(l.HEADER_EXPLICIT, 12, 255, True) # 显式头+CRC，长度给 255
l.setSyncWord(l.LORA_SYNC_WORD_PUBLIC)            # 0x3444
i = 0
while True:
    payload = f"HeLoRa {i}".encode()
    l.beginPacket(); l.put(payload); l.endPacket(5000); l.wait()
    print("TX:", payload)
    i += 1
    time.sleep(1.5)
