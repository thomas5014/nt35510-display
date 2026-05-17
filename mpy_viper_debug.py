import micropython

@micropython.viper                                                                                                                                                                   
def add(x: int, y: int) -> int:
    return x + y                                                                                                                                                                     

@micropython.viper        
def zero():
    0

@micropython.viper        
def one():
    0+1


@micropython.viper                    
def vprint(n: int):
    print(n)


raw = micropython.viper_code(add)                                                                                                                                                    
print(len(raw), 'bytes of machine code (ARM Thumb2)')
print(' '.join('%02x' % b for b in raw))
vprint(10)