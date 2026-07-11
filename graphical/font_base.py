# font_base.py -- 2-bit anti-aliased font renderer for the NT35510 display.
#
# Library module only: no hardware setup or benchmarks happen on import.
# See font_base_demo.py for usage examples and the benchmark harness.
import micropython
from color_control import PALETTE_WHITE

# Printable ASCII range covered by .raw2 font files.
# NOTE: viper functions below repeat these as literals (32 / 126) because
# reading module globals from viper code costs a dict lookup per call.
_FIRST = 32
_LAST = 126
_NUM_CHARS = _LAST - _FIRST + 1

@micropython.asm_thumb
def _blit_gs2_row(r0, r1, r2, r3):
    # Blit one row of GS2_HMSB (2 bits/pixel) glyph data into an RGB565
    # buffer, mapping each 2-bit value through a 4-entry RGB565 palette.
    # r0: dst byte addr (RGB565 row), r1: src byte addr (GS2 row)
    # r2: palette byte addr (4 x u16 RGB565)
    # r3: packed = n_bytes | ((key & 7) << 8)
    #     key 0-3 = transparent palette index (pixel skipped);
    #     key 4-7 = no transparency (-1 & 7 = 7 never matches a 2-bit value)
    # Each src byte expands to 4 pixels (8 dst bytes).
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

# Optional shared arena for font data. Callers may pre-allocate one buffer
# (font_base.font_buffer = bytearray(n)) before constructing Fonts; each
# Font then claims a slice of it instead of allocating its own bytearray,
# keeping all font data in a single contiguous block.
font_buffer = None

