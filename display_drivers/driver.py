# nt35510.py  — NT35510 16-bit 8080-parallel driver for RP2350 MicroPython
# - Uses a PIO SM to clock 16-bit words to DB0..DB15 with a WR strobe
# - Command/data select via DC pin; CS handled in Python
# - Minimal init (0x11, 0x3A 0x55, 0x36, 0x29). Adjust as needed.
#
# Wiring (example; change in PINMAP below):
#   DB0..DB15  -> 16 contiguous GPIOs (required by PIO 'out pins, 16')
#   WR         -> one GPIO (strobe)
#   CS, DC, RST, BL -> GPIOs
#
# Notes:
# - Tie RD high on the panel if you don't read.
# - Many 8080-16bit panels accept 8-bit command indices; we write commands
#   as 8-bit on the lower byte (upper byte 0). Some break out CMD/DATA lines.
# - Some NT35510 boards need additional magic registers for timing/gamma.
#   Start with this; if you see noise or wrong colors, check:
#     * DC polarity (0=command, 1=data here)
#     * Byte order (RGB/BGR), set via MADCTL (0x36)
#     * X/Y offsets; adjust X_OFFSET/Y_OFFSET for glass vs. RAM origin
#
from machine import Pin
import machine 
print(machine.freq())
#machine.freq()
from micropython import const
import time

try:
    from rp2 import PIO, StateMachine, asm_pio
except ImportError:
    # RP2350 MicroPython should expose rp2; if not, fallback to bitbang (slow)
    PIO = None

# ---------- Basic LCD constants ----------
CMD_SLEEP_OUT   = const(0x11)
CMD_DISPLAY_ON  = const(0x29)
CMD_DISPLAY_OFF = const(0x28)
CMD_COLMOD      = const(0x3A)  # pixel format
CMD_MADCTL      = const(0x36)  # memory access control
CMD_CASET       = const(0x2A)  # column address set
CMD_PASET       = const(0x2B)  # page (row) address set
CMD_RAMWR       = const(0x2C)  # memory write

COLMOD_16BPP    = const(0x55)  # 16-bit (RGB565)

# Adjust if your glass has a RAM offset
X_OFFSET = const(0)
Y_OFFSET = const(0)

# ---------- Pin mapping (EDIT THESE) ----------
class PINMAP:
    # 16 contiguous pins for data bus D0..D15 (lowest to highest bit)
    DATA_BASE = 0          # D0 on GPIO0 => D0..D15 occupy GPIO0..GPIO15
    WR        = 18         # WR strobe pin
    CS        = 19         # Chip select
    DC        = 20         # Data/Command (0=cmd, 1=data)
    RST       = 21         # Reset (active low)
    BL        = 22         # Backlight (optional)
    RD        = 16



# ---------- PIO to output 16 bits and pulse WR ----------
# We set 'out pins, 16' to present data, and use sideset to toggle WR low/high.
# sideset[1] = WR, with initial high. Two NOPs create the WR falling/rising edges.
if PIO:
    # --- PIO: write 16 data bits, then pulse WR low->high using SET pin ---
    @asm_pio(
        out_init=(PIO.OUT_HIGH,)*16,       # D0..D15 outputs
        out_shiftdir=PIO.SHIFT_RIGHT,
        autopull=True, pull_thresh=16,
        set_init=(PIO.OUT_HIGH,)           # WR starts high
    )
    def pio_16wr():
        out(pins, 16)          # put 16 bits on D0..D15
        set(pins, 0)   [1]     # WR = 0 (low pulse)
        set(pins, 1)   [1]     # WR = 1 (back high)

