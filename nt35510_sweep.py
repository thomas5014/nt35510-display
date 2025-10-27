# nt35510_sweep.py — brute-force bring-up for 8080-16 TFT (NT35510-ish)
from machine import Pin
import time

# ---- Your pins ----
DB_BASE = 0          # DB0..DB15 = GP0..GP15
PIN_RD  = 16
PIN_WR  = 18
PIN_CS  = 19
PIN_RS  = 20
PIN_RST = 21
PIN_BL  = 22

# ---- Control pins ----
wr  = Pin(PIN_WR,  Pin.OUT, value=1)
cs  = Pin(PIN_CS,  Pin.OUT, value=1)  # tie to GND for testing if you can
rs  = Pin(PIN_RS,  Pin.OUT, value=0)
rd  = Pin(PIN_RD,  Pin.OUT, value=1)  # hold HIGH; tie to 3V3 if you can
rst = Pin(PIN_RST, Pin.OUT, value=1)
bl  = Pin(PIN_BL,  Pin.OUT, value=0)

DP = [Pin(DB_BASE + i, Pin.OUT, value=0) for i in range(16)]

# ---- helpers ----
def wr_pulse():
    wr(0); wr(1)

def put16(v, reversed_bits=False):
    if not reversed_bits:
        for i in range(16):
            DP[i].value((v >> i) & 1)
    else:
        # MSB on DB0 (fully reversed bus)
        for i in range(16):
            DP[i].value((v >> (15 - i)) & 1)
    wr_pulse()

def put8_low(v8, reversed_bits=False):
    if not reversed_bits:
        for i in range(8):
            DP[i].value((v8 >> i) & 1)
    else:
        # still drive the 8 pins closest to DB0 (but reversed)
        for i in range(8):
            DP[i].value((v8 >> (7 - i)) & 1)
    wr_pulse()

def cmd(c8, rs_cmd_high=True, cmd_mode="low8", reversed_bits=False):
    cs(0)
    # rs polarity: True => RS=1 is COMMAND, False => RS=0 is COMMAND
    rs(1 if rs_cmd_high else 0)
    if cmd_mode == "low8":
        put8_low(c8 & 0xFF, reversed_bits)
    else:
        val = ((c8 & 0xFF) << 8) | (c8 & 0xFF)
        put16(val, reversed_bits)
    cs(1)

def data8(d8, rs_cmd_high=True, reversed_bits=False):
    cs(0)
    rs(0 if rs_cmd_high else 1)  # opposite of command
    put8_low(d8 & 0xFF, reversed_bits)
    cs(1)

def data16(p16, rs_cmd_high=True, reversed_bits=False):
    cs(0)
    rs(0 if rs_cmd_high else 1)
    put16(p16 & 0xFFFF, reversed_bits)
    cs(1)

# DCS
SLEEPOUT, DISPON, COLMOD, MADCTL, CASET, PASET, RAMWR = 0x11, 0x29, 0x3A, 0x36, 0x2A, 0x2B, 0x2C

def reset_panel():
    cs(1); rs(0); rd(1); wr(1)
    rst(0); time.sleep_ms(50)
    rst(1); time.sleep_ms(180)

def init_basic(rs_cmd_high, cmd_mode, reversed_bits):
    # extra-gentle wake
    for _ in range(3):
        cmd(SLEEPOUT, rs_cmd_high, cmd_mode, reversed_bits); time.sleep_ms(150)
    cmd(COLMOD, rs_cmd_high, cmd_mode, reversed_bits); data8(0x55, rs_cmd_high, reversed_bits); time.sleep_ms(5)
    # try both BGR off first
    cmd(MADCTL, rs_cmd_high, cmd_mode, reversed_bits); data8(0x00, rs_cmd_high, reversed_bits); time.sleep_ms(5)
    for _ in range(3):
        cmd(DISPON, rs_cmd_high, cmd_mode, reversed_bits); time.sleep_ms(30)

def set_window(w, h, order_xy, rs_cmd_high, cmd_mode, reversed_bits):
    x1, y1 = w - 1, h - 1
    if order_xy:
        cmd(CASET, rs_cmd_high, cmd_mode, reversed_bits)
        data8((0 >> 8) & 0xFF, rs_cmd_high, reversed_bits); data8(0 & 0xFF, rs_cmd_high, reversed_bits)
        data8((x1 >> 8) & 0xFF, rs_cmd_high, reversed_bits); data8(x1 & 0xFF, rs_cmd_high, reversed_bits)
        cmd(PASET, rs_cmd_high, cmd_mode, reversed_bits)
        data8((0 >> 8) & 0xFF, rs_cmd_high, reversed_bits); data8(0 & 0xFF, rs_cmd_high, reversed_bits)
        data8((y1 >> 8) & 0xFF, rs_cmd_high, reversed_bits); data8(y1 & 0xFF, rs_cmd_high, reversed_bits)
    else:
        cmd(PASET, rs_cmd_high, cmd_mode, reversed_bits)
        data8(0, rs_cmd_high, reversed_bits); data8(0, rs_cmd_high, reversed_bits)
        data8((y1 >> 8) & 0xFF, rs_cmd_high, reversed_bits); data8(y1 & 0xFF, rs_cmd_high, reversed_bits)
        cmd(CASET, rs_cmd_high, cmd_mode, reversed_bits)
        data8(0, rs_cmd_high, reversed_bits); data8(0, rs_cmd_high, reversed_bits)
        data8((x1 >> 8) & 0xFF, rs_cmd_high, reversed_bits); data8(x1 & 0xFF, rs_cmd_high, reversed_bits)
    cmd(RAMWR, rs_cmd_high, cmd_mode, reversed_bits)

def flood_block(color565, count, rs_cmd_high, reversed_bits):
    hi, lo = (color565 >> 8) & 0xFF, color565 & 0xFF
    cs(0); rs(0 if rs_cmd_high else 1)
    for _ in range(count):
        put16((hi << 8) | lo, reversed_bits)
    cs(1)

def blink_bl():
    for _ in range(2):
        bl(0); time.sleep_ms(150)
        bl(1); time.sleep_ms(150)

def sweep():
    rst(0)
    time.sleep(1)
    rst(1)
    bl(1)
    blink_bl()
    combos = []
    for w,h in ((800,480),(480,800)):
        for rs_cmd_high in (True, False):             # RS=1 cmd vs RS=0 cmd
            for cmd_mode in ("low8","mir16"):        # CMD on low8 vs mirrored 16
                for order_xy in (True, False):       # CASET->PASET vs PASET->CASET
                    for rev in (False, True):        # data bit order
                        combos.append((w,h,rs_cmd_high,cmd_mode,order_xy,rev))

    # Keep RD high, CS can be tied to GND physically if desired
    for idx, (W,H,rs_high,cmode,order_xy,revbits) in enumerate(combos, 1):
        print("Try %02d/%02d: %dx%d, RS_CMD_HIGH=%s, CMD=%s, ORDER=%s, REVBITS=%s" %
              (idx, len(combos), W, H, rs_high, cmode, "XY" if order_xy else "YX", revbits))
        reset_panel()
        time.sleep_ms(50)
        init_basic(rs_high, cmode, revbits)
        set_window(W, H, order_xy, rs_high, cmode, revbits)
        # write a modest block (~60k pixels) so a stripe/flash is visible
        flood_block(0x001F, W*80, rs_high, revbits)
        time.sleep_ms(180)

if __name__ == "__main__":
    sweep()
