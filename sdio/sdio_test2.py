import gc
import os
import time
import machine
import binascii

# Adjust these if your sdio constructor takes arguments.
# This script assumes something like:
#   sd = sdio.SDCard()
# and that it supports readblocks(sector, buf)
import sdio


def hexdump_tail(buf, n=32):
    tail = buf[-n:]
    return " ".join("{:02x}".format(b) for b in tail)


def hexdump_head(buf, n=32):
    head = buf[:n]
    return " ".join("{:02x}".format(b) for b in head)


def count_nonzero(buf):
    c = 0
    for b in buf:
        if b:
            c += 1
    return c


def sector_signature_ok(buf):
    return len(buf) >= 512 and buf[510] == 0x55 and buf[511] == 0xAA


def try_init():
    gc.collect()
    try:
        sd = sdio.SDCard()
        print("sdio init: OK")
        return sd
    except Exception as e:
        print("sdio init failed:", repr(e))
        return None


def read_sector(sd, sector=0):
    buf = bytearray(512)
    t0 = time.ticks_us()
    sd.readblocks(sector, buf)
    dt = time.ticks_diff(time.ticks_us(), t0)
    return buf, dt


def compare_buffers(a, b):
    diffs = 0
    first_diff = -1
    for i in range(len(a)):
        if a[i] != b[i]:
            diffs += 1
            if first_diff < 0:
                first_diff = i
    return diffs, first_diff


def print_sector_summary(buf, dt_us, label=""):
    print("-" * 50)
    if label:
        print(label)
    print("read time us:", dt_us)
    print("nonzero bytes:", count_nonzero(buf))
    print("sig @510,511: 0x{:02x} 0x{:02x}".format(buf[510], buf[511]))
    print("sig ok:", sector_signature_ok(buf))
    print("head32:", hexdump_head(buf, 32))
    print("tail32:", hexdump_tail(buf, 32))


def basic_read_test(sd, attempts=5, sector=0):
    print("\n=== BASIC READ TEST ===")
    prev = None
    good = 0
    for i in range(attempts):
        try:
            buf, dt = read_sector(sd, sector)
            print_sector_summary(buf, dt, "attempt {}".format(i + 1))
            if sector_signature_ok(buf):
                good += 1
            if prev is not None:
                diffs, first_diff = compare_buffers(prev, buf)
                print("diffs vs previous:", diffs, "first diff:", first_diff)
            prev = buf
        except Exception as e:
            print("attempt", i + 1, "failed:", repr(e))
    print("good signatures:", good, "/", attempts)


def repeat_stability_test(sd, attempts=20, sector=0):
    print("\n=== STABILITY TEST ===")
    reference = None
    stable = 0
    ok_sig = 0
    for i in range(attempts):
        try:
            buf, dt = read_sector(sd, sector)
            sig = sector_signature_ok(buf)
            if sig:
                ok_sig += 1
            if reference is None:
                reference = bytes(buf)
                stable += 1
                print("baseline captured, dt_us =", dt, "sig =", sig)
            else:
                if bytes(buf) == reference:
                    stable += 1
                else:
                    diffs, first_diff = compare_buffers(reference, buf)
                    print("unstable read at", i + 1, "diffs =", diffs, "first_diff =", first_diff, "sig =", sig)
        except Exception as e:
            print("stability attempt", i + 1, "failed:", repr(e))
    print("stable reads:", stable, "/", attempts)
    print("good signatures:", ok_sig, "/", attempts)


def mount_test(sd):
    print("\n=== MOUNT TEST ===")
    try:
        vfs = os.VfsFat(sd)
        os.mount(vfs, "/sd")
        print("mount: OK")
        try:
            print("root:", os.listdir("/sd")[:20])
        finally:
            os.umount("/sd")
            print("unmounted")
    except Exception as e:
        print("mount failed:", repr(e))


def freq_sweep_test(freqs, sector=0, attempts_per_freq=3):
    print("\n=== MACHINE.FREQ SWEEP ===")
    original = machine.freq()
    print("original machine.freq():", original)
    for f in freqs:
        print("\nSetting machine.freq({})".format(f))
        try:
            machine.freq(f)
            time.sleep_ms(100)
            sd = try_init()
            if sd is None:
                continue
            good = 0
            for i in range(attempts_per_freq):
                try:
                    buf, dt = read_sector(sd, sector)
                    sig = sector_signature_ok(buf)
                    if sig:
                        good += 1
                    print("  read", i + 1, "dt_us =", dt,
                          "sig =", sig,
                          "tail =", "{:02x} {:02x}".format(buf[510], buf[511]))
                except Exception as e:
                    print("  read", i + 1, "failed:", repr(e))
            print("  good signatures:", good, "/", attempts_per_freq)
        except Exception as e:
            print("freq", f, "failed:", repr(e))

    try:
        machine.freq(original)
    except Exception as e:
        print("failed to restore original freq:", repr(e))


def main():
    print("Machine freq:", machine.freq())
    sd = try_init()
    if sd is None:
        return

    basic_read_test(sd, attempts=5, sector=0)
    repeat_stability_test(sd, attempts=20, sector=0)
    mount_test(sd)

    # Optional sweep. Adjust or comment out if too aggressive.
    freq_sweep_test([
        80_000_000,
        100_000_000,
        120_000_000,
        140_000_000,
        160_000_000,
        180_000_000,
        200_000_000,
    ])


if __name__ == "__main__":
    main()