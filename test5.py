from nt35510 import NT35510, color565, MyFrameBuffer, cx_bright
from color_control import PALETTE_WHITE
import framebuf, gc, micropython, os

BG  = (0,0,0)#(30,20,40)
nt = NT35510()
nt.fill(color565(*BG))
import time
import machine 
machine.freq(240_000_000)
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
        width, height = size.split("x")
        self.char_width = int(width)
        self.char_height = int(height)
        row_size = (self.char_width + 3) // 4
        self.bytes_per_char = row_size * self.char_height
        num_chars = 127-32
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

    @micropython.viper
    def draw_char(self, c: object, fb: object, x: int, y: int, key: int, palette: object) -> int:
        v: int = int(ptr8(c)[0])
        if v < 32 or v > 126:
            v = 32
        v -= 32
        fb.blit(self._glyph_fb[v], x, y, key, palette if palette else self.pal_default)
        return ptr8(self.widths)[v]
    
    def draw_text(self, text, fb, x, y, key=0, palette=None):
        if not text:
            return x, y
        # t0 = time.ticks_us()
        fb = fb(self.get_width(text),self.char_height)
        # t1 = time.ticks_us()
        fb.fill(color565(*BG))
        x0 = x; y0 = y
        # t2 = time.ticks_us()
        for c in text:
            x += self.draw_char(c, fb, x-x0, y-y0, key, palette)
        # t3 = time.ticks_us()
        nt.draw_framebuf(x0, y0, fb)
        # t4 = time.ticks_us()
        # print(f"draw_text: prep fb {t1-t0:,}us, draw chars {t3-t2:,}us, blit {t4-t3:,}us")
        return x, y+self.char_height


    @micropython.viper
    def draw_text2(self, text: object, FBClass: object, x0: int, y0: int, key: int, palette: object) -> object:
        if not text:
            return x0, y0
        w: int = int(self.get_width(text))
        self._ensure_line_fb(FBClass, w)
        fb: object = self._line_fb
        fb.fill(self.bg)
        x: int = 0
        pal = palette if palette else self.pal_default
        widths_ptr = ptr8(self.widths)
        
        for c in text:
            v: int = ptr8(c)[0]
            if v < 32 or v > 126:
                v = 32
            v -= 32
            fb.blit(self._glyph_fb[v], x, 0, key, pal)
            x += widths_ptr[v]
            if x >= w: # This comparison now works (int vs int)
                break

        nt.draw_framebuf(x0, y0, fb)
        h: int = int(self.char_height)
        return x0 + x, y0 + h
    
    @micropython.viper
    def draw_text_bytes(self, s: object, FBClass: object, x0: int, y0: int, key: int, palette: object) -> int:
        # s must be bytes
        n: int = int(len(s))
        sp = ptr8(s)

        w: int = int(min(self.get_width(s),480-x0))
        self._ensure_line_fb(FBClass, w)
        fb = self._line_fb
        fb.fill(self.bg)   # precomputed int, see below

        widths = ptr8(self.widths)
        pal = palette if palette else self.pal_default

        x: int = 0
        for i in range(n):
            v: int = int(sp[i])
            if v < 32 or v > 126:
                v = 32
            v -= 32
            fb.blit(self._glyph_fb[v], x, 0, key, pal)
            x += int(widths[v])
            if x >= w:
                break

        nt.draw_framebuf(x0, y0, fb)
        return x
    
    def wrap_text_fast(self, text, fb, ix, iy, width, force_cut=False, lim=(0,480), key=0, palette=None):
        if not text:
            return ix, self.char_height, True

        y = iy
        end_in_bounds = True
        end_y = 0

        # split into paragraphs on real newline characters
        for para in text.split("\n"):
            x = ix
            line = ""

            for word in para.split():
                word_sp = word + " "          # your previous behavior
                wrdwidth = self.get_width(word_sp)

                if x + wrdwidth < width:
                    line += word_sp
                    x += wrdwidth
                else:
                    if y > lim[0] - self.char_height and y < lim[1]:
                        end_y = self.draw_text_bytes(line, fb, ix, y, key, palette)
                    elif y > lim[1]:
                        end_in_bounds = False
                        break

                    y += self.char_height
                    x = ix + wrdwidth
                    line = word_sp

            if not end_in_bounds:
                break

            # flush last line of paragraph
            if line:
                if y > lim[0] - self.char_height and y < lim[1]:
                    end_y = self.draw_text(line, fb, ix, y, key, palette)
                elif y > lim[1]:
                    end_in_bounds = False
                    break

            # paragraph break: advance one line (optional; remove if you want tight newlines)
            y += self.char_height

        return end_y, self.char_height, end_in_bounds
    
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
                            self.draw_text_bytes(b[cut_start:j], FBClass, ix, y, key, palette, width_px)
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
                        self.draw_text_bytes(b[cut_start:we], FBClass, ix, y, key, palette, width_px)
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

    def center_text(self, text, fb, xcenter, ycenter, w, h, key=0, palette=None):
        widths, lines = self.get_lines(text, w)
        #print("lines: ",lines, "text", text)
        num_lines = len(lines)
        ystart = ycenter - num_lines * self.char_height // 2
        #print("center-y: ",ycenter, "start=y: ", ystart)
        if num_lines * self.char_height > h:
            print("Number of lines exceeds alotted height")
        y = ystart
        for l in range(num_lines):
            line = lines[l]
            x = xcenter - widths[l] // 2
            self.draw_text(line,fb,x,y,key,palette)
            y += self.char_height
        
    def get_lines(self, text, iwidth):
        lines_nums = []
        tx_lines = []
        cur_line = ""
        width = 0
        wrd_num = 0
        for word in text.split():
            if not word or word == '':
                #print("empty, continueing to nxt wrd")
                continue
            if wrd_num > 0:
                word = " " + word
            length = self.get_width(word)
            if width + length < iwidth:
                cur_line = cur_line + word
                wrd_num += 1
                width += length
            elif length > iwidth:
                #print("Word wider than bbox")
                lines_nums.append(length)
                tx_lines.append(word)
                width = 0
                wrd_num = 0
            else:
                lines_nums.append(width)
                tx_lines.append(cur_line)
                cur_line = word[1:]
                width = length
                wrd_num = 1
        if wrd_num > 0:
            lines_nums.append(width)
            tx_lines.append(cur_line)
        return lines_nums, tx_lines
    
    @micropython.viper
    def _draw_bytes_range(self, b: object, start: int, end: int,
                        FBClass: object, x0: int, y0: int,
                        key: int, palette: object, max_w: int) -> int:
        bp = ptr8(b)
        widths = ptr8(self.widths)

        fb = self._line_fb
        # assume python wrapper already ensured _line_fb exists at >= max_w

        fb.fill(int(self.bg))
        pal = palette if palette else self.pal_default

        x: int = 0
        i: int = start
        while i < end:
            v: int = int(bp[i])
            if v < 32 or v > 126:
                v = 32
            v -= 32
            fb.blit(self._glyph_fb[v], x, 0, key, pal)
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
        for i in range(w_len):
            v = int(w_buf[i]) # Faster than ord(letter)
            if v < 32 or v > 126:
                v = 32
            v -= 32
            total_width += int(w_ptr[v])
            
        return total_width
    
