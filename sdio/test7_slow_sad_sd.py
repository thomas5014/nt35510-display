import machine
machine.freq(150_000_000)
print("freq", machine.freq())
opt = 1
if opt == 0:
    from machine import SoftSPI, Pin                                                                                                                                                           
    import sd, os                                                                                                                                                                          
                                                            
    spi = SoftSPI(baudrate=100_000, sck=Pin(24), mosi=Pin(25), miso=Pin(26))                                                                                                                   
    cs  = Pin(29, Pin.OUT, value=1)                           
                                                                                                                                                                                                
    sd = sd.SDCard(spi, cs)
    os.mount(sd, '/sd')                                                                                                                                                                        
    print(os.listdir('/sd')) 

    while True:                                                                                                                                                      
        buf = bytearray(512)                                                                                                                                                                       
        sd.readblocks(0, buf)
                                                                                                                                                                                                    
        # Check MBR signature
        print("55 AA present:", buf[510] == 0x55 and buf[511] == 0xAA)
        print(f"bytes 510-511: {buf[510]:02X} {buf[511]:02X}")                                                                                                                                     
                                                                                                                                                                                                    
        # Also dump the first 16 bytes and last 16 bytes for sanity                                                                                                                                
        #print("tail:", bbytes(buf).hex())
        print(''.join([f"{i:02x} " for i in buf[438:]]))
        import time
        time.sleep(1)
elif opt == 1:
    import sdio, os
    sd = sdio.SDCard()
    buf = bytearray(512)
    sd.readblocks(100, buf)  # sanity check
    print(''.join([f"{i:02x} " for i in buf[438:]]))
    os.mount(sd, "/sd")
    files = os.listdir("/sd")
    print("SD Card Files:", files)

# print("Sector 0 head:", " ".join("{:02x}".format(b) for b in buf[32*(offset):32*(offset+10)]))

