import time, machine
from micropython import const
# import micropython 
from nt35510 import MyFrameBuffer
machine.freq(240_000_000)
# >>> 1_000_000_000/240_000_000
# 4.1666664ns

@micropython.viper
def gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a

# test_file = open("sample5_480-800.raw", "rb").read()
# buf = memoryview(bytearray(32))
# fb = MyFrameBuffer(4,4,buf)
a: int = 0 
ONE = const(1)
@micropython.viper
def test(itter: int) -> int:
    global a
    i: int = 0
    #buf22 = memoryview(bytearray(32))
    # t_p: ptr8 = ptr8(test_file)
    # print(f"ptr8 of buf: {t_p:X}, ptr8 of buf[0]: {t_p[0]}")
    # fb = MyFrameBuffer(4,4,buf)
    x: int = 0
    # buf: bytearray = bytearray(0)
    # c_ptr: ptr8 = ptr8("A")
    t0: int = time.ticks_us()
    while i < itter:
        # i: int = i + 0
        # x: int = 0
        # fb.pixel(0,0,0)
        # t_p[0]
        i += ONE
    t1: int = time.ticks_us()
    t: int = int(t1-t0)
    return t

# print("with: 't_p: ptr8 = ptr8(buf)'")
# raw = micropython.viper_code(test)                                                                                                                                                    
# print(len(raw), 'bytes of machine code (ARM Thumb2)')
# print(' '.join('%02x' % b for b in raw))
# import sys
# sys.exit(1)
print("Starting")
print(test)
itter: int = 1_000_000
length: int = test(itter)
zero: int = 45836
ns_per_cycle: float = 4.1666664
length -= zero
print(f"Time for itterating {itter:,} times: {length:>9,} microseconds. Times per us or MHz: {itter/length:>11.2f}, ns per itter: {length*1000/itter:>7.2f}, clock cycles per itter: {(length*1000/itter)/ns_per_cycle:>7.2f}. Freq {machine.freq()/1_000_000:.} MHz. Baseline: {zero:,} microseconds.")
# Time for itterating 1,000,000 times:    45,836 microseconds. Times per us: 21.82, ns per itter: 45.84.   baseline
# Time for itterating 1,000,000 times:    54,169 microseconds. Times per us: 18.46, ns per itter: 54.17.   o: int = 0
# Time for itterating 1,000,000 times:        -1 microseconds. Times per us or MHz: -1000000.00, ns per itter:   -0.00. Freq 240 MHz. Baseline: 45,836 microseconds. tared baseline, so -1 us is just noise. o: int = 0
# Time for itterating 1,000,000 times:     8,333 microseconds. Times per us or MHz:      120.00, ns per itter:    8.33. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = 0
# Time for itterating 1,000,000 times:    33,332 microseconds. Times per us or MHz:       30.00, ns per itter:   33.33. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = 10/10
# Time for itterating 1,000,000 times:     8,333 microseconds. Times per us or MHz:      120.00, ns per itter:    8.33. Freq 240 MHz. Baseline: 45,836 microseconds.  o: int = 10//10
# Time for itterating 1,000,000 times: 2,441,703 microseconds. Times per us or MHz:        0.41, ns per itter: 2441.70. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = ord("A")
# Time for itterating 1,000,000 times:   533,341 microseconds. Times per us or MHz:        1.87, ns per itter:  533.34. Freq 240 MHz. Baseline: 45,836 microseconds.  o: int = ptr8("A")[0]
# Time for itterating 1,000,000 times:     8,333 microseconds. Times per us or MHz:      120.00, ns per itter:    8.33. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = c_ptr[0]
# Time for itterating 1,000,000 times:    12,499 microseconds. Times per us or MHz:       80.01, ns per itter:   12.50. Freq 240 MHz. Baseline: 45,836 microseconds. if i: 0 
# Time for itterating 1,000,000 times:     8,332 microseconds. Times per us or MHz:      120.02, ns per itter:    8.33. Freq 240 MHz. Baseline: 45,836 microseconds. ... + x # x: int = 0
# Time for itterating 1,000,000 times: 2,562,539 microseconds. Times per us or MHz:        0.39, ns per itter: 2562.54. Freq 240 MHz. Baseline: 45,836 microseconds. x = int(len("A"))
# Time for itterating 1,000,000 times: 2,291,693 microseconds. Times per us or MHz:        0.44, ns per itter: 2291.69. Freq 240 MHz. Baseline: 45,836 microseconds. x = int(len(buf)) buf: bytearray = bytearray(16)
# Time for itterating 1,000,000 times:    12,499 microseconds. Times per us or MHz:       80.01, ns per itter:   12.50. Freq 240 MHz. Baseline: 45,836 microseconds. x: str = "A"
# Time for itterating 1,000,000 times:     8,333 microseconds. Times per us or MHz:      120.00, ns per itter:    8.33. Freq 240 MHz. Baseline: 45,836 microseconds. x: str = "A" but pre loop x: str = "A"
# Time for itterating 1,000,000 times: 4,925,056 microseconds. Times per us or MHz:        0.20, ns per itter: 4925.06. Freq 240 MHz. Baseline: 45,836 microseconds. x: str = f"a"
# Time for itterating 1,000,000 times:   437,507 microseconds. Times per us or MHz:        2.29, ns per itter:  437.51. Freq 240 MHz. Baseline: 45,836 microseconds. if x: 0 pre loop: x: str = "A"
# Time for itterating 1,000,000 times:     4,165 microseconds. Times per us or MHz:      240.10, ns per itter:    4.17. Freq 240 MHz. Baseline: 45,836 microseconds. x: int = 0 pre look x: int = 0
# Time for itterating 1,000,000 times: 11,888,471microseconds. Times per us or MHz:        0.08, ns per itter: 11888.47.Freq 240 MHz. Baseline: 45,836 microseconds. gcd(10,10)
# Time for itterating 1,000,000 times: 1,500,007 microseconds. Times per us or MHz:        0.67, ns per itter: 1500.01. Freq 240 MHz. Baseline: 45,836 microseconds. gcd(10,10) with viper
# Time for itterating 1,000,000 times:     4,165 microseconds. Times per us or MHz:      240.10, ns per itter:    4.17. Freq 240 MHz. Baseline: 45,836 microseconds. x: int = 10 % 2
# Time for itterating 1,000,000 times:     4,167 microseconds. Times per us or MHz:      239.98, ns per itter:    4.17, clock cycles per itter:    1.00. Freq 240 MHz. Baseline: 45,836 microseconds. x: int = 0 pre look x: int = 0 not big outside allocations\


