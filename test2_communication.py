# nt35510_quick_fix.py — LCDWiki NT35510 8080-16 bring-up (RS=1 for CMD per manual)
from machine import Pin
import time

# ----- EDIT IF NEEDED -----
DATA_BASE = 0        # DB0 on GP0 -> DB0..DB15 = GP0..GP15
PIN_WR    = 18
PIN_CS    = 19
PIN_RS    = 20       # RS/D-C: HIGH=COMMAND, LOW=DATA (per manual!)
PIN_RD    = 16
PIN_RST   = 21
PIN_BL    = 22
WIDTH, HEIGHT = 800, 480  # many of these are 800x480

# ----- GPIO -----
wr  = Pin(PIN_WR,  Pin.OUT, value=1)
cs  = Pin(PIN_CS,  Pin.OUT, value=1)   # active-low
rs  = Pin(PIN_RS,  Pin.OUT, value=0)   # LOW=data, HIGH=command
rd  = Pin(PIN_RD,  Pin.OUT, value=1)   # keep HIGH (no reads)
rst = Pin(PIN_RST, Pin.OUT, value=1)
bl  = Pin(PIN_BL,  Pin.OUT, value=0)

DP = [Pin(DATA_BASE + i, Pin.OUT, value=0) for i in range(16)]

def _wr_pulse():
    wr(0); wr(1)

def _put16(v):
    for i in range(16):
        DP[i].value((v >> i) & 1)
    _wr_pulse()

def _put8_low(v8):
    for i in range(8):
        DP[i].value((v8 >> i) & 1)
    _wr_pulse()

def cmd(c8):
    cs(0); rs(1)      # RS=1 => COMMAND (per manual)
    _put8_low(c8 & 0xFF)
    cs(1)

def data8(d8):
    cs(0); rs(0)      # RS=0 => DATA
    _put8_low(d8 & 0xFF)
    cs(1)

def data16(p16):
    cs(0); rs(0)
    _put16(p16 & 0xFFFF)
    cs(1)

# DCS
SLEEPOUT  = 0x11
DISPON    = 0x29
COLMOD    = 0x3A
MADCTL    = 0x36
CASET     = 0x2A
PASET     = 0x2B
RAMWR     = 0x2C

def reset_panel():
    cs(1); rs(0); rd(1); wr(1)
    rst(0); time.sleep_ms(30)
    rst(1); time.sleep_ms(150)

def init_simple():
    # wake
    cmd(SLEEPOUT); time.sleep_ms(150)
    # 16bpp
    cmd(COLMOD); data8(0x55); time.sleep_ms(5)
    # orientation: start with BGR off; toggle later if colors swapped
    cmd(MADCTL); data8(0x00); time.sleep_ms(5)
    # on
    cmd(DISPON); time.sleep_ms(20)

def set_window_full():
    cmd(CASET); data8(0x00); data8(0x00); data8((WIDTH-1)>>8); data8((WIDTH-1)&0xFF)
    cmd(PASET); data8(0x00); data8(0x00); data8((HEIGHT-1)>>8); data8((HEIGHT-1)&0xFF)
    cmd(RAMWR)

def flood(color565, count):
    hi = (color565 >> 8) & 0xFF; lo = color565 & 0xFF
    cs(0); rs(0)
    for _ in range(count):
        _put16((hi << 8) | lo)
    cs(1)

def demo():
    bl(1)
    time.sleep(.5)
    bl(0)
    time.sleep(.5)
    bl(1)
    reset_panel()
    init_simple()
    set_window_full()
    # write a big chunk of blue; should see a flash/stripe if GRAM is receiving
    flood(0x001F, WIDTH*80)     # a few rows
    # try full-fill colors
    for color in (0x0000, 0xF800, 0x07E0, 0x001F, 0xFFFF):
        set_window_full()
        flood(color, WIDTH*HEIGHT)

demo()
