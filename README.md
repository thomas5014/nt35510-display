**NT35510 16bit Parallel Micropython Drivers and Simple Graphics**
Utilizing the DMA and PIO processes of the RP2350(in this case, the B variant) on the [4.3 inch 480x800 nt35510]([url](https://www.ebay.com/itm/385792037170?_skw=nt35510&itmmeta=01KSEZT5P2AK1Y4K128JHNS5BP&hash=item59d2ff5132:g:n6gAAOSwRIpkuM~C&itmprp=enc%3AAQALAAAA4GfYFPkwiKCW4ZNSs2u11xAdGZ3DtHtuGdfUYgE63QfTp3IIIUln1Z5xu27ORRCsO2Tm1Rje3sAQUtyusLgkAE59JdlyfhvgLFH1sPkiwSw%2FJtBcyip5lGGkiptqxDZsBCMN0ej%2FhMp%2BAsjOEWmRWAHeEtpzApXzCLWtxeV0tsenIru7GmMKNhLo0jZusJoPAHFA5y0cWiLHbQ4zw3wSeKHdL929lvFNsypLXtMdA4LAFh%2FT0mtAEXitc7LNXSd3CqOB8QhsPUUa7tj8nYC8VFaAvDIPUHd3GYmWtDkQnshM%7Ctkp%3ABk9SR47c6N_LZw)) display, 
This library offers fast displaying of rects to buffers, including a method of rendering text into two-bit per pixel (4 grayscale) glyphs.

**For the speeds that can be expected:**
fullframe color flush: 7.5ms
rgb565 buffer from flash: Total- 174.8ms, Read- 153.4ms, Draw- 21.5ms # could be faster pnce i get sdio to work
Roboto-16-14x18 render speed, microseconds per letter: "h"- 1,374 | 2,948 chars- 69.4

**Software Quirks**
While all are technically in Python, through micropython's decorators, lower-level, high-repetition functions are moved into viper
and then even inline assembly.