font1 = Font("/InterBold-14-15x18.raw2")
# font1 = Font("Astroz-36-35x38.raw2")
# font1 = Font("HelloPain-36-37x41.raw2")
# font1 = Font("/fonts/Dejavu-10-10x10.raw2")
# font1 = Font("/fonts/Roboto-16-14x18.raw2")
# font1 = Font("/fonts/HelloPain-12-13x15.raw2")
# font1 = Font("/fonts/Astroz-16-15x18.raw2")
# font1 = Font("/fonts/Marseille-22-25x23.raw2")
# font1 = Font("/fonts/Hollyberry-20-19x20.raw2")
example_long = 'Mao Li Qiu looked at the light on Fang Yuan\'s body, there was nothing it could do, it bore its fangs and scratched the ground with its claws, causing deep marks to form.\n\nBai Ning Bing\'s and Hei Lou Lan\'s eyelids were twitching, they were evidently moved.\n\nZhao Lian Yun had woken up, she looked at Ma Hong Yun\'s corpse, held in Fang Yuan\'s arm, her tears were flowing out.\n\nShe cried in her heart: "Hong Yun, Hong Yun, how could you leave me like this. Without you, I am all alone in this world. What is the point of living? Do you know, the perseverance of one person is so difficult!"\n\nHow difficult is the perseverance of one person?\n\nAll of the Gu Immortals here could answer that question.\n\nBecause among them, some persevered because of responsibility, some persevered because of hatred, some persevered because of excitement, and some persevered because of love?\n\nAnd Fang Yuan\'s answer?\n\nHe was still expressionless, he continued to move forward relentlessly.\n\nI had once screamed, gradually, I lost my voice.\n\nI had once cried, gradually, I lost my tears.\n\nI had once grieved, gradually, I became able to withstand everything.'
# example_long = """To man the world is twofold, in accordance with his twofold attitude. The attitude of man is twofold, in accordance with the twofold nature of the primary words which he speaks. The primary words are not isolated words, but combined words. The one primary word is the combination I-Thou. The other primary word is the combination I-It; wherein, without a change in the primary word, one of the words He and She can replace It. Hence the I of man is also twofold. For the I of the primary word I-Thou is a different I from that of the primary word I-It. Primary words do not signify things, but. they intimate relations. Primary words do not describe something that might exist independently of them, but being spoken they bring about existence. Primary words are spoken from the being. If Thou is said, the I of the combination I-Thou is said along with it. If It is said, the I of the combination I-It is said along with it. The primary word I-Thou can only be spoken with the whole being. • The primary word I-It can never be spoken with the whole being. * 3"""
example_long = """Peter Piper picked a peck of pickled peppers.\nA peck of pickled peppers Peter Piper picked.\nIf Peter Piper picked a peck of pickled peppers,\nWhere's the peck of pickled peppers Peter Piper picked?"""
example_long = """Of all elements that are solid at room temperature, caesium is the softest: it has a hardness of Mohs 0.2. It is a very ductile, pale metal, which darkens in the presence of trace amounts of oxygen.[14][15][16] When in the presence of mineral oil (where it is best kept during transport), it loses its metallic lustre and takes on a duller, grey appearance. It has a melting point of 28.5 °C (83.3 °F), making it one of the few elemental metals that are liquid near room temperature. The others are rubidium (39 °C [102 °F]), francium (estimated at 27 °C [81 °F]), mercury (−39 °C [−38 °F]), and gallium (30 °C [86 °F]); bromine is also liquid at room temperature (melting at −7.2 °C [19.0 °F]), but it is a halogen and not a metal. Mercury is the only stable elemental metal with a known melting point lower than caesium.[17] In addition, caesium has a rather low boiling point, 641 °C (1186 °F), the lowest of all stable metals other than mercury.[18] Copernicium and flerovium have been predicted to have lower boiling points than mercury and caesium, but they are extremely radioactive and it is not certain that they are metals.[19][20]"""
# font1.draw_char("A", MyFrameBuffer(font1.char_width, font1.char_height), 20,20)
example = "Hello 2 3 23World! aeyshdvfudvtbyktvdtfbyhiuguvtjbnkhgrvfbguylbony;o9"
example1 = "hi"
items = os.listdir("/fonts")
test: int = 0
times: int = 1
t0: int = time.ticks_us()
if test == 0:
    times: int = 44
    for i in range(times):
        font1.draw_text_bytes(example, MyFrameBuffer, 20, 0+i*20,0,None)
