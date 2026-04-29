content = {
    1: """sdcard_init: ocr=0xc0ff8000 is_sdhc=1
    sdcard_init: CID MID=0x27 OID=PH PNM=SD32G PRV=6.0
    sdcard_init: CID raw: 27 50 48 53 44 33 32 47 60 6b 22 62 b2 01 7a d7
    sdcard_init: rca=0x00010000 CMD3_status=0x0520
    sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=60532736
    sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 e6 e9 7f 80 0a 40 00 b7
    sdcard_init: CMD7 reply=0x00000700
    sdcard_init: ACMD42 reply=0x00000920
    sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
    sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
    sdcard_init: CMD16 reply=0x00000900
    sdcard_init: GPIO after ACMD6/CMD16: CLK=0 CMD=1 D0=1 D1=1 D2=1 D3=1
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (-924767139, 669428318)
    [SDIO ERR] SDIO CRC hi: computed=%d received=%d (153024973, -2001493396)
    [SDIO ERR] SDIO checksum error in read (1, 1)
    sdcard_init: SCR read failed st=6 (non-fatal)""",
    2: """sdcard_init: ocr=0xc0ff8000 is_sdhc=1
    sdcard_init: CID MID=0x03 OID=SD PNM=SC32G PRV=8.0
    sdcard_init: CID raw: 03 53 44 53 43 33 32 47 80 70 7e 23 7a 01 61 33
    sdcard_init: rca=0xaaaa0000 CMD3_status=0x0520
    sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=62333952
    sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 ed c8 7f 80 0a 40 40 c3
    sdcard_init: CMD7 reply=0x00000700
    sdcard_init: ACMD42 reply=0x00000920
    sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
    sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
    sdcard_init: CMD16 reply=0x00000900
    sdcard_init: GPIO after ACMD6/CMD16: CLK=0 CMD=1 D0=1 D1=1 D2=1 D3=1
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (-819898387, -1869176530)
    [SDIO ERR] SDIO CRC hi: computed=%d received=%d (-983220614, -2072795876)
    [SDIO ERR] SDIO checksum error in read (1, 1)
    sdcard_init: SCR read failed st=6 (non-fatal)""",
    3: """sdcard_init: ocr=0xc0ff8000 is_sdhc=1
    sdcard_init: CID MID=0x03 OID=SD PNM=SD32G PRV=8.5
    sdcard_init: CID raw: 03 53 44 53 44 33 32 47 85 5c 03 0b a2 01 5c 19
    sdcard_init: rca=0xaaaa0000 CMD3_status=0x0520
    sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=62333952
    sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 ed c8 7f 80 0a 40 40 c3
    sdcard_init: CMD7 reply=0x00000700
    sdcard_init: ACMD42 reply=0x00000920
    sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
    sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
    sdcard_init: CMD16 reply=0x00000900
    sdcard_init: GPIO after ACMD6/CMD16: CLK=1 CMD=1 D0=1 D1=1 D2=1 D3=1
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (-819898387, -1869176530)
    [SDIO ERR] SDIO CRC hi: computed=%d received=%d (-983220614, -2072795876)
    [SDIO ERR] SDIO checksum error in read (1, 1)
    sdcard_init: SCR read failed st=6 (non-fatal)"""
}
content2 = {
    1:"""sdcard_init: ocr=0xc0ff8000 is_sdhc=1
    sdcard_init: CID MID=0x27 OID=PH PNM=SD32G PRV=6.0
    sdcard_init: CID raw: 27 50 48 53 44 33 32 47 60 6b 22 62 b2 01 7a d7
    sdcard_init: rca=0x00010000 CMD3_status=0x0520
    sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=60532736
    sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 e6 e9 7f 80 0a 40 00 b7
    sdcard_init: CMD7 reply=0x00000700
    sdcard_init: ACMD42 reply=0x00000920
    sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
    sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
    sdcard_init: CMD16 reply=0x00000900
    sdcard_init: GPIO after ACMD6/CMD16: CLK=0 CMD=1 D0=1 D1=1 D2=1 D3=1
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (-924767139, 669428318)
    [SDIO ERR] SDIO CRC hi: computed=%d received=%d (153024973, -2001493396)
    [SDIO ERR] SDIO checksum error in read (1, 1)
    sdcard_init: SCR st=6 raw: 02 85 80 83 00 00 00 00
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (1737525496, -1751615233)
    [SDIO ERR] SDIO CRC hi: co[SDIO ERR] SDIO data rx timeout (1, 0)
    readblocks: rx_poll failed st=5
    Failed to readblock 0 from sd: [Errno 5] EIO""",
    2:"""sdcard_init: ocr=0xc0ff8000 is_sdhc=1
    sdcard_init: CID MID=0x03 OID=SD PNM=SC32G PRV=8.0
    sdcard_init: CID raw: 03 53 44 53 43 33 32 47 80 70 7e 23 7a 01 61 33
    sdcard_init: rca=0xaaaa0000 CMD3_status=0x0520
    sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=62333952
    sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 ed c8 7f 80 0a 40 40 c3
    sdcard_init: CMD7 reply=0x00000700
    sdcard_init: ACMD42 reply=0x00000920
    sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
    sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
    sdcard_init: CMD16 reply=0x00000900
    sdcard_init: GPIO after ACMD6/CMD16: CLK=1 CMD=1 D0=1 D1=1 D2=1 D3=1
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (-819898387, -1869176530)
    [SDIO ERR] SDIO CRC hi: computed=%d received=%d (-983220614, -2072795876)
    [SDIO ERR] SDIO checksum error in read (1, 1)
    sdcard_init: SCR st=6 raw: 02 35 80 43 00 00 00 00
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (-1162903432, 732460271)
    [SDIO ERR] SDIO CRC hi: computed[SDIO ERR] SDIO checksum error in read (1, 1)
    readblocks: CRC error sector=0
    readblocks: post-transfer GPIO: D0=1 D1=1 D2=1 D3=1
    readblocks: sentinel 0x77 remaining: 0/512

    000: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    010: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    020: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    030: 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
    Failed to readblock 0 from sd: [Errno 5] EIO""",
    3:"""sdcard_init: ocr=0xc0ff8000 is_sdhc=1
    sdcard_init: CID MID=0x03 OID=SD PNM=SD32G PRV=8.5
    sdcard_init: CID raw: 03 53 44 53 44 33 32 47 85 5c 03 0b a2 01 5c 19
    sdcard_init: rca=0xaaaa0000 CMD3_status=0x0520
    sdcard_init: CSD ver=1 TRAN_SPEED=0x32 CCCL=0x5b5 sectors=62333952
    sdcard_init: CSD raw: 40 0e 00 32 5b 59 00 00 ed c8 7f 80 0a 40 40 c3
    sdcard_init: CMD7 reply=0x00000700
    sdcard_init: ACMD42 reply=0x00000920
    sdcard_init: CMD55 reply=0x00000920 (APP_CMD=1)
    sdcard_init: ACMD6 reply=0x00000920 (ILLEGAL_CMD=0)
    sdcard_init: CMD16 reply=0x00000900
    sdcard_init: GPIO after ACMD6/CMD16: CLK=1 CMD=1 D0=1 D1=1 D2=1 D3=1
    [SDIO ERR] SDIO CRC lo: computed=%d received=%d (1184801378, -1)
    [SDIO ERR] SDIO CRC hi: computed=%d received=%d (1590495280, -1)
    [SDIO ERR] SDIO checksum error in read (1, 1)
    sdcard_init: SCR st=6 raw: 96 a1 2e ff ff ff ff ff
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'"""
}
while True:
    cont = content2
    opt = int(input("Select mode, 1-[view once card] 2-[compare line from all]: "))
    if opt == 1:
        content_num = int(input("Which card? 1-3: "))
        print(cont[content_num])
    elif opt == 2:
        inopt = 1
        while True:
            if inopt != 0:
                line_num = int(input("Select line: "))
            else:
                line_num += 1
                print("current line number: ",line_num)
            for i in range(1, 4):
                try:
                    print(cont[i].split("\n")[line_num])
                except: continue
            inopt = int(input("Remain 1, return 2, or next 0?: "))
            if inopt == 2:
                break
