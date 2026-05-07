import micropython

@micropython.viper                                                                                                                                                                   
def add(x: int, y: int) -> int:
    return x + y                                                                                                                                                                     
                
raw = micropython.viper_code(add)                                                                                                                                                    
print(len(raw), 'bytes of machine code (ARM Thumb2)')
print(' '.join('%02x' % b for b in raw))