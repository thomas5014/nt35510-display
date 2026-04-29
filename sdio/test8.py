import time, gc, machine
print(machine.freq())
freq = 250_000_000
print(f"Changing freq to: {freq}")
machine.freq(freq)
print("Current new freq: ",machine.freq())
@micropython.viper
def mem_access_stest():
    itters: int = 1_000_000
    in_time: int = 0
    out_time: int = 0
    control: int = 0
    i: int = 0
    buf_size = 100*1024
    bufs = []
    for i in range(70):
        bufs.append(bytearray(buf_size))
        print(f"p {ptr32(bufs[-1]):x}")

    buf1 = bufs[0]
    buf2 = bufs[-1]
    print(f"pointers {ptr32(buf1):x} {ptr32(buf2):x}")
    gc.collect()
    # internal memory test
    t0 = time.ticks_cpu()
    while i < itters:
        buf1[i%buf_size] = i
        i += 1
    t1 = time.ticks_cpu()
    # external memory test
    i: int = 0
    t2 = time.ticks_cpu()
    while i < itters:
        buf2[i%buf_size] = i
        i += 1
    t3 = time.ticks_cpu()
    # assign proper value when raw while/i cycle is measured
    t_shift = 0
    in_time: int = int(t1-t0)
    out_time: int = int(t3-t2)
    control: int = int(time.ticks_cpu()-time.ticks_cpu())
    print(f"Internal memory access: {in_time:,}")
    print(f"External memory acces speed: {out_time:,}")
    print(f"Control: {control}")
    import micropython
    micropython.mem_info()

mem_access_stest()