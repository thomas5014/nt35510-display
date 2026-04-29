from display_drivers.nt35510 import NT35510, color565, cx_bright
import time
d = NT35510()
d.fill(color565(30,20,40))
for o in range(100):
    offset = 0-o*5
    t0 = time.ticks_ms()
    
    for i in range(6):
        x = 30 + 220*(i%2)
        y = (30 + 250*(i//2) + offset) % 800

        d.fill_rect(x ,y ,200, 230, color565(70,40,70))
        d.fill_rect(x ,y+230 ,200, 20, color565(230,20,40))

        # print(x,y,i,i%2,250*i%2)
    d.fill_rect(30, 0, 480, 30, color565(30,20,40))
    d.fill_rect(30, 770, 480, 30, color565(30,20,40))
    t1 = time.ticks_ms()
    print("total time: ", t1- t0)

# thomas does not in fact know what he is doing right now