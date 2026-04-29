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
# buf1 = bytearray(480*650*2)

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
def average_points_2x2_565(x: int, y: int, w: int, mv_buf: object) -> int:
    p = ptr8(mv_buf)

    row0: int = (y * w + x) * 2
    row1: int = row0 + w * 2

    c0: int = p[row0] | (p[row0 + 1] << 8)
    c1: int = p[row0 + 2] | (p[row0 + 3] << 8)
    c2: int = p[row1] | (p[row1 + 1] << 8)
    c3: int = p[row1 + 2] | (p[row1 + 3] << 8)

    r: int = ((c0 >> 11) & 31) + ((c1 >> 11) & 31) + ((c2 >> 11) & 31) + ((c3 >> 11) & 31)
    g: int = ((c0 >> 5) & 63) + ((c1 >> 5) & 63) + ((c2 >> 5) & 63) + ((c3 >> 5) & 63)
    b: int = (c0 & 31) + (c1 & 31) + (c2 & 31) + (c3 & 31)

    return ((r >> 2) << 11) | ((g >> 2) << 5) | (b >> 2)

@micropython.viper
def average_points_2x2(x: int, y: int, w: int, mv_buf: object) -> object:
    p = ptr8(mv_buf)

    row0: int = (y * w + x) * 2
    row1: int = row0 + w * 2

    c0: int = p[row0] | (p[row0 + 1] << 8)
    c1: int = p[row0 + 2] | (p[row0 + 3] << 8)
    c2: int = p[row1] | (p[row1 + 1] << 8)
    c3: int = p[row1 + 2] | (p[row1 + 3] << 8)

    r: int = ((c0 >> 11) & 0x1F) + ((c1 >> 11) & 0x1F) + ((c2 >> 11) & 0x1F) + ((c3 >> 11) & 0x1F)
    g: int = ((c0 >> 5)  & 0x3F) + ((c1 >> 5)  & 0x3F) + ((c2 >> 5)  & 0x3F) + ((c3 >> 5)  & 0x3F)
    b: int = ( c0        & 0x1F) + ( c1        & 0x1F) + ( c2        & 0x1F) + ( c3        & 0x1F)

    r >>= 2
    g >>= 2
    b >>= 2

    # expand back to 8-bit
    r = (r << 3) | (r >> 2)
    g = (g << 2) | (g >> 4)
    b = (b << 3) | (b >> 2)

    return r, g, b

@micropython.viper
def average_points_2x2_luma(x: int, y: int, w: int, mv_buf: object) -> int:
    p = ptr8(mv_buf)

    row0: int = (y * w + x) * 2
    row1: int = row0 + w * 2

    c0: int = p[row0] | (p[row0 + 1] << 8)
    c1: int = p[row0 + 2] | (p[row0 + 3] << 8)
    c2: int = p[row1] | (p[row1 + 1] << 8)
    c3: int = p[row1 + 2] | (p[row1 + 3] << 8)

    r: int = ((c0 >> 11) & 31) + ((c1 >> 11) & 31) + ((c2 >> 11) & 31) + ((c3 >> 11) & 31)
    g: int = ((c0 >> 5) & 63) + ((c1 >> 5) & 63) + ((c2 >> 5) & 63) + ((c3 >> 5) & 63)
    b: int = (c0 & 31) + (c1 & 31) + (c2 & 31) + (c3 & 31)

    r >>= 2
    g >>= 2
    b >>= 2

    # convert to roughly 8-bit before luma
    r = (r << 3) | (r >> 2)
    g = (g << 2) | (g >> 4)
    b = (b << 3) | (b >> 2)

    return (77 * r + 150 * g + 29 * b) >> 8

@micropython.viper
def dither_block(fb: object,x: int,y: int,bri: int,dith_pix: int): # 0-255
    bri //= 51
    pix: int = 0
    dith_pix = dith_pix>>(bri*4)
    while pix < 4:
        # if dith_pix[bri][pix]: continue
        # fb.pixel(pix%2,pix//2,int(dith_pix[bri][pix])*-1)
        fb.pixel(pix&1 ,pix>>1 ,-((dith_pix>>pix)&1))
        pix += 1
    n.draw_framebuf(x,y,fb)