"""[SDIO ERR] SDIO CRC lo: computed=%d received=%d (-1162903432, 732460271)
[SDIO ERR] SDIO CRC hi: computed=%d received=%d (371922855, -1726733784)
[SDIO ERR] SDIO checksum error in read (1, 1)
readblocks: CRC error sector=0
  b444-b463: 00 00 80 ef ff f0 bf ef ff f0 02 00 00 00 00 4b 70 30 00 00
  b508-b511: 00 05 5a ae

  sdio 00 00 34 cd 60 49 00 00 80 (lost nibble) ef ff f0 bf ef ff f0 02 00 00 00 00 4b 70 30 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 05 5a ae
 spi  00 00 34 cd 60 49 00 00 80 fe ff ff 0b fe ff ff 00 20 00 00 00 04 b7 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 55 aa
freq 80mhz
 1  00 00 34 cd 60 49 00 00 80 ef ff f0 bf ef ff f0 02 00 00 00 00 4b 70 30 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 05 5a ae
 0  00 00 34 cd 60 49 00 00 80 fe ff ff 0b fe ff ff 00 20 00 00 00 04 b7 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 55 aa
 
 alt1 00 00 00 00 00 00 00 00 80 ef ff f0 bf ef ff f0 02 00 00 00 08 89 b0 30 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 05 5a a9
 alt1
  
 pny: sdcard_init: ocr=0xc0ff8000 is_sdhc=1
sdcard_init: rca=0x00010000
sdcard_init: sectors=60532736
failed

sandWhite: sdcard_init: ocr=0xc0ff8000 is_sdhc=1
sdcard_init: rca=0xaaaa0000
sdcard_init: sectors=62333952
failed

sanA1: sdcard_init: ocr=0xc0ff8000 is_sdhc=1
sdcard_init: rca=0xaaaa0000
sdcard_init: sectors=62333952
worked

sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (1737525496, -1751615233)
[SDIO ERR] SDIO CRC hi: computed=%d received=%d (1297674476, -1[SDIO ERR] SDIO checksum error in read (1, 1)
readblocks: CRC error sector=0
sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (-1162903432, 732460271)
[SDIO ERR] SDIO CRC hi: computed=%d received=%d (371922855, -172[SDIO ERR] SDIO checksum error in read (1, 1)
readblocks: CRC error sector=0
sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)


freq 150000000
sdcard_init: ocr=0xc0ff8000 is_sdhc=1
sdcard_init: CID MID=0x27 OID=PH PNM=SD32G PRV=6.0
sdcard_init: CID raw: 27 50 48 53 44 33 32 47 60 6b 22 62 b2 01 7a d7
sdcard_init: rca=0x00010000 CMD3_status=0x0520
sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=60532736
sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 e6 e9 7f 80 0a 40 00 b7
sdcard_init: CMD7 reply=0x00000700
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (-32440064, -286330882)
[SDIO ERR[SDIO ERR] SDIO checksum error in read (1, 1)
sdcard_init: SCR read failed st=6
sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (1737525496, -1751615233[SDIO ERR] SDIO checksum error in read (1, 1)
readblocks: CRC error sector=0

000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
020: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
030: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
040: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
050: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
060: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
070: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
080: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
090: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0b0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0c0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0d0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0e0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0f0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
100: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
110: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
120: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
130: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
140: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
150: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
160: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
170: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
190: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1b0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 80 ef
1c0: ff f0 bf ef ff f0 02 00 00 00 08 89 b0 30 00 00
1d0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1e0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1f0: 00 00 00 00 00 00 00 00 00 00 00 00 00 05 5a a9
Traceback (most recent call last):
  File "<stdin>", line 33, in <module>
OSError: [Errno 5] EIO

freq 150000000
sdcard_init: ocr=0xc0ff8000 is_sdhc=1
sdcard_init: CID MID=0x03 OID=SD PNM=SC32G PRV=8.0
sdcard_init: CID raw: 03 53 44 53 43 33 32 47 80 70 7e 23 7a 01 61 33
sdcard_init: rca=0xaaaa0000 CMD3_status=0x0520
sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=62333952
sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 ed c8 7f 80 0a 40 40 c3
sdcard_init: CMD7 reply=0x00000700
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (-300871423, -269553921)
[SDIO ER[SDIO ERR] SDIO checksum error in read (1, 1)
sdcard_init: SCR read failed st=6
sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (-1162903432, 732460271)[SDIO ERR] SDIO checksum error in read (1, 1)
readblocks: CRC error sector=0

000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
020: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
030: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
040: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
050: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
060: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
070: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
080: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
090: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0b0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0c0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0d0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0e0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0f0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
100: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
110: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
120: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
130: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
140: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
150: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
160: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
170: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
180: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
190: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1a0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1b0: 00 00 00 00 00 00 00 00 34 cd 60 49 00 00 80 ef
1c0: ff f0 bf ef ff f0 02 00 00 00 00 4b 70 30 00 00
1d0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1e0: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
1f0: 00 00 00 00 00 00 00 00 00 00 00 00 00 05 5a ae
Traceback (most recent call last):
  File "<stdin>", line 33, in <module>
OSError: [Errno 5] EIO

freq 150000000
sdcard_init: ocr=0xc0ff8000 is_sdhc=1
sdcard_init: CID MID=0x03 OID=SD PNM=SD32G PRV=8.5
sdcard_init: CID raw: 03 53 44 53 44 33 32 47 85 5c 03 0b a2 01 5c 19
sdcard_init: rca=0xaaaa0000 CMD3_status=0x0520
sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=62333952
sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 ed c8 7f 80 0a 40 40 c3
sdcard_init: CMD7 reply=0x00000700
[SDIO ERR] SDIO CRC lo: computed=%d received=%d (-285212672, -286331154)
[SDIO ER[SDIO ERR] SDIO data rx timeout (1, 0)
sdcard_init: SCR read failed st=5
sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
00 00 00 00 00 00 00 00 00 fe ff ff 0b fe ff ff 00 08 00 00 00 18 b7 03 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 55 aa 
SD Card Files: ['.Spotlight-V100', 'hellow_w.py', '__init__.py', '.Trashes', 'Novels', 'Settings.json', '.fseventsd', '._Settings.json', 'Novels1', 'burto.raw_480-700.raw', 'Wallpapers', 'burto_480-700.raw', 'berto_480-700.raw', 'bertto_480-700.raw']

    """