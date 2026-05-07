from machine import Pin
import machine
import time
import framebuf
import rp2
import micropython

# ---------------------------
# Helpers
# ---------------------------
@micropython.viper
def cx_bright(color:int,brightness:int) -> int:
    if brightness == 0:
        return 0
    return ((color>>11)*brightness//100)<<11 | ((color & 2016 >>5)*brightness//100)<<5 | ((color & 31)*brightness//100)

def color565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
from micropython import const
SIO_BASE   = 0xD0000000  # alias for SIO (faster to access, same hardware)
GPIO_OUT   = SIO_BASE + 0x10
DATA_MASK  = const(0xFFFF)  # GPIO0–15
WR_MASK    = const(1 << 18)
DC_MASK    = const(1 << 20)

class MyFrameBuffer(framebuf.FrameBuffer):
    def __init__(self, width, height, buf=None):
        self.buffer = buf if buf is not None else bytearray(width * height * 2)
        self.width = width
        self.height = height
        super().__init__(self.buffer, width, height, framebuf.RGB565)


# ---------------------------
# PIO program
# ---------------------------
#
# Assumptions:
# - OUT base pin = GPIO0
# - 16 contiguous data pins: GPIO0..15
# - sideset pin = WR
#
# sideset=1 means WR high
# sideset=0 means WR low
#
# For each pulled 16-bit word:
# - put word on bus
# - pulse WR low then high
#
@rp2.asm_pio(
    out_init=tuple(rp2.PIO.OUT_LOW for _ in range(16)),
    out_shiftdir=rp2.PIO.SHIFT_RIGHT,
    autopull=True,
    pull_thresh=16,
    sideset_init=rp2.PIO.OUT_HIGH,
)
def nt35510_pixels16():
    wrap_target()
    out(pins, 16)         .side(1)
    nop()                 .side(0)
    nop()                 .side(0)
    nop()                 .side(1)
    nop()                 .side(1)
    wrap()

@micropython.viper                                                                                                                                                                                           
def _buf_ptr(buf: object) -> int:                                                                                                                                                                            
    return int(ptr8(buf))

# ---------------------------
# Driver
# ---------------------------

class NT35510:
    def __init__(
        self,
        data_base=0,     # GPIO0..15 must be data bus
        wr=18,
        cs=19,
        dc=20,
        rst=21,
        bl=22,
        rd=40,
        width=480,
        height=800,
        sm_id=0,
        pio_freq=160_000_000,
    ):
        if data_base != 0:
            raise ValueError("This first version assumes data_base=0 (GPIO0..15)")

        self.width = width
        self.height = height

        self.data_base = data_base
        self.wr_pin = wr
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=1)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.bl = Pin(bl, Pin.OUT, value=0)
        self.rd = Pin(rd, Pin.OUT, value=1)
        self.cs_pin = cs
        self.dc_pin = dc
        self.rst_pin = rst
        self.rd_pin = rd
        self.bl_pin = bl
        dma_channel=0
        # DMA setup — fixed write address (PIO TX FIFO), ctrl word pre-built                                                                                                                                         
        self._dma_base = 0x50000000 + dma_channel * 0x40                                                                                                                                                             
        fifo_addr = 0x50200010 + sm_id * 4
        machine.mem32[self._dma_base + 0x4] = fifo_addr        # WRITE_ADDR = PIO FIFO (fixed)                                                                                                                       
        dreq = sm_id & 3                                        # DREQ_PIO0_TX{n}                                                                                                                                    
        # EN | DATA_SIZE=word(2) | INCR_READ | CHAIN_TO=self | DREQ                                                                                                                                                  
        self._dma_ctrl = (1) | (2<<2) | (1<<4) | (dma_channel<<11) | (dreq<<15)

        # Keep direct GPIO write helpers for command/data register writes
        self._out_reg = machine.mem32
        self.SIO_BASE = 0xD0000000
        self.GPIO_OUT = self.SIO_BASE + 0x10
        self.DATA_MASK = 0xFFFF
        self.WR_MASK = 1 << wr
        self.DC_MASK = 1 << dc

        # Preconfigure data pins so GPIO control is sane before PIO takes over
        self._dpins = [Pin(i, Pin.OUT, value=0) for i in range(16)]
        self.wr = Pin(wr, Pin.OUT, value=1)

        self.hw_reset()
        self.init_display()

        self.set_window(0, 0, 0, 0)
        self._bus_write16(0xF800)
        time.sleep_ms(100)

        self.sm_id = sm_id
        self.pio_freq = pio_freq
        self.sm = None
        self._pio_active = False

    # ---------------------------
    # Basic low-level direct-write methods
    # ---------------------------

    def hw_reset(self):
        self.rst.high()
        time.sleep_ms(50)
        self.rst.low()
        time.sleep_ms(50)
        self.rst.high()
        time.sleep_ms(120)

    @micropython.viper
    def _cmd(self, v: int):
        pout = ptr32(self.GPIO_OUT)
        data_mask = int(self.DATA_MASK)
        dc_mask = int(self.DC_MASK)
        wr_mask = int(self.WR_MASK)

        cur = pout[0]
        cur = (cur & ~dc_mask & ~data_mask) | (v & data_mask)
        pout[0] = cur & ~wr_mask
        pout[0] = cur | wr_mask

    @micropython.viper
    def _data(self, v: int):
        pout = ptr32(self.GPIO_OUT)
        data_mask = int(self.DATA_MASK)
        dc_mask = int(self.DC_MASK)
        wr_mask = int(self.WR_MASK)

        cur = pout[0]
        cur = (cur & ~data_mask) | (v & data_mask) | dc_mask
        pout[0] = cur & ~wr_mask
        pout[0] = cur | wr_mask

    @micropython.viper
    def _cmddata(self, c: int, d: int):
        pout = ptr32(self.GPIO_OUT)
        data_mask = int(self.DATA_MASK)
        dc_mask = int(self.DC_MASK)
        wr_mask = int(self.WR_MASK)

        # command
        cur = pout[0]
        cur = (cur & ~dc_mask & ~data_mask) | (c & data_mask)
        pout[0] = cur & ~wr_mask
        pout[0] = cur | wr_mask

        # data
        cur = pout[0]
        cur = (cur & ~data_mask) | (d & data_mask) | dc_mask
        pout[0] = cur & ~wr_mask
        pout[0] = cur | wr_mask

    def _ensure_sm(self):
        if self.sm is None:
            self.sm = rp2.StateMachine(
                self.sm_id,
                nt35510_pixels16,
                freq=self.pio_freq,
                out_base=Pin(self.data_base),
                sideset_base=Pin(self.wr_pin),
            )
            self.sm.active(0)

    def _claim_bus_gpio(self):
        for i in range(16):
            Pin(i, Pin.OUT, value=0)
        Pin(self.wr_pin, Pin.OUT, value=1)
        self.dc = Pin(self.dc.id(), Pin.OUT, value=self.dc.value())
        self.cs = Pin(self.cs.id(), Pin.OUT, value=self.cs.value())
        self.rd = Pin(self.rd.id(), Pin.OUT, value=self.rd.value())
        self.rst = Pin(self.rst.id(), Pin.OUT, value=self.rst.value())

    @micropython.viper
    def _claim_bus_gpio(self):
        # Switch GPIO 0-15 function from PIO0 (6) back to SIO (5)                                                                                                                                                
        ctrl = ptr32(0x40014004)  # GPIO0_CTRL, stride 8 bytes = 2 words                                                                                                                                         
        i: int = 0                                                                                                                                                                                               
        while i < 16:                                                                                                                                                                                            
            ctrl[i * 2] = 5                                                                                                                                                                                      
            i += 1                                                                                                                                                                                               
        ptr32(0xD0000028)[0] = 0xFFFF   # GPIO_OE_SET: re-enable output

    def _pio_on(self):
        self._ensure_sm()
        self.cs.low()
        self.rd.high()
        self.dc.high()
        self.sm.active(1)
        self._pio_active = True

    def _pio_off(self):                                                                                                                                                                                          
        if self._pio_active:                                                                                                                                                                                   
            if self.sm is not None:
                # wait for TX FIFO to drain before killing the SM
                fstat_mask = 1 << (24 + self.sm_id)                                                                                                                                                              
                while not (machine.mem32[0x50200004] & fstat_mask):
                    pass                                                                                                                                                                                         
                self.sm.active(0)                                                                                                                                                                              
            self._claim_bus_gpio()                                                                                                                                                                               
            self.cs.low()                                                                                                                                                                                      
            self.rd.high()
            self.dc.high()                                                                                                                                                                                       
            self._pio_active = False

    # ---------------------------
    # Init / setup
    # ---------------------------

    def init_display(self):
        self.bl.on()
        self.rd.high()
        self.cs.low()

        self.init_extra()
        self._cmd(0x3A00)
        self._data(0x55)   # RGB565
        self._cmd(0x1100)
        time.sleep_ms(120)
        self._cmd(0x2900)

    @micropython.viper
    def _bus_write16(self, v:int):
        pout = ptr32(self.GPIO_OUT)
        data_mask = int(self.DATA_MASK)
        dc_mask = int(self.DC_MASK)
        wr_mask = int(self.WR_MASK)

        cur = pout[0]
        cur = (cur & ~data_mask) | (v & data_mask) | dc_mask
        pout[0] = cur & ~wr_mask
        pout[0] = cur | wr_mask

    @micropython.viper
    def set_window(self, x0: int, y0: int, x1: int, y1: int):
        cmddata = self._cmddata
        cmd = self._cmd

        cmddata(0x2A00, x0 >> 8)
        cmddata(0x2A01, x0 & 0xFF)
        cmddata(0x2A02, x1 >> 8)
        cmddata(0x2A03, x1 & 0xFF)

        cmddata(0x2B00, y0 >> 8)
        cmddata(0x2B01, y0 & 0xFF)
        cmddata(0x2B02, y1 >> 8)
        cmddata(0x2B03, y1 & 0xFF)

        cmd(0x2C00)

    # ---------------------------
    # PIO bulk write helpers
    # ---------------------------

    def _pio_write_repeat16(self, value, count):
        value &= 0xFFFF
        for _ in range(count):
            self.sm.put(value)

    def _pio_write_buf16(self, buf):
        mv = memoryview(buf)
        n = len(mv)
        if n & 1:
            raise ValueError("buffer length must be even")

        for i in range(0, n, 2):
            self.sm.put(mv[i] | (mv[i + 1] << 8))

    @micropython.viper
    def _write_buf16_gpio(self, buf_obj: object):
        n = int(len(buf_obj))
        if n & 1:
            return

        bp = ptr8(buf_obj)
        pout = ptr32(self.GPIO_OUT)
        data_mask = int(self.DATA_MASK)
        dc_mask = int(self.DC_MASK)
        wr_mask = int(self.WR_MASK)

        # Precompute base GPIO value (non-data bits with DC=1) outside the loop
        base = (pout[0] & ~data_mask) | dc_mask
        base_lo = base & ~wr_mask
        base_hi = base | wr_mask

        i = 0
        while i < n:
            pixel = int(bp[i]) | (int(bp[i + 1]) << 8)
            pout[0] = base_lo | pixel
            pout[0] = base_hi | pixel
            i += 2

    @micropython.viper
    def _write_repeat16_gpio(self, value: int, count: int):
        pout = ptr32(self.GPIO_OUT)
        data_mask = int(self.DATA_MASK)
        dc_mask = int(self.DC_MASK)
        wr_mask = int(self.WR_MASK)
        v = int(value) & data_mask

        cur = pout[0]
        cur = (cur & ~data_mask) | v | dc_mask

        i = 0
        while i < count:
            pout[0] = cur & ~wr_mask
            pout[0] = cur | wr_mask
            i += 1

    # ---------------------------
    # Public drawing API
    # ---------------------------

    def fill_rect(self, x, y, width, height, color):
        self._pio_off()
        self.set_window(x, y, x + width - 1, y + height - 1)
        self._write_repeat16_gpio(color, width * height)

    def fill(self, color):
        self.fill_rect(0, 0, self.width, self.height, color)

    def draw_buf(self, x, y, width, height, buf):
        self._pio_off()
        self.set_window(x, y, x + width - 1, y + height - 1)
        self._write_buf16_gpio(buf)

    def draw_framebuf(self, x, y, fb):                                                                                                                                                                           
        self._pio_off()                                                                                                                                                                                        
        self.set_window(x, y, x + fb.width - 1, y + fb.height - 1)
        self._pio_on()                                                                                                                                                                                           
        # 2 pixels per 32-bit DMA word — existing PIO/pull_thresh=16 handles both halves
        n = (fb.width * fb.height) >> 1                                                                                                                                                                          
        machine.mem32[self._dma_base + 0x0] = _buf_ptr(fb.buffer)  # READ_ADDR                                                                                                                                 
        machine.mem32[self._dma_base + 0x8] = n                     # TRANS_COUNT                                                                                                                                
        machine.mem32[self._dma_base + 0xC] = self._dma_ctrl        # CTRL_TRIG — starts DMA                                                                                                                     
        # wait for DMA completion (BUSY bit)                                                                                                                                                                     
        while machine.mem32[self._dma_base + 0xC] & (1 << 24):                                                                                                                                                   
            pass 

    def pixel(self, x, y, color):
        self._pio_off()
        self.set_window(x, y, x, y)
        self._write_repeat16_gpio(color, 1)

    def fb_text(self, text, x=0, y=0, color=0xFFFF, bg=0):
        w = len(text) * 8 + 8
        h = 8
        fb = MyFrameBuffer(w, h)
        if bg:
            fb.fill(bg)
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
    d = NT35510(sm_id=2)
    print("direct init done")

    # direct GPIO sanity check BEFORE PIO claims the bus pins
    d.set_window(0, 0, 39, 39)
    for _ in range(40 * 40):
        d._bus_write16(0xF800)
    time.sleep(.1)

    d.set_window(50, 0, 89, 39)
    for _ in range(40 * 40):
        d._bus_write16(0x07E0)
    time.sleep(.1)

    d.set_window(100, 0, 139, 39)
    for _ in range(40 * 40):
        d._bus_write16(0x001F)
    time.sleep(.1)

    # now let PIO claim the bus
    d.fill_rect(20, 600, 200, 20, 0x07E0)
    time.sleep(.1)

    # fb = MyFrameBuffer(100, 106)
    # fb.fill(0)
    # fb.text("PIO", 0, 0, -1)
    # d.draw_framebuf(200, 200, fb)

    # full display fill test
    t0 = time.ticks_ms()
    d.fill(0)
    t1 = time.ticks_ms()
    print("Full fill time: {} ms".format(time.ticks_diff(t1, t0)))