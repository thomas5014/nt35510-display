import machine, time, os
machine.freq(260_000_000)

image_num = 0
file = [f for f in os.listdir("/") if "sample" in f][image_num]
width  = int(file.split("_")[1][:3])
height = int(file.split("_")[1][4:7])
print(f"file: {file}  {width}x{height}")

# Allocate both SRAM chunk buffers before any other large allocation
CHUNK_ROWS = 200
buf_A = bytearray(width * CHUNK_ROWS * 2)
buf_B = bytearray(width * CHUNK_ROWS * 2)

from nt35510 import NT35510
from rp2 import PIO, StateMachine, asm_pio, DMA

n = NT35510()

buf = bytearray(width*height*2)    
t0 = time.ticks_us()
with open(file, "rb") as f:
    f.readinto(buf)
    t2 = time.ticks_us()
    n.draw_buf_be(0, 0, width, height, buf)
t1 = time.ticks_us()
print(f"{t1-t0:,}:Total {t2-t0:,}:Read {t1-t2:,}:Draw (PSRAM)")
n.fill(0)
time.sleep(1)
del buf

# ── DMA + PIO SM1 (same setup as speed_image_testing.py) ──────────────────
PIO0_TXF1 = 0x50200014

@asm_pio(
    out_init=(PIO.OUT_HIGH,)*16,
    out_shiftdir=PIO.SHIFT_RIGHT,
    autopull=True, pull_thresh=16,
    sideset_init=PIO.OUT_HIGH,
)
def _pio_16wr_dma():
    out(pins, 16).side(1)
    nop()        .side(0)
    nop()        .side(1)

sm1 = StateMachine(1, _pio_16wr_dma, freq=60_000_000,
                   out_base=machine.Pin(0), sideset_base=machine.Pin(18))

_dma = DMA()
_dma_ctrl = _dma.pack_ctrl(
    size=1, inc_read=True, inc_write=False,
    treq_sel=1, bswap=True, irq_quiet=True, enable=True,
)

def load_image(filename):
    """Load file into GRAM via double-buffered DMA (~49 ms)."""
    row_bytes = width * 2
    mv_a = memoryview(buf_A)
    mv_b = memoryview(buf_B)

    n.set_window(0, 0, width - 1, height - 1)
    n.cs(0)
    n.dc(1)
    sm1.active(1)

    with open(filename, "rb") as f:
        rows = min(CHUNK_ROWS, height)
        dma_chunk = mv_a[:rows * row_bytes]
        f.readinto(dma_chunk)
        dma_rows = rows
        row = rows
        use_a = True

        while True:
            _dma.config(read=dma_chunk, write=PIO0_TXF1, count=dma_rows * width,
                        ctrl=_dma_ctrl, trigger=True)
            if row < height:
                rows = min(CHUNK_ROWS, height - row)
                next_mv = mv_b if use_a else mv_a
                next_chunk = next_mv[:rows * row_bytes]
                f.readinto(next_chunk)
                row += rows
            else:
                next_chunk = None
            while _dma.active():
                pass
            if next_chunk is None:
                break
            dma_chunk = next_chunk
            dma_rows = rows
            use_a = not use_a

    sm1.active(0)
    n.cs(1)

def vscrdef(tfa, vsa, bfa):
    """Define vertical scroll area (VSCRDEF 0x33)."""
    n._cmddata(0x3300, tfa >> 8)
    n._cmddata(0x3301, tfa & 0xFF)
    n._cmddata(0x3302, vsa >> 8)
    n._cmddata(0x3303, vsa & 0xFF)
    n._cmddata(0x3304, bfa >> 8)
    n._cmddata(0x3305, bfa & 0xFF)

def vscrsadd(addr):
    """Set vertical scroll start address (VSCRSADD 0x37)."""
    n._cmddata(0x3700, addr >> 8)
    n._cmddata(0x3701, addr & 0xFF)


# Load image into display GRAM once
t0 = time.ticks_us()
load_image(file)
print(f"loaded in {time.ticks_diff(time.ticks_us(), t0):,} us")

# Full-screen scroll area — no fixed top/bottom rows
vscrdef(0, height, 0)

# Scroll loop — just two register writes per frame, no pixel data
scroll = 0
speed  = 2    # pixels per frame — increase for faster scroll
frame_ms = 16 # target ~60 fps

while True:
    vscrsadd(scroll)
    scroll = (scroll + speed) % height
    time.sleep_ms(frame_ms)
