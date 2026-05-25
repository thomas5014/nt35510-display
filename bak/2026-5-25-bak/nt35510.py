from machine import Pin, PWM # type: ignore
import machine, micropython, framebuf, time
from micropython import const
CLOCK = const(260_000_000)
machine.freq(CLOCK)  # 250MHz for faster GPIO toggling


@micropython.viper
def color565(r:int,g:int,b:int) -> int:
    return ((r & 0xF8)<<8) | ((g & 0xFC)<<3) | (b>>3)

@micropython.viper
def cx_bright(color:int, brightness:int) -> int:
    if brightness == 0:
        return 0
    r = ((color >> 11) & 0x1F) * brightness // 100
    g = ((color >> 5)  & 0x3F) * brightness // 100
    b = (color & 0x1F) * brightness // 100
    return (r << 11) | (g << 5) | b
    
SIO_BASE   = 0xD0000000  # alias for SIO (faster to access, same hardware)
GPIO_OUT   = SIO_BASE + 0x10
GPIO_SET   = SIO_BASE + 0x1C
DATA_MASK  = const(0xFFFF)  # GPIO0–15
WR_MASK    = const(1 << 18)
DC_MASK    = const(1 << 20)
# IO_BANK0 atomic aliases for GPIO18 CTRL (base=0x40028000, GPIO18 offset=0x94)
# Atomic SET/CLR only modify the written bits — FUNCSEL is preserved after sm1.init().
GPIO18_CTRL_SET = 0x4002A094  # IO_BANK0 base + 0x2000 (atomic SET) + 0x94
GPIO18_CTRL_CLR = 0x4002B094  # IO_BANK0 base + 0x3000 (atomic CLR) + 0x94
OUTOVER_HIGH    = const(3 << 12)  # CTRL bits 13:12 = OUTOVER; value 3 = force output HIGH

@micropython.asm_thumb
def _strobe_bulk(r0, r1, r2, r3):
    # r0=addr, r1=low, r2=high, r3=count//16
    label(LOOP)
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    sub(r3, 1)
    bne(LOOP)

@micropython.asm_thumb
def _strobe_rem(r0, r1, r2, r3):
    # r0=addr, r1=low, r2=high, r3=remainder
    label(LOOP)
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    sub(r3, 1)
    bne(LOOP)

@micropython.asm_thumb
def _strobe_n(r0, r1, r2, r3):
    # r0=addr, r1=low, r2=high, r3=count
    label(LOOP)
    str(r1, [r0, 0])
    str(r2, [r0, 0])
    sub(r3, 1)
    bne(LOOP)

from rp2 import PIO, StateMachine, asm_pio, DMA

PIO0_TXF1 = 0x50200014  # PIO0 SM1 TX FIFO
SM1_FREQ   = 130_000_000  # 60 MHz → 16.7 ns/instruction

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
_dma_ctrl_le = _dma.pack_ctrl(
    size=1,
    inc_read=True,
    inc_write=False,
    treq_sel=1,
    bswap=False,      # little-endian RGB565 framebuffer — no swap needed
    irq_quiet=True,
    enable=True,
)

class MyFrameBuffer(framebuf.FrameBuffer):
    def __init__(self, width, height, buf=None):
        self.buffer = memoryview(buf) if buf else memoryview(bytearray(width * height * 2))
        self.width = width
        self.height = height
        super().__init__(self.buffer, self.width, self.height, framebuf.RGB565)

