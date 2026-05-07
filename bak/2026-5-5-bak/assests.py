# CORE/ASSETS.py
import math
from micropython import const

sprites = {
    'house1':        ('16x16',"000000000001400000069000001be400006ff90001bffe4006ffff901bffffe41bffffe41bfaafe41bf96fe41bf96fe41bf96fe41bf96fe41bf96fe405541550"),
    'house2':        ('16x16','0001400000069000001be400006ff90001bffe4006ffff901bffffe46ffffff9bffffffe5bfaafe51bf96fe41bf96fe41bf96fe41bf96fe41bf96fe405541550'),
    'book1':         ('16x16','0000000000000000000000003e6400002ab800003e7903e03e2e02a03eee42a03eeb83e03ee793ee3ee2e3ee3ee1e6ae2ae0baae3ee07bee1550555500000000'),
    'book2':         ('16x16','0000000000000000000180000006d00003fae00002a9f4343bf9a8342bf8b8383bf87d382bf82e382bfbaa3d3bfb9f7d2aab8bbd3bfb8bbd1555455400000000'),
    'book3':         ('16x16','00000000000000000000000003f4000002e8000003b4003d02e83fbd03b43bbd3ae83bbd3bb43bbd2aebbbbd2bb7bbbd3aebbbbd3bf7bfbd1151151400000000'),
    'wheel':         ('16x16','000000000000000000055000006ff90001bb5e4002d2c7800741c2d0077fdbd007e7fdd0078341d006d3878001b5ee40006ff900000550000000000000000000'),
    'gear':          ('16x16','000100000047180008375c60076ff9c001fb5f442ed2c7b01741c1d40743c1fd7f4fe7d017787ed40ef407b811f95f40036ff9d00935dc200024d10000004000'),
    'circle':        ('08x08','05501be46ff97ffd7ffd6ff91be40550'),
    'hollow circle': ('16x16','007ffd0007d007d01d0000743400001c7000000dd0000007c0000003c0000003c0000003c0000003d00000077000000d3400001c1d00007407d007d0007ffd00'),
    'clock':         ('16x16','007ffd0003d307c00d8302703403001c7803002dd0030007c0030003c003c00be001e003c0007003d000380778000c2d3400001c0d80027003d087c0007ffd00'),
    'eye glass':     ('16x16','02fe00000e46c00034007000a0002800d0001c00c0000c00d0001c00a0002800340078000e46f90002feae4000001b90000006e4000001b90000006e00000019'),
    'right arrow':   ('16x16','000a0000000b8000000be0000002f8000000be0000002f8000000be0000002f8000002f800000be000002f800000be000002f800000be000000b8000000a0000'),
    'up arrow':      ('16x8','0007d000002ff80000ffff0007ffffd06ffffff9ffffffff1ffffff40ffffff0'),
    'down arrow':    ('16x8','0ffffff01ffffff4ffffffff2ffffff807ffffd000ffff00002ff8000007d000')
}
class AssetCache:
    def __init__(self, max_bytes=64_000):
        self.max_bytes = max_bytes
        self.map = {}   # key -> (data, size, use_counter)
        self.total = 0
        self.counter = 0
       

    def curves(self,radi):
        # supported to r=8
        if radi == 1:
            curve = (1,(0,0))
        elif radi == 2:
            curve = (2,(-1,0),(-1,-1),(0,-1))
        elif radi == 3:
            curve = (3,(-2,0),(-2,-1),(-2,-2),(-1,-2),(0,-2))
        elif radi == 4:
            curve = (4,(-3,0),(-3,-1),(-3,-2),(-2,-2),(-2,-3),(-1,-3),(0,-3))
        elif radi == 5:
            curve = (5,(-4,0),(-4,-1),(-4,-2),(-3,-3),(-2,-4),(-1,-4),(0,-4))
        elif radi == 6:
            curve = (6,(-5,0),(-5,-1),(-5,-2),(-5,-3),(-4,-3),(-4,-4),(-3,-4),(-3,-5),(-2,-5),(-1,-5),(0,-5))
        elif radi == 7:
            curve = (7,(-6,0),(-6,-1),(-6,-2),(-6,-3),(-5,-3),(-5,-4),(-4,-4),(-4,-5),(-3,-5),(-3,-6),(-2,-6),(-1,-6),(0,-6))
        elif radi == 8:
            curve = (8,(-7,0),(-7,-1),(-7,-2),(-7,-3),(-6,-3),(-6,-4),(-6,-5),(-5,-5),(-5,-6),(-4,-6),(-3,-6),(-3,-7),(-2,-7),(-1,-7),(0,-7))
        elif radi == 9:
            curve = (9,(-8,0),(-8,-1),(-8,-2),(-8,-3),(-8,-4),(-7,-4),(-7,-5),(-6,-5),(-6,-6),(-5,-6),(-5,-7),(-4,-7),(-3,-8),(-2,-8),(-1,-8),(0,-8))
        elif radi == 10:
            curve = (10,(-9, 0), (-9, -1), (-9, -2), (-9, -3), (-9, -4), (-8, -4), (-8, -5), (-7, -6), (-7, -7), (-6, -7), (-5, -8), (-4, -8), (-4, -9), (-3, -9), (-2, -9), (-1, -9), (0, -9))
        else:
            pts = [radi]
            for tup in self.curve_plotter(radi):
                pts.append(tup)
            curve = pts
        return curve

    # internal
    def curve_plotter(self,radius=11):
        coordinates = [(0,0)]
        save_points = []
        skipping = 0
        for a in range(90): # drawing points for rounded corners
            angle = 360 - a + 270
            roundx = int(math.cos(math.radians(angle))*radius)
            roundy = int(math.sin(math.radians(angle))*radius)
            coordinates.append((roundx,roundy))
            if not coordinates[-1] == coordinates[-2]:
                save_points.append((roundx,roundy))
        coordinates = None

        def swapper(inlist):
            outlist = []
            for i in range(len(inlist)):
                outlist.append(inlist[len(inlist)-i-1])
            return outlist
        return swapper(save_points)[:-1]
    
    def sprite(self,fb,x,y,name,color,background=None):
        sprite_data = sprites[name]
        fb.add_sprite(x,y,color,sprite_data,background)
    
    
    


