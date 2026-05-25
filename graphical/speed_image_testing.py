import machine, random, time, os
machine.freq(260_000_000)

image_num = 0
file = [f for f in os.listdir("/") if "sample" in f][image_num]
width = int(file.split("_")[1][:3])
height = int(file.split("_")[1][4:7])
print(f"Displaying file: {file}, with w and h of {width} and {height} respectively.")

CHUNK_ROWS = 200  # 192 KB each — both fit in SRAM; 400 rows (375 KB) would overflow
buf_A = bytearray(width * CHUNK_ROWS * 2)
buf_B = bytearray(width * CHUNK_ROWS * 2)

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

def buf_location(b):
    addr = uctypes.addressof(b)
    return f"{'SRAM' if addr >= 0x20000000 else 'PSRAM'} @ {hex(addr)} ({len(b)//1024}KB)"

import uctypes, gc, micropython
from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer

n = NT35510()
# gc.collect()
# micropython.mem_info()  # show free/used memory before allocating buf_B
frac_buf = buf_A  # alias so draw_file_chunked / draw_file_dma_chunked still work
print("buf_A:", buf_location(buf_A))
print("buf_B:", buf_location(buf_B))
buf = bytearray(width*height*2)               # 750 KB — too big for remaining SRAM → PSRAM
print("buf:  ", buf_location(buf))

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

if False:
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

# Prime: one bit-bang GRAM write while GPIO is still in SIO mode.
# StateMachine() below steals GPIO0-15+18 for PIO; after that, any bit-bang
# draw silently fails.  The PIO path only works if the display has already
# received a complete CASET+PASET+CMD_RAMWR transaction at least once.
n.fill(0)

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

GPIO_SET          = 0xD000001C  # SIO atomic-set
DC_MASK           = 1 << 20    # DC on GPIO20
# IO_BANK0 atomic aliases for GPIO18 CTRL (IO_BANK0_BASE=0x40028000, GPIO18 offset=0x94).
# Atomic SET/CLR only touch the written bits — FUNCSEL is left as-is after sm1.init().
GPIO18_CTRL_SET   = 0x4002A094  # IO_BANK0 base + 0x2000 (atomic SET) + 0x94
GPIO18_CTRL_CLR   = 0x4002B094  # IO_BANK0 base + 0x3000 (atomic CLR) + 0x94
OUTOVER_HIGH      = 3 << 12    # CTRL bits 13:12 = OUTOVER; value 3 = force output HIGH

def _pio_claim():
    """Reclaim GPIO0-15+GPIO18 for PIO (call after set_window).
    sm1.init() pulses WR LOW during the SIO→PIO FUNCSEL transition because PIO output
    register starts at 0 before sideset_init=OUT_HIGH is applied.  Fix: force WR HIGH
    via OUTOVER atomic SET (leaves FUNCSEL alone) for the duration of sm1.init.
    After sm1.init the PIO output register already holds WR=1 (sideset_init=OUT_HIGH),
    so atomic CLR of OUTOVER is safe — WR stays HIGH from PIO."""
    machine.mem32[GPIO_SET]        = DC_MASK      # DC=1
    machine.mem32[GPIO18_CTRL_SET] = OUTOVER_HIGH  # lock WR HIGH
    sm1.init(_pio_16wr_dma, freq=SM1_FREQ, out_base=machine.Pin(0), sideset_base=machine.Pin(18))
    machine.mem32[GPIO18_CTRL_CLR] = OUTOVER_HIGH  # release — PIO already holds WR=1

def _sio_restore():
    """Return GPIO0-15+GPIO18 to SIO so bit-bang set_window works."""
    for i in range(16):
        machine.Pin(i, machine.Pin.OUT)
    machine.Pin(18, machine.Pin.OUT, value=1)  # WR idle-high

def draw_file_dma_chunked(filename, x=0, y=0, w=width, h=height):
    row_bytes = w * 2
    mv = memoryview(frac_buf)
    read_us = 0
    draw_us = 0

    _sio_restore()
    n.cs(0)
    n.set_window(x, y, x + w - 1, y + h - 1)  # one CMD_RAMWR for the whole image
    n._bus_write16(0x0000)  # NT35510 requires a DC=1 WR strobe before PIO/DMA pixel writes
    _pio_claim()
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
    _sio_restore()
    print(f"  read:{read_us:,} draw:{draw_us:,} ({h//CHUNK_ROWS + (1 if h%CHUNK_ROWS else 0)} chunks)")

if False:
    n.fill(0)
    t0 = time.ticks_us()
    draw_file_dma_chunked(file)
    t1 = time.ticks_us()
    print(f"{t1-t0:,} us DMA+PIO single-buf")

# ── Double-buffered DMA: overlap flash read with DMA draw ──────────────────
# While DMA drains buf_A → display, CPU fills buf_B from flash, then swap.
# Total ≈ N_chunks × max(read/chunk, draw/chunk) + last_draw
#       ≈ 4 × 10.2 ms + 4.9 ms ≈ 45.7 ms  (vs 62 ms single-buf)
# dma_idle shows time spent waiting for DMA after each read finishes.
# For all but the last chunk this will be ~0 (read is the bottleneck).