class NT35510:
    def __init__(self, wr=18, cs=19, dc=20, rst=21, bl=22, rd=40, width=480, height=800):
        # Data bus: must initialize so RP2350 clears pad isolation before viper writes
        for i in range(16):
            Pin(i, Pin.OUT, value=0)
        self.wr  = Pin(wr, Pin.OUT, value=1)
        self.rd  = Pin(rd, Pin.OUT, value=1)
        self.cs  = Pin(cs, Pin.OUT, value=1)
        self.dc  = Pin(dc, Pin.OUT, value=1)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.bl  = Pin(bl, Pin.OUT, value=0)  # or PWM later

        self.width = width
        self.height = height

        self.init_display()
        self.MyFrameBuffer = MyFrameBuffer

    def init_display(self):
        # Just send sleep-out and fill small area red
        #_bl.off()
        self.bl.on()
        self.rd.high()
        self.cs.low()
        self.hw_reset()
        self.init_extra()
        self._cmd(0x3a00); self._data(0x55)               # set pixel format
        self._cmd(0x1100); time.sleep_ms(120)        # exit sleep booster on
        self._cmd(0x2900)                            # display on

    @micropython.viper
    def _bus_write16_too_fast(self, v: int, count: int):
        pout = ptr32(GPIO_OUT)
        v = pout[0] & ~DATA_MASK | (v & DATA_MASK) | DC_MASK
        low:int  = v & ~WR_MASK
        high:int = v | WR_MASK
        bulk:int = count >> 4
        rem:int  = count & 15
        if bulk:
            _strobe_bulk(GPIO_OUT, low, high, bulk)
        if rem:
            _strobe_rem(GPIO_OUT, low, high, rem)

    @micropython.viper
    def _bus_write16_fast(self, v: int, count: int):
        pout = ptr32(GPIO_OUT)
        v = pout[0] & ~DATA_MASK | (v & DATA_MASK) | DC_MASK
        _strobe_n(GPIO_OUT, v & ~WR_MASK, v | WR_MASK, count)
        
    @micropython.viper
    def _bus_write16(self, v:int):
        pout = ptr32(GPIO_OUT)
        v:int = pout[0] & ~DATA_MASK | (v & DATA_MASK) | DC_MASK

        pout[0] = v & ~WR_MASK
        pout[0] = v | WR_MASK

    @micropython.viper
    def _cmd(self, v:int):
        pout = ptr32(GPIO_OUT)
        v:int = pout[0] & ~DC_MASK & ~DATA_MASK | (v & DATA_MASK)

        pout[0] = v & ~WR_MASK
        pout[0] = v | WR_MASK
        
    @micropython.viper
    def _data(self, v:int):
        pout = ptr32(GPIO_OUT)
        v:int = pout[0] & ~DATA_MASK | (v & DATA_MASK) | DC_MASK

        pout[0] = v & ~WR_MASK
        pout[0] = v | WR_MASK

    @micropython.viper
    def _cmddata(self, c: int, d: int):
        pout = ptr32(GPIO_OUT)
        v:int = pout[0] & ~DC_MASK & ~DATA_MASK | (c & DATA_MASK)
        pout[0] = v & ~WR_MASK
        pout[0] = v | WR_MASK

        v:int = pout[0] & ~DATA_MASK | (d & DATA_MASK) | DC_MASK
        pout[0] = v & ~WR_MASK
        pout[0] = v | WR_MASK

        
    @micropython.viper
    def _bus_write16_buf(self, buf):
        pout = ptr32(GPIO_OUT)
        base_low:int = pout[0] & ~DATA_MASK & ~WR_MASK | DC_MASK
        i:int = 0
        buf_p = ptr16(buf)
        buf_len:int = int(len(buf)) // 2

        while i < buf_len:
            low:int = base_low | buf_p[i]
            pout[0] = low
            pout[0] = low | WR_MASK
            i += 1

    def _bus_write16_buf_dmapio(self, buf, width, height):
        # NT35510 requires a DC=1 WR strobe (via bit-bang) before PIO/DMA pixel writes work.
        # set_window leaves DC=0 (CMD_RAMWR is a command); _bus_write16 gives the needed prime.
        self._bus_write16(0x0000)
        # Lock WR HIGH via OUTOVER during sm1.init() — the SIO→PIO FUNCSEL transition
        # briefly drives WR LOW (PIO output register = 0 before sideset_init applies).
        # Atomic SET/CLR leave FUNCSEL intact after sm1.init() changes it to PIO.
        machine.mem32[GPIO_SET]        = DC_MASK       # DC=1 before FUNCSEL switch
        machine.mem32[GPIO18_CTRL_SET] = OUTOVER_HIGH  # lock WR HIGH
        sm1.init(_pio_16wr_dma, freq=SM1_FREQ, out_base=machine.Pin(0), sideset_base=machine.Pin(18))
        machine.mem32[GPIO18_CTRL_CLR] = OUTOVER_HIGH  # release — PIO already holds WR=1
        sm1.active(1)
        _dma.config(read=buf, write=PIO0_TXF1, count=width * height,
                    ctrl=_dma_ctrl_le, trigger=True)
        while _dma.active():
            pass
        sm1.active(0)
        # Restore GPIO0-15 and GPIO18 to SIO so bit-bang path continues to work
        for i in range(16):
            machine.Pin(i, machine.Pin.OUT)
        machine.Pin(18, machine.Pin.OUT, value=1)  # WR idle-high

    @micropython.viper
    def _bus_write16_buf_be(self, buf):
        # Read 4 bytes (2 big-endian pixels) per ptr32 load — halves SRAM transactions vs ptr8×2.
        # ptr32 on little-endian ARM: word = byte0 | (byte1<<8) | (byte2<<16) | (byte3<<24)
        # File layout per pair: [pix0_hi, pix0_lo, pix1_hi, pix1_lo]
        # → pix0 for display = (byte0<<8)|byte1 = ((word&0xFF)<<8)|((word>>8)&0xFF)
        # → pix1 for display = (byte2<<8)|byte3 = (((word>>16)&0xFF)<<8)|((word>>24)&0xFF)
        pout = ptr32(GPIO_OUT)
        base_low:int = pout[0] & ~DATA_MASK & ~WR_MASK | DC_MASK
        i:int = 0
        buf_p = ptr32(buf)
        buf_len:int = int(len(buf)) >> 2  # number of 4-byte words

        while i < buf_len:
            word:int = buf_p[i]
            low0:int = base_low | ((word & 0xFF) << 8) | ((word >> 8) & 0xFF)
            pout[0] = low0
            pout[0] = low0 | WR_MASK
            low1:int = base_low | (((word >> 16) & 0xFF) << 8) | ((word >> 24) & 0xFF)
            pout[0] = low1
            pout[0] = low1 | WR_MASK
            i += 1

    def hw_reset(self):
        self.rst.high(); time.sleep_ms(50)
        self.rst.low(); time.sleep_ms(50)
        self.rst.high(); time.sleep_ms(120)

    @micropython.viper
    def set_window(self, x0: int, y0: int, x1: int, y1: int):
        pout = ptr32(GPIO_OUT)
        g:int  = pout[0]
        cb:int = g & ~DC_MASK & ~DATA_MASK
        db:int = g & ~DATA_MASK | DC_MASK
        wr:int = WR_MASK
        v:int  = 0

        v = cb | 0x2A00
        pout[0] = v & ~wr;  pout[0] = v | wr  # again no semicolons, just showing pairs
        v = db | (x0 >> 8)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2A01
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (x0 & 0xFF)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2A02
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (x1 >> 8)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2A03
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (x1 & 0xFF)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2B00
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (y0 >> 8)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2B01
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (y0 & 0xFF)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2B02
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (y1 >> 8)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2B03
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = db | (y1 & 0xFF)
        pout[0] = v & ~wr
        pout[0] = v | wr
        v = cb | 0x2C00
        pout[0] = v & ~wr
        pout[0] = v | wr

    @micropython.viper
    def fill_rect(self, x: int, y: int, width: int, height: int, color: int):
        self.set_window(x, y, x + width - 1, y + height - 1)
        self._bus_write16_fast(color, width*height)

    @micropython.viper
    def fill(self,color: int):
        self.fill_rect(0, 0, self.width, self.height, color)

    def draw_buf(self, x, y, width, height, buf):
        self.set_window(x, y, x + width - 1, y + height - 1)
        self._bus_write16_buf_dmapio(buf, width, height)

    @micropython.viper
    def draw_buf_be(self, x: int, y: int, width: int, height: int, buf: object):
        # Big-endian variant: swaps bytes during draw, skipping a separate switch_bytes pass.
        self.set_window(x, y, x + width - 1, y + height - 1)
        self._bus_write16_buf_be(buf)

    @micropython.viper
    def draw_framebuf(self, x: int, y: int, fb: object):
        # only works with MyFrameBuffer
        self.draw_buf(x, y, fb.width, fb.height, fb.buffer)

    @micropython.viper
    def pixel(self, x:int,y:int,color:int):
        self.set_window(x, y, x, y)
        self._bus_write16(color)

    @micropython.viper
    def hline(self, x:int,y:int,w:int,color:int):
        self.set_window(x, y, x+w-1, y)
        _bus_write16 = self._bus_write16
        for i in range(w):
            _bus_write16(color)

    @micropython.viper
    def vline(self, x:int,y:int,h:int,color:int):
        self.set_window(x, y, x, y+h-1)
        _bus_write16 = self._bus_write16
        for i in range(h):
            _bus_write16(color)

    def fb_text(self, text, x=0, y=0, color=-1, bg=0):
        str_length = max(8, len(text) * 8 + 8)
        fb = self.MyFrameBuffer(str_length, 8)
        if bg:
            fb.fill(bg)
        else:
            fb.fill(0)
        fb.text(text, 0, 0, color)
        self.draw_framebuf(x, y, fb)

    def init_extra(self):
        _cmd = self._cmd
        _data = self._data
        _cmd(0xF000); _data(0x55)
        _cmd(0xF001); _data(0xAA)
        _cmd(0xF002); _data(0x52)
        _cmd(0xF003); _data(0x08)
        _cmd(0xF004); _data(0x01)
        
        _cmd(0xB600); _data(0x34)
        _cmd(0xB601); _data(0x34)
        _cmd(0xB602); _data(0x34)

        _cmd(0xB000); _data(0x0D)
        _cmd(0xB001); _data(0x0D)
        _cmd(0xB002); _data(0x0D)
        
        _cmd(0xB700); _data(0x24)
        _cmd(0xB701); _data(0x24)
        _cmd(0xB702); _data(0x24)

        _cmd(0xB100); _data(0x0D)
        _cmd(0xB101); _data(0x0D)
        _cmd(0xB102); _data(0x0D)
        
        _cmd(0xB800); _data(0x24)
        _cmd(0xB801); _data(0x24)
        _cmd(0xB802); _data(0x24)

        _cmd(0xB200); _data(0x00)

        
        _cmd(0xB900); _data(0x24)
        _cmd(0xB901); _data(0x24)
        _cmd(0xB902); _data(0x24)

        _cmd(0xB300); _data(0x05)
        _cmd(0xB301); _data(0x05)
        _cmd(0xB302); _data(0x05)
        
        _cmd(0xBA00); _data(0x34)
        _cmd(0xBA01); _data(0x34)
        _cmd(0xBA02); _data(0x34)
        
        _cmd(0xB500); _data(0x0B)
        _cmd(0xB501); _data(0x0B)
        _cmd(0xB502); _data(0x0B)
        
        _cmd(0xBC00); _data(0X00)
        _cmd(0xBC01); _data(0xA3)
        _cmd(0xBC02); _data(0X00)
        
        _cmd(0xBD00); _data(0x00)
        _cmd(0xBD01); _data(0xA3)
        _cmd(0xBD02); _data(0x00)
        
        _cmd(0xBE00); _data(0x00)
        _cmd(0xBE01); _data(0x63)
        
    
        _cmd(0xD100); _data(0x00)
        _cmd(0xD101); _data(0x37)
        _cmd(0xD102); _data(0x00)
        _cmd(0xD103); _data(0x52)
        _cmd(0xD104); _data(0x00)
        _cmd(0xD105); _data(0x7B)
        _cmd(0xD106); _data(0x00)
        _cmd(0xD107); _data(0x99)
        _cmd(0xD108); _data(0x00)
        _cmd(0xD109); _data(0xB1)
        _cmd(0xD10A); _data(0x00)
        _cmd(0xD10B); _data(0xD2)
        _cmd(0xD10C); _data(0x00)
        _cmd(0xD10D); _data(0xF6)
        _cmd(0xD10E); _data(0x01)
        _cmd(0xD10F); _data(0x27)
        _cmd(0xD110); _data(0x01)
        _cmd(0xD111); _data(0x4E)
        _cmd(0xD112); _data(0x01)
        _cmd(0xD113); _data(0x8C)
        _cmd(0xD114); _data(0x01)
        _cmd(0xD115); _data(0xBE)
        _cmd(0xD116); _data(0x02)
        _cmd(0xD117); _data(0x0B)
        _cmd(0xD118); _data(0x02)
        _cmd(0xD119); _data(0x48)
        _cmd(0xD11A); _data(0x02)
        _cmd(0xD11B); _data(0x4A)
        _cmd(0xD11C); _data(0x02)
        _cmd(0xD11D); _data(0x7E)
        _cmd(0xD11E); _data(0x02)
        _cmd(0xD11F); _data(0xBC)
        _cmd(0xD120); _data(0x02)
        _cmd(0xD121); _data(0xE1)
        _cmd(0xD122); _data(0x03)
        _cmd(0xD123); _data(0x10)
        _cmd(0xD124); _data(0x03)
        _cmd(0xD125); _data(0x31)
        _cmd(0xD126); _data(0x03)
        _cmd(0xD127); _data(0x5A)
        _cmd(0xD128); _data(0x03)
        _cmd(0xD129); _data(0x73)
        _cmd(0xD12A); _data(0x03)
        _cmd(0xD12B); _data(0x94)
        _cmd(0xD12C); _data(0x03)
        _cmd(0xD12D); _data(0x9F)
        _cmd(0xD12E); _data(0x03)
        _cmd(0xD12F); _data(0xB3)
        _cmd(0xD130); _data(0x03)
        _cmd(0xD131); _data(0xB9)
        _cmd(0xD132); _data(0x03)
        _cmd(0xD133); _data(0xC1)
        
        _cmd(0xD200); _data(0x00)
        _cmd(0xD201); _data(0x37)
        _cmd(0xD202); _data(0x00)
        _cmd(0xD203); _data(0x52)
        _cmd(0xD204); _data(0x00)
        _cmd(0xD205); _data(0x7B)
        _cmd(0xD206); _data(0x00)
        _cmd(0xD207); _data(0x99)
        _cmd(0xD208); _data(0x00)
        _cmd(0xD209); _data(0xB1)
        _cmd(0xD20A); _data(0x00)
        _cmd(0xD20B); _data(0xD2)
        _cmd(0xD20C); _data(0x00)
        _cmd(0xD20D); _data(0xF6)
        _cmd(0xD20E); _data(0x01)
        _cmd(0xD20F); _data(0x27)
        _cmd(0xD210); _data(0x01)
        _cmd(0xD211); _data(0x4E)
        _cmd(0xD212); _data(0x01)
        _cmd(0xD213); _data(0x8C)
        _cmd(0xD214); _data(0x01)
        _cmd(0xD215); _data(0xBE)
        _cmd(0xD216); _data(0x02)
        _cmd(0xD217); _data(0x0B)
        _cmd(0xD218); _data(0x02)
        _cmd(0xD219); _data(0x48)
        _cmd(0xD21A); _data(0x02)
        _cmd(0xD21B); _data(0x4A)
        _cmd(0xD21C); _data(0x02)
        _cmd(0xD21D); _data(0x7E)
        _cmd(0xD21E); _data(0x02)
        _cmd(0xD21F); _data(0xBC)
        _cmd(0xD220); _data(0x02)
        _cmd(0xD221); _data(0xE1)
        _cmd(0xD222); _data(0x03)
        _cmd(0xD223); _data(0x10)
        _cmd(0xD224); _data(0x03)
        _cmd(0xD225); _data(0x31)
        _cmd(0xD226); _data(0x03)
        _cmd(0xD227); _data(0x5A)
        _cmd(0xD228); _data(0x03)
        _cmd(0xD229); _data(0x73)
        _cmd(0xD22A); _data(0x03)
        _cmd(0xD22B); _data(0x94)
        _cmd(0xD22C); _data(0x03)
        _cmd(0xD22D); _data(0x9F)
        _cmd(0xD22E); _data(0x03)
        _cmd(0xD22F); _data(0xB3)
        _cmd(0xD230); _data(0x03)
        _cmd(0xD231); _data(0xB9)
        _cmd(0xD232); _data(0x03)
        _cmd(0xD233); _data(0xC1)
        
        _cmd(0xD300); _data(0x00)
        _cmd(0xD301); _data(0x37)
        _cmd(0xD302); _data(0x00)
        _cmd(0xD303); _data(0x52)
        _cmd(0xD304); _data(0x00)
        _cmd(0xD305); _data(0x7B)
        _cmd(0xD306); _data(0x00)
        _cmd(0xD307); _data(0x99)
        _cmd(0xD308); _data(0x00)
        _cmd(0xD309); _data(0xB1)
        _cmd(0xD30A); _data(0x00)
        _cmd(0xD30B); _data(0xD2)
        _cmd(0xD30C); _data(0x00)
        _cmd(0xD30D); _data(0xF6)
        _cmd(0xD30E); _data(0x01)
        _cmd(0xD30F); _data(0x27)
        _cmd(0xD310); _data(0x01)
        _cmd(0xD311); _data(0x4E)
        _cmd(0xD312); _data(0x01)
        _cmd(0xD313); _data(0x8C)
        _cmd(0xD314); _data(0x01)
        _cmd(0xD315); _data(0xBE)
        _cmd(0xD316); _data(0x02)
        _cmd(0xD317); _data(0x0B)
        _cmd(0xD318); _data(0x02)
        _cmd(0xD319); _data(0x48)
        _cmd(0xD31A); _data(0x02)
        _cmd(0xD31B); _data(0x4A)
        _cmd(0xD31C); _data(0x02)
        _cmd(0xD31D); _data(0x7E)
        _cmd(0xD31E); _data(0x02)
        _cmd(0xD31F); _data(0xBC)
        _cmd(0xD320); _data(0x02)
        _cmd(0xD321); _data(0xE1)
        _cmd(0xD322); _data(0x03)
        _cmd(0xD323); _data(0x10)
        _cmd(0xD324); _data(0x03)
        _cmd(0xD325); _data(0x31)
        _cmd(0xD326); _data(0x03)
        _cmd(0xD327); _data(0x5A)
        _cmd(0xD328); _data(0x03)
        _cmd(0xD329); _data(0x73)
        _cmd(0xD32A); _data(0x03)
        _cmd(0xD32B); _data(0x94)
        _cmd(0xD32C); _data(0x03)
        _cmd(0xD32D); _data(0x9F)
        _cmd(0xD32E); _data(0x03)
        _cmd(0xD32F); _data(0xB3)
        _cmd(0xD330); _data(0x03)
        _cmd(0xD331); _data(0xB9)
        _cmd(0xD332); _data(0x03)
        _cmd(0xD333); _data(0xC1)

        
        _cmd(0xD400); _data(0x00)
        _cmd(0xD401); _data(0x37)
        _cmd(0xD402); _data(0x00)
        _cmd(0xD403); _data(0x52)
        _cmd(0xD404); _data(0x00)
        _cmd(0xD405); _data(0x7B)
        _cmd(0xD406); _data(0x00)
        _cmd(0xD407); _data(0x99)
        _cmd(0xD408); _data(0x00)
        _cmd(0xD409); _data(0xB1)
        _cmd(0xD40A); _data(0x00)
        _cmd(0xD40B); _data(0xD2)
        _cmd(0xD40C); _data(0x00)
        _cmd(0xD40D); _data(0xF6)
        _cmd(0xD40E); _data(0x01)
        _cmd(0xD40F); _data(0x27)
        _cmd(0xD410); _data(0x01)
        _cmd(0xD411); _data(0x4E)
        _cmd(0xD412); _data(0x01)
        _cmd(0xD413); _data(0x8C)
        _cmd(0xD414); _data(0x01)
        _cmd(0xD415); _data(0xBE)
        _cmd(0xD416); _data(0x02)
        _cmd(0xD417); _data(0x0B)
        _cmd(0xD418); _data(0x02)
        _cmd(0xD419); _data(0x48)
        _cmd(0xD41A); _data(0x02)
        _cmd(0xD41B); _data(0x4A)
        _cmd(0xD41C); _data(0x02)
        _cmd(0xD41D); _data(0x7E)
        _cmd(0xD41E); _data(0x02)
        _cmd(0xD41F); _data(0xBC)
        _cmd(0xD420); _data(0x02)
        _cmd(0xD421); _data(0xE1)
        _cmd(0xD422); _data(0x03)
        _cmd(0xD423); _data(0x10)
        _cmd(0xD424); _data(0x03)
        _cmd(0xD425); _data(0x31)
        _cmd(0xD426); _data(0x03)
        _cmd(0xD427); _data(0x5A)
        _cmd(0xD428); _data(0x03)
        _cmd(0xD429); _data(0x73)
        _cmd(0xD42A); _data(0x03)
        _cmd(0xD42B); _data(0x94)
        _cmd(0xD42C); _data(0x03)
        _cmd(0xD42D); _data(0x9F)
        _cmd(0xD42E); _data(0x03)
        _cmd(0xD42F); _data(0xB3)
        _cmd(0xD430); _data(0x03)
        _cmd(0xD431); _data(0xB9)
        _cmd(0xD432); _data(0x03)
        _cmd(0xD433); _data(0xC1)

        
        _cmd(0xD500); _data(0x00)
        _cmd(0xD501); _data(0x37)
        _cmd(0xD502); _data(0x00)
        _cmd(0xD503); _data(0x52)
        _cmd(0xD504); _data(0x00)
        _cmd(0xD505); _data(0x7B)
        _cmd(0xD506); _data(0x00)
        _cmd(0xD507); _data(0x99)
        _cmd(0xD508); _data(0x00)
        _cmd(0xD509); _data(0xB1)
        _cmd(0xD50A); _data(0x00)
        _cmd(0xD50B); _data(0xD2)
        _cmd(0xD50C); _data(0x00)
        _cmd(0xD50D); _data(0xF6)
        _cmd(0xD50E); _data(0x01)
        _cmd(0xD50F); _data(0x27)
        _cmd(0xD510); _data(0x01)
        _cmd(0xD511); _data(0x4E)
        _cmd(0xD512); _data(0x01)
        _cmd(0xD513); _data(0x8C)
        _cmd(0xD514); _data(0x01)
        _cmd(0xD515); _data(0xBE)
        _cmd(0xD516); _data(0x02)
        _cmd(0xD517); _data(0x0B)
        _cmd(0xD518); _data(0x02)
        _cmd(0xD519); _data(0x48)
        _cmd(0xD51A); _data(0x02)
        _cmd(0xD51B); _data(0x4A)
        _cmd(0xD51C); _data(0x02)
        _cmd(0xD51D); _data(0x7E)
        _cmd(0xD51E); _data(0x02)
        _cmd(0xD51F); _data(0xBC)
        _cmd(0xD520); _data(0x02)
        _cmd(0xD521); _data(0xE1)
        _cmd(0xD522); _data(0x03)
        _cmd(0xD523); _data(0x10)
        _cmd(0xD524); _data(0x03)
        _cmd(0xD525); _data(0x31)
        _cmd(0xD526); _data(0x03)
        _cmd(0xD527); _data(0x5A)
        _cmd(0xD528); _data(0x03)
        _cmd(0xD529); _data(0x73)
        _cmd(0xD52A); _data(0x03)
        _cmd(0xD52B); _data(0x94)
        _cmd(0xD52C); _data(0x03)
        _cmd(0xD52D); _data(0x9F)
        _cmd(0xD52E); _data(0x03)
        _cmd(0xD52F); _data(0xB3)
        _cmd(0xD530); _data(0x03)
        _cmd(0xD531); _data(0xB9)
        _cmd(0xD532); _data(0x03)
        _cmd(0xD533); _data(0xC1)
        
        _cmd(0xD600); _data(0x00)
        _cmd(0xD601); _data(0x37)
        _cmd(0xD602); _data(0x00)
        _cmd(0xD603); _data(0x52)
        _cmd(0xD604); _data(0x00)
        _cmd(0xD605); _data(0x7B)
        _cmd(0xD606); _data(0x00)
        _cmd(0xD607); _data(0x99)
        _cmd(0xD608); _data(0x00)
        _cmd(0xD609); _data(0xB1)
        _cmd(0xD60A); _data(0x00)
        _cmd(0xD60B); _data(0xD2)
        _cmd(0xD60C); _data(0x00)
        _cmd(0xD60D); _data(0xF6)
        _cmd(0xD60E); _data(0x01)
        _cmd(0xD60F); _data(0x27)
        _cmd(0xD610); _data(0x01)
        _cmd(0xD611); _data(0x4E)
        _cmd(0xD612); _data(0x01)
        _cmd(0xD613); _data(0x8C)
        _cmd(0xD614); _data(0x01)
        _cmd(0xD615); _data(0xBE)
        _cmd(0xD616); _data(0x02)
        _cmd(0xD617); _data(0x0B)
        _cmd(0xD618); _data(0x02)
        _cmd(0xD619); _data(0x48)
        _cmd(0xD61A); _data(0x02)
        _cmd(0xD61B); _data(0x4A)
        _cmd(0xD61C); _data(0x02)
        _cmd(0xD61D); _data(0x7E)
        _cmd(0xD61E); _data(0x02)
        _cmd(0xD61F); _data(0xBC)
        _cmd(0xD620); _data(0x02)
        _cmd(0xD621); _data(0xE1)
        _cmd(0xD622); _data(0x03)
        _cmd(0xD623); _data(0x10)
        _cmd(0xD624); _data(0x03)
        _cmd(0xD625); _data(0x31)
        _cmd(0xD626); _data(0x03)
        _cmd(0xD627); _data(0x5A)
        _cmd(0xD628); _data(0x03)
        _cmd(0xD629); _data(0x73)
        _cmd(0xD62A); _data(0x03)
        _cmd(0xD62B); _data(0x94)
        _cmd(0xD62C); _data(0x03)
        _cmd(0xD62D); _data(0x9F)
        _cmd(0xD62E); _data(0x03)
        _cmd(0xD62F); _data(0xB3)
        _cmd(0xD630); _data(0x03)
        _cmd(0xD631); _data(0xB9)
        _cmd(0xD632); _data(0x03)
        _cmd(0xD633); _data(0xC1)



        
        _cmd(0xF000); _data(0x55)
        _cmd(0xF001); _data(0xAA)
        _cmd(0xF002); _data(0x52)
        _cmd(0xF003); _data(0x08)
        _cmd(0xF004); _data(0x00)
        
        _cmd(0xB000); _data(0x08)
        _cmd(0xB001); _data(0x05)
        _cmd(0xB002); _data(0x02)
        _cmd(0xB003); _data(0x05)
        _cmd(0xB004); _data(0x02)
        
        _cmd(0xB600); _data(0x08)
        _cmd(0xB500); _data(0x50)

        
        _cmd(0xB700); _data(0x00)
        _cmd(0xB701); _data(0x00)

        
        _cmd(0xB800); _data(0x01)
        _cmd(0xB801); _data(0x05)
        _cmd(0xB802); _data(0x05)
        _cmd(0xB803); _data(0x05)

        
        _cmd(0xBC00); _data(0x00)
        _cmd(0xBC01); _data(0x00)
        _cmd(0xBC02); _data(0x00)

        
        _cmd(0xCC00); _data(0x03)
        _cmd(0xCC01); _data(0x00)
        _cmd(0xCC02); _data(0x00)

        
        _cmd(0xBD00); _data(0x01)
        _cmd(0xBD01); _data(0x84)
        _cmd(0xBD02); _data(0x07)
        _cmd(0xBD03); _data(0x31)
        _cmd(0xBD04); _data(0x00)

        _cmd(0xBA00); _data(0x01)

        _cmd(0xFF00); _data(0xAA)
        _cmd(0xFF01); _data(0x55)
        _cmd(0xFF02); _data(0x25)
        _cmd(0xFF03); _data(0x01)

        
