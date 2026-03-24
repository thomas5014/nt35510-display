import sdio, errno    
import uctypes                                                                                                                                                                           
try:            
    sd = sdio.SDCard()
except OSError as e:
    print("errno:", e.args[0], errno.errorcode.get(-e.args[0], "?"))       

import sdio                                                                                                                                                                                
d = sdio.SDCard()                                                                                                                                                                          
buf = bytearray(512)                                                                                                                                                                       
d.readblocks(0, buf)                                                           
for i in range(0, 512, 32):                                                                                                                                                                
    print('%3d:' % i, ' '.join('%02x' % b for b in buf[i:i+32]))                                                                                                            
print(hex(buf[510]), hex(buf[511]))   # expect 0x55, 0xaa for valid MBR            

# raise
import sdio, os                                             
d = sdio.SDCard()                                                                                                                                                                          
buf = bytearray(512)                                                                                                                                                                       
d.readblocks(0, buf)            
d.readblocks(0, buf)                                                                                                                                                                     
print(hex(buf[510]), hex(buf[511]))  # should be 0x55, 0xaa for valid MBR                                                                                                                                                           
# check: does os.mount work?                                                                                                                                                               
# os.mount(d, '/sd')                                                                                                                                                                         
# os.listdir('/sd')

# raise
import sdio, os                                                                                                                                                                            
d = sdio.SDCard()                                                                                                                                                                          
buf = bytearray(512)                                                                                                                                                                       
d.readblocks(0, buf)                                                                                                                                                                       
print(buf[:16].hex())

# raise
import uctypes                                                                                                                                                                             
# PIO1 GPIOBASE register at 0x50300000 + 0x03C                                                                                                                                             
r = uctypes.struct(0x5030003C, {'v': 0 | uctypes.UINT32})                                                                                                                                  
print(f"PIO1 GPIOBASE = {r.v}")

# raise
 # PIO1 base: 0x50300000                                                                                                                                                                    
# SM0 PINCTRL offset: 0x0DC                                                                                                                                                                
PIO1_SM0_PINCTRL = 0x503000DC                                                                                                                                                              
reg = uctypes.struct(PIO1_SM0_PINCTRL, {'v': 0 | uctypes.UINT32})                                                                                                                          
v = reg.v                                                                                                                                                                                  
in_base  = (v >> 16) & 0x1F                                                                                                                                                                
out_base = (v >>  0) & 0x1F                                                                                                                                                                
set_base = (v >>  5) & 0x1F                                                                                                                                                                
side_base= (v >> 10) & 0x1F                                                                                                                                                                
print(f"PINCTRL: {v:#010x}")                                                                                                                                                               
print(f"  in_base={in_base}  out_base={out_base}  set_base={set_base}  sideset_base={side_base}") 
# raise
                                                                                                                                                                         
                                                                                                                                                                                             
# Read raw SIO GPIO_IN register (all GPIO0-31 input values, bypasses Python Pin)                                                                                                           
SIO_GPIO_IN = uctypes.struct(0xD0000004, {'v': 0 | uctypes.UINT32})                                                                                                                        
val = SIO_GPIO_IN.v                                                                                                                                                                        
print(f"GPIO24-29 raw: {(val >> 24) & 0x3F:06b}")
print(f"  GPIO24(CLK)={val>>24&1}  GPIO25(CMD)={val>>25&1}  GPIO26(D0)={val>>26&1}")                                                                                                       
print(f"  GPIO27(D1)={val>>27&1}  GPIO28(D2)={val>>28&1}  GPIO29(D3)={val>>29&1}")


# raise
buf = bytearray(512)                                                                                                                                                                         
sd.readblocks(0, buf)
print(buf[:16].hex())
os.mount(d, '/sd')                                                                                                                                                                         
os.listdir('/sd')