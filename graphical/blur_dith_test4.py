from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
import machine, random, time, os
machine.freq(260_000_000)

image_num = 2
file = [f for f in os.listdir("/") if "sample" in f][image_num]
width = int(file.split("_")[1][:3])
height = int(file.split("_")[1][4:7])

@micropython.viper
def color565_to_rgb(c: int):
    r: int = (c >> 11) & 0x1F
    g: int = (c >> 5)  & 0x3F
    b: int = c & 0x1F

    # expand to 0–255
    r: int = (r << 3) | (r >> 2)
    g: int = (g << 2) | (g >> 4)
    b: int = (b << 3) | (b >> 2)

    return r, g, b

n = NT35510()
temp = bytearray(520*1024*2)
buf = bytearray(width*height*2)
del temp

@micropython.viper
def switch_bytes(buf: object):
    p = ptr8(buf)
    n = int(len(buf)) & ~1
    tmp: int = 0
    for i in range(0, n, 2):
        tmp = p[i]
        p[i] = p[i + 1]
        p[i + 1] = tmp

    return buf

def timer(func):
    def wrapper(*args, **kwargs):
        print("Starting, setting t0")
        t0 = time.ticks_ms()
        result = func(*args, **kwargs)
        t1 = time.ticks_ms()
        print(f"function: {func.__name__} completed in {t1-t0:,} ms")
        return result
    return wrapper

@micropython.viper
def average_points_3x3_luma(x: int, y: int, w: int, buf: object) -> int:
    p = ptr8(buf)

    row0: int = (y * w + x) * 2
    row1: int = row0 + w * 2
    row2: int = row1 + w * 2

    c: int = 0
    r: int = 0
    g: int = 0
    b: int = 0

    c = p[row0] | (p[row0 + 1] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31
    c = p[row0 + 2] | (p[row0 + 3] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31
    c = p[row0 + 4] | (p[row0 + 5] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31

    c = p[row1] | (p[row1 + 1] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31
    c = p[row1 + 2] | (p[row1 + 3] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31
    c = p[row1 + 4] | (p[row1 + 5] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31

    c = p[row2] | (p[row2 + 1] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31
    c = p[row2 + 2] | (p[row2 + 3] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31
    c = p[row2 + 4] | (p[row2 + 5] << 8)
    r += (c >> 11) & 31; g += (c >> 5) & 63; b += c & 31

    r //= 9
    g //= 9
    b //= 9

    r = (r << 3) | (r >> 2)
    g = (g << 2) | (g >> 4)
    b = (b << 3) | (b >> 2)

    return (77 * r + 150 * g + 29 * b) >> 8

@micropython.viper
def average_points_3x3_565(x: int, y: int, w: int, buf: object) -> int:
    p = ptr8(buf)

    row0: int = (y * w + x) * 2
    row1: int = row0 + w * 2
    row2: int = row1 + w * 2

    c: int = 0
    r: int = 0
    g: int = 0
    b: int = 0

    # row 0
    c = p[row0] | (p[row0 + 1] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    c = p[row0 + 2] | (p[row0 + 3] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    c = p[row0 + 4] | (p[row0 + 5] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    # row 1
    c = p[row1] | (p[row1 + 1] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    c = p[row1 + 2] | (p[row1 + 3] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    c = p[row1 + 4] | (p[row1 + 5] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    # row 2
    c = p[row2] | (p[row2 + 1] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    c = p[row2 + 2] | (p[row2 + 3] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    c = p[row2 + 4] | (p[row2 + 5] << 8)
    r += (c >> 11) & 31
    g += (c >> 5) & 63
    b += c & 31

    return ((r // 9) << 11) | ((g // 9) << 5) | (b // 9)

@micropython.viper
def dither_block(fb: object, x: int, y: int, bri: int, dith_list: object):
    bri = (bri * 10) >> 8
    dith_pix: int = int(dith_list[bri])
    pix: int = 0
    while pix < 9:
        fb.pixel(pix%3, pix // 3, -((dith_pix >> pix) & 1))
        pix += 1

    n.draw_framebuf(x, y, fb)

@micropython.viper
def dither_line(fb: object, x: int, y: int, w: int, dith_list: object):
    sx: int = 0
    ap_luma: object = average_points_3x3_luma
    while sx < w -2:
        bri: int = int(ap_luma(x + sx, y, w, buf))
        bri = (bri * 10) >> 8
        dith_pix: int = int(dith_list[bri])
        pix: int = 0
        while pix < 9:
            fb.pixel(sx + pix%3, pix // 3, -((dith_pix >> pix) & 1))
            pix += 1
        sx += 3

    n.draw_framebuf(x, y, fb)

@timer
def blur_3x3(x,y,w,h,buf,dest=n):
   y: int = 0
   while y < h - 2:
        x: int = 0
        while x < w - 2:
            c = int(average_points_3x3_565(x, y, w, buf)) & 0xFFFF
            dest.fill_rect(x, y, 3, 3, c)
            x += 3
        y += 3

@timer
def dith3x3(buf, w=width, h=height): # completed in 5,060 ms
    dith_pix = ( 
        0b000000000,
        0b000000001,
        0b100000001,
        0b100000101,
        0b101000101,
        0b101010101,
        0b101010111,
        0b101110111,
        0b111110111,
        0b111111111
        )
    fb = MyFrameBuffer(3, 3, bytearray(18))
    for y in range(0, h - 2, 3):
        for x in range(0, w - 2, 3):
            dither_block(fb, x, y, average_points_3x3_luma(x, y, w, buf), dith_pix)

@timer
def dith3x3_lbl(buf, w=width, h=height): # completed in 2,019 ms
    dith_pix = ( 
        0b000000000,
        0b000000001,
        0b100000001,
        0b100000101,
        0b101000101,
        0b101010101,
        0b101010111,
        0b101110111,
        0b111110111,
        0b111111111
        )
    fb = MyFrameBuffer(w, 3, bytearray(6*w))
    for y in range(0, h - 2, 3):
        dither_line(fb, 0, y, w, dith_pix)
        

n.fill(0)
t0 = time.ticks_us()
with open(file,"rb") as f:
    f.readinto(buf)
    t2 = time.ticks_us()
    buf = switch_bytes(buf)
    # buf[0] = color565(0,0,255)
    # buf[2] = color565(0,0,255)
    n.draw_buf(0, 0, width, height, buf)
t1 = time.ticks_us()
print(f"{t1-t0:,} {t2-t0:,}")

# blur_3x3(0,0,480,700,buf)
# dith3x3(buf)
dith3x3_lbl(buf)