if __name__ == "__main__":
    d = NT35510()
    print(f"NT35510 initialize, Display: {d.width}X{d.height}")
    print(f"Clock freq: {CLOCK:,} hz")
    sl = time.sleep
    d.fill(0xF800)  # red
    print("first color")
    sl(1)
    d.fill(0x07E0)  # green
    sl(1)
    d.fill(0x001F)  # blue
    sl(1)
    c = color565(150,200,150)
    print("timing start")
    t0 = time.ticks_ms()
    for i in range(100):
        d.fill(cx_bright(c,i))
    t1 = time.ticks_ms()
    print("Time:",time.ticks_diff(t1,t0),"ms")
    print(f"Time per frame: {time.ticks_diff(t1,t0)/100} ms")
    t0 = time.ticks_us()
    d.fill(cx_bright(c,i))
    t1 = time.ticks_us()
    print("Time:",time.ticks_diff(t1,t0),"us")
    import sys
    sys.exit(1)
    # import sdio
    # sd = sdio.SDCard()
    # import os
    # os.mount(sd, "/sd")
    # novs = os.listdir("/sd")
    # print(novs)
    # name = "ZARQA_210_WN"
    # with open(f"/sd/novels/{name}/Images/Cover_320-448.raw", "rb") as f:
    #     buf = f.read()
    #     d.draw_buf(100, 100, 320, 448, buf)
    with open("/sd/berto_480-700.raw","rb") as f:
        buf = f.read()
        d.draw_buf(0, 0, 480, 700, buf)

