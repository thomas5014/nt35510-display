import micropython

@micropython.asm_thumb
def add_one(r0):
    add(r0, 1)

# print(add_one(1))

@micropython.asm_thumb
def fun():
    movw(r0, 42)

# print(fun())
# SIO_BASE   = 0xD0000000
# import machine
# @micropython.asm_thumb
# def led_on():
#     movwt(r0, 0xD0000000)
#     movw(r1, 1 << 23)
#     str(r1, [r0, 0x14])

# led_on()

@micropython.asm_thumb
def compare1(r0,r1):
    mov(r2,r1)
    mov(r1,r0)
    mov(r0,1)
    cmp(r1,r2)
    it(eq)
    mov(r0,0)

# print(compar1(6,5))


@micropython.asm_thumb
def compare2(r0,r1):
    cmp(r0,r1)
    ite(eq)
    mov(r0,0)
    mov(r0,1)

# print(compare2(5,5))

@micropython.asm_thumb
def compare3(r0): # if r0 == 12: return 0 else 1
    cmp(r0,12)
    ite(eq)
    mov(r0,0)
    mov(r0,1)

# print(compare3(12))

@micropython.asm_thumb
def compare4(r0): # if r0 == 12: return 0 else 1
    cmp(r0,12)
    ite(ge)
    mov(r0,0)
    mov(r0,1)

# print(compare4(11))

@micropython.asm_thumb
def loop(r0):
    b(start)
    label(loop_start)
    add(r0,1)
    cmp(r0,100)
    label(start)
    bge(loop_start)

# print(loop(0))

@micropython.asm_thumb
def quad(r0):
    b(START)
    label(DOUBLE)
    add(r0, r0, r0)
    bx(lr)
    label(START)
    bl(DOUBLE)
    bl(DOUBLE)

# print(quad(1))

@micropython.asm_thumb
def threeXplusOne(r0):
    mov(r1, 1)
    and_(r1, r0)
    cmp(r1, 0)
    
    beq(EVEN)

    label(ODD)
    mov(r1, 3)
    mul(r0, r1)
    add(r0, 1)
    b(EXIT)

    label(EVEN)
    asr(r0, r1)

    label(EXIT)
    # bx(lr)

# print([threeXplusOne(i) for i in range(40)])

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

import math
# print([f"{factorial(i)}-{i}-{math.factorial(i)}-{factorial(i)==math.factorial(i)}" for i in range(0,17)])

@micropython.asm_thumb
def factorial_big(r0):
    cmp(r0,2)
    bls(EXIT)

    mov(r1,r0)
    cmp(r0,12)
    bgt(TOO_BIG)

    label(LOOP)
    sub(r1,r1,1)
    mul(r0,r1)
    cmp(r1,2)
    bgt(LOOP)
    bls(EXIT)

    label(TOO_BIG)
    label(LOOP1)
    sub(r1,r1,1)
    mul(r0,r1)
    clz(r2,r0)
    cmp(r2,2)
    bls(EAT_ZEROS)
    cmp(r1,2)
    bgt(LOOP1)
    bls(EXIT)

    label(EAT_ZEROS)
    label(LOOP2)
    mov(r2,10)
    udiv(r0,r0,r2)
    mov(r2,7)
    mov(r3,r0)
    and_(r3,r2)
    cmp(r3,2)
    beq(LOOP2)
    b(TOO_BIG)

    label(EXIT)
    cmp(r0,0)
    it(eq)
    mov(r0,1)


# print([f"{factorial_big(i)}-{i}-{math.factorial(i)}-{factorial_big(i)==math.factorial(i)}" for i in range(0,17)])

@micropython.asm_thumb
def safe_mul(r0,r1):
    clz(r2,r0)
    clz(r3,r1)
    add(r2,r2,r3)
    cmp(r2,32)
    ite(ge)
    mul(r0,r1)
    mov(r0,0)

# print(safe_mul(0xffff_ffff,0x1))

import array

_test_buf = array.array('I', [0])

@micropython.asm_thumb
def _test_str(r0, r1):
    # r0 = address, r1 = value to write
    str(r1, [r0, 0])

_test_str(_test_buf, 0xDEADBEEF)
print(hex(_test_buf[0]))  # expect 0xdeadbeef