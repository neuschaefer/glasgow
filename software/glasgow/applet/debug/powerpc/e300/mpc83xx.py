import asyncio

from .....database.powerpc import *

class MPC83xx:
    def __init__(self, core, name: str):
        self.core = core
        self.name = name
        self.immr = 0xff40_0000 # internal memory-mapped registers base
        self.sysclk = 166_666_666
        self.local_access = LocalAccess(self, 0x0_0000)
        self.syscon = SysCon(self, 0x0_0100)
        self.gpio = GPIO(self, 0x0_0c00)
        self.uart1 = UART(self, 0x0_4500)
        self.uart2 = UART(self, 0x0_4600)
        self.elbc = ELBC(self, 0x0_5000)

class MMIOBase:
    def __init__(self, soc: MPC83xx, base: int):
        self.soc = soc
        self.base = base

    async def _read(self, addr: int, width: int):
        return await self.soc.core.sap_read(self.soc.immr + self.base + addr, width)

    async def _write(self, addr: int, width: int, value: int):
        return await self.soc.core.sap_write(self.soc.immr + self.base + addr, width, value)

    async def read8 (self, addr): return await self._read(addr,  8)
    async def read16(self, addr): return await self._read(addr, 16)
    async def read32(self, addr): return await self._read(addr, 32)

    async def write8 (self, addr, value): return await self._write(addr,  8, value)
    async def write16(self, addr, value): return await self._write(addr, 16, value)
    async def write32(self, addr, value): return await self._write(addr, 32, value)

class LocalAccess(MMIOBase):
    IMMRBAR     = 0x00
    ALTCBAR     = 0x08
    LBLAWBAR0   = 0x20
    LBLAWAR0    = 0x24
    LBLAWBAR1   = 0x28
    LBLAWAR1    = 0x2c

class SysCon(MMIOBase):
    SGPRL       = 0x00
    SGPRH       = 0x04

class GPIO(MMIOBase):
    GPDIR       = 0x00
    GPODR       = 0x04
    GPDAT       = 0x08
    GPIER       = 0x0c
    GPIMR       = 0x10
    GPICR       = 0x14

    async def get(self):
        return await self.read32(self.GPDAT)

class UART(MMIOBase):
    # this is mostly a normal 16550
    RBR = THR = 0
    IER = 1
    IIR = 2
    LCR = 3
    LCR_DLAB = 1 << 7
    MCR = 4
    LSR = 5
    LSR_DR   = 1 << 0
    LSR_THRE = 1 << 5
    MSR = 6
    SCR = 7
    DLL = 0 # divisor latch LSB/MSB, if LCR[DLAB] = 1
    DLM = 1

    async def set_div(self, div):
        lcr = await self.read8(self.LCR)
        await self.write8(self.LCR, lcr | self.LCR_DLAB)
        await self.write8(self.DLL, (div >> 0) & 0xff)
        await self.write8(self.DLM, (div >> 8) & 0xff)
        await self.write8(self.LCR, lcr)

    async def set_baud(self, baud):
        await self.write8(self.LCR, 0x03) # 8 bits
        div = self.soc.sysclk // (16 * baud)
        await self.set_div(div)

    async def tx(self, data: [int, bytes]):
        if type(data) == bytes:
            for c in data:
                await self.tx(c)
        else:
            while (await self.read8(self.LSR) & self.LSR_THRE) == 0:
                await asyncio.sleep(0.001)
            await self.write8(self.THR, data)

    async def rx(self, length=1) -> bytes:
        buf = bytearray()
        for _ in range(length):
            while (await self.read8(self.LSR) & self.LSR_DR) == 0:
                await asyncio.sleep(0.001)
            buf.append(await self.read8(self.RBR))
        return bytes(buf)

    async def rx_all(self) -> bytes:
        buf = bytearray()
        while (await self.read8(self.LSR) & self.LSR_DR):
            buf.append(await self.read8(self.RBR))
        return bytes(buf)

class ELBC(MMIOBase):
    pass
