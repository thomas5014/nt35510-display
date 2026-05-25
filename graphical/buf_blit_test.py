test = 1
if test == 0:
    from nt35510_pio import NT35510, cx_bright, color565, MyFrameBuffer
    import machine, random, time, os
    machine.freq(260_000_000)

    image_num = 0
    file = [f for f in os.listdir("/") if "sample" in f][image_num]
    width = int(file.split("_")[1][:3])
    height = int(file.split("_")[1][4:7])

    n = NT35510()
    # n = NT35510(pio_freq=260_000_000)
    temp = bytearray(520*1024*2)
    buf = bytearray(width*height*2)
    del temp

    n.fill(0)
    t0 = time.ticks_us()
    with open(file,"rb") as f:
        f.readinto(buf)
        t2 = time.ticks_us()
        n.draw_buf(0, 0, width, height, buf)
        # n.draw_buf_be(0, 0, width, height, buf)  # swap+draw in one PSRAM pass; no switch_bytes needed
    t1 = time.ticks_us()
    print(f"{t1-t0:,}:Total {t2-t0:,}:Read {t1-t2:,}:Draw")
    print(machine.freq())

elif test == 1:
    from nt35510 import NT35510, cx_bright, color565, MyFrameBuffer
    import machine, random, time, os
    machine.freq(260_000_000)

    image_num = 0
    file = [f for f in os.listdir("/") if "sample" in f][image_num]
    width = int(file.split("_")[1][:3])
    height = int(file.split("_")[1][4:7])
    print(f"Displaying file: {file}, with w and h of {width} and {height} respectively.")

    n = NT35510()
    temp = bytearray(520*1024*2)
    buf = bytearray(width*height*2)
    del temp


    n.fill(0)
    t0 = time.ticks_us()
    with open(file,"rb") as f:
        f.readinto(buf)
        t2 = time.ticks_us()
        n.draw_buf(0, 0, width, height, buf)
        # n.draw_buf_be(0, 0, width, height, buf)  # swap+draw in one PSRAM pass; no switch_bytes needed
    t1 = time.ticks_us()
    print(f"{t1-t0:,}:Total {t2-t0:,}:Read {t1-t2:,}:Draw")
    print(machine.freq())

print("test: ",test)