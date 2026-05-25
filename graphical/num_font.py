from nt35510 import NT35510, color565, MyFrameBuffer, cx_bright
from color_control import PALETTE_WHITE
import framebuf, gc, micropython, os, uctypes

@micropython.asm_thumb
def _blit_gs2_row(r0, r1, r2, r3):
    # r0: dst byte addr, r1: src byte addr, r2: pal byte addr
    # r3: packed = n_bytes | ((key & 7) << 8)
    #     key 0-3 = transparent palette index; key 4-7 = no transparency (-1 & 7 = 7)
    push({r4, r5, r6, r7})
    lsr(r7, r3, 8)       # r7 = key (0-7)
    lsl(r3, r3, 24)      # isolate low byte
    lsr(r3, r3, 24)      # r3 = n_bytes

    label(LOOP)
    ldrb(r4, [r1, 0])
    add(r1, r1, 1)

    lsl(r5, r4, 30)      # pixel 0: isolate bits [1:0]
    lsr(r5, r5, 30)
    cmp(r5, r7)
    beq(SKIP0)
    lsl(r5, r5, 1)
    add(r5, r5, r2)
    ldrh(r6, [r5, 0])
    strh(r6, [r0, 0])
    label(SKIP0)
    add(r0, r0, 2)

    lsr(r5, r4, 2)       # pixel 1: bits [3:2]
    lsl(r5, r5, 30)
    lsr(r5, r5, 30)
    cmp(r5, r7)
    beq(SKIP1)
    lsl(r5, r5, 1)
    add(r5, r5, r2)
    ldrh(r6, [r5, 0])
    strh(r6, [r0, 0])
    label(SKIP1)
    add(r0, r0, 2)

    lsr(r5, r4, 4)       # pixel 2: bits [5:4]
    lsl(r5, r5, 30)
    lsr(r5, r5, 30)
    cmp(r5, r7)
    beq(SKIP2)
    lsl(r5, r5, 1)
    add(r5, r5, r2)
    ldrh(r6, [r5, 0])
    strh(r6, [r0, 0])
    label(SKIP2)
    add(r0, r0, 2)

    lsr(r5, r4, 6)       # pixel 3: bits [7:6] (already 0-3)
    cmp(r5, r7)
    beq(SKIP3)
    lsl(r5, r5, 1)
    add(r5, r5, r2)
    ldrh(r6, [r5, 0])
    strh(r6, [r0, 0])
    label(SKIP3)
    add(r0, r0, 2)

    sub(r3, 1)
    bne(LOOP)
    pop({r4, r5, r6, r7})

BG  = [(0,0,0),(30,20,40),(100,0,0)][2]
nt = NT35510()
nt.fill(color565(*BG))
import time
import machine 
machine.freq(260_000_000)
def mem(name):
    gc.collect()
    print("\nMem", name, gc.mem_free())
    micropython.mem_info()
    print(f"total time: {time.ticks_ms():,}")

mem("start")
# quart = bytearray(200*480*2) # 200 lines of 480 pixels, 2 bytes per pixel

