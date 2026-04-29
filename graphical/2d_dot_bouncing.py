from nt35510 import NT35510, MyFrameBuffer
import machine, random, time, os
machine.freq(260_000_000)

gravity = 

n = NT35510()
temp = bytearray(520*1024*2)
buf = MyFrameBuffer(n.width,n.height,bytearray(n.width*n.height*2))
del temp

def timer(func):
    def wrapper(*args, **kwargs):
        print("Starting, setting t0")
        t0 = time.ticks_ms()
        try:
            result = func(*args, **kwargs)
            t1 = time.ticks_ms()
            print(f"function: {func.__name__} completed in {t1-t0:,} ms")
        except Exception as e:
            t1 = time.ticks_ms()
            print(f"function: {func.__name__} raised an exception after {t1-t0:,} ms: {e}")
            raise
        return result
    return wrapper

@micropython.viper
def cx_bright(color:int,brightness:int) -> int:
    if brightness == 0:
        return 0
    return ((color>>11)*brightness//100)<<11 | (((color & 2016) >> 5)*brightness//100)<<5 | ((color & 31)*brightness//100)

@micropython.viper
def color565(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

import micropython

# Standard helper for Python space
def c_bright(r, g, b, brightness=100, background=None):
    br, bg, bb = background if background else (0, 0, 0)
    return c_bright_viper(r, g, b, brightness, br, bg, bb)

@micropython.viper
def c_bright_viper(r: int, g: int, b: int, brightness: int, br: int, bg: int, bb: int) -> int:
    # 1. Handle edge cases
    if brightness <= 0:
        r, g, b = br, bg, bb
    elif brightness == 100:
        pass # Use original r, g, b
    else:
        # 2. Integer-based Alpha Blending (scaled by 100)
        # For brightness > 100, it acts as a multiplier
        # For brightness < 100, it blends with background
        inv_alpha: int = 100 - brightness
        
        r = (r * brightness + br * inv_alpha) // 100
        g = (g * brightness + bg * inv_alpha) // 100
        b = (b * brightness + bb * inv_alpha) // 100

    # 3. Constrain to 8-bit range
    if r > 255: r = 255
    if g > 255: g = 255
    if b > 255: b = 255
    if r < 0: r = 0
    if g < 0: g = 0
    if b < 0: b = 0

    # 4. Inline RGB565 conversion (Viper can't call outside functions easily)
    # (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)

@micropython.viper
def get_dist(x0,y0,x1,y1) -> int:
    dx: int = x1 - x0
    dy: int = y1 - y0
    return int((dx*dx + dy*dy)**0.5)