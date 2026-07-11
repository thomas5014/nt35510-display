# font_base_demo.py -- demo / benchmark harness for font_base.Font.
# This is the runnable script that used to live at the bottom of
# font_base.py: it brings up the display, loads fonts and times rendering.
import gc, machine, micropython, os, time
from nt35510 import NT35510, color565, MyFrameBuffer
from font_base import Font

BG  = [(0,0,0),(30,20,40),(100,0,0),(30,150,150)][1]
nt = NT35510()
nt.fill(color565(*BG))
machine.freq(240_000_000)

def mem(name):
    gc.collect()
    print("\nMem", name, gc.mem_free())
    micropython.mem_info()
    print(f"total time: {time.ticks_ms():,}")

mem("start")

bg565 = color565(*BG)
font1 = Font("/InterBold-14-15x18.raw2", nt, bg=bg565)
# font1 = Font("/fonts/Marseille-22-25x23.raw2", nt, bg=bg565)
# font1 = Font("Astroz-36-35x38.raw2", nt, bg=bg565)
# font1 = Font("HelloPain-36-37x41.raw2", nt, bg=bg565)
# font1 = Font("/fonts/Dejavu-10-10x10.raw2", nt, bg=bg565)
font1 = Font("/fonts/Roboto-16-14x18.raw2", nt, bg=bg565)
# font1 = Font("/fonts/Strong-18-17x18.raw2", nt, bg=bg565)
# font1 = Font("/fonts/HelloPain-12-13x15.raw2", nt, bg=bg565)
# font1 = Font("/fonts/Astroz-16-15x18.raw2", nt, bg=bg565)
# font1 = Font("/fonts/Marseille-22-25x23.raw2", nt, bg=bg565)
# font1 = Font("/fonts/Hollyberry-20-19x20.raw2", nt, bg=bg565)
example_long = 'Mao Li Qiu looked at the light on Fang Yuan\'s body, there was nothing it could do, it bore its fangs and scratched the ground with its claws, causing deep marks to form.\n\nBai Ning Bing\'s and Hei Lou Lan\'s eyelids were twitching, they were evidently moved.\n\nZhao Lian Yun had woken up, she looked at Ma Hong Yun\'s corpse, held in Fang Yuan\'s arm, her tears were flowing out.\n\nShe cried in her heart: "Hong Yun, Hong Yun, how could you leave me like this. Without you, I am all alone in this world. What is the point of living? Do you know, the perseverance of one person is so difficult!"\n\nHow difficult is the perseverance of one person?\n\nAll of the Gu Immortals here could answer that question.\n\nBecause among them, some persevered because of responsibility, some persevered because of hatred, some persevered because of excitement, and some persevered because of love?\n\nAnd Fang Yuan\'s answer?\n\nHe was still expressionless, he continued to move forward relentlessly.\n\nI had once screamed, gradually, I lost my voice.\n\nI had once cried, gradually, I lost my tears.\n\nI had once grieved, gradually, I became able to withstand everything.'
# example_long = """To man the world is twofold, in accordance with his twofold attitude. The attitude of man is twofold, in accordance with the twofold nature of the primary words which he speaks. The primary words are not isolated words, but combined words. The one primary word is the combination I-Thou. The other primary word is the combination I-It; wherein, without a change in the primary word, one of the words He and She can replace It. Hence the I of man is also twofold. For the I of the primary word I-Thou is a different I from that of the primary word I-It. Primary words do not signify things, but. they intimate relations. Primary words do not describe something that might exist independently of them, but being spoken they bring about existence. Primary words are spoken from the being. If Thou is said, the I of the combination I-Thou is said along with it. If It is said, the I of the combination I-It is said along with it. The primary word I-Thou can only be spoken with the whole being. • The primary word I-It can never be spoken with the whole being. * 3"""
example_long = """Peter Piper picked a peck of pickled peppers.\nA peck of pickled peppers Peter Piper picked.\nIf Peter Piper picked a peck of pickled peppers,\nWhere's the peck of pickled peppers Peter Piper picked?"""
# example_long = """Of all elements that are solid at room temperature, caesium is the softest: it has a hardness of Mohs 0.2. It is a very ductile, pale metal, which darkens in the presence of trace amounts of oxygen.[14][15][16] When in the presence of mineral oil (where it is best kept during transport), it loses its metallic lustre and takes on a duller, grey appearance. It has a melting point of 28.5 °C (83.3 °F), making it one of the few elemental metals that are liquid near room temperature. The others are rubidium (39 °C [102 °F]), francium (estimated at 27 °C [81 °F]), mercury (−39 °C [−38 °F]), and gallium (30 °C [86 °F]); bromine is also liquid at room temperature (melting at −7.2 °C [19.0 °F]), but it is a halogen and not a metal. Mercury is the only stable elemental metal with a known melting point lower than caesium.[17] In addition, caesium has a rather low boiling point, 641 °C (1186 °F), the lowest of all stable metals other than mercury.[18] Copernicium and flerovium have been predicted to have lower boiling points than mercury and caesium, but they are extremely radioactive and it is not certain that they are metals.[19][20]"""
example = "Hello 2 3 23World! aeyshdvfudvtbyktvdtfbyhiuguvtjbnkhgrvfbguylbony;"
example1 = "hi"
items = os.listdir("/fonts")
test: int = 1
times: int = 1
i: int = 0
t0: int = time.ticks_us()
if test == 0:
    times: int = 44
    while i < times:
        font1.draw_text_bytes(example, MyFrameBuffer, 5, 0+i*20,0,None)
        i += 1
