from PIL import Image, ImageFont, ImageDraw
from time import time_ns


items = ['Cosmic_Curtaincall_144', 'Creation_Of_All_Things_247_WN', 'God_Slayer_The_Tale_of_Humanitys_Last_Stand_176', 'Lord_of_Mysteries', 'Lord_of_Mysteries_2-_Circle_of_Inevitability_WN', "Omniscient Reader's Viewpoint", 'ReZero', 'Reborn_with_Infinity_Skill_Points_I_Enslaved_All_Universes_126', 'Reverend_Insanity', 'SS', 'SSS-Class_Suicide_Hunter_Novel', 'S^3_awakening', 'The_Begining_After_the_End_516', 'The_Legendary_Mechanic_WN', 'The_Mech_Touch', 'stop.txt', 'tbate', 'wOther', 'z-filler.txt']

class sys_snippet():
    def __init__(self,draw):
        self.display = draw
        self.font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 8)
        self.font2 = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 12)
        
        
    def draw_tab(self,spacing,string,num,selected=False): # draws selectable tab
        y = spacing * 22

        try:
            if string.endswith(".xhtml"):
                string = string.split('_', 1)[1]
                string = string.rpartition('.')[0]
        except:
            print("too weird")

        if len(string) > 28:
            tsize = self.font
            pass
        else:
            tsize = self.font2
            pass
        if selected: # alter colors if selected
            c = (230,255,200)
            self.display.rectangle([(7,7+y),(233,22+y)],(150,100,200))
        else:
            backround = (40,40,40)
            self.display.rectangle([(7,7+y),(233,22+y)],(40,40,40))
            c = (10,130,255)

        self.display.rectangle([(5,5+y),(235,24+y)],outline=(70,70,70))
        self.display.text((9,9+y),string,c,tsize)
        self.display.text((220,10+y),str(num),c,self.font)


    def draw_dir(self,files,tab_num=[(0,0)],full_refresh=False):
        max_vis = 13
        if tab_num[-1][0] > max_vis-1: # add offset if > max_vis
            tab_shift = (tab_num[-1][0]//max_vis)*max_vis
        else:
            tab_shift = 0
        
        if not full_refresh: # ingore if already fullrefresh
            if tab_num[-1][0]>tab_num[-2][0] and (tab_num[-2][0]%max_vis)==max_vis-1: # finds if page redraw needed when going down
                print(tab_num[-2][0])
                print("refresh for down")
                full_refresh = True
                self.display.rectangle([(0, 0), (240, 7 + 22 * min(len(files),13))], (0, 0, 0))
            elif tab_num[-1][0]<tab_num[-2][0] and (tab_num[-1][0]%max_vis)==max_vis-1: # finds if page redraw needed when going up
                print(tab_num[-1][0])
                print("refresh for up")
                full_refresh = True
        
        if full_refresh:
            print("full refresh",tab_shift)
            ran = min(len(files)-tab_shift,max_vis)
            print("range",ran)
            for i in range(ran):
                self.draw_tab(i,files[i+tab_shift],i+1+tab_shift, i+tab_shift == tab_num[-1][0])
                
        else:
            if tab_num[-2][0] > max_vis-1: # finds find prev selected tab local
                prev_tab = tab_num[-2][0]-((tab_num[-2][0]//max_vis)*max_vis)
            else:
                prev_tab = tab_num[-2][0]
            self.draw_tab(prev_tab,files[tab_num[-2][0]],prev_tab+1+tab_shift,False)
            cur_tab = tab_num[-1][0]-tab_shift # draws cur selected tab
            self.draw_tab(cur_tab,files[tab_num[-1][0]],cur_tab+1+tab_shift,True)



# Create a new image with RGB mode, a size of 200x150 pixels, and a white background
# 'RGB' defines the color mode (Red, Green, Blue)
# (200, 150) is a tuple representing (width, height)
# (255, 255, 255) is a tuple representing the RGB color for white
img = Image.new('RGB', (480,800), (255, 255, 255))
#240, 320)

# You can then draw on this image, add text, etc.
# For example, to draw a red rectangle:
from PIL import ImageDraw
draw = ImageDraw.Draw(img)
draw.rectangle([(0, 0), (239, 319)], fill=(0, 0, 0)) # Red rectangle
s = sys_snippet(draw)
s.draw_dir(items,full_refresh=True)

# Save the image to a file
img.save('my_new_image_but_diff.png')

# Optionally, display the image
img.show()