elif test == 1:
    times: int = len(items)
    for i in range(len(items)):
        font1 = Font(f"/fonts/{items[i]}")
        examplein = f"{items[i][:-5]} {example[:40]}"
        # font1.draw_text2(example, MyFrameBuffer, 20, 0+i*18,0,None)
        font1.draw_text_bytes(examplein, MyFrameBuffer, 2, 0+i*20,0,None)
elif test == 2:
    example = example_long
    font1.wrap_text_fast(example,MyFrameBuffer, 4, 0, 475)
elif test == 3:
    example = example_long
    font1.wrap_text_viper(example,MyFrameBuffer,0,0,480,lim=(0,800))#,vert_swish=14)
elif test == 4:
    # example = "Hello World!"
    font1.draw_text_bytes(example, MyFrameBuffer, 0, 20,0,None)
elif test == 5:
    nt.fb_text("example", 20, 20)
elif test == 6: # spped numbers
    i = 0
    prev = time.ticks_us()
    while i < 1_000_000:
        val = str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        font1.draw_text_bytes(val, MyFrameBuffer, 0, 20, 0, None)
        if i % 400 == 0:
            print(val)
        i += 1

t1 = time.ticks_us()
t2 = time.ticks_us()
t3 = time.ticks_cpu()
# font1.get_width(example)
t4 = time.ticks_cpu()
print(f"draw_text-test{test}: prep fb {t1-t0:,}us, draw chars, control {t2-t1:,}us - {t4-t3:,}cpu, letters per second: {len(example)*times / ((t1-t0) / 1_000_000):,.2f}, us per letter: {(t1-t0) / (len(example)*times):,}")

