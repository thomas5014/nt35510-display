@micropython.viper
def test_add(a: int, b: int) -> int:
    return a + b

@micropython.viper
def test_sub(a: int, b: int) -> int:
    return a - b

print(test_add(3,4), test_sub(7, 8))