def draw_file_dma_double(filename, x=0, y=0, w=width, h=height):
    row_bytes = w * 2
    mv_a = memoryview(buf_A)
    mv_b = memoryview(buf_B)
    read_us = 0
    idle_us = 0

    _sio_restore()
    n.cs(0)
    n.set_window(x, y, x + w - 1, y + h - 1)
    n._bus_write16(0x0000)  # NT35510 requires a DC=1 WR strobe before PIO/DMA pixel writes
    _pio_claim()
    sm1.active(1)

    with open(filename, "rb") as f:
        # Prime: read the very first chunk so DMA has something to start on
        rows = min(CHUNK_ROWS, h)
        dma_chunk = mv_a[:rows * row_bytes]
        t = time.ticks_us()
        f.readinto(dma_chunk)
        read_us += time.ticks_diff(time.ticks_us(), t)
        dma_rows = rows
        row = rows
        use_a = True   # which buffer DMA will consume this iteration

        while True:
            # Kick off DMA on whichever buffer was just filled
            _dma.config(read=dma_chunk, write=PIO0_TXF1, count=dma_rows * w,
                        ctrl=_dma_ctrl, trigger=True)

            # While DMA runs, fill the idle buffer with the next chunk
            if row < h:
                rows = min(CHUNK_ROWS, h - row)
                next_mv = mv_b if use_a else mv_a
                next_chunk = next_mv[:rows * row_bytes]
                t = time.ticks_us()
                f.readinto(next_chunk)        # overlaps with DMA
                read_us += time.ticks_diff(time.ticks_us(), t)
                row += rows
            else:
                next_chunk = None

            # Wait for DMA to finish (usually already done since read > draw)
            t = time.ticks_us()
            while _dma.active():
                pass
            idle_us += time.ticks_diff(time.ticks_us(), t)

            if next_chunk is None:
                break

            dma_chunk = next_chunk
            dma_rows = rows
            use_a = not use_a

    sm1.active(0)
    n.cs(1)
    _sio_restore()
    chunks = h // CHUNK_ROWS + (1 if h % CHUNK_ROWS else 0)
    print(f"  read:{read_us:,} dma_idle:{idle_us:,} ({chunks} chunks)")

if False:
    n.fill(0)
    t0 = time.ticks_us()
    draw_file_dma_double(file)
    t1 = time.ticks_us()
    print(f"{t1-t0:,} us DMA+PIO double-buf")

# ── DMA directly from PSRAM ────────────────────────────────────────────────
# buf is already in PSRAM (0x11xxxxxx). DMA reads through XIP/QMI (QPI at
# 130 MHz). One set_window + one DMA transfer — no chunking.
# Timed twice: cold cache first, then warm cache (steady-state per-frame cost
# when the same image is drawn repeatedly from PSRAM).

def draw_psram_dma():
    _sio_restore()
    n.cs(0)
    n.set_window(0, 0, width - 1, height - 1)
    n._bus_write16(0x0000)  # NT35510 requires a DC=1 WR strobe before PIO/DMA pixel writes
    _pio_claim()
    sm1.active(1)
    _dma.config(read=buf, write=PIO0_TXF1, count=width * height,
                ctrl=_dma_ctrl, trigger=True)
    while _dma.active():
        pass
    sm1.active(0)
    n.cs(1)
    _sio_restore()

@micropython.viper
def _fill_red_be(b: object):
    """Fill buffer with big-endian RGB565 red (0xF8, 0x00 per pixel)."""
    p = ptr8(b)
    n: int = int(len(b)) & ~1
    i: int = 0
    while i < n:
        p[i]     = 0xF8
        p[i + 1] = 0x00
        i += 2

# ── DMA sanity check: SRAM → display ──────────────────────────────────────────
# Fill buf_A (SRAM) with bright red and DMA the top CHUNK_ROWS to the display.
# If the top band turns red, the DMA+PIO path works; image just has dark content.
_fill_red_be(buf_A)
_sio_restore()
n.cs(0)
n.set_window(0, 0, width - 1, CHUNK_ROWS - 1)
n._bus_write16(0xF800)
# n.fill(0)
# n.pixel(0,0,0)
_pio_claim()
sm1.active(1)
_dma.config(read=memoryview(buf_A), write=PIO0_TXF1, count=width * CHUNK_ROWS,
            ctrl=_dma_ctrl, trigger=True)
while _dma.active():
    pass
sm1.active(0)
n.cs(1)
_sio_restore()
print("red-band DMA done — top 200 rows should be RED")

if True:
    t0 = time.ticks_us()
    with open(file, "rb") as f:
        f.readinto(buf)
    t_load = time.ticks_diff(time.ticks_us(), t0)
    print(f"load→PSRAM: {t_load:,} us")
    print(f"buf[0:4]: {[hex(b) for b in buf[:4]]}")

    t0 = time.ticks_us()
    draw_psram_dma()
    t1 = time.ticks_us()
    print(f"{t1-t0:,} us DMA from PSRAM (cold cache)")

    # # Bit-bang fallback with same buf — compare with DMA result.
    # _sio_restore()
    # n.cs(0)
    # n.draw_buf_be(0, 0, width, height, buf)
    # print("bit-bang draw done")
