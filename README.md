# NT35510 16bit Parallel Micropython Drivers and Simple Graphics
Utilizing the DMA and PIO processes of the RP2350(in this case, the B variant) on the [4.3 inch 480x800 nt35510](https://www.ebay.com/itm/385792037170?_skw=nt35510&itmmeta=01KSEZT5P2AK1Y4K128JHNS5BP&hash=item59d2ff5132:g:n6gAAOSwRIpkuM~C&itmprp=enc%3AAQALAAAA4GfYFPkwiKCW4ZNSs2u11xAdGZ3DtHtuGdfUYgE63QfTp3IIIUln1Z5xu27ORRCsO2Tm1Rje3sAQUtyusLgkAE59JdlyfhvgLFH1sPkiwSw%2FJtBcyip5lGGkiptqxDZsBCMN0ej%2FhMp%2BAsjOEWmRWAHeEtpzApXzCLWtxeV0tsenIru7GmMKNhLo0jZusJoPAHFA5y0cWiLHbQ4zw3wSeKHdL929lvFNsypLXtMdA4LAFh%2FT0mtAEXitc7LNXSd3CqOB8QhsPUUa7tj8nYC8VFaAvDIPUHd3GYmWtDkQnshM%7Ctkp%3ABk9SR47c6N_LZw) display, 
This library offers fast displaying of rects to buffers, including a method of rendering text into two-bit per pixel (4 grayscale) glyphs.

In addition, this project includes serveral graphical experiments including
   - black/white dithering
   - attempts at anti-ailiasing
   - funky colored rectangles
   - and an alternate version of the font renderer for numbers alone

## Speeds!
1. fullframe color flush:
   - 7.5ms
2. rgb565 buffer from flash: 
   - Total- 174.8ms, 
   - Read- 153.4ms, *could be faster once I get SDIO to work
   - Draw- 21.5ms 
3. Font:
   - Roboto-16-14x18 render speed, microseconds per letter: 
     - "h"- 1,374 
     - 2,948 chars- 69.4


### Software Quirks
While all are technically in Python, through micropython's decorators, lower-level, high-repetition functions can be put into:
- [viper](https://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html?highlight=viper#the-viper-code-emitter):
```
@micropython.viper
def get_width(self, word: object) -> int:
   w_ptr = ptr8(self.widths) 
   w_buf = ptr8(word)
   w_len = int(len(word))
   total_width: int = 0
   i: int = 0
   while i < w_len:
      v = int(w_buf[i]) # Faster than ord(letter)
      if v < 32 or v > 126:
          v = 32
      v -= 32
      total_width += int(w_ptr[v])
      i += 1
   return total_width
```
- [inline assembly](https://docs.micropython.org/en/v1.9.3/pyboard/reference/speed_python.html?highlight=viper#accessing-hardware-directly)
```
# can only go up to 12! on a 32bit system
@micropython.asm_thumb
def factorial(r0):
    cmp(r0,2)
    bls(EXIT)
    mov(r1,r0)
    label(LOOP)
    sub(r1,r1,1)
    mul(r0,r1)
    cmp(r1,2)
    bgt(LOOP)
    label(EXIT)
    cmp(r0,0)
    it(eq)
    mov(r0,1)
```
