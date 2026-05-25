@micropython.viper
def c_bright_viper(r: int, g: int, b: int, brightness: int, br: int, bg: int, bb: int) -> int:
    # 1. Handle edge cases
    if brightness <= 0:
        r, g, b = br, bg, bb
    elif brightness == 100:
        pass # Use original r, g, b
    else:
        # 2. Integer-based Alpha Blending (scaled by 100)
        # For brightness > 100, it acts as a multiplier
        # For brightness < 100, it blends with background
        inv_alpha: int = 100 - brightness
        
        r = (r * brightness + br * inv_alpha) // 100
        g = (g * brightness + bg * inv_alpha) // 100
        b = (b * brightness + bb * inv_alpha) // 100

    # 3. Constrain to 8-bit range
    if r > 255: r = 255
    if g > 255: g = 255
    if b > 255: b = 255
    if r < 0: r = 0
    if g < 0: g = 0
    if b < 0: b = 0

    # 4. Inline RGB565 conversion (Viper can't call outside functions easily)
    # (r >> 3) << 11 | (g >> 2) << 5 | (b >> 3)
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


@micropython.asm_thumb
def _distance_bits(r0, r1, r2, r3):
    sub(r2, r2, r0)
    bpl(lbl_dx_ok)
    neg(r2, r2)
    label(lbl_dx_ok)
    sub(r3, r3, r1)
    bpl(lbl_dy_ok)
    neg(r3, r3)
    label(lbl_dy_ok)
    vmov(s0, r2)
    vcvt_f32_s32(s0, s0)
    vmul(s0, s0, s0)
    vmov(s1, r3)
    vcvt_f32_s32(s1, s1)
    vmul(s1, s1, s1)
    vadd(s0, s0, s1)
    vsqrt(s0, s0)
    vmov(r0, s0)             # raw float bits, no vcvt back to int

import struct
_buf = bytearray(4)

def distance(x1, y1, x2, y2):
    struct.pack_into('<I', _buf, 0, _distance_bits(x1, y1, x2, y2))
    return struct.unpack_from('<f', _buf, 0)[0]

import time
t0 = time.ticks_cpu()
distance(0,0,3,1)
t1 = time.ticks_cpu()
print(f"Distance calculated in {t1-t0} CPU ticks")  