"""['100XMultiplier_System_My_Essence_is_Glitched_as_an_Ultimate_Cheat_51_WN', 'Shadow_Slave_2864_WN', 'Demonic_Pornstar_System_615_WN', 'A_Cold-Blooded_POV_63_WN', 'Slime_Evolution_42_WN', 'Accidentally_Reincarnated_in_Cultivation_World_200_WN', 'SSS_Awakening_Rebirth_of_the_Strongest_Vampire_God_714_WN', 'a_little_sisters_all_i_need_29', 'His_innocent_wife_is_a_dangerous_hacker_550_WN', 'An_Extras_Rise_in_a_Romance_Fantasy_Novel_47_WN', '100X_Returns_System_I_Dominate_the_Age_of_Gods_71_WN', 'Bandit_System_I_Just_Wanted_To_Go_Home_79_WN', 'Wastelands_Only_King_137_WN', 'BIPARTITE_33_WN', 'The_Lone_Healer_224_WN', 'Brand_New_Life_Online_Rise_Of_The_Goddess_Of_Harvest_1673_WN', 'The_Demon_King_Chases_His_Wife_11385', 'The_Evil_God_Summoned_by_the_Saintess_42_WN', 'Infinite_Mana_in_the_Apocalypse_4667_WN', 'Contracted_The_Beautiful_Triplets_And_I_Gained_The_10000x_Rebate_System_470_WN', 'Engagement_Canceled_I_Can_Extract_Prefixes_109_WN', 'Cultivation_Online_1997', 'Daily_Intelligence_System_Dont_Kill_Me_Honey_922_WN', 'Doomcycle_Ninety_Days_Before_the_End_10_WN', 'The_Nameless_Extra_I_Proofread_This_World_43_WN', 'Embers_Ad_Infinitum_953_WN', 'Strongest_Hammer_God_424_WN', 'Evolving_infinitely_from_ground_zero_577_WN', 'Online_Game_I_Have_A_100_Drop_Rate_85_WN', 'F-ranker_Sword_Saint_My_Soulbound_Sword_is_Secretly_SSS-tier_77_WN', 'Vampire_Summoners_Rebirth_Summoning_The_Vampire_Queen_At_The_Start_1537_WN', 'Follow_the_path_of_Dao_from_infancy_1498_WN', 'Game-like_Apocalypse_Rise_Of_The_Blood_Monarch_14_WN', 'I_Just_Wanted_to_Teach_Cultivation_But_Goddesses_Keep_Coming_213_WN', 'Hero_of_Darkness_1176_WN', 'Horror_Game_Developer_My_games_arent_that_scary_188_WN', 'I_AM_A_MAGE_BUT_WITH_MILF_SYSTEM_539_WN', 'Strongest_Mage_with_the_Lust_system_880_WN', 'Izuka_175_WN', 'Jobless_Transmigration_Im_the_only_one_who_loves_monsters_44_WN', 'I_Have_10000_SSS_Rank_Villains_In_My_System_Space_282_WN', 'Junior_sister_keep_forbear_for_a_while_I_almost_become_invincible_as_soon_74_WN', 'Kagami_Witch_of_the_Sealed_Pact_34_WN', 'Kill_the_Sun_972', 'Supreme_Magus (1)', 'Legacy_Of_Fire_Chronicles_Of_The_F-ranked_Anomaly_127_WN', 'Lord_of_Mysteries_2-_Circle_of_Inevitability_WN', 'Lord_of_Mysteries_1432_WN', 'Mafia_Boss_To_Another_World_26_WN', 'Mysteries_of_Immortal_Puppet_Master_1041_WN', 'The_Innkeeper_1910_WN', 'Naked_Sword_Art_445_WN', 'Napping_My_Way_to_Immortality_Until_I_Become_Strong_enough_13_WN', 'Ocean_Lords_Start_Harvesting_Double_from_Dice_Rolls_193_WN', 'Cultivating_life_in_Another_World_with_my_Op_Wife_17_WN', "Omniscient Reader's Viewpoint - Sing-shong (singsyong)", 'Origins_of_Blood_90_WN', 'Paragon_of_Sin_1945', 'Primordial_Awakening_I_Can_Evolve_My_Skills_Infinitely_228_WN', 'Qingge_121_WN', 'Reborn_as_the_bastard_son_of_a_Duke_41_WN', 'Resetting_Lady_282', 'Reverend_Insanity_2334_WN', 'Struggling_as_a_Villain_305_WN', 'The Noble Queen-A Shadow Slave Fanfic_514', 'The_Authors_POV_WN', 'The_Eminence_in_the_Shadow_202', 'Throne_of_Magical_Arcana_910_WN', 'Ultimate_Tycoon_Building_the_Richest_Empire_with_System_and_Heroines_85_WN', 'Unscientific_Beast_Taming_1962_WN', 'Vampires_Slice_Of_Life_1198_WN', 'Weakest_Beast_Tamer_Gets_All_SSS_Dragons_690_WN', 'While_My_Mage_Wife_Grinds_I_Power_Up_Idly_140_WN', 'X_Saga_Eng_Ver_60_WN', 'X-Code_312_WN', 'Yandere_Levelling_in_Her_World_62_WN', 'You_Have_Science_I_Have_Martial_Arts_169_WN', 'ZARQA_210_WN', 'Zombie_King_Babysits_the_Reborn_Empress_274_WN']"""
