import time, machine
machine.freq(240_000_000)
# >>> 1_000_000_000/240_000_000
# 4.1666664ns

@micropython.viper
def test(itter: int) -> int:
    i: int = 0
    x: int = 0
    c_ptr: ptr8 = ptr8("A")
    t0: int = time.ticks_us()
    while i < itter:
        i += 1 + x
    t1: int = time.ticks_us()
    t: int = int(t1-t0)
    return t


itter: int = 1_000_000
length: int = test(itter)
zero: int = 45836
length -= zero
print(f"Time for itterating {itter:,} times: {length:,} microseconds. Times per us or MHz: {itter/length:.2f}, ns per itter: {length*1000/itter:.2f}. Freq {machine.freq()/1_000_000:.} MHz. Baseline: {zero:,} microseconds.")
# Time for itterating 1,000,000 times: 45,836 microseconds. Times per us: 21.82, ns per itter: 45.84.   baseline
# Time for itterating 1,000,000 times: 54,169 microseconds. Times per us: 18.46, ns per itter: 54.17.   o: int = 0
# Time for itterating 1,000,000 times: -1 microseconds. Times per us or MHz: -1000000.00, ns per itter: -0.00. Freq 240 MHz. Baseline: 45,836 microseconds. tared baseline, so -1 us is just noise. o: int = 0
# Time for itterating 1,000,000 times: 8,333 microseconds. Times per us or MHz: 120.00, ns per itter: 8.33. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = 0
# Time for itterating 1,000,000 times: 33,332 microseconds. Times per us or MHz: 30.00, ns per itter: 33.33. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = 10/10
# Time for itterating 1,000,000 times: 8,333 microseconds. Times per us or MHz: 120.00, ns per itter: 8.33. Freq 240 MHz. Baseline: 45,836 microseconds.  o: int = 10//10
# Time for itterating 1,000,000 times: 2,441,703 microseconds. Times per us or MHz: 0.41, ns per itter: 2441.70. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = ord("A")
# Time for itterating 1,000,000 times: 533,341 microseconds. Times per us or MHz: 1.87, ns per itter: 533.34. Freq 240 MHz. Baseline: 45,836 microseconds.  o: int = ptr8("A")[0]
# Time for itterating 1,000,000 times: 8,333 microseconds. Times per us or MHz: 120.00, ns per itter: 8.33. Freq 240 MHz. Baseline: 45,836 microseconds. o: int = c_ptr[0]
# Time for itterating 1,000,000 times: 12,499 microseconds. Times per us or MHz: 80.01, ns per itter: 12.50. Freq 240 MHz. Baseline: 45,836 microseconds. if i: 0 
# Time for itterating 1,000,000 times: 8,332 microseconds. Times per us or MHz: 120.02, ns per itter: 8.33. Freq 240 MHz. Baseline: 45,836 microseconds. ... + x # x: int = 0