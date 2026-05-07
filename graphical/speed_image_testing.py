from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
import machine, random, time, os
machine.freq(260_000_000)

image_num = 0
file = [f for f in os.listdir("/") if "sample" in f][image_num]
width = int(file.split("_")[1][:3])
height = int(file.split("_")[1][4:7])
print(f"Displaying file: {file}, with w and h of {width} and {height} respectively.")

@micropython.viper
def switch_bytes(buf: object):
    p = ptr8(buf)
    n = int(len(buf)) & ~1
    tmp: int = 0
    i: int = 0
    while i < n:
        tmp = p[i]
        p[i] = p[i + 1]
        p[i + 1] = tmp
        i += 2

    return buf

import uctypes

def buf_location(b):
    addr = uctypes.addressof(b)
    return f"{'SRAM' if addr >= 0x20000000 else 'PSRAM'} @ {hex(addr)} ({len(b)//1024}KB)"

n = NT35510()
CHUNK_ROWS = 200  # 192KB — confirmed to fit in SRAM; 400 rows (375KB) overflows to PSRAM
frac_buf = bytearray(width * CHUNK_ROWS * 2)
print("frac_buf:", buf_location(frac_buf))
temp = bytearray(520*1024*2)
buf = bytearray(width*height*2)               # PSRAM (for other tests)
del temp
print("buf:     ", buf_location(buf))

def draw_file_chunked(filename, x=0, y=0, w=width, h=height):
    # Reads flash → SRAM chunk → draw from SRAM.  No PSRAM in the hot path.
    row_bytes = w * 2
    mv = memoryview(frac_buf)
    read_us = 0
    draw_us = 0
    with open(filename, "rb") as f:
        row = 0
        while row < h:
            rows = min(CHUNK_ROWS, h - row)
            chunk = mv[:rows * row_bytes]
            t = time.ticks_us()
            f.readinto(chunk)
            read_us += time.ticks_diff(time.ticks_us(), t)
            t = time.ticks_us()
            n.draw_buf_be(x, y + row, w, rows, chunk)
            draw_us += time.ticks_diff(time.ticks_us(), t)
            row += rows
    print(f"  read:{read_us:,} draw:{draw_us:,} ({h//CHUNK_ROWS + (1 if h%CHUNK_ROWS else 0)} chunks)")

n.fill(0)                                                 
t = time.ticks_us()
n.fill(0xF800)
print(f"fill: {time.ticks_diff(time.ticks_us(), t):,} us")

t0 = time.ticks_us()
draw_file_chunked(file)
t1 = time.ticks_us()
print(f"{t1-t0:,} us chunked (flash->SRAM->display)")

# comparison: full PSRAM buf approach
t0 = time.ticks_us()
with open(file, "rb") as f:
    f.readinto(buf)
    t2 = time.ticks_us()
    n.draw_buf_be(0, 0, width, height, buf)
t1 = time.ticks_us()
print(f"{t1-t0:,}:Total {t2-t0:,}:Read {t1-t2:,}:Draw (PSRAM)")

# ── DMA + PIO SM1 draw path ────────────────────────────────────────────────
# SM1 uses 1-bit non-optional sideset for WR (pin 18).
# 3 instructions/pixel at 60 MHz → 50 ns/pixel → ~19 ms for 480×800.
# bswap=True swaps the two bytes of each halfword so big-endian file data
# arrives in the PIO TX FIFO as a correct 16-bit pixel (hi<<8|lo).
# CS is held low manually across all chunks so one CMD_RAMWR covers the whole
# image; GRAM address auto-advances without intermediate set_window calls.

from rp2 import PIO, StateMachine, asm_pio, DMA

PIO0_TXF1 = 0x50200014  # PIO0 SM1 TX FIFO
SM1_FREQ   = 60_000_000  # 60 MHz → 16.7 ns/instruction

@asm_pio(
    out_init=(PIO.OUT_HIGH,)*16,
    out_shiftdir=PIO.SHIFT_RIGHT,
    autopull=True, pull_thresh=16,
    sideset_init=PIO.OUT_HIGH,   # WR starts HIGH
)
def _pio_16wr_dma():
    out(pins, 16).side(1)        # pixel on D0-D15, WR=1 (1-cycle setup time)
    nop()        .side(0)        # WR=0 (write strobe low)
    nop()        .side(1)        # WR=1 (write complete)

sm1 = StateMachine(1, _pio_16wr_dma, freq=SM1_FREQ,
                   out_base=machine.Pin(0), sideset_base=machine.Pin(18))

_dma = DMA()
_dma_ctrl = _dma.pack_ctrl(
    size=1,           # halfword — each transfer moves one 16-bit pixel
    inc_read=True,
    inc_write=False,  # always target PIO TX FIFO (fixed address)
    treq_sel=1,       # DREQ_PIO0_TX1
    bswap=True,       # [hi,lo] bytes in buffer → hi<<8|lo in FIFO
    irq_quiet=True,
    enable=True,
)

def draw_file_dma_chunked(filename, x=0, y=0, w=width, h=height):
    row_bytes = w * 2
    mv = memoryview(frac_buf)
    read_us = 0
    draw_us = 0

    n.set_window(x, y, x + w - 1, y + h - 1)  # one CMD_RAMWR for the whole image
    n.cs(0)   # hold CS low — GRAM address advances until CS rises
    n.dc(1)   # data mode
    sm1.active(1)

    with open(filename, "rb") as f:
        row = 0
        while row < h:
            rows = min(CHUNK_ROWS, h - row)
            chunk = mv[:rows * row_bytes]
            t = time.ticks_us()
            f.readinto(chunk)
            read_us += time.ticks_diff(time.ticks_us(), t)
            t = time.ticks_us()
            _dma.config(read=chunk, write=PIO0_TXF1, count=rows * w,
                        ctrl=_dma_ctrl, trigger=True)
            while _dma.active():
                pass
            draw_us += time.ticks_diff(time.ticks_us(), t)
            row += rows

    sm1.active(0)
    n.cs(1)
    print(f"  read:{read_us:,} draw:{draw_us:,} ({h//CHUNK_ROWS + (1 if h%CHUNK_ROWS else 0)} chunks)")

n.fill(0)
t0 = time.ticks_us()
draw_file_dma_chunked(file)
t1 = time.ticks_us()
print(f"{t1-t0:,} us DMA+PIO (flash->SRAM->PIO0/SM1)")

