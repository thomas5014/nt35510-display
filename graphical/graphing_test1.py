import alias_lines
from display_drivers.nt35510_pio import NT35510, cx_bright, color565, MyFrameBuffer
import machine, random, time
machine.freq(240_000_000)

n = NT35510()

def alter_origin(x,y,x_offset=0,y_offset=400):
    return x+x_offset, y_offset-y

import math
def sine_graphed():
    for x in range(n.width):
        y = 40*math.sin(x/40)
        alias_lines.alias_point(n,*alter_origin(x,y),-1)

def x_squared(offset=240):
    for x in range(n.width):
        y = (x-offset)**2/100
        alias_lines.alias_point(n,*alter_origin(x,y),-1)

def x_inverse():
    for x in range(n.width):
        if not x-100: continue
        y = 1000/(x-100)
        alias_lines.alias_point(n,*alter_origin(x,y),-1)

def log_x():
    for x in range(n.width):
        if not x: continue
        y = 50*math.log(10*x)-100
        alias_lines.alias_point(n,*alter_origin(x,y),-1)

def tan_graphed():
    for x in range(n.width):
        y = 20*math.tan(x/30)
        alias_lines.alias_point(n,*alter_origin(x,y),-1)

def heart():
    for x in range(n.width):
        x-=100
        x/= 100
        try:
            y = math.sqrt(1-x**2)+x**2/3
        except: continue
        y *= 100
        x *= 100
        alias_lines.alias_point(n,*alter_origin(x,y,240),-1)
    for x in range(n.width):
        x-=100
        x/= 100
        try:
            y = -1*math.sqrt(1-x**2)+x**2/3
        except: continue
        y *= 100
        x *= 100
        alias_lines.alias_point(n,*alter_origin(x,y,240),-1)

n.fill(0)
# sine_graphed()
# x_squared()
# x_inverse()
# log_x()
# tan_graphed()
heart()