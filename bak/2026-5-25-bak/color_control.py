import framebuf, time
from nt35510 import MyFrameBuffer

#@micropython.viper
def color565(r: int, g: int, b: int) -> int:
    """Return RGB565 color value.

    Args:
        r (int): Red value.
        g (int): Green value.
        b (int): Blue value.
        g001000,b01000,r01000 nope
    """
    gb = (g & 0xfc)
    gb_upper = gb >> 5 # 111|11100 -> 111
    gb_lower = gb & 31 # 111|11100 -> 11100
    return gb_lower << 11 | (b & 0xf8) << 5 | (r & 0xf8) | gb_upper

def c565_to_rgb(c): # 0b110.010.00 0b100.110000110.110
    r = (c & 0xF8)
    g = (c & 7) << 5 | c >> 11
    b = (c >> 5) & 0xf8 
    return r, g, b

def c_bright(r, g, b, brightness, background=None): # brightness 0-100
    """
    r, g, b: foreground color
    brightness: > 0
    background: optional r, g, b
    Returns 16-bit RGB565
    """
    alpha = brightness * 0.01
    if brightness == 100:
        return color565(r, g, b)
    elif brightness <= 0:
        if background:
            r, g, b = background
            return color565(r, g, b)
        else:
            return 0
    elif brightness > 100:
        r = min(int(r * alpha),255)
        g = min(int(g * alpha),255)
        b = min(int(b * alpha),255)
        return color565(r, g, b)
    else:
        if background is None:
            # No background: scale brightness by multiplying
            r = int(r * alpha)
            g = int(g * alpha)
            b = int(b * alpha)
            return color565(r, g, b)
        else:
            # Blend over background
            r_bg, g_bg, b_bg = background
            r_out = int(r * alpha + r_bg * (1 - alpha))
            g_out = int(g * alpha + g_bg * (1 - alpha))
            b_out = int(b * alpha + b_bg * (1 - alpha))
            return color565(r_out, g_out, b_out)

def octile_approx(x0, y0, x1, y1):
    # max + (√2-1)*min  ≈  max + (106/256)*min  (0.4140625)
    dx = abs(x1 - x0); dy = abs(y1 - y0)
    a, b = (dx, dy) if dx >= dy else (dy, dx)
    return a + ((106 * b) >> 8)

def rgb565_bytes(c):
    return bytes((c & 0XFF, c >> 8))

def rgb888_to_rgb565_bytes(r, g, b):
    """
    Convert 24-bit RGB to a 2-byte little-endian RGB565 byte pair.
    Returns a bytes object of length 2 that you can append/assign
    directly into a bytearray screen buffer.
    """
    # Pack into 5-6-5 bits: RRRRR GGGGGG BBBBB
    rgb565 = ((r & 0xF8) << 8)  |  ((g & 0xFC) << 3)  |  (b >> 3)
    # Split into little-endian low/high bytes
    #return bytes((rgb565 & 0xFF, rgb565 >> 8))
    return bytes((rgb565 >> 8, rgb565 & 0XFF))

def mono8_to_rgb565_bytes(v):
    v = v & 0xff
    return rgb888_to_rgb565_bytes(v, v, v)

def make_palette_from_bytes(data):
    return MyFrameBuffer(4, 1, bytearray(data))
    #return framebuf.FrameBuffer(bytearray(data), 4, 1, framebuf.RGB565)

def make_palette(r, g, b, background=None,invert=False,tones=(0,33,67,100)):
    if type(background) is int:
        background = c565_to_rgb(background)
    t = tones
    if invert: 
        return make_palette_from_bytes(
        rgb565_bytes(c_bright(r, g, b, t[0], background=background)) +
        rgb565_bytes(c_bright(r, g, b, t[3], background=background)) +
        rgb565_bytes(c_bright(r, g, b, t[2], background=background)) +
        rgb565_bytes(c_bright(r, g, b, t[1], background=background)))
    return make_palette_from_bytes(
        rgb565_bytes(c_bright(r, g, b, t[0], background=background)) +
        rgb565_bytes(c_bright(r, g, b, t[1], background=background)) +
        rgb565_bytes(c_bright(r, g, b, t[2], background=background)) +
        rgb565_bytes(c_bright(r, g, b, t[3], background=background)))


PALETTE_WHITE = make_palette(0xff, 0xff, 0xff)