font_buffer = None
class Font:
    def __init__(self, path):
        name = path.split("/")[-1]
        size = name.split(".")[0].split('-')[-1]
        width, height = size.split("n")
        self.char_width = int(width)
        self.char_height = int(height)
        row_size = (self.char_width + 3) // 4
        self.bytes_per_char = row_size * self.char_height
        num_chars = 58-48
        data_len = num_chars + num_chars * self.bytes_per_char
        global font_buffer

        f = open(path, "rb")
        if font_buffer is None:
            data = memoryview(bytearray(f.read(data_len)))
            print(f"Loaded {len(data)} bytes from {path}, no buffer")
        else:
            count = f.readinto(font_buffer)
            if count < 1:
                print("Failed to read font", path)
            elif count >= len(font_buffer):
                print("Ran out of font buffer", count, len(font_buffer))
            else:
                data = font_buffer[:count]
                font_buffer = font_buffer[count:]
                print(f"Loaded {len(data)} bytes from {path}, {len(font_buffer)} buf remaining")

        self.widths = data[0:num_chars]
        self.data = data[num_chars:]

        # --- glyph cache (NO per-char FrameBuffer allocation) ---
        self._glyph_fb = [None] * num_chars
        for v in range(num_chars):
            start = v * self.bytes_per_char
            mv = self.data[start : start + self.bytes_per_char]   # memoryview slice (no copy)
            self._glyph_fb[v] = framebuf.FrameBuffer(
                mv, self.char_width, self.char_height, framebuf.GS2_HMSB
            )
        
        self._line_fb = None
        self._line_w  = 0
        self.bg = color565(*BG)
        self.pal_default = PALETTE_WHITE
        #print("Font", name, self.char_width, self.char_height, data_len, len(self.data))
    
    def _ensure_line_fb(self, FBClass, w):
        # allocate only when we need a bigger buffer than before
        if self._line_fb is None or w > self._line_w:
            self._line_w = w
            self._line_fb = FBClass(w, self.char_height)


    def draw_text_bytes(self, s, FBClass, x0, y0, key=0, palette=None):
        max_w = 480 - x0
        text_w = self.get_width(s)
        if text_w > max_w:
            text_w = max_w
        self._ensure_line_fb(FBClass, text_w)
        return self._draw_bytes_range(s, 0, len(s), FBClass, x0, y0,
                                      key, palette, text_w)
    
    
    def wrap_text_viper(self, text, FBClass, ix, iy, width, force_cut=False, lim=(0,480), vert_swish=0, key=0, palette=None):
        if not text:
            return iy, self.char_height, True

        if isinstance(text, str):
            b = text.encode("ascii", "replace")
        else:
            b = text

        # allocate reusable line buffer once (critical)
        self._ensure_line_fb(FBClass, width)

        end_y, ch_h, inb = self.wrap_text_viper_in(b, FBClass, ix, iy, width,
                                            1 if force_cut else 0,
                                            lim[0], lim[1], vert_swish,
                                            key, palette)
        return end_y, ch_h, bool(inb)

    @micropython.viper
    def wrap_text_viper_in(self, b: object, FBClass: object,
                        ix: int, iy: int, width_px: int,
                        force_cut: int, lim0: int, lim1: int, vert_swish: int,
                        key: int, palette: object) -> object:
        n: int = int(len(b))
        if n == 0:
            return iy, int(self.char_height), 1
        bp = ptr8(b)
        widths = ptr8(self.widths)

        ch_h: int = int(self.char_height) - int(vert_swish)
        y: int = iy
        end_y: int = iy
        in_bounds: int = 1

        line_start: int = 0
        line_end: int = 0
        line_w: int = 0

        i: int = 0
        while i < n:
            prev_i: int = i  # failsafe
            c: int = int(bp[i])

            # ignore \r
            if c == 13:
                i += 1
                continue

            # newline => flush line
            if c == 10:
                if line_end > line_start:
                    if (y > (lim0 - ch_h)) and (y < lim1):
                        self._draw_bytes_range(b, line_start, line_end, FBClass, ix, y, key, palette, width_px)
                        end_y = y + ch_h
                    elif y > lim1:
                        in_bounds = 0
                        break
                y += ch_h
                i += 1
                line_start = i
                line_end = i
                line_w = 0
                continue

            # skip whitespace (space/tab/etc)
            if c <= 32:
                i += 1
                continue

            # scan word [ws,we) and measure pixel width
            ws: int = i
            word_w: int = 0
            while i < n:
                c = int(bp[i])
                if c == 10 or c == 13 or c <= 32:
                    break
                if c < 32 or c > 126:
                    c = 32
                word_w += int(widths[c - 32])
                i += 1
            we: int = i

            space_w: int = int(widths[0])

            if line_w == 0:
                line_start = ws
                line_end = we
                line_w = word_w
            else:
                needed: int = line_w + space_w + word_w
                if needed <= width_px:
                    line_end = we
                    line_w = needed
                else:
                    # flush current line
                    if (y > (lim0 - ch_h)) and (y < lim1):
                        self._draw_bytes_range(b, line_start, line_end, FBClass, ix, y, key, palette, width_px)
                        end_y = y + ch_h
                    elif y > lim1:
                        in_bounds = 0
                        break

                    y += ch_h 
                    line_start = ws
                    line_end = we
                    line_w = word_w

            # optional: force-cut long word (keep for later if needed)
            if force_cut and word_w > width_px:
                cut_start: int = ws
                cut_w: int = 0
                j: int = ws
                while j < we:
                    cc: int = int(bp[j])
                    if cc < 32 or cc > 126:
                        cc = 32
                    cw: int = int(widths[cc - 32])

                    if cut_w + cw > width_px:
                        if (y > (lim0 - ch_h)) and (y < lim1):
                            self._draw_bytes_range(b, cut_start, j, FBClass, ix, y, key, palette, width_px)
                            end_y = y + ch_h
                        elif y > lim1:
                            in_bounds = 0
                            break
                        y += ch_h
                        cut_start = j
                        cut_w = 0

                    cut_w += cw
                    j += 1

                if in_bounds == 0:
                    break

                if cut_start < we:
                    if (y > (lim0 - ch_h)) and (y < lim1):
                        self._draw_bytes_range(b, cut_start, we, FBClass, ix, y, key, palette, width_px)
                        end_y = y + ch_h
                    elif y > lim1:
                        in_bounds = 0
                        break
                    y += ch_h

                line_start = we
                line_end = we
                line_w = 0

            # FAILSAFE: never allow i to stall
            if i == prev_i:
                i += 1

        # final flush
        if in_bounds and (line_end > line_start):
            if (y > (lim0 - ch_h)) and (y < lim1):
                self._draw_bytes_range(b, line_start, line_end, FBClass, ix, y, key, palette, width_px)
                end_y = y + ch_h
            elif y > lim1:
                in_bounds = 0

        return end_y, ch_h, in_bounds


    @micropython.viper
    def _fast_blit_2(self, fb: object, v: int, x0: int, palette: object, key: int):
        fb_base: int    = int(ptr8(fb.buffer)) + x0 * 2
        fb_stride: int  = int(fb.width) * 2
        src_base: int   = int(ptr8(self.data)) + v * int(self.bytes_per_char)
        src_stride: int = (int(self.char_width) + 3) >> 2
        pal_addr: int   = int(ptr8(palette.buffer))
        h: int          = int(self.char_height)
        # Clip to fb row: don't write past fb.width — asm n_bytes=0 underflows loop counter
        n_bytes: int    = src_stride
        avail: int      = (int(fb.width) - x0) >> 2
        if n_bytes > avail:
            n_bytes = avail
        if n_bytes <= 0:
            return
        packed: int     = n_bytes | ((key & 7) << 8)
        y: int = 0
        while y < h:
            _blit_gs2_row(fb_base + y * fb_stride,
                          src_base + y * src_stride,
                          pal_addr, packed)
            y += 1

    @micropython.viper
    def _draw_bytes_range(self, b: object, start: int, end: int,
                          FBClass: object, x0: int, y0: int,
                          key: int, palette: object, max_w: int) -> int:
        bp = ptr8(b)
        widths = ptr8(self.widths)
        fb = self._line_fb
        fb.fill(int(self.bg) >> 8 | (int(self.bg)&0xff) << 8)
        pal = palette if palette else self.pal_default
        x: int = 0
        i: int = start
        while i < end:
            v: int = int(bp[i])
            if v < 48 or v > 57:
                v = 48
            v -= 48
            #fb.blit(self._glyph_fb[v], x, 0, key, pal)
            self._fast_blit_2(fb, v, x, pal, key)
            x += int(widths[v])
            if x >= max_w:
                break
            i += 1
        nt.draw_framebuf(x0, y0, fb)
        return x

    @micropython.viper
    def get_width(self, word: object) -> int:
        w_ptr = ptr8(self.widths) 
        w_buf = ptr8(word)
        w_len = int(len(word))
        total_width: int = 0
        i: int = 0
        while i < w_len:
            v = int(w_buf[i]) # Faster than ord(letter)
            if v < 48 or v > 57:
                v = 48
            v -= 48
            total_width += int(w_ptr[v])
            i += 1
            
        return total_width
    
