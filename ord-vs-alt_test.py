import time, machine, framebuf


@micropython.viper
def test(c: object) -> int:
    for _ in range(1_000_000):
        # i: int = int(ptr8(c)[0])
        i: int = ord(c)
    return 0

t0: int = time.ticks_us()
test("A")
t1: int = time.ticks_us()
print(f"test: {t1 - t0:,}us, times per ms: {1_000_000 / ((t1 - t0) / 1_000):,.2f}")



# test: 986,726us, times per ms: 1013.45

# >>> ord
# test: 3,633,418us, times per ms: 275.22