import os, gc
import micropython

stat = os.statvfs("/")
size = stat[1] * stat[2]
free = stat[0] * stat[3]
used = size - free

KB = 1024
MB = 1024 * 1024

print("Size : {:,} bytes, {:,} KB, {} MB".format(size, size / KB, size / MB))
print("Used : {:,} bytes, {:,} KB, {} MB".format(used, used / KB, used / MB))
print("Free : {:,} bytes, {:,} KB, {} MB".format(free, free / KB, free / MB))
micropython.mem_info(1)
print(f"Free memory: {gc.mem_free():,} Bytes")