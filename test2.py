# nt35510_8080_16bit.py  —  minimal bring-up for portrait 480x800
import time
from machine import Pin, PWM # type: ignore
import machine, micropython, framebuf # type: ignore
machine.freq(300_000_000)

W = 480
H = 800

def color565(r,g,b):
    return ((r & 0xF8)<<8) | ((g & 0xFC)<<3) | (b>>3)

@micropython.viper
def cx_bright(color:int,brightness:int) -> int:
    if brightness == 0:
        return 0
    return ((color>>11)*brightness//100)<<11 | ((color & 2016 >>5)*brightness//100)<<5 | ((color & 31)*brightness//100)

# colors:
RED = color565(255,0,0)
BLUE = color565(0,0,255)
GREEN = color565(0,255,0)
ORANGE = color565(255, 143, 2)
YELLOW = color565(255, 255, 2)
WHITE = color565(255,255,255)


# --- GPIO assignments (change if needed)
DATA_BASE = 0            # D0 on GPIO0 ... D15 on GPIO15
PIN_WR    = 18
PIN_RD    = 26
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

SIO_BASE   = 0xD0000000  # alias for SIO (faster to access, same hardware)
GPIO_OUT   = SIO_BASE + 0x10
GPIO_SET   = SIO_BASE + 0x1C

DATA_MASK  = const(0xFFFF)  # GPIO0–15
WR_MASK    = const(1 << 18)


@micropython.viper
def _bus_write16_fast(v:int, count:int):
    pout = ptr32(GPIO_OUT)
    v:int = pout[0] & ~DATA_MASK | (v & DATA_MASK)

    low: int = v & ~WR_MASK
    high: int = v | WR_MASK
    i: int = 0
    fcount:int = count // 16 * 16
    while i < fcount:
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        pout[0] = low
        pout[0] = high
        i += 16

    while i < count:  # remainer
        pout[0] = low
        pout[0] = high
        i += 1


@micropython.viper
def _bus_write16(v:int, count:int):
    for i in range(16):
        _dpins[i].value((v >> i) & 1)

    for _ in range(0, count):
        _wr.low()
        _wr.high()

def _cmd(c):
    _rs.low()
    _cs.low()
    _bus_write16(c,1)
    _cs.high()

def _data(c):
    _rs.high()
    _cs.low()
    _bus_write16(c,1)
    _cs.high()

def hw_reset():
    _rst.high(); time.sleep_ms(50)
    _rst.low(); time.sleep_ms(50)
    _rst.high(); time.sleep_ms(120)


def set_window(x0, y0, x1, y1):
    _cmd(0x2A00); _data(x0 >> 8)      # setx start high-byte
    _cmd(0x2A01); _data(x0 & 0xFF)      # setx start low-byte
    _cmd(0x2A02); _data(x1 >> 8)      # setx end high-byte
    _cmd(0x2A03); _data(x1 & 0xFF)     # setx end low-byte

    _cmd(0x2B00); _data(y0 >> 8)      # sety start high-byte
    _cmd(0x2B01); _data(y0 & 0xFF)      # sety start low-byte
    _cmd(0x2B02); _data(y1 >> 8)      # sety end high-byte
    _cmd(0x2B03); _data(y1 & 0xFF)     # sety end low-byte

    _cmd(0x2C00)        # write ram

def fill_rect(x, y, width, height, color):
    t0 = time.ticks_ms()
    set_window(x, y, x + width - 1, y + height - 1)

    _rs.high()
    _cs.low()
    _bus_write16_fast(color, width*height)
    _cs.high()
    #print("done",f"{time.ticks_diff(time.ticks_ms(),t0):,}")

def fb_hello_world():
    fb = framebuf.FrameBuffer(bytearray(100*100*2),100,100,framebuf.RGB565)
    fb.text("Hello World", 0, 0,-1)
    set_window(0,0,100,100)
    

@micropython.viper
def pixel(x:int,y:int,color:int):
    set_window(x,y,x,y)
    _rs.high()
    _cs.low()
    _bus_write16_fast(color, 1)
    _cs.high()
    

def pixel_helloworld(x,y,color):
    hello_x = [0,0,0,0,0,1,2,2,2,2,2,4,4,4,4,4,5,5,5,6,6,6,8,8,8,8,8,9,10,12,12,12,12,12,13,14,16,16,16,16,16,17,17,18,18,18,18,18]
    hello_y = [0,1,2,3,4,2,0,1,2,3,4,0,1,2,3,4,0,2,4,0,2,4,0,1,2,3,4,4,4,0,1,2,3,4,4,4,0,1,2,3,4,0,4,0,1,2,3,4]
    for i in range(len(hello_x)):
        pixel(x+hello_x[i],y+hello_y[i],color)
    world_x = [0,0,0,0,0,1,2,2,3,4,4,4,4,4,6,6,6,6,6,7,7,8,8,8,8,8,10,10,10,10,10,11,11,12,12,12,12,14,14,14,14,14,15,16,18,18,18,18,18,19,19,20,20,20]
    world_y = [0,1,2,3,4,4,2,3,4,0,1,2,3,4,0,1,2,3,4,0,4,0,1,2,3,4,0,1,2,3,4,0,2,0,1,3,4,0,1,2,3,4,4,4,0,1,2,3,4,0,4,1,2,3]
    for i in range(len(world_x)):
        pixel(x+world_x[i],y+7+world_y[i],color)

def main():
    # Just send sleep-out and fill small area red
    #_bl.off()
    _bl.on()
    _rd.high()
    hw_reset()
    init_extra()
    _cmd(0x3a00); _data(0x55)               # set pixel format
    _cmd(0x1100); time.sleep_ms(120)        # exit sleep booster on
    _cmd(0x2900)                            # display on

    fill_rect(0, 0, 300, 500, 0xF800)
    fill_rect(300, 0, 100, 200, 0x8a00)
    fill_rect(300, 300, 100, 200, 0x0a00)
    fill_rect(280, 200, 100, 200, 0x001f)
    fill_rect(0, 600, 480, 200, 0x002f)
    fill_rect(380, 300, 100, 100, color565(0,255,255))
    fill_rect(90,70,48,80,0b11111100000)
    fill_rect(90,170,48,80,color565(0,255,0))
    fill_rect(90,300,48,80,cx_bright(GREEN,50))
    for o in range(45):
        continue
        for i in range(21):
            pixel_helloworld(0+i*22,0+o*13,WHITE)
    for i in range(100):
        fill_rect(190,170+i*3,48,3,cx_bright(GREEN,100-i))
        fill_rect(250,170+i*3,48,3,cx_bright(BLUE,100-i))

    for o in range(100):
        for i in range(200):
            pixel(100+i*2+o%2,300+o,BLUE)
    #fill_rect(160,300,60,10,BLUE)

    t0 = time.ticks_ms()
    w:int = 480
    h:int = 800
    for i in range(0,100):
        fill_rect(0,0,w,h, color565(0xff, 0, 0))
        fill_rect(0,0,w,h, color565(0, 0xff, 0))
        fill_rect(0,0,w,h, color565(0, 0, 0xff))

    delta = time.ticks_diff(time.ticks_ms(),t0)
    print(f"{delta/1000} sec ({300/delta*1000} fps)")
    print(machine.freq())
    w:int = 480
    h:int = 800
    for i in range(0,100):
        fill_rect(0,0,w,h, color565(0xff, 0, 0))
        time.sleep(1)
        fill_rect(0,0,w,h, color565(0, 0xff, 0))
        time.sleep(1)
        fill_rect(0,0,w,h, color565(0, 0, 0xff))
        time.sleep(1)
    return

    t0 = time.ticks_ms()
    for i in range(100):
        fill_rect(0,0,50,50,0XF8)
        fill_rect(0,0,50,50,0X001F)
    delta = time.ticks_diff(time.ticks_ms(),t0)
    print("time for hundred:",delta)
    print("mini frames per second: ",f"{100000/delta:,}")
    for i in range(16):
        fill_rect(0+30*i,400,30,100,2<<i)
        print(2<<i)
    time.sleep(5)
    while True:
        fill_rect(0,0,300,300,0XF8)
        fill_rect(0,0,300,300,0X001F)
        fill_rect(0,0,300,300,0b11111100000)
    

    
    print('done!')




def init_extra():
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
    main()
 