class NT35510:
    def __init__(self, width=480, height=800, rotate=0, pinmap=PINMAP, sm_id=0, freq=30_000_000):
        self.width  = width
        self.height = height
        self.rotate = rotate & 3

        self.count = 0

        # Control pins
        self.cs  = Pin(pinmap.CS,  Pin.OUT, value=1)
        self.dc  = Pin(pinmap.DC,  Pin.OUT, value=1)
        self.rst = Pin(pinmap.RST, Pin.OUT, value=1)
        self.bl  = Pin(pinmap.BL,  Pin.OUT, value=0)
        self.rd  = Pin(pinmap.RD,  Pin.OUT, value=1)

        # Data bus base + 16 pins contiguous
        self._data_base = pinmap.DATA_BASE
        self._data_mask = 0
        for i in range(16):
            Pin(self._data_base + i, Pin.OUT)

        # WR pin is controlled by PIO sideset
        self._wr = Pin(pinmap.WR, Pin.OUT, value=1)

        # PIO state machine for 16-bit writes
        if PIO:
            self.sm = StateMachine(
                sm_id, pio_16wr,
                freq=freq,
                out_base=Pin(self._data_base),
                sideset_base=self._wr,
            )
            self.sm.active(1)
        else:
            self.sm = None  # bit-bang fallback if needed

        self.reset()
        self._init_panel()
        self.set_backlight(True)

    # --------- Low-level helpers ---------
    def reset(self, t_low=0.02, t_high=0.12):
        self.cs(1)
        self.dc(1)
        self.rst(0)
        time.sleep(t_low)
        self.rst(1)
        time.sleep(t_high)

    def set_backlight(self, on=True):
        try:
            self.bl(1 if on else 0)
        except Exception:
            pass

    def _cs_low(self):  self.cs(0)
    def _cs_high(self): self.cs(1)

    def _dc_cmd(self):  self.dc(0)
    def _dc_data(self): self.dc(1)

    def _write16(self, value):
        self.count += 1
        if self.count%1000 == 0:
            print("count", self.count)

        """Write one 16-bit word using PIO or bit-bang."""
        if self.sm:
            # pack into 16-bit and push
            self.sm.put(value & 0xFFFF)
        else:
            # Slow fallback: set bus then toggle WR manually
            v = value & 0xFFFF
            for i in range(16):
                Pin(self._data_base + i).value((v >> i) & 1)
            self._wr(0)
            self._wr(1)

    def _write_buf16(self, buf):
        """
        Write a buffer of big-endian RGB565 pixels (len(buf) must be even).
        Works on MicroPython builds without memoryview.cast().
        """
        mv = memoryview(buf)
        n = len(mv)
        if n & 1:
            raise ValueError("buf length must be even")

        if self.sm:
            # Fast path: push 16-bit words to the PIO
            put = self.sm.put
            for i in range(0, n, 2):
                put((mv[i] << 8) | mv[i + 1])
        else:
            # Bit-bang fallback
            for i in range(0, n, 2):
                self._write16((mv[i] << 8) | mv[i + 1])


    # Command writes (8-bit index; upper byte 0)
    def write_cmd(self, cmd8):
        self._cs_low()
        self._dc_cmd()
        self._write16(cmd8 & 0xFF)   # cmd on low byte; many boards accept this in 16-bit mode
        self._cs_high()

    def write_data8(self, data8):
        self._cs_low()
        self._dc_data()
        self._write16(data8 & 0xFF)
        self._cs_high()

    def write_data16(self, data16):
        self._cs_low()
        self._dc_data()
        self._write16(data16 & 0xFFFF)
        self._cs_high()

    def write_data(self, buf):
        self._cs_low()
        self._dc_data()
        self._write_buf16(buf)
        self._cs_high()

    # ---------- Init sequence ----------
    def _init_panel(self):
        # Wake & 16bpp & orientation & display on
        self.write_cmd(CMD_SLEEP_OUT)
        time.sleep(0.12)

        self.write_cmd(CMD_COLMOD)
        self.write_data8(COLMOD_16BPP)   # 16-bit RGB565

        # MADCTL (memory access control): tweak for rotation/BGR
        # Bit meanings (typical): MY MX MV ML BGR MH
        # We'll set BGR=1 commonly used; adjust if colors look swapped.
        mad = 0x08  # BGR=1 (set bit 3)
        if self.rotate == 1:   # 90°
            mad ^= 0x20 | 0x40 | 0x08  # MX|MV plus keep BGR
        elif self.rotate == 2: # 180°
            mad ^= 0x80 | 0x40 | 0x08  # MY|MX
        elif self.rotate == 3: # 270°
            mad ^= 0x80 | 0x20 | 0x08  # MY|MV
        self.write_cmd(CMD_MADCTL)
        self.write_data8(mad)

        self.write_cmd(CMD_DISPLAY_ON)
        time.sleep(0.02)

    # ---------- Address window & drawing ----------
    def set_window(self, x0, y0, x1, y1):
        x0 += X_OFFSET; x1 += X_OFFSET
        y0 += Y_OFFSET; y1 += Y_OFFSET

        # Column
        self.write_cmd(CMD_CASET)
        self._cs_low(); self._dc_data()
        self._write16((x0 >> 8) & 0xFF); self._write16(x0 & 0xFF)
        self._write16((x1 >> 8) & 0xFF); self._write16(x1 & 0xFF)
        self._cs_high()

        # Row
        self.write_cmd(CMD_PASET)
        self._cs_low(); self._dc_data()
        self._write16((y0 >> 8) & 0xFF); self._write16(y0 & 0xFF)
        self._write16((y1 >> 8) & 0xFF); self._write16(y1 & 0xFF)
        self._cs_high()

        self.write_cmd(CMD_RAMWR)

    def draw_pixel(self, x, y, color565):
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self.set_window(x, y, x, y)
        # color565 must be big-endian (hi,lo) when streamed; here we send as 16
        self._cs_low(); self._dc_data()
        self._write16(color565)
        self._cs_high()

    def fill_rect(self, x, y, w, h, color565):
        if w <= 0 or h <= 0: return
        x1 = x + w - 1
        y1 = y + h - 1
        if x >= self.width or y >= self.height: return
        if x1 < 0 or y1 < 0: return
        if x < 0:   w -= (0 - x); x = 0
        if y < 0:   h -= (0 - y); y = 0
        if x + w > self.width:  w = self.width - x
        if y + h > self.height: h = self.height - y
        if w <= 0 or h <= 0: return

        self.set_window(x, y, x + w - 1, y + h - 1)

        # Prepare a line buffer of w pixels (big-endian)
        hi = (color565 >> 8) & 0xFF
        lo = color565 & 0xFF
        line = bytearray(2 * w)
        for i in range(w):
            line[2*i] = hi; line[2*i+1] = lo

        self._cs_low(); self._dc_data()
        for _ in range(h):
            self._write_buf16(line)
        self._cs_high()

    def blit_rgb565(self, x, y, w, h, buf_be):
        """
        Blit an RGB565 image already arranged as big-endian (hi,lo) per pixel.
        len(buf_be) == 2*w*h
        """
        if w <= 0 or h <= 0: return
        self.set_window(x, y, x + w - 1, y + h - 1)
        self._cs_low(); self._dc_data()
        self._write_buf16(buf_be)
        self._cs_high()
