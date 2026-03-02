from nt35510 import NT35510, color565, cx_bright
import time

t0 = time.ticks_ms()
d = NT35510()
d.fill(color565(30,20,40))
for i in range(6):
    x = 30 + 220*(i%2)
    y = 30 + 250*(i//2)
    d.fill_rect(x ,y ,200, 230, color565(70,40,70))
    print(x,y,i,i%2,250*i%2)


t1 = time.ticks_ms()
print("total time: ", t1- t0)