# >>> 
# without: 't_p: ptr8 = ptr8(buf)'
# 254 bytes of machine code (ARM Thumb2)
# fe b5 9a b0 47 68 be 68 ff 68 7f 69 13 90 08 46 11 46 1d 46 00 29 40 f0 04 80 01 22 90 42 00 f0 07 80 40 f2 02 02 c0 f2 02 02 d7 f8 b0 30 98 47 28 68 02 21 fb 68 98 47 04 46 13 98 40 68 40 68 7b 69 98 47 14 90 00 28 00 f0 0e 80 00 a8 d7 f8 80 30 98 47 00 28 00 f0 07 80 14 98 7b 69 98 47 01 98 d7 f8 88 30 98 47 00 25 00 20 1b 90 b0 88 fb 69 98 47 15 aa b1 8c bb 6a 98 47 15 aa 00 20 00 21 3b 6f 98 47 1a 90 00 f0 06 b8 00 20 1b 90 01 22 29 46 89 18 0d 46 29 46 a1 42 b4 bf 01 20 00 20 00 28 f2 d1 b0 88 fb 69 98 47 15 aa b1 8c bb 6a 98 47 15 aa 00 20 00 21 3b 6f 98 47 19 90 19 98 16 90 1a 98 02 46 16 99 1c 20 bb 6c 98 47 02 21 fb 68 98 47 18 90 18 98 02 21 3b 69 98 47 12 90 00 f0 00 b8 14 98 00 28 00 f0 05 80 7b 69 98 47 d7 f8 84 30 98 47 12 98 1a b0 fe bd
# Starting
# Time for itterating 1,000,000 times:     8,340 microseconds. Times per us or MHz:      119.90, ns per itter:    8.34, clock cycles per itter:    2.00. Freq 240 MHz. Baseline: 45,836 microseconds.

# >>> 
# with: 't_p: ptr8 = ptr8(buf)'
# 268 bytes of machine code (ARM Thumb2)
# fe b5 9a b0 47 68 be 68 ff 68 7f 69 13 90 08 46 11 46 1d 46 00 29 40 f0 04 80 01 22 90 42 00 f0 07 80 40 f2 02 02 c0 f2 02 02 d7 f8 b0 30 98 47 28 68 02 21 fb 68 98 47 04 46 13 98 40 68 40 68 7b 69 98 47 14 90 00 28 00 f0 0e 80 00 a8 d7 f8 80 30 98 47 00 28 00 f0 07 80 14 98 7b 69 98 47 01 98 d7 f8 88 30 98 47 00 25 70 8e fb 69 98 47 05 21 fb 68 98 47 1c 90 00 20 1b 90 b0 88 fb 69 98 47 15 aa b1 8c bb 6a 98 47 15 aa 00 20 00 21 3b 6f 98 47 1a 90 00 f0 06 b8 00 20 1b 90 01 22 29 46 89 18 0d 46 29 46 a1 42 b4 bf 01 20 00 20 00 28 f2 d1 b0 88 fb 69 98 47 15 aa b1 8c bb 6a 98 47 15 aa 00 20 00 21 3b 6f 98 47 19 90 19 98 16 90 1a 98 02 46 16 99 1c 20 bb 6c 98 47 02 21 fb 68 98 47 18 90 18 98 02 21 3b 69 98 47 12 90 00 f0 00 b8 14 98 00 28 00 f0 05 80 7b 69 98 47 d7 f8 84 30 98 47 12 98 1a b0 fe bd
# Starting
# Time for itterating 1,000,000 times:     8,339 microseconds. Times per us or MHz:      119.92, ns per itter:    8.34, clock cycles per itter:    2.00. Freq 240 MHz. Baseline: 45,836 microseconds.