#!/usr/bin/env python3
# Minimal LoRaWAN OTAA (Join + periodic uplink) for Raspberry Pi + SX1262
# Pure Python (no external libraries). Uses your local SX126x.py driver.

import time, struct, json, secrets
from SX126x import SX126x

# ------------------- USER SETTINGS -------------------
# Copy from TTN device (OTAA)
DEVEUI   = "0000000000000001"  # 16 hex
JOINEUI  = "0000000000000000"  # 16 hex (aka AppEUI)
APPKEY   = "00112233445566778899AABBCCDDEEFF"  # 32 hex

# Region / RF (EU868 example; change for your plan)
FREQ_HZ  = 868100000
SF       = 7
BW       = 125000
CR       = 5
PREAMBLE = 8
TX_POWER = 14

# After join
FPORT    = 1
PAYLOAD  = b"hello-otaa"
UP_PERIOD_SEC = 60

# Pins (BCM)
SPI_BUS, SPI_CS = 0, 0
PIN_RST, PIN_BUSY, PIN_DIO1 = 18, 20, 16
PIN_TXEN, PIN_RXEN = 6, -1

# Persist session
SESSION_FILE = "lorawan_session.json"

# ----------------- AES/CMAC utils --------------------
SBOX = [
0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16]
RCON = [0x00,0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1B,0x36]

def _rotword(w): return w[1:]+w[:1]
def _subword(w): return [SBOX[b] for b in w]

