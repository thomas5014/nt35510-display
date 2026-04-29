from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
import machine, random, time, os, math
machine.freq(260_000_000)

image_num = 0
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

nt = NT35510()
temp = bytearray(520*1024*2)
buf = bytearray(width*height*2)
line_buf = bytearray(width*2)
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

# Precompute once
GAMMA = 2.2
LUT5 = bytes(int((i / 31) ** GAMMA * 255 + 0.5) for i in range(32))
LUT6 = bytes(int((i / 63) ** GAMMA * 255 + 0.5) for i in range(64))

@micropython.viper
def rgb565_to_gamma_corrected(val: int):
    r = LUT5[(val >> 11) & 0x1F]
    g = LUT6[(val >> 5)  & 0x3F]
    b = LUT5[ val        & 0x1F]
    return r, g, b

def timer(func):
    def wrapper(*args, **kwargs):
        print("Starting, setting t0")
        t0 = time.ticks_ms()
        result = func(*args, **kwargs)
        t1 = time.ticks_ms()
        try:
            print(f"function: {func.__name__} completed in {t1-t0:,} ms")
        except:
            print(f"function completed in {t1-t0:,} ms")
        return result
    return wrapper

nt.fill(0)
t0 = time.ticks_us()
with open(file,"rb") as f:
    f.readinto(buf)
    t2 = time.ticks_us()
    buf = switch_bytes(buf)
    # buf[0] = color565(0,0,255)
    # buf[2] = color565(0,0,255)
    nt.draw_buf(0, 0, width, height, buf)
t1 = time.ticks_us()
print(f"{t1-t0:,} {t2-t0:,}")

@timer
# @ micropython.viper
@micropython.viper
def color_corrected(buf: ptr8, width: int, height: int):
    lut5 = ptr8(LUT5)
    lut6 = ptr8(LUT6)
    idx: int = 0
    x: int = 0
    y: int = 0
    for i in range(width * height):
        val: int = buf[idx] | (buf[idx + 1] << 8)
        idx += 2
        r: int = lut5[(val >> 11) & 0x1F]
        g: int = lut6[(val >> 5)  & 0x3F]
        b: int = lut5[ val        & 0x1F]
        nt.pixel(x, y, ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3))
        x += 1
        if x >= width:
            x = 0
            y += 1

@micropython.viper
def process_line_cc(buf: ptr8, line_buf: ptr8, width: int, y: int):
    lut5 = ptr8(LUT5)
    lut6 = ptr8(LUT6)
    src: int = y * width * 2
    dst: int = 0
    for x in range(width):
        val: int = buf[src] | (buf[src + 1] << 8)
        r: int = lut5[(val >> 11) & 0x1F]
        g: int = lut6[(val >> 5)  & 0x3F]
        b: int = lut5[ val        & 0x1F]
        out: int = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        line_buf[dst]     = out & 0xFF
        line_buf[dst + 1] = out >> 8
        src += 2
        dst += 2

@timer
def color_corrected_line_by_line(buf: ptr8, width: int, height: int):
    line_buf = bytearray(width * 2)
    for y in range(height):
        process_line_cc(buf, line_buf, width, y)
        nt.draw_buf(0, y, width, 1, line_buf) 

@micropython.viper
def apply_gamma_inplace(buf: ptr8, n_pixels: int):
    lut5 = ptr8(LUT5)
    lut6 = ptr8(LUT6)
    idx: int = 0
    for i in range(n_pixels):
        lo: int = buf[idx]
        hi: int = buf[idx + 1]
        val: int = lo | (hi << 8)
        r: int = lut5[(val >> 11) & 0x1F]
        g: int = lut6[(val >> 5)  & 0x3F]
        b: int = lut5[ val        & 0x1F]
        out: int = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        buf[idx]     = out & 0xFF
        buf[idx + 1] = out >> 8
        idx += 2

@timer
def color_corrected_full_frame(buf: ptr8, width: int, height: int):
    apply_gamma_inplace(buf, width * height)
    nt.draw_buf(0, 0, width, height, buf) 


@micropython.viper
def rgb565_to_gray565(val: int) -> int:
    r = (val >> 11) & 0x1F
    g = (val >> 5)  & 0x3F
    b =  val        & 0x1F
    # BT.601 weights normalized to 5-bit output, scaled by 128
    luma = (r * 38 + g * 37 + b * 15) >> 7  # 0-31
    return (luma << 11) | (luma << 6) | luma  # R5 G6 B5 (G6 = luma<<1)

@micropython.viper
def process_line_gs(buf: ptr8, line_buf: ptr8, width: int, y: int):
    lut5 = ptr8(LUT5)
    lut6 = ptr8(LUT6)
    src: int = y * width * 2
    dst: int = 0
    for x in range(width):
        val: int = buf[src] | (buf[src + 1] << 8)
        luma = int(rgb565_to_gray565(val))
        line_buf[dst]     = luma & 0xFF
        line_buf[dst + 1] = luma >> 8
        src += 2
        dst += 2

@timer
def gray_scale_line_by_line(buf: ptr8, width: int, height: int):
    line_buf = bytearray(width * 2)
    for y in range(height):
        process_line_gs(buf, line_buf, width, y)
        nt.draw_buf(0, y, width, 1, line_buf) 

# color_corrected_line_by_line(buf,width,height)
# color_corrected(buf, width, height)
# color_corrected_full_frame(buf, width, height)

gray_scale_line_by_line(buf, width, height)