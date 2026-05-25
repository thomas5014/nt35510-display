from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
import machine, random, time, os
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

n = NT35510()
# n = NT35510(pio_freq=260_000_000)
temp = bytearray(520*1024*2)
buf = bytearray(width*height*2)
del temp

@micropython.viper
def switch_bytes(buf):
    @micropython.asm_thumb
    def switch_bytes(r0,r1):
        mov(r2,1)
        bic(r1,r2)
        
        mov(r2,r0)
        label(LOOP_START)
        add(r3,r0,r1)
        cmp(r2,r3)
        beq(LOOP_END)

        ldrb(r3,[r2,0])
        ldrb(r4,[r2,1])

        strb(r4,[r2,0])
        strb(r3,[r2,1])
        
        add(r2,2)
        b(LOOP_START)
        label(LOOP_END)
    return switch_bytes(int(ptr8(buf)),len(buf))

# b = bytearray(16)
# for i in range(len(b)): b[i] = 0xf0 
# print(b)
# switch_bytes(b)
# print(b)
# import sys
# sys.exit(1)

def timer(func):
    def wrapper(*args, **kwargs):
        print("Starting, setting t0")
        t0 = time.ticks_ms()
        result = func(*args, **kwargs)
        t1 = time.ticks_ms()
        print(f"function: {func.__name__} completed in {t1-t0:,} ms")
        return result
    return wrapper


n.fill(0)
t0 = time.ticks_us()
with open(file,"rb") as f:
    f.readinto(buf)
    switch_bytes(buf) # for testing non mv versions of blur/dither
    t2 = time.ticks_us()
    n.draw_buf(0, 0, width, height, buf)
    # n.draw_buf_be(0, 0, width, height, buf)  # swap+draw in one PSRAM pass; no switch_bytes needed
t1 = time.ticks_us()
print(f"{t1-t0:,}:Total {t2-t0:,}:Read {t1-t2:,}:Draw")

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

@micropython.viper                                                                                                                                                                                           
def dither_line_pio(fb_buf: object, y: int, w: int, src_buf: object, dith_list: object):
    pb = ptr8(fb_buf)       # fb's raw buffer, 3 rows × w pixels × 2 bytes                                                                                                                                   
    i: int = 0                                                                                                                                                                                               
    sx: int = 0                                                                                                                                                                                              
    while sx < w - 2:                                                                                                                                                                                        
        bri: int = int(average_points_3x3_luma(sx, y, w, src_buf))
        bri = (bri * 10) >> 8                                                                                                                                                                                
        dith_pix: int = int(dith_list[bri])
                                                                                                                                                                                                            
        # write 9 pixels directly — no method dispatch                                                                                                                                                       
        r0: int = sx * 2
        r1: int = (w + sx) * 2                                                                                                                                                                               
        r2: int = (w * 2 + sx) * 2
        c: int = 0                                                                                                                                                                                           
        for bit in range(9):  # unroll manually if needed
            c = -(( dith_pix >> bit) & 1)   # 0x0000 or 0xFFFF                                                                                                                                               
            off: int = r0 + (bit % 3) * 2 if bit < 3 else (r1 + (bit%3)*2 if bit < 6 else r2 + (bit%3)*2)                                                                                                    
            pb[off] = c                                                                                                                                                                                      
            pb[off + 1] = c                                                                                                                                                                                  
        sx += 3      
    n.draw_framebuf(0, y, fb_buf)

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

@micropython.viper
def cx_bright(color:int,brightness:int) -> int:
    if brightness == 0:
        return 0
    return ((color>>11)*brightness//100)<<11 | (((color & 2016) >> 5)*brightness//100)<<5 | ((color & 31)*brightness//100)
       
@micropython.viper
def off_to_on_fade():
    i:int = 0
    b = ptr8(buf)
    while i < 800*480*2:
        c:int = int(cx_bright(0xffff,i//7680))
        b[i] = c & 0xff
        b[i+1] = c >> 8
        i += 2

# off_to_on_fade()
# n.draw_buf(0, 0, width, height, buf)

blur_3x3(0,0,480,700,buf)
# dith3x3(buf)
dith3x3_lbl(buf)
