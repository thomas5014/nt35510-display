# --- PIO 8080 16-bit write engine for RP2350/RP2040 (MicroPython) ---
import time
from machine import Pin, PWM
from rp2 import PIO, asm_pio, StateMachine
from array import array

W = 480
H = 800

# --- Pins (same as your script) ---
DATA_BASE = 0            # D0..D15 on GPIO0..15
PIN_WR    = 18           # WR (active-low strobe)
PIN_RD    = 16           # keep HIGH for write-only
PIN_CS    = 19
PIN_RS    = 20           # RS/DC  (your board: RS=0 data? RS=1 cmd?  adjust if needed)
PIN_RST   = 21
PIN_BL    = 22

_dpins = [Pin(DATA_BASE+i, Pin.OUT, value=0) for i in range(16)]
_wr  = Pin(PIN_WR, Pin.OUT, value=1)
_rd  = Pin(PIN_RD, Pin.OUT, value=1)
_cs  = Pin(PIN_CS, Pin.OUT, value=1)
_rs  = Pin(PIN_RS, Pin.OUT, value=0)     # choose a safe default
_rst = Pin(PIN_RST, Pin.OUT, value=1)
_bl  = Pin(PIN_BL, Pin.OUT, value=0)

# ---------------- PIO program ----------------
# - Autopull 16 bits from TX FIFO to PINs
# - sideset pin drives WR (1 = idle/high, 0 = low)
# Timing: one WR low cycle + one WR high cycle; add [n] to stretch if needed.
@asm_pio(
    out_init=PIO.OUT_LOW,
    out_shiftdir=PIO.SHIFT_LEFT,
    autopull=True, pull_thresh=16,
    sideset_init=PIO.OUT_HIGH
)
def mpu8080_16w():
    # Put next 16-bit word on D[15:0]
    out(pins, 16)          .side(1)      # keep WR high while placing data
    nop()                  .side(0)      # WR low (pulse start)   (stretch by adding [1] if needed)
    nop()                  .side(1)      # WR high (latch on rising edge)

# State machine: run fast; you can go very high since WR is generated in PIO
SM_FREQ = 40_000_000      # 40 MHz PIO clock; WR pulse is a few cycles long

sm = StateMachine(0, mpu8080_16w, freq=SM_FREQ,
                  out_base=Pin(DATA_BASE),
                  sideset_base=Pin(PIN_WR))

def pio_start():
    # Ensure bus is idle before enabling PIO
    _wr.value(1); _cs.value(1); _rd.value(1)
    sm.active(1)

def pio_stop():
    sm.active(0)

# --------- High-level helpers using PIO writes ----------
def _bus_write16_pio(v: int):
    # Single 16-bit write
    sm.put(v & 0xFFFF)

def _bus_write_repeat(color565: int, count: int):
    # Fast constant-color flood without building a big buffer
    # (sm.put() accepts small ints repeatedly)
    c = color565 & 0xFFFF
    for _ in range(count):
        sm.put(c)

def _bus_write_buf_u16(buf_u16):
    # Burst from a Python array('H')—much faster than per-pixel loops in Python
    for v in buf_u16:
        sm.put(v)

# --- Your existing helpers, now calling PIO ---
def _cmd(c):
    _rs.low()             # RS=0 -> COMMAND  (flip if your board uses opposite)
    _cs.low()
    _bus_write16_pio(c)
    _cs.high()

def _data(v):
    _rs.high()            # RS=1 -> DATA
    _cs.low()
    _bus_write16_pio(v)
    _cs.high()

def hw_reset():
    _rst.high(); time.sleep_ms(50)
    _rst.low();  time.sleep_ms(50)
    _rst.high(); time.sleep_ms(120)

# --- Window / Draw (your register style 0x2A00.. sub-index form) ---
def set_window(x0, y0, x1, y1):
    _cmd(0x2A00); _data(x0 >> 8)
    _cmd(0x2A01); _data(x0 & 0xFF)
    _cmd(0x2A02); _data(x1 >> 8)
    _cmd(0x2A03); _data(x1 & 0xFF)

    _cmd(0x2B00); _data(y0 >> 8)
    _cmd(0x2B01); _data(y0 & 0xFF)
    _cmd(0x2B02); _data(y1 >> 8)
    _cmd(0x2B03); _data(y1 & 0xFF)

    _cmd(0x2C00)  # RAMWR

def fill_rect(x, y, width, height, color):
    set_window(x, y, x + width - 1, y + height - 1)
    # Stream pixels with CS low and RS=data the whole time:
    _rs.high(); _cs.low()
    _bus_write_repeat(color, width * height)
    _cs.high()

# Optional: buffer write (e.g., scanline)
def write_scanline(x, y, pixels_u16):
    set_window(x, y, x + len(pixels_u16) - 1, y)
    _rs.high(); _cs.low()
    _bus_write_buf_u16(pixels_u16)
    _cs.high()

# ---------------- Example init & test ----------------
def init_minimal():
    # Minimal “DCS-like” path; keep your vendor table if needed
    _cmd(0x1100); time.sleep_ms(130)        # SLPOUT
    _cmd(0x3A00); _data(0x55)               # COLMOD 16bpp
    _cmd(0x3600); _data(0x08)               # MADCTL (portrait + BGR if needed)
    _cmd(0x1300); time.sleep_ms(10)         # NORON
    _cmd(0x2900); time.sleep_ms(10)         # DISPON

def color565(r,g,b):
    return ((r & 0xF8)<<8)|((g & 0xFC)<<3)|((b>>3)&0x1F)

if __name__ == "__main__":
    _bl.on()
    pio_start()
    _rd.high()
    hw_reset()

    # If you have that long vendor init table, call it here instead:
    # init_extra()
    init_minimal()

    # Paint bars as a sanity check
    fill_rect(0,    0, W, H//5, color565(255,0,0))
    fill_rect(0, H//5, W, H//5, color565(0,255,0))
    fill_rect(0,2*H//5, W, H//5, color565(0,0,255))
    fill_rect(0,3*H//5, W, H//5, color565(255,255,255))
    fill_rect(0,4*H//5, W, H//5, color565(0,0,0))
    print("DONE")