class Font:
    """Renderer for .raw2 bitmap fonts (2-bit anti-aliased grayscale).

    Binary file layout (for the printable ASCII range 32..126, 95 chars):
        [95 width bytes][95 glyphs x bytes_per_char]
    Each glyph is a fixed cell of char_width x char_height pixels stored as
    GS2_HMSB (2 bits/pixel, 4 gray levels, 4 pixels/byte), with
    row_size = (char_width + 3) // 4 bytes. The per-character width table
    gives the proportional advance width used when laying out text.

    The cell dimensions are parsed from the filename, which must look like
    'Name-Size-WxH.raw2' (e.g. 'Roboto-16-14x18.raw2').

    Rendering parameters shared by the draw methods:
        key      -- palette index 0-3 treated as transparent, or -1 to
                    draw all pixels (opaque).
        palette  -- 4-entry RGB565 palette buffer (see color_control
                    .make_palette); None uses the font's default palette.
    """

    def __init__(self, path, display, bg=0, palette=None):
        """Load a .raw2 font.

        path     -- font file path; filename encodes the cell size (WxH).
        display  -- NT35510 (or compatible) instance; rendered lines are
                    pushed to it and its width/height bound the drawing.
        bg       -- RGB565 color the line buffer is filled with before
                    glyphs are drawn (the text background).
        palette  -- default 4-entry RGB565 palette; PALETTE_WHITE if None.
        """
        name = path.rsplit("/", 1)[-1]
        try:
            size = name.rsplit(".", 1)[0].rsplit("-", 1)[-1]
            width, height = size.split("x")
            self.char_width = int(width)
            self.char_height = int(height)
        except ValueError:
            raise ValueError(
                "Font filename must look like 'Name-Size-WxH.raw2', got %r" % name)
        row_size = (self.char_width + 3) // 4
        self.bytes_per_char = row_size * self.char_height
        data_len = _NUM_CHARS + _NUM_CHARS * self.bytes_per_char
        global font_buffer

        with open(path, "rb") as f:
            if font_buffer is None:
                data = memoryview(bytearray(f.read(data_len)))
                print(f"Loaded {len(data)} bytes from {path}, no buffer")
            else:
                count = f.readinto(font_buffer)
                if count < data_len:
                    raise OSError(
                        "Short read from %s: got %d bytes, need %d" % (path, count, data_len))
                if count >= len(font_buffer):
                    raise OSError(
                        "Font buffer too small for %s: read %d into %d" % (path, count, len(font_buffer)))
                data = font_buffer[:count]
                font_buffer = font_buffer[count:]
                print(f"Loaded {len(data)} bytes from {path}, {len(font_buffer)} buf remaining")

        self.widths = data[0:_NUM_CHARS]
        self.data = data[_NUM_CHARS:]

        self.nt = display
        self._line_fb = None
        self._line_w  = 0
        self.bg = bg
        self.pal_default = palette if palette else PALETTE_WHITE

    def _ensure_line_fb(self, FBClass, w):
        # allocate only when we need a bigger buffer than before
        if self._line_fb is None or w > self._line_w:
            self._line_w = w
            self._line_fb = FBClass(w, self.char_height)


    def draw_text_bytes(self, s, FBClass, x0, y0, key=0, palette=None):
        """Draw a single line of text at (x0, y0), clipped to the display
        width. Returns the pixel width actually rendered."""
        max_w = self.nt.width - x0
        text_w = self.get_width(s)
        if text_w > max_w:
            text_w = max_w
        self._ensure_line_fb(FBClass, text_w)
        return self._draw_bytes_range(s, 0, len(s), FBClass, x0, y0,
                                      key, palette, text_w)


    def wrap_text_viper(self, text, FBClass, ix, iy, width, force_cut=False, lim=None, vert_swish=0, key=0, palette=None):
        """Word-wrap and draw `text` in a column `width` px wide starting
        at (ix, iy).

        force_cut  -- also split words wider than the column.
        lim        -- (top, bottom) vertical clip window in display pixels;
                      lines outside it are measured but not drawn. Defaults
                      to the full display height.
        vert_swish -- pixels to shave off the line height (tighter leading).

        Returns (end_y, line_height, in_bounds); in_bounds is False when
        the text ran past the bottom clip limit.
        """
        if not text:
            return iy, self.char_height, True

        if isinstance(text, str):
            b = text.encode("ascii", "replace")
        else:
            b = text

        if lim is None:
            lim = (0, self.nt.height)

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
    def _fast_blit_2(self, fb: object, fb_w: int, v: int, x0: int, pal_addr: int, key: int,
                    slf_data: int, btc: int, row_stride: int, h: int):
        # Blit glyph index v into line buffer fb at x offset x0 using the
        # asm row blitter. slf_data/btc/row_stride/h are hoisted by the
        # caller so they are computed once per line, not per glyph.
        n_bytes: int = row_stride
        # Common case: no right clipping.
        # row_stride GS2 bytes = row_stride * 4 pixels.
        if x0 + (row_stride << 2) > fb_w:
            n_bytes = (fb_w - x0) >> 2
            if n_bytes <= 0:
                return
        dst: int = int(ptr8(fb.buffer)) + (x0 << 1)
        src: int = slf_data + v * btc
        fb_stride: int = fb_w << 1
        packed: int = n_bytes | ((key & 7) << 8)
        while h:
            _blit_gs2_row(dst, src, pal_addr, packed)
            dst += fb_stride
            src += row_stride
            h -= 1


    @micropython.viper
    def _draw_bytes_range(self, b: object, start: int, end: int,
                          FBClass: object, x0: int, y0: int,
                          key: int, palette: object, max_w: int) -> int:
        # Render bytes b[start:end] into the shared line buffer, then push
        # it to the display at (x0, y0). Returns the pixel width drawn.
        bp = ptr8(b)
        widths = ptr8(self.widths)
        fb = self._line_fb
        fb_w: int = int(fb.width)
        fb.fill(int(self.bg))
        pal = palette if palette else self.pal_default
        pal_addr: int = int(ptr8(pal.buffer))
        x: int = 0
        i: int = start
        h: int = int(self.char_height)
        src_stride: int = (int(self.char_width) + 3) >> 2
        slf_data: int = int(ptr8(self.data))
        btc: int = int(self.bytes_per_char)
        while i < end:
            v: int = int(bp[i])
            if v < 32 or v > 126:
                v = 32
            v -= 32
            self._fast_blit_2(fb, fb_w, v, x, pal_addr, key, slf_data, btc, src_stride, h)
            x += int(widths[v])
            if x >= max_w:
                break
            i += 1
        self.nt.draw_framebuf(x0, y0, fb)
        return x

    @micropython.viper
    def get_width(self, word: object) -> int:
        """Return the pixel width of `word` (str or bytes) in this font."""
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