# num = Font("/CrestoriaMonogram-50-40n35.raw2")
num = Font("HelloPain-80-44n59.raw2")
# num = Font("NewTimes-80-40n63.raw2")
# num = Font("Freakshow-50-52n96.raw2")
# font = Font("/InterBold-14-15x18.raw2")

example_long = 'Mao Li Qiu looked at the light on Fang Yuan\'s body, there was nothing it could do, it bore its fangs and scratched the ground with its claws, causing deep marks to form.\n\nBai Ning Bing\'s and Hei Lou Lan\'s eyelids were twitching, they were evidently moved.\n\nZhao Lian Yun had woken up, she looked at Ma Hong Yun\'s corpse, held in Fang Yuan\'s arm, her tears were flowing out.\n\nShe cried in her heart: "Hong Yun, Hong Yun, how could you leave me like this. Without you, I am all alone in this world. What is the point of living? Do you know, the perseverance of one person is so difficult!"\n\nHow difficult is the perseverance of one person?\n\nAll of the Gu Immortals here could answer that question.\n\nBecause among them, some persevered because of responsibility, some persevered because of hatred, some persevered because of excitement, and some persevered because of love?\n\nAnd Fang Yuan\'s answer?\n\nHe was still expressionless, he continued to move forward relentlessly.\n\nI had once screamed, gradually, I lost my voice.\n\nI had once cried, gradually, I lost my tears.\n\nI had once grieved, gradually, I became able to withstand everything.'
# example_long = """To man the world is twofold, in accordance with his twofold attitude. The attitude of man is twofold, in accordance with the twofold nature of the primary words which he speaks. The primary words are not isolated words, but combined words. The one primary word is the combination I-Thou. The other primary word is the combination I-It; wherein, without a change in the primary word, one of the words He and She can replace It. Hence the I of man is also twofold. For the I of the primary word I-Thou is a different I from that of the primary word I-It. Primary words do not signify things, but. they intimate relations. Primary words do not describe something that might exist independently of them, but being spoken they bring about existence. Primary words are spoken from the being. If Thou is said, the I of the combination I-Thou is said along with it. If It is said, the I of the combination I-It is said along with it. The primary word I-Thou can only be spoken with the whole being. • The primary word I-It can never be spoken with the whole being. * 3"""
# example_long = """Peter Piper picked a peck of pickled peppers.\nA peck of pickled peppers Peter Piper picked.\nIf Peter Piper picked a peck of pickled peppers,\nWhere's the peck of pickled peppers Peter Piper picked?"""
# example_long = """Of all elements that are solid at room temperature, caesium is the softest: it has a hardness of Mohs 0.2. It is a very ductile, pale metal, which darkens in the presence of trace amounts of oxygen.[14][15][16] When in the presence of mineral oil (where it is best kept during transport), it loses its metallic lustre and takes on a duller, grey appearance. It has a melting point of 28.5 °C (83.3 °F), making it one of the few elemental metals that are liquid near room temperature. The others are rubidium (39 °C [102 °F]), francium (estimated at 27 °C [81 °F]), mercury (−39 °C [−38 °F]), and gallium (30 °C [86 °F]); bromine is also liquid at room temperature (melting at −7.2 °C [19.0 °F]), but it is a halogen and not a metal. Mercury is the only stable elemental metal with a known melting point lower than caesium.[17] In addition, caesium has a rather low boiling point, 641 °C (1186 °F), the lowest of all stable metals other than mercury.[18] Copernicium and flerovium have been predicted to have lower boiling points than mercury and caesium, but they are extremely radioactive and it is not certain that they are metals.[19][20]"""
import time
test = 0
t0: int = time.ticks_us()
prev = time.time()
if test == 0:
    while True:
        if prev < time.time():
            t = time.gmtime()
            example = f"{t[3]:02}"#"0123456789"#"Hello World!"
            num.draw_text_bytes(example, MyFrameBuffer, 0, 20,0,None)
            example = f"{t[4]:02}"#"0123456789"#"Hello World!"
            num.draw_text_bytes(example, MyFrameBuffer, 90, 20,0,None)
            example = f"{t[5]:02}"#"0123456789"#"Hello World!"
            num.draw_text_bytes(example, MyFrameBuffer, 180, 20,0,None)
            # font.draw_text_bytes(":", MyFrameBuffer, 80, 20,0,None)
            # font.draw_text_bytes(":", MyFrameBuffer, 170, 20,0,None)
            prev = time.time()
            time.sleep(.9)
elif test == 1:
    i = 0
    import random
    prev = time.ticks_us()
    while i < 1_000_000:
        # val = str(i)#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 20, 0, None)
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 100, 0, None)
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 180, 0, None)
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 260, 0, None)
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 340, 0, None)
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 420, 0, None)
        val = f"{random.randint(0, 999999)}{random.randint(0, 999999)}"#str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        num.draw_text_bytes(val, MyFrameBuffer, 0, 500, 0, None)
        if i % 400 == 0:
            print(val)
        i += 1

# t1 = time.ticks_us()
# t2 = time.ticks_us()
# t3 = time.ticks_cpu()
# # font1.get_width(example)
# t4 = time.ticks_cpu()
# print(f"draw_text-test{0}: prep fb {t1-t0:,}us, draw chars, control {t2-t1:,}us - {t4-t3:,}cpu, letters per second: {len(example)*times / ((t1-t0) / 1_000_000):,.2f}, us per letter: {(t1-t0) / (len(example)*times):,}")

# print(machine.freq())
# mem("end")