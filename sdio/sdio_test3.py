import time
import gc
import os
import machine
import sdio


class SDIODiag:
    def __init__(self):
        self.sd = sdio.SDCard()

    @staticmethod
    def _tail(buf, n=32):
        return " ".join("{:02x}".format(b) for b in buf[-n:])

    @staticmethod
    def _head(buf, n=32):
        return " ".join("{:02x}".format(b) for b in buf[:n])

    @staticmethod
    def _count_nonzero(buf):
        c = 0
        for b in buf:
            if b:
                c += 1
        return c

    @staticmethod
    def _find_sig(buf, sig=b"\x55\xaa"):
        hits = []
        n = len(buf) - len(sig) + 1
        for i in range(n):
            if buf[i:i + len(sig)] == sig:
                hits.append(i)
        return hits

    @staticmethod
    def _diff_count(a, b):
        diffs = 0
        first = -1
        for i in range(len(a)):
            if a[i] != b[i]:
                diffs += 1
                if first < 0:
                    first = i
        return diffs, first

    def read_sector(self, lba=0):
        buf = bytearray(512)
        t0 = time.ticks_us()
        self.sd.readblocks(lba, buf)
        dt = time.ticks_diff(time.ticks_us(), t0)
        return buf, dt

    def summarize(self, buf, dt_us=None, label=None):
        if label is not None:
            print("-" * 60)
            print(label)
        if dt_us is not None:
            print("read_us:", dt_us)
        print("nonzero:", self._count_nonzero(buf))
        print("sig_510_511: 0x{:02x} 0x{:02x}".format(buf[510], buf[511]))
        print("sig_hits_55aa:", self._find_sig(buf, b"\x55\xaa"))
        print("sig_hits_5aae:", self._find_sig(buf, b"\x5a\xae"))
        print("sig_hits_5aa9:", self._find_sig(buf, b"\x5a\xa9"))
        print("head32:", self._head(buf, 32))
        print("tail32:", self._tail(buf, 32))

    def repeat_sector(self, lba=0, count=10):
        baseline = None
        good = 0
        for i in range(count):
            try:
                buf, dt = self.read_sector(lba)
                self.summarize(buf, dt, "read {}".format(i + 1))
                if buf[510] == 0x55 and buf[511] == 0xAA:
                    good += 1
                if baseline is None:
                    baseline = bytes(buf)
                else:
                    diffs, first = self._diff_count(baseline, buf)
                    print("diffs_vs_baseline:", diffs, "first_diff:", first)
            except Exception as e:
                print("read", i + 1, "failed:", repr(e))
        print("good_final_sig:", good, "/", count)

    def compare_lbas(self, lbas=(0, 1, 2048)):
        for lba in lbas:
            try:
                buf, dt = self.read_sector(lba)
                self.summarize(buf, dt, "lba {}".format(lba))
            except Exception as e:
                print("lba", lba, "failed:", repr(e))

    def mount_try(self):
        try:
            vfs = os.VfsFat(self.sd)
            os.mount(vfs, "/sd")
            try:
                print("mount_ok")
                print("root:", os.listdir("/sd"))
            finally:
                os.umount("/sd")
        except Exception as e:
            print("mount_failed:", repr(e))

    def freq_sweep(self, freqs):
        original = machine.freq()
        print("orig_freq:", original)
        for f in freqs:
            print("\n=== freq", f, "===")
            try:
                machine.freq(f)
                time.sleep_ms(100)
                gc.collect()
                self.sd = sdio.SDCard()
                buf, dt = self.read_sector(0)
                self.summarize(buf, dt, "freq {}".format(f))
            except Exception as e:
                print("freq", f, "failed:", repr(e))
        try:
            machine.freq(original)
        except Exception as e:
            print("restore_freq_failed:", repr(e))


def main():
    print("machine.freq():", machine.freq())
    d = SDIODiag()
    d.repeat_sector(0, 8)
    d.compare_lbas((0, 1, 2048))
    d.mount_try()
    d.freq_sweep((80_000_000, 100_000_000, 120_000_000, 150_000_000, 180_000_000))


if __name__ == "__main__":
    main()