elif test == 1:
    times: int = len(items)
    for i in range(len(items)):
        print(f"trying font:/fonts/{items[i]}")
        # print(f"following font:/fonts/{items[i+1]}")
        # if f"/fonts/{items[i]}" in ["/fonts/Marseille-22-25x23.raw2","/fonts/MontserratR-18-20x20.raw2","/fonts/PlayfairR-18-17x20.raw2"]:
        #     continue
        font1 = Font(f"/fonts/{items[i]}", nt, bg=bg565)
        examplein = f"{items[i][:-5]} {example[:40]}"
        font1.draw_text_bytes(examplein, MyFrameBuffer, 2, 0+i*20,0,None)
elif test == 2:
    example = example_long
    font1.wrap_text_viper(example,MyFrameBuffer,0,0,480,lim=(0,800))#,vert_swish=14)
elif test == 3:
    example = ".............................."#"Hello World!"
    font1.draw_text_bytes(example, MyFrameBuffer, 0, 20,0,None)
elif test == 4:
    nt.fb_text("example", 20, 20)
elif test == 5: # spped numbers
    i = 0
    prev = time.ticks_us()
    while i < 1_000_000:
        val = str(i*1000000//time.ticks_diff(time.ticks_us(), prev))
        font1.draw_text_bytes(val, MyFrameBuffer, 0, 20, 0, None)
        if i % 400 == 0:
            print(val)
        i += 1
elif test == 6:
    example = "h"
    font1.draw_text_bytes(example, MyFrameBuffer, 5, 0+i*20,0,None)

t1 = time.ticks_us()
t2 = time.ticks_us()
t3 = time.ticks_cpu()
# font1.get_width(example)
t4 = time.ticks_cpu()
print(f"draw_text-test{test}: prep fb {t1-t0:,}us, draw chars, control {t2-t1:,}us - {t4-t3:,}cpu, letters per second: {len(example)*times / ((t1-t0) / 1_000_000):,.2f}, us per letter: {(t1-t0) / (len(example)*times):,}")
print(f"Opperations per pixel: {machine.freq()*(t1-t0)/(1_000_000*font1.get_width(example)*font1.char_height*times):,}, alternate calculation: {(t1-t0) / (len(example)*times) * 1000 / (font1.char_height*font1.char_width):,}")

print(machine.freq())
mem("end")

# Baseline numbers from before the library/demo split (font_base.py with
# the 95-FrameBuffer glyph cache still allocated at init):
# Mem start 8607696
# stack: 756 out of 12032
# GC: total: 8641216, used: 33520, free: 8607696
#  No. of 1-blocks: 71, 2-blocks: 95, max blk sz: 359, max free sz: 512276
# total time: 227,788
# Loaded 6935 bytes from /InterBold-14-15x18.raw2, no buffer
# draw_text-test0: prep fb 213,789us, draw chars, control 6us - 4cpu, letters per second: 14200.92, us per letter: 70.418
# 240000000

# Mem end 8575776
# stack: 756 out of 12032
# GC: total: 8641216, used: 65440, free: 8575776
#  No. of 1-blocks: 213, 2-blocks: 238, max blk sz: 1069, max free sz: 512276
# total time: 228,219
