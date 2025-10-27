# nt35510_8080_16bit.py  —  minimal bring-up for portrait 480x800
import time
from machine import Pin, PWM
import machine 
machine.freq(100_000_000)

W = 480
H = 800

# --- GPIO assignments (change if needed)
DATA_BASE = 0            # D0 on GPIO0 ... D15 on GPIO15
PIN_WR    = 18
PIN_RD    = 16
PIN_CS    = 19
PIN_RS    = 20    # aka DC
PIN_RST   = 21
PIN_BL    = 22

# Pre-grab data pins for speed
_dpins = [Pin(DATA_BASE+i, Pin.OUT, value=0) for i in range(16)]
_wr  = Pin(PIN_WR, Pin.OUT, value=1)
_rd  = Pin(PIN_RD, Pin.OUT, value=1)
_cs  = Pin(PIN_CS, Pin.OUT, value=1)
_rs  = Pin(PIN_RS, Pin.OUT, value=1)
_rst = Pin(PIN_RST, Pin.OUT, value=1)
_bl  = Pin(PIN_BL, Pin.OUT, value=0)  # or PWM later


def _bus_write16(v):
    for i in range(16):
        _dpins[i].value((v >> i) & 1)
    _wr.off()
    _wr.on()

def _cmd(c):
    _rs.off()      # RS=1 means COMMAND on this board
    _cs.off()
    _bus_write16(c)
    _rs.on()
    #_cs.on()

def _dat8(v):
    # write lower 8 bits onto D0..D7 (or pack if you drive all 16)
    for i in range(16):
        _dpins[i].value((v >> i) & 1 if i < 8 else 0)
    _wr.off(); _wr.on()
    _cs.on()

def _dat8s(seq):
    # burst 8-bit sequence (fast enough for init)
    for b in seq:
        _dat8(b)

def hw_reset():
    _rst.on(); time.sleep_ms(5)
    _rst.off(); time.sleep_ms(20)
    _rst.on(); time.sleep_ms(120)

def backlight(percent=100):
    percent = max(0, min(100, percent))
    _bl.value(1 if percent >= 50 else 0)  # simple on/off by default

# ---- DCS helpers shared by many NT35510 panels ----
def sleep_out():  _cmd(0x11); time.sleep_ms(120)
def display_on(): _cmd(0x29); time.sleep_ms(10)


# MADCTL bits: MY=0x80, MX=0x40, MV=0x20, ML=0x10, BGR=0x08, MH=0x04
# NT35510 usually needs BGR=1 for RGB565; experiment if colors are swapped.
ROT_PORTRAIT   = 0x00 | 0x08      # 480(w) × 800(h)
ROT_LANDSCAPE  = 0x20 | 0x08      # MV
ROT_INV_POR    = 0xC0 | 0x08      # MX|MY
ROT_INV_LAND   = 0xE0 | 0x08      # MX|MY|MV


def color565(r,g,b):
    return ((r & 0xF8)<<8) | ((g & 0xFC)<<3) | (b>>3)




if __name__ == "__main__":
    # Just send sleep-out and fill small area red
    _bl.off()
    _rd.on()
    hw_reset()
    _cmd(0x11); _cs.on(); time.sleep_ms(150)
    _cmd(0x01); _cs.on(); time.sleep_ms(150)
    _cmd(0x3A); _dat8(0x55)
    _cmd(0x29); _cs.on()
    _cmd(0x2A); _dat8s([0,0,0,39])
    _cmd(0x2B); _dat8s([0,0,0,39])
    _cmd(0x2C); _cs.on()
    _bl.on()
    for _ in range(40*40):
        _dat8(0xF8); _dat8(0x00)  # red
