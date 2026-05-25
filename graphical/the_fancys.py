from nt35510 import NT35510, MyFrameBuffer
import machine, random, time, os
machine.freq(260_000_000)

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


def brightness_coef(drop_off):
    lim = drop_off + 10
    # 16.16 fixed-point scale
    return (100 << 16) // lim, lim

@micropython.viper
def brightness_from_point_viper(x0:int, y0:int, ptx:int, pty:int,
                                coef:int, lim:int) -> int:
    dx:int = x0 - ptx
    dy:int = y0 - pty
    n:int = dx*dx + dy*dy

    # int sqrt (Newton)
    if n <= 0:
        dist:int = 0
    else:
        x:int = n
        y:int = (x + 1) >> 1
        while y < x:
            x = y
            y = (x + n // x) >> 1
        dist:int = x

    if dist <= 10:
        return 100
    if dist > lim:
        return 0

    # brightness = 100 * (lim - (dist-10)) / lim
    # -> ((coef * (lim - (dist-10))) >> 16)
    d:int = dist - 10
    usable:int = lim - d
    return (coef * usable) >> 16

@micropython.viper                                                                                                                                                                                           
def brightness_directional(x:int, y:int, cx:int, cy:int, ldx:int, ldy:int) -> int:                                                                                                                           
    # ldx, ldy = light direction * 100, e.g. top-left = (-70, -70)                                                                                                                                           
    dx:int = x - cx                                                                                                                                                                                          
    dy:int = y - cy                                                                                                                                                                                          
    dot:int = dx*ldx + dy*ldy                                                                                                                                                                                
    # scale down — divide by half-diagonal * 100                                                                                                                                                           
    b:int = 50 + dot // 200  # tune the divisor                                                                                                                                                              
    if b < 0: b = 0                                                                                                                                                                                          
    if b > 100: b = 100                                                                                                                                                                                      
    return b 

@micropython.viper    
def brightness_dome(x:int, y:int, cx:int, cy:int, hw:int, hh:int,                                                                                                                                            
                    ldx:int, ldy:int, ldz:int) -> int:                                                                                                                                                     
    # ldx, ldy, ldz = light direction, each component * 256                                                                                                                                                  
    # hw, hh = half width, half height of rect                                                                                                                                                               
    nx:int = (x - cx) * 256 // hw                                                                                                                                                                            
    ny:int = (y - cy) * 256 // hh                                                                                                                                                                            
    n2:int = nx*nx + ny*ny                                                                                                                                                                                   
    if n2 >= 65536:
        nz:int = 0  # edge/outside the dome                                                                                                                                                                  
    else:                                                                                                                                                                                                    
        r:int = 65536 - n2  # sqrt to get z component
        s:int = r; t:int = (s+1) >> 1                                                                                                                                                                        
        while t < s:                                                                                                                                                                                       
            s = t; t = (s + r//s) >> 1                                                                                                                                                                       
        nz:int = s                                                                                                                                                                                           
    dot:int = (nx*ldx + ny*ldy + nz*ldz) >> 16
    if dot < 0: dot = 0                                                                                                                                                                                      
    if dot > 100: dot = 100                                                                                                                                                                                  
    return dot

@timer
def fancy_fill_rect_b(fb,x,y,w,h,c,light_point=(0,0),drop_off=100):
        coef, lim = brightness_coef(drop_off)
        c = color565(c[0],c[1],c[2])
        b = MyFrameBuffer(50,50,bytearray(50*50*2))
        b.fill(c)
        n.draw_framebuf(0, 0, b)
        n.fill_rect(0, 500, 100, 100, c)
        for i in range(h):
            fancy_hline_fast(fb,x,y+i,w,c,light_point,coef,lim)

@timer
def fancy_fill_rect_a(fb,x,y,w,h,c,light_point=(0,0),drop_off=100):
        for i in range(h):
            fancy_hline(fb,x,y+i,w,c,light_point,drop_off)

@timer       
def fancy_rect(fb,x,y,w,h,c,light_point=(0,0),drop_off=100,y_lim=480):
    w -= 1
    h -= 1
    fancy_hline(fb,x,y,w,c,light_point,drop_off)
    if y+h < y_lim:
        fancy_hline(fb,x,y+h,w,c,light_point,drop_off)
    fancy_vline(fb,x,y,h,c,light_point,drop_off,y_lim)
    fancy_vline(fb,x+w,y,h,c,light_point,drop_off,y_lim)
    
def fancy_vline(fb,x,y,h,c,light_point=(0,0),drop_off=100,y_lim=480):
    coef, lim = brightness_coef(drop_off)
    for i in range(h+1 if y+h+1 < y_lim or y+h+1 < 480 else y_lim-y):
        b = brightness_from_point_viper(x, y+i, light_point[0], light_point[1], coef, lim)
        color = c_bright(c[0],c[1],c[2],b)
        fb.pixel(x,y+i,color)
    
def fancy_hline(fb,x,y,w,c,light_point=(0,0),drop_off=100):
    coef, lim = brightness_coef(drop_off)
    for i in range(w+1 if x+w+1 < 480 else 480-x):
        b = brightness_from_point_viper(x+i, y, light_point[0], light_point[1], coef, lim)
        color = c_bright(c[0],c[1],c[2],b)
        fb.pixel(x+i,y,color)

def fancy_hline_fast(fb,x,y,w,c,light_point,coef,lim):
    lp_x, lp_y = light_point
    for i in range(w+1 if x+w+1 < 480 else 480-x):
        bri = brightness_from_point_viper(x+i, y, lp_x, lp_y, coef, lim)
        color = cx_bright(c,bri)
        fb.pixel(x+i,y,color)

@timer
def fancy_fill_rect_direc(fb,x,y,w,h,c,light_point=(0,0),drop_off=100):
        coef, lim = brightness_coef(drop_off)
        c = color565(c[0],c[1],c[2])
        b = MyFrameBuffer(50,50,bytearray(50*50*2))
        b.fill(c)
        n.draw_framebuf(0, 0, b)
        n.fill_rect(0, 500, 100, 100, c)
        for i in range(h):
            fancy_hline_directional(fb,x,y+i,w,c,light_point,lp_end=(240,400))

def fancy_hline_directional(fb,x,y,w,c,light_point,lp_end):
    lp_x, lp_y = light_point
    vt_x, vt_y = lp_end
    for i in range(w+1 if x+w+1 < 480 else 480-x):
        bri = brightness_directional(x+i, y, lp_x, lp_y, vt_x, vt_y)
        color = cx_bright(c,bri)
        fb.pixel(x+i,y,color)

def fancy_hline_dome(fb,x,y,w,c,light_point,lp_end):
    lp_x, lp_y = light_point
    vt_x, vt_y = lp_end
    for i in range(w+1 if x+w+1 < 480 else 480-x):
        bri = brightness_dome(x+i, y, lp_x, lp_y, w//2, h//2,)
        color = cx_bright(c,bri)
        fb.pixel(x+i,y,color)

fancy_fill_rect_a(buf, 0, 50, 220, 380, (255,0,0), light_point=(110,240), drop_off=200)
fancy_fill_rect_b(buf, 220, 50, 220, 380, (255,0,0), light_point=(330,240), drop_off=200)
# fancy_fill_rect_direc(buf, 0, 0, 480, 800, (255,0,0), light_point=(240,400), drop_off=200) # idk what this does
# fancy_rect(buf, 50, 50, 220, 380, (255,0,0), light_point=(160,240), drop_off=200)

n.draw_framebuf(0, 0, buf)
c = (255,0,0)
print("c_bright: ", c_bright(c[0],c[1],c[2],50))
print("cx_bright: ",cx_bright(color565(c[0],c[1],c[2]),50))

# c_bright:  30720
# cx_bright:  108
# n.fill(0)
# for i in range(100):
#     n.fill_rect(int(i*4.8), 50, 100, 100, cx_bright(color565(255,0,0),100-i))