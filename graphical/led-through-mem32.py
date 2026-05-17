import machine
# machine.Pin(23,machine.Pin.OUT).value(0)
# print(hex(machine.mem32[0x4001c060]))
print(hex(machine.mem32[0x40000000])) 

# Use the API to handle the complex TrustZone/Isolation setup for you
led = machine.Pin(23, machine.Pin.OUT)

# Now try the "Raw" toggle using the SIO Alias
SIO_GPIO_XOR = 0xd000001c
machine.mem32[SIO_GPIO_XOR] = (1 << 23) # This should flip the LED state