print(machine.freq())
mem("end")

# draw_text: prep fb 2,791us, draw chars 17,333us, blit 3,291us
# """Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_char 'H': char data prep 62us, char fb prep 45us, blit 180us
# draw_char 'e': char data prep 146us, char fb prep 39us, blit 165us
# draw_char 'l': char data prep 107us, char fb prep 37us, blit 175us
# draw_char 'l': char data prep 81us, char fb prep 37us, blit 201us
# draw_char 'o': char data prep 96us, char fb prep 39us, blit 177us
# draw_char ' ': char data prep 105us, char fb prep 36us, blit 168us
# draw_char 'W': char data prep 110us, char fb prep 39us, blit 186us
# draw_char 'o': char data prep 107us, char fb prep 38us, blit 172us
# draw_char 'r': char data prep 89us, char fb prep 38us, blit 201us
# draw_char 'l': char data prep 95us, char fb prep 39us, blit 172us
# draw_char 'd': char data prep 107us, char fb prep 36us, blit 176us
# draw_char '!': char data prep 127us, char fb prep 41us, blit 157us
# draw_char ' ': char data prep 114us, char fb prep 40us, blit 166us
# draw_char 'a': char data prep 70us, char fb prep 42us, blit 170us
# draw_char 'e': char data prep 109us, char fb prep 36us, blit 182us
# draw_char 'y': char data prep 120us, char fb prep 37us, blit 179us
# draw_char 's': char data prep 115us, char fb prep 38us, blit 177us
# draw_char 'h': char data prep 123us, char fb prep 37us, blit 164us
# draw_char 'd': char data prep 103us, char fb prep 52us, blit 178us
# draw_char 'v': char data prep 122us, char fb prep 35us, blit 179us
# draw_char 'f': char data prep 118us, char fb prep 39us, blit 173us
# draw_char 'u': char data prep 114us, char fb prep 37us, blit 175us
# draw_char 'd': char data prep 122us, char fb prep 40us, blit 165us
# draw_char 'v': char data prep 121us, char fb prep 37us, blit 176us
# draw_char 't': char data prep 115us, char fb prep 39us, blit 174us
# draw_char 'b': char data prep 120us, char fb prep 37us, blit 178us
# draw_char 'y': char data prep 122us, char fb prep 76us, blit 175us
# draw_char 'k': char data prep 156us, char fb prep 38us, blit 178us
# draw_char 't': char data prep 161us, char fb prep 36us, blit 174us
# draw_char 'v': char data prep 171us, char fb prep 39us, blit 174us
# draw_char 'd': char data prep 172us, char fb prep 41us, blit 180us
# draw_char 't': char data prep 156us, char fb prep 36us, blit 173us
# draw_char 'f': char data prep 157us, char fb prep 37us, blit 176us
# draw_char 'b': char data prep 170us, char fb prep 39us, blit 178us
# draw_char 'y': char data prep 165us, char fb prep 39us, blit 181us
# draw_char 'h': char data prep 168us, char fb prep 37us, blit 179us
# draw_char 'i': char data prep 173us, char fb prep 39us, blit 170us
# draw_char 'u': char data prep 169us, char fb prep 37us, blit 176us
# draw_char 'g': char data prep 166us, char fb prep 38us, blit 182us
# draw_char 'u': char data prep 162us, char fb prep 38us, blit 176us
# draw_char 'v': char data prep 170us, char fb prep 39us, blit 161us
# draw_char 't': char data prep 166us, char fb prep 36us, blit 171us
# draw_char 'j': char data prep 167us, char fb prep 39us, blit 174us
# draw_char 'b': char data prep 172us, char fb prep 38us, blit 178us
# draw_char 'n': char data prep 159us, char fb prep 47us, blit 178us
# draw_char 'k': char data prep 170us, char fb prep 39us, blit 180us
# draw_char 'h': char data prep 171us, char fb prep 39us, blit 179us
# draw_char 'g': char data prep 168us, char fb prep 38us, blit 178us
# draw_char 'r': char data prep 176us, char fb prep 36us, blit 159us
# draw_char 'v': char data prep 175us, char fb prep 39us, blit 176us
# draw_char 'f': char data prep 144us, char fb prep 41us, blit 199us
# draw_char 'b': char data prep 152us, char fb prep 49us, blit 182us
# draw_char 'g': char data prep 174us, char fb prep 36us, blit 183us
# draw_char 'u': char data prep 170us, char fb prep 41us, blit 176us
# draw_char 'y': char data prep 169us, char fb prep 39us, blit 177us
# draw_char 'l': char data prep 166us, char fb prep 35us, blit 174us
# draw_char 'b': char data prep 173us, char fb prep 37us, blit 179us
# draw_char 'o': char data prep 149us, char fb prep 38us, blit 203us
# draw_char 'n': char data prep 158us, char fb prep 50us, blit 177us
# draw_char 'y': char data prep 171us, char fb prep 38us, blit 180us
# draw_char ';': char data prep 176us, char fb prep 37us, blit 171us
# draw_char 'o': char data prep 171us, char fb prep 40us, blit 176us
# draw_char '9': char data prep 173us, char fb prep 36us, blit 135us
# draw_text: prep fb 2,721us, draw chars 52,496us, blit 3,341us"""
# other reader:
# draw_char 'L': char data prep 112us, char fb prep 42us, blit 142us
# draw_char 'o': char data prep 93us, char fb prep 33us, blit 117us
# draw_char 'a': char data prep 81us, char fb prep 34us, blit 129us
# draw_char 'd': char data prep 87us, char fb prep 32us, blit 129us
# draw_char 'i': char data prep 91us, char fb prep 30us, blit 128us
# draw_char 'n': char data prep 59us, char fb prep 29us, blit 148us
# draw_char 'g': char data prep 77us, char fb prep 32us, blit 119us
# draw_char '.': char data prep 80us, char fb prep 34us, blit 128us
# draw_char '.': char data prep 82us, char fb prep 34us, blit 118us
# draw_char '.': char data prep 77us, char fb prep 31us, blit 123us
# current hand made
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 847,715us, draw chars, control 9us - 3cpu
# 240000000
# after
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 623,322us, draw chars, control 8us - 4cpu
# 240000000
# previuous
# draw_text: prep fb 1,877us, draw chars 9,451us, blit 2,306us
# draw_text: prep fb 1,935us, draw chars 9,415us, blit 2,306us
# draw_text: prep fb 1,919us, draw chars 9,386us, blit 2,311us
# draw_text: prep fb 1,982us, draw chars 9,384us, blit 2,306us
# draw_text: prep fb 2,019us, draw chars 9,410us, blit 2,320us
# draw_text: prep fb 2,004us, draw chars 9,420us, blit 2,295us
# draw_text: prep fb 2,037us, draw chars 9,443us, blit 2,313us
# draw_text: prep fb 2,105us, draw chars 9,380us, blit 2,291us
# draw_text: prep fb 2,136us, draw chars 9,496us, blit 2,311us
# draw_text: prep fb 2,116us, draw chars 9,395us, blit 2,317us
# draw_text: prep fb 649,875us, draw chars, control 16us - 5cpu
# 240000000
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 439,209us, draw chars, control 10us - 4cpu
# 240000000
# had to use get_widtha again
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 487,764us, draw chars, control 10us - 4cpu
# 240000000
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 400,405us, draw chars, control 8us - 46cpu, letters per second: 6922.99
# 240000000
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 400,490us, draw chars, control 9us - 44cpu, letters per second: 6921.52, ms per letter: 0.144477
# 240000000

