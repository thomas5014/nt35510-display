import time
from display_drivers.nt35510 import NT35510, cx_bright, color565
import machine
machine.freq(240_000_000)
d = NT35510()

def alias_point(x,y,color):
    if type(x) is float or type(y) is float:
        xf: float = (x % 1) * 50
        yf: float = (y % 1) * 50
        c0: int = int(50 - xf)
        c1: int = int(50 - yf)
        c2: int = int(xf)
        c3: int = int(yf)
        # print(f"alias_point: x={x:.2f}, y={y:.2f}, c0={c0:.2f}, c1={c1:.2f}, c2={c2:.2f}, c3={c3:.2f}")
        # print((c0+c1), (c2+c1), (c0+c3), (c2+c3))
        x:int = int(x); y: int = int(y)
        d.pixel(x,y,cx_bright(color, (c0+c1)))
        d.pixel(x+1,y,cx_bright(color, (c2+c1)))
        d.pixel(x,y+1,cx_bright(color, (c0+c3)))
        d.pixel(x+1,y+1,cx_bright(color, (c2+c3)))
    else:
        d.pixel(x,y,color)

def alias_line(x0, y0, x1, y1, color):
    if x0 == x1:  # vertical line
        if y0 > y1:
            y0, y1 = y1, y0
        for y in range(int(y0), int(y1)+1):
            alias_point(x0, y, color)
        return

    slope: float = (y1 - y0) / (x1 - x0)
    if abs(slope) <= 1:
        if x0 > x1:
            x0, x1 = x1, x0
        for x in range(int(x0), int(x1)+1):
            y: float = y0 + slope * (x - x0)
            alias_point(x, y, color)
    else:
        if y0 > y1:
            y0, y1, x0, x1 = y1, y0, x1, x0
        for y in range(int(y0), int(y1)+1):
            x: float = x0 + (y - y0) / slope
            alias_point(x, y, color)

# from assests import AssetCache
# asses = AssetCache()
# def round_rect(fb,x,y,w,h,color,fill=True,curve=5):
#     if fill:
#         fill = 1
#     else:
#         fill = 0
#     round_rect_viper(fb,int(x),int(y),int(w),int(h),color,fill,curve)

# @micropython.viper
# def round_rect_viper(fb:object,x:int,y:int,w:int,h:int,color:object,fill:int,curve:int):
#         if type(color) is tuple:
#             color: int = color565(*color)
#         w -= 1
#         h -= 1
#         if fill:
#             fb.fill_rect(x+curve,y,w-curve*2+1,h,color)
#             for i in range(2):
#                 x_inv: int = -1 if i%2 == 1 else 1
#                 w_shift: int = w if i%2 == 1 else 0
#                 fb.vline(x+w_shift,y+curve,h-curve*2,color)
#                 for pt in asses.curves(curve):
#                     if type(pt) is int:
#                         continue
#                     lx = x + w_shift + (curve+pt[0]) * x_inv 
#                     ly = y + curve + pt[1]
#                     llength = h - (curve+pt[1]) * 2
#                     fb.vline(lx,ly,llength,color)
#         else:
#             for i in range(4):
#                 x_inv = -1 if i%2 == 1 else 1
#                 y_inv = -1 if i//2 == 1 else 1
#                 w_shift = w if i%2 == 1 else 0
#                 h_shift = h if i//2 == 1 else 0
#                 center = (x+curve*x_inv + w_shift, y+curve*y_inv + h_shift)

#                 lx = x + curve if i%2 == 0 else x + (w_shift if i != 3 else 0) # i'm sorry
#                 ly = y + curve if i%2 == 1 else y + h_shift
#                 llength = w - curve*2 if i%2 == 0 else h - curve*2  # nvm f u
#                 ltype = fb.hline if i%2 == 0 else fb.vline
#                 ltype(lx,ly,llength+1,color)
                
#                 for pt in asses.curves(curve):
#                     if type(pt) is int:
#                         continue
#                     px = center[0] + pt[0] * x_inv
#                     py = center[1] + pt[1] * y_inv
#                     fb.pixel(px,py,color)

d.fill(0)
import math

for i in range(0, 10, 10):
    for a in range(0, 360, 1):
        x = 120 + 100 * math.cos(math.radians(a)) + i
        y = 120 + 100 * math.sin(math.radians(a)) + i

        alias_point(x, y, -1)
        d.pixel(int(x),int(y+50),-1)
        # d.pixel(int(x), int(y), -1)
alias_line(10, 10, 200, 200, -1)
alias_line(10, 10, 200, 800, -1)

# p = 0
# t0 = time.ticks_ms()
# while p < 1_000:
#     round_rect(d, 10, 10, 400, 500, (200,255,180), fill=True, curve=5)
#     p += 1
# t1 = time.ticks_ms()
# print(f"Time taken: {t1 - t0} ms")  

