import time, machine
from micropython import const
machine.freq(240_000_000)
# >>> 1_000_000_000/240_000_000
# 4.1666664ns
a: int = 0 
ONE = const(1)
@micropython.viper
def test(itter: int) -> int:
    global a
    i: int = 0
    x: int = 0
    buf: bytearray = bytearray(0)
    c_ptr: ptr8 = ptr8("A")
    t0: int = time.ticks_us()
    while i < itter:
        # a: int = 0
        i += ONE
    t1: int = time.ticks_us()
    t: int = int(t1-t0)
    return t


itter: int = 1_000_000
length: int = test(itter)
zero: int = 45836
length -= zero
print(f"Time for itterating {itter:,} times: {length:>9,} microseconds. Times per us or MHz: {itter/length:>11.2f}, ns per itter: {length*1000/itter:>7.2f}. Freq {machine.freq()/1_000_000:.} MHz. Baseline: {zero:,} microseconds.")
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