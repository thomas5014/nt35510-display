""" 4-Bit SDIO communication test
Allocated Pins:
    GPIO0 - 15: 16-Bit Display communication
    GPIO18    : WR  :  Write Pin
    GPIO19    : CS  :  Chip Select
    GPIO20    : DC  :  Command/Data
    GPIO21    : RST :  Reset
    GPIO22    : BL  :  Back Light
    GPIO26/40 : RD  :  Read        ---       pin 40 for RP2350B Plus W Board
    #######  new  ########
    GPIO24    : CLK :  Clock
    GPIO25    : CMD :  Command
    GPIO26    : DO  :  Data 0
    GPIO27    : D1  :  Data 1
    GPIO28    : D2  :  Data 2
    GPIO29    : D3  :  Data 3
"""
from nt35510 import NT35510
import gc, micropython, os, sdio

from machine import Pin
for n in [24, 25, 26, 27, 28, 29]:  # CMD, D0-D3                                                                                                                                                 
    print(f"GPIO{n}: {Pin(n, Pin.IN).value()}")
sd = sdio.SDCard(clk=24, cmd=25, d0=26, d1=27, d2=28, d3=29)
print(os.listdir())
os.mount(sd, "/sd")
files = os.listdir()
if files:
    print("SD Csrd Files: ", files)
    for file in files:
        if file.split(".") == "txt":
            print(f"Opening {file}, Contents: {open(f'/sd/{file}',"r").read()}")
else:
    print("SD Card is empty")
    import sys
    sys.exit(1)