@micropython.viper
def dither_line(fb: object,x: int,y: int,w: int,dith_pix: int, mv_buf: object): # 0-255 
    sx: int = 0
    dpix: int = 0
    ap_luma: object = average_points_2x2_luma
    while sx < w-1:
        bri: int = int(ap_luma(x + sx, y, w, mv_buf))
        bri //= 51
        pix: int = 0
        dpix: int = dith_pix>>(bri*4)
        while pix < 4:
            # if dith_pix[bri][pix]: continue
            # fb.pixel(pix%2,pix//2,int(dith_pix[bri][pix])*-1)
            fb.pixel(sx + (pix&1) ,pix>>1 ,-((dpix>>pix)&1))
            # fb.pixel(sx,0,-1)
            pix += 1
        sx += 2
    n.draw_framebuf(x,y,fb)

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

@timer
def blur2x2(buf, dest, w=width, h=height):
    blur2x2_v(buf, dest, w, h)

@micropython.viper
def blur2x2_v(mv_buf, dest, w:int, h:int):
    y: int = 0

    while y < h - 1:
        x: int = 0
        speed_boost = x, 0, 0 # ^'magic'^
        while x < w - 1:
            # dest.pixel(x, y, color565(*average_points_2x2(x, y, w, mv_buf)))
            #c2 = color565(*average_points_2x2(x, y, w, mv_buf))
            #c2 = average_points_2x2(x, y, w, mv_buf)
            # dest.fill_rect(x, y, 2, 2, color565(*average_points_2x2(x, y, w, mv_buf)))
            dest.fill_rect(x, y, 2, 2, average_points_2x2_565(x, y, w, mv_buf))
            x += 2
        y += 2

@timer
def dith2x2(buf, w=width, h=height): # completed in 10,631 ms
    dith_pix = 0b1111_1011_1001_0001_0000 # im not sorry
    fb = MyFrameBuffer(2,2,bytearray(8))
    mv_buf = memoryview(buf)
    for y in range(0, h - 1, 2):
        for x in range(0, w - 1, 2):
            # dither_block(fb,x,y,sum(average_points_2x2(x, y, w, mv_buf))//4,dith_pix)
            dither_block(fb,x,y,average_points_2x2_luma(x, y, w, mv_buf),dith_pix)

@timer
def dith2x2_lbl(buf, w=width, h=height): # completed in 2,095 ms
    dith_pix = 0b1111_1011_1001_0001_0000 # im not sorry
    fb = MyFrameBuffer(w,2,bytearray(4*w))
    print(w,h)
    mv_buf = memoryview(buf)
    for y in range(0, h - 1, 2):
        # dither_block(fb,x,y,sum(average_points_2x2(x, y, w, mv_buf))//4,dith_pix)
        dither_line(fb,0,y,w,dith_pix,mv_buf)

# buf = bytearray(b'\xff\xff\xff\xff\xff\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00')

@timer
def test_avg_rgb(buf, w=80, h=height):
    mv_buf = memoryview(buf)
    s = 0
    for y in range(0, h - 1, 2):
        for x in range(0, w - 1, 2):
            r, g, b = average_points_2x2(x, y, w, mv_buf)
            s += r + g + b
    print(s)

@timer
def test_avg_565(buf, w=80, h=height):
    s = 0
    for y in range(0, h - 1, 2):
        for x in range(0, w - 1, 2):
            s += average_points_2x2_565(x, y, w, buf)
    print(s)

# test_avg_rgb(buf)
# test_avg_565(buf)
# n.fill(0)
# blur2x2(buf,n)
print(buf[:16])
# dith2x2(buf)
dith2x2_lbl(buf)

# blur2x2
# function: blur2x2 completed in 24,539 ms
# function: blur2x2 completed in 18,757 ms
# function: blur2x2 completed in 66,019 ms average_points_2x2_565
# function: blur2x2 completed in 14,033 ms average_points_2x2
# function: blur2x2 completed in 14,352 ms non mv 
# function: blur2x2 completed in 65,540 ms dest.fill_rect(x, y, 2, 2, -1)


# dith2x2
# function: dith2x2 completed in 13,852 ms
# function: dith2x2 completed in 12,189 ms average_points_2x2
# function: dith2x2 completed in 10,107 ms average_points_2x2_luma

# Pio 
# 289,434 85,097
# bytearray(b'\x13l\x13l\x13t\x13t\x13t\x13t\x13t3t')
# Starting, setting t0
# 480 700
# function: dith2x2_lbl completed in 2,154 ms

#dma
# 264,703 85,074
# bytearray(b'\x13l\x13l\x13t\x13t\x13t\x13t\x13t3t')
# Starting, setting t0
# 480 700
# function: dith2x2_lbl completed in 2,096 ms