# >>> 
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 400,332us, draw chars, control 9us - 49cpu, letters per second: 6924.25, us per letter: 144.42
# 240000000

# >>> 
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 400,348us, draw chars, control 9us - 6cpu, letters per second: 6923.98, us per letter: 144.426
# 240000000

# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 355,107us, draw chars, control 8us - 5cpu, letters per second: 7806.10, us per letter: 128.105
# 240000000


# stack: 716 out of 12032
# GC: total: 497408, used: 29696, free: 467712
#  No. of 1-blocks: 110, 2-blocks: 30, max blk sz: 359, max free sz: 25328
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 183,234us, draw chars, control 16us - 4cpu, letters per second: 6199.72, us per letter: 161.298
# 240000000
# stack: 716 out of 12032
# GC: total: 497408, used: 61104, free: 436304
#  No. of 1-blocks: 249, 2-blocks: 159, max blk sz: 1076, max free sz: 17951

# stack: 716 out of 12032
# GC: total: 497408, used: 29696, free: 467712
#  No. of 1-blocks: 110, 2-blocks: 30, max blk sz: 359, max free sz: 25328
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text: prep fb 133,750us, draw chars, control 12us - 4cpu, letters per second: 8493.46, us per letter: 117.738
# 240000000
# stack: 716 out of 12032
# GC: total: 497408, used: 61168, free: 436240
#  No. of 1-blocks: 249, 2-blocks: 159, max blk sz: 1080, max free sz: 24248

# Mem start 466816
# stack: 716 out of 12032
# GC: total: 497408, used: 30592, free: 466816
#  No. of 1-blocks: 108, 2-blocks: 30, max blk sz: 359, max free sz: 25195
# total time: 1,019,878
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# Loaded 2945 bytes from /fonts/Dejavu-10-10x10.raw2, no buffer
# draw_text: prep fb 169,961us, draw chars, control 8us - 49cpu, letters per second: 17862.92, us per letter: 55.9819
# 240000000
# Mem end 441664
# stack: 716 out of 12032
# GC: total: 497408, used: 55744, free: 441664
#  No. of 1-blocks: 257, 2-blocks: 168, max blk sz: 460, max free sz: 25195
# total time: 1,020,092