def aes_key_expand(key16):
    w = [list(key16[i:i+4]) for i in range(0,16,4)]
    i = 4
    while len(w) < 44:
        t = w[-1][:]
        if i % 4 == 0:
            t = _subword(_rotword(t)); t[0] ^= RCON[i//4]
        w.append([(w[-4][j]^t[j])&0xFF for j in range(4)]); i += 1
    return [sum(w[i:i+4],[]) for i in range(0,44,4)]

def _xtime(a): return ((a<<1)^0x1B)&0xFF if a&0x80 else (a<<1)&0xFF
def _mul(a,b):
    r=0
    for _ in range(8):
        if b&1: r^=a
        a=_xtime(a); b>>=1
    return r

def aes_enc_block(block16, rks):
    s=[list(block16[i:i+4]) for i in range(0,16,4)]
    def add_rk(rk): 
        for r in range(4):
            for c in range(4): s[r][c]^=rk[r*4+c]
    def sub_bytes():
        for r in range(4):
            for c in range(4): s[r][c]=SBOX[s[r][c]]
    def shift_rows():
        s[1]=s[1][1:]+s[1][:1]; s[2]=s[2][2:]+s[2][:2]; s[3]=s[3][3:]+s[3][:3]
    def mix_cols():
        for c in range(4):
            a0,a1,a2,a3=s[0][c],s[1][c],s[2][c],s[3][c]
            s[0][c]=_mul(a0,2)^_mul(a1,3)^a2^a3
            s[1][c]=a0^_mul(a1,2)^_mul(a2,3)^a3
            s[2][c]=a0^a1^_mul(a2,2)^_mul(a3,3)
            s[3][c]=_mul(a0,3)^a1^a2^_mul(a3,2)
    add_rk(rks[0])
    for rnd in range(1,10):
        sub_bytes(); shift_rows(); mix_cols(); add_rk(rks[rnd])
    sub_bytes(); shift_rows(); add_rk(rks[10])
    return bytes([s[r][c] for r in range(4) for c in range(4)])

def aes_ecb_encrypt(blk, key16): return aes_enc_block(blk, aes_key_expand(key16))

def rb128(b):
    carry=0; out=[0]*16
    for i in range(15,-1,-1):
        out[i]=((b[i]<<1)&0xFF)|carry; carry=1 if b[i]&0x80 else 0
    if carry: out[15]^=0x87
    return bytes(out)

def aes_cmac(key16, msg):
    L  = aes_ecb_encrypt(b"\\x00"*16, key16)
    K1 = rb128(list(L)); K2 = rb128(list(K1))
    n = (len(msg)+15)//16
    if n==0: n=1; flag=False
    else: flag=(len(msg)%16)==0
    last = msg[(n-1)*16:]
    if flag: M_last = bytes([a^b for a,b in zip(last, K1)])
    else:
        last_padded = last + b"\\x80" + b"\\x00"*(16-len(last)-1)
        M_last = bytes([a^b for a,b in zip(last_padded, K2)])
    X = b"\\x00"*16
    for i in range(n-1):
        Y = bytes([x^y for x,y in zip(X, msg[i*16:(i+1)*16])])
        X = aes_ecb_encrypt(Y, key16)
    Y = bytes([x^y for x,y in zip(X, M_last)])
    T = aes_ecb_encrypt(Y, key16)
    return T

def bytes_le(hexstr): return bytes.fromhex(hexstr)[::-1]

def build_join_request(deveui_hex, joineui_hex, appkey_hex, devnonce_u16):
    MHDR = b"\\x00"
    JoinEUI = bytes_le(joineui_hex)
    DevEUI  = bytes_le(deveui_hex)
    DevNonce = struct.pack("<H", devnonce_u16)
    msg = MHDR + JoinEUI + DevEUI + DevNonce
    mic = aes_cmac(bytes.fromhex(appkey_hex), msg)[:4]
    return msg + mic, DevNonce

def decrypt_join_accept_and_check(appkey_hex, mhdr, enc_payload):
    key = bytes.fromhex(appkey_hex)
    out = b""
    for i in range(0, len(enc_payload), 16):
        out += aes_ecb_encrypt(enc_payload[i:i+16], key)
    mic_calc = aes_cmac(key, mhdr + out[:-4])[:4]
    if mic_calc != out[-4:]: return None
    return out[:-4]

def derive_session_keys(appkey_hex, appnonce, netid, devnonce):
    key = bytes.fromhex(appkey_hex)
    b1 = bytes([0x01]) + appnonce + netid + devnonce + b"\\x00"*7
    b2 = bytes([0x02]) + appnonce + netid + devnonce + b"\\x00"*7
    nwk_s_key = aes_ecb_encrypt(b1, key)
    app_s_key = aes_ecb_encrypt(b2, key)
    return nwk_s_key, app_s_key

def lorawan_encrypt_frm(appskey, devaddr_le, fcnt, direction, frm_payload):
    out = bytearray(); i=1
    while len(out) < len(frm_payload):
        Ai = b"\\x01"+b"\\x00"*4+bytes([direction])+devaddr_le+struct.pack("<I",fcnt)+b"\\x00"+bytes([i])
        Si = aes_ecb_encrypt(Ai, appskey)
        block = frm_payload[len(out):len(out)+16]
        out.extend(bytes([a^b for a,b in zip(block, Si[:len(block)])])); i+=1
    return bytes(out)

def lorawan_uplink_phy(nwkskey, appskey, devaddr_hex, fcnt, fport, payload_bytes):
    MHDR = b"\\x40"
    devaddr_le = bytes_le(devaddr_hex)
    FCtrl = b"\\x00"
    FCnt  = struct.pack("<H", fcnt & 0xFFFF)
    FHDR  = devaddr_le + FCtrl + FCnt
    enc   = lorawan_encrypt_frm(appskey, devaddr_le, fcnt, 0x00, payload_bytes)
    mac_payload = FHDR + bytes([fport]) + enc
    B0 = b"\\x49"+b"\\x00"*4+b"\\x00"+devaddr_le+struct.pack("<I",fcnt)+b"\\x00"+bytes([len(mac_payload)])
    mic = aes_cmac(nwkskey, B0 + MHDR + mac_payload)[:4]
    return MHDR + mac_payload + mic

# ----------------- Radio helpers --------------------
def radio_setup():
    l = SX126x()
    if not l.begin(SPI_BUS, SPI_CS, PIN_RST, PIN_BUSY, PIN_DIO1, PIN_TXEN, PIN_RXEN):
        raise RuntimeError("SX1262 begin failed")
    l.setDio2RfSwitch(True)
    l.setFrequency(FREQ_HZ)
    l.setTxPower(TX_POWER, l.TX_POWER_SX1262)
    l.setLoRaModulation(SF, BW, CR)
    l.setLoRaPacket(l.HEADER_EXPLICIT, PREAMBLE, 255, True)
    l.setSyncWord(l.LORA_SYNC_WORD_PUBLIC)
    return l

def radio_tx(lora, data: bytes, timeout_ms=5000):
    lora.beginPacket()
    lora.put(data)
    lora.endPacket(timeout_ms)
    lora.wait()

def radio_rx_once(lora, rx_ms=5000):
    lora.request(rx_ms)
    lora.wait(rx_ms/1000.0 + 0.5)
    n = lora.available()
    if n <= 0: return None
    return lora.get(n)

# ----------------- Session persist ------------------
def load_session():
    try:
        with open(SESSION_FILE,"r") as f:
            s = json.load(f)
            return {
                "DevAddr": s["DevAddr"],
                "NwkSKey": bytes.fromhex(s["NwkSKey"]),
                "AppSKey": bytes.fromhex(s["AppSKey"]),
                "FCntUp":  s.get("FCntUp",0)
            }
    except: return None

def save_session(devaddr, nwk, app, fcnt_up):
    with open(SESSION_FILE,"w") as f:
        json.dump({"DevAddr":devaddr,"NwkSKey":nwk.hex(),"AppSKey":app.hex(),"FCntUp":fcnt_up}, f)

# ----------------- Main flow ------------------------
def do_join(lora):
    devnonce = secrets.randbelow(65536)
    jr, devnonce_le = build_join_request(DEVEUI, JOINEUI, APPKEY, devnonce)
    print(f"[Join] sending DevEUI={DEVEUI} JoinEUI={JOINEUI} DevNonce=0x{devnonce:04X}")
    radio_tx(lora, jr)
    t0=time.time()
    while time.time()-t0 < 20:
        pkt = radio_rx_once(lora, 3000)
        if not pkt: 
            continue
        if pkt[0] != 0x20:  # MHDR join-accept
            continue
        ja_plain = decrypt_join_accept_and_check(APPKEY, pkt[:1], pkt[1:])
        if not ja_plain:
            print("[Join] invalid MIC")
            continue
        appnonce = ja_plain[0:3]
        netid    = ja_plain[3:6]
        devaddr  = ja_plain[6:10][::-1].hex().upper()
        nwk, app = derive_session_keys(APPKEY, appnonce, netid, devnonce_le)
        print(f"[Join] accepted DevAddr=0x{devaddr}")
        return devaddr, nwk, app
    return None, None, None

def main():
    if len(DEVEUI)!=16 or len(JOINEUI)!=16 or len(APPKEY)!=32:
        raise ValueError("Fill DEVEUI(16 hex) / JOINEUI(16 hex) / APPKEY(32 hex).")
    lora = radio_setup()
    sess = load_session()
    if sess:
        devaddr = sess["DevAddr"]; nwk=sess["NwkSKey"]; app=sess["AppSKey"]; fcnt=sess["FCntUp"]
        print(f"[Resume] DevAddr=0x{devaddr} FCntUp={fcnt}")
    else:
        devaddr, nwk, app = do_join(lora)
        if not devaddr: raise RuntimeError("Join failed")
        fcnt = 0
        save_session(devaddr, nwk, app, fcnt)

    try:
        while True:
            phy = lorawan_uplink_phy(nwk, app, devaddr, fcnt, FPORT, PAYLOAD)
            radio_tx(lora, phy)
            print(time.strftime("[%H:%M:%S]"), "Uplink FCntUp=", fcnt, "len=", len(phy))
            fcnt += 1
            save_session(devaddr, nwk, app, fcnt)
            time.sleep(UP_PERIOD_SEC)
    finally:
        save_session(devaddr, nwk, app, fcnt)
        lora.end()

if __name__ == "__main__":
    main()
