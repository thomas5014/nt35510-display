from display_drivers.nt35510_pio import NT35510 as NT35510_PIO
from display_drivers.nt35510 import color565, MyFrameBuffer, cx_bright, NT35510 as NT35510_DMA
from color_control import PALETTE_WHITE
import time


def test_dma_driver(): 
    d = NT35510_DMA()
    t0 = time.ticks_us()
    d.fill(0)
    d.fill_rect(200, 600, 200, 20, 0x07E0)
    t1 = time.ticks_us()
    print(f"DMA driver, FullFrame time: {t1 - t0:,} us")
    t0 = time.ticks_us()
    for i in range(100):
        d.pixel(400,i*3, -1)
    t1 = time.ticks_us()
    print(f"DMA driver, 100 pixels time: {t1 - t0:,} us")
    t0 = time.ticks_us()
    fb = MyFrameBuffer(100, 106)
    fb.text("Test", 0, 0, -1)
    d.draw_framebuf(200, 200, fb)
    t1 = time.ticks_us()
    print(f"DMA driver, Test DrawBuffer time: {t1 - t0:,} us")
    del d

def test_pio_driver():
    d = NT35510_PIO()
    t0 = time.ticks_us()
    d.fill(0)
    d.fill_rect(200, 600, 200, 20, 0x07E0)
    t1 = time.ticks_us()
    print(f"PIO driver, FullFrame time: {t1 - t0:,} us")
    t0 = time.ticks_us()
    for i in range(100):
        d.pixel(400,i*3, -1)
    t1 = time.ticks_us()
    print(f"PIO driver, 100 pixels time: {t1 - t0:,} us")
    t0 = time.ticks_us()
    fb = MyFrameBuffer(100, 106)
    fb.text("Test", 0, 0, -1)
    d.draw_framebuf(200, 200, fb)
    t1 = time.ticks_us()
    print(f"PIO driver, Test DrawBuffer time: {t1 - t0:,} us")
    del d


if __name__ == "__main__":
    test_dma_driver()
    time.sleep(1)
    test_pio_driver()


"""DMA driver, FullFrame time: 54,812 us
DMA driver, 100 pixels time: 18,443 us
DMA driver, Test DrawBuffer time: 7,535 us
PIO driver, FullFrame time: 187,824 us
PIO driver, 100 pixels time: 165,020 us
PIO driver, Test DrawBuffer time: 14,969 us"""