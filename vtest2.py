import micropython

@micropython.viper
def add3(x: int) -> int:
    return x + 3

