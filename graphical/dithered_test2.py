from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
import machine, random
machine.freq(240_000_000)

n = NT35510()

dithbuf = bytearray(480*3) # 480 pixel, 2 byte per pixel buffer

def dithered_rect(x,y,w,h,tcolor,bcolor,dithbuf=None,use_gcd=True):
    if dithbuf:
        dithbuf = memoryview(dithbuf[:w*2])
        print("Dithering buffer exists, skipping")
    else:
        print("Creating dithering buffer")
        dithbuf = bytearray(w*2) # 1 line of pixel data
    fb = MyFrameBuffer(w,1,dithbuf)
    def dith_line(x,y,percent):
        nonlocal fb
        fb.fill(tcolor)
        lx: int = 0
        while lx < w:
            if random.random() < percent/100:
                fb.pixel(lx, y, bcolor)
            lx += 1
        n.draw_framebuf(x,y,fb)

    y -= h//2
    for ly in range(h):
        dith_line(x,y+ly,ly*100/h)


BLUE = color565(0,150,255)
n.fill(0)
# n.fill_rect(0,0,480,400,YELLOW)
n.fill_rect(0,400,480,400,BLUE)
# dithered_rect(0,400,480,200,YELLOW,BLUE,dithbuf)

dithered_rect(0,400,480,800,0,BLUE,dithbuf)