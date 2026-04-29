from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
import machine
machine.freq(240_000_000)

@micropython.viper
def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a

n = NT35510()

dithbuf = bytearray(480*3) # 480 pixel, 2 byte per pixel buffer

n.fill(-1)
BLUE = color565(0,150,255)
YELLOW = color565(255,255,0)
n.fill(YELLOW)
bcolors = [
    color565(0,150,255),  # Bright blue
    color565(0,0,255),    # Blue
    color565(0,71,171),   # Colbalt blue
    color565(63,0,255),   # Indigo
    color565(31,81,255),  # Neon blue
    color565(65,105,225), # Royal blue
    color565(4,55,242),   # Ultramarine
    color565(137,207,240),# Baby blue
    color565(125,249,255),# Electric blue
    color565(93,63,211),  # Iris
    color565(173,216,230),# Light blue
    color565(25,25,112),  # Midnight blue
    color565(167,199,231),# Pastel blue
    color565(15,82,186),  # Sapphire blue
    color565(64,224,208), # Turquose
    color565(70,130,180), # Steel blue
    color565(8,24,168),   # Zaffre
    color565(111,143,175) # Denim
]
BLUE = bcolors[2]
ycolors = [
    color565(255,255,0),    # Pure yellow
    color565(255,222,33),   # Bright yellow
    color565(223,222,0),    # Chartreuse
    color565(255,255,143),  # Canary yellow
    color565(253,218,13),   # Cadmium yellow
    color565(255,215,0),    # Gold
    color565(255,192,0),    # Golden yellow
    color565(252,245,95),   # Icterine
]
YELLOW = ycolors[5]
for i, c in enumerate(bcolors):
    height = 800/len(bcolors)
    n.fill_rect(0, round(i*height), 480, round((i+1)*height), c)

import sys
# sys.exit(1)
import time
# time.sleep(3)
# n.fill(YELLOW)
n.fill_rect(0,0,480,400,YELLOW)
n.fill_rect(0,400,480,400,BLUE)

def dithered_rect(x,y,w,h,tcolor,bcolor,dithbuf=None,use_gcd=True):
    if dithbuf:
        dithbuf = memoryview(dithbuf[:w*2])
        print("Dithering buffer exists, skipping")
    else:
        print("Creating dithering buffer")
        dithbuf = bytearray(w*3) # 1 line of pixel data
    fb = MyFrameBuffer(w,1,dithbuf)
    def dith_line(x,y,percent):
        nonlocal fb
        intresting_int = 0
        # print("Percent: ",percent)
        if use_gcd:
            gcf = gcd(percent,100)
            cycle_len = 100//gcf
            c_freq = percent//gcf
        else:
            cycle_len = w
            c_freq = int(percent * w)
        # print(f"Lap Lenght: {cycle_len}, color freq: {c_freq}")
        fb.fill(tcolor)
        itters = c_freq//100 + 100//(percent+.1)
        for lx in range(itters):
            if not c_freq: continue
            if use_gcd:
                bx = ((lx%cycle_len)*cycle_len//c_freq)# % cycle_len
                fb.pixel(bx + lx//cycle_len*(cycle_len+intresting_int), 0, bcolor)
            else:
                bx = (lx%cycle_len)*cycle_len*100//c_freq
                if bx > cycle_len: continue
                fb.pixel(int(bx + lx//cycle_len*cycle_len), 0, bcolor)
            # fb.pixel(lx,0,-1)
        n.draw_framebuf(x,y,fb)
    y -= h//2
    for ly in range(h):
        if use_gcd:
            dith_line(x,y+ly,ly*100//h)
        else:
            dith_line(x,y+ly,ly*100/h)
    
# height = 60
# start = 400-10*height//2
# for i in range(5):
#     dithered_rect(0,start+i*height*2,480,height,YELLOW,BLUE,dithbuf)
#     dithered_rect(0,start+height+i*height*2,480,height,BLUE,YELLOW,dithbuf)
# dithered_rect(0,start+height*2+i*height*2,480,height,YELLOW,BLUE,dithbuf)


# time.sleep(3)
n.fill(0)
# n.fill_rect(0,0,480,400,YELLOW)
# n.fill_rect(0,400,480,400,BLUE)
# dithered_rect(0,400,480,200,YELLOW,BLUE,dithbuf)
t0 = time.ticks_us()
dithered_rect(0,400,480,800,0,BLUE,dithbuf,use_gcd=False)
t1 = time.ticks_us()
print(f"{t1-t0:,}us")