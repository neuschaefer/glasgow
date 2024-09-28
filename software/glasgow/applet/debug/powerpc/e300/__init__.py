# Ref: e300 Power Architecture™ Core Family Reference Manual
# Document Number: e300CORERM
# Accession: TODO

# Notes:
# * Official documentation is extremely sparse. In the words on an NXP
#   employee: "Information about JTAG/COP interface is proprietary of NXP and
#   is not available for general access. This interface uses internal
#   possibilities of processor core and this information is closed."
# * Different processor generations use largely incompatible debug protocols.
# * MPC83xx SoCs have three ways to access memory via JTAG:
#   * issuing load/store instructions
#   * core memory access (similar to GPR/FPR/etc. access)
#   * SAP (storage access port?), which works independently of the core, and
#     doesn't require halting
# * When feeding instructions into the e300 core via JTAG, you don't feed
#   PowerPC instructions as they appear in memory, you feed their *prefetched*
#   form, which is different in a few ways:
#   * The positions of RS/RA fields are swapped to align with RT/RA: The source
#     register is always at bit 11 and the target register at bit 6 (in IBM bit
#     numbers, which count the MSB as bit 0 and the LSB as bit 31).
#   * Some instructions with opcode 31 use a different encoding.
# * The processor context is fetched in several chunks:
#   1. Fixed-point/branch unit state (GPRs and PC/LR/CTR/etc.)
#   2. Floating-point unit state (FPRs)
#   3. Segment registers
#   4. Block address translation registers (IBATs/DBATs)
#   5. Miscellaneous system registers
#   * The first chunk is fetched when entering debug mode, the other are
#   fetched when necessary
#
# The following features/processors have been tested:
#
# | core    | SoC     | PVR ID   | run/step | breakp.| GPR/FPR | mem    |
# |---------|---------|----------|----------|--------|---------|--------|
# | e300c3  | MPC83xx | TODO     | TODO     | TODO   | TODO    | TODO   |


# TODO:
# - load code into icache
# - discover icache layout
# - clearer debug enter/exit
# - gdb interface
# - RE internal floating-point representation
# - high-level gateware interface:
#   - reg read  (type(4), index(12)) -> data
#   - reg write (type(4), index(12), data)
#     - exec instruction
#   - SAP read  (addr(32), width(8), repeat(24)) -> [(status, data)]
#   - SAP write (addr(32), width(8), repeat(24), data) -> status
# - test with multiple TAPs in the chain

import logging
import argparse
import asyncio
import struct
import enum
from dataclasses import dataclass
from glasgow.arch.jtag import *
from glasgow.arch.powerpc.e300 import *
from glasgow.arch.powerpc.e300.instr import *
from glasgow.arch.powerpc.jtag.e300 import *
from glasgow.database.jedec import *
from glasgow.database.powerpc import *
from glasgow.protocol.gdb_remote import GDBRemote
from glasgow.support.bits import *
from glasgow.support.arepl import AsyncInteractiveConsole
from glasgow.applet import GlasgowAppletError
from glasgow.applet.interface.jtag_probe import JTAGProbeApplet
from .mpc83xx import MPC83xx


__all__ = []


class DebugE300Error(GlasgowAppletError):
    pass


@dataclass
class DebugE300FPUContext:
    fpscr: int
    f0:  int; f1:  int; f2:  int; f3:  int; f4:  int; f5:  int; f6:  int; f7:  int
    f8:  int; f9:  int; f10: int; f11: int; f12: int; f13: int; f14: int; f15: int
    f16: int; f17: int; f18: int; f19: int; f20: int; f21: int; f22: int; f23: int
    f24: int; f25: int; f26: int; f27: int; f28: int; f29: int; f30: int; f31: int

    def __str__(self):
        lines = [f"fpscr: {self.fpscr:08x}"]
        for i in range(0, 32):
            name = f"f{i}"
            raw = self.__getattribute__(name)
            flo, = struct.unpack('<d', struct.pack('<Q', raw))
            lines.append(f"  {name+":":4} {raw:016x} ({flo})")
        return "\n".join(lines)

@dataclass
class DebugE300SegmentContext:
    sr0:    int; sr1:    int; sr2:    int; sr3:    int
    sr4:    int; sr5:    int; sr6:    int; sr7:    int
    sr8:    int; sr9:    int; sr10:   int; sr11:   int
    sr12:   int; sr13:   int; sr14:   int; sr15:   int

    def __str__(self):
        return "\n".join([
            f"  sr0:    {self.sr0 :08x}; sr1:    {self.sr0 :08x}; sr2:    {self.sr0 :08x}; sr3:    {self.sr0 :08x}",
            f"  sr4:    {self.sr4 :08x}; sr5:    {self.sr4 :08x}; sr6:    {self.sr4 :08x}; sr7:    {self.sr4 :08x}",
            f"  sr8:    {self.sr8 :08x}; sr9:    {self.sr8 :08x}; sr10:   {self.sr8 :08x}; sr11:   {self.sr8 :08x}",
            f"  sr12:   {self.sr12:08x}; sr13:   {self.sr12:08x}; sr14:   {self.sr12:08x}; sr15:   {self.sr12:08x}",
        ])

@dataclass
class DebugE300BATContext:
    ibat0u: int; ibat0l: int; ibat1u: int; ibat1l: int  # note: the core implements
    ibat2u: int; ibat2l: int; ibat3u: int; ibat3l: int  # 8 instead of 4 I/DBATs
    dbat0u: int; dbat0l: int; dbat1u: int; dbat1l: int  # but GDB doesn't care
    dbat2u: int; dbat2l: int; dbat3u: int; dbat3l: int

    def __str__(self):
        return "\n".join([
            f"  IBAT0U: {self.ibat0u:08x}; IBAT0L: {self.ibat0l:08x}; IBAT1U: {self.ibat1u:08x}; IBAT1L: {self.ibat1l:08x}",
            f"  IBAT2U: {self.ibat2u:08x}; IBAT2L: {self.ibat2l:08x}; IBAT3U: {self.ibat3u:08x}; IBAT3L: {self.ibat3l:08x}",
            f"  DBAT0U: {self.dbat0u:08x}; DBAT0L: {self.dbat0l:08x}; DBAT1U: {self.dbat1u:08x}; DBAT1L: {self.dbat1l:08x}",
            f"  DBAT2U: {self.dbat2u:08x}; DBAT2L: {self.dbat2l:08x}; DBAT3U: {self.dbat3u:08x}; DBAT3L: {self.dbat3l:08x}",
        ])

@dataclass
class DebugE300SystemContext:
    # PowerPC Operating Environment Architecture (OEA)
    sdr1:   int; asr:    int; dar:    int; dsisr:  int
    sprg0:  int; sprg1:  int; sprg2:  int; sprg3:  int
    srr0:   int; srr1:   int; tbl:    int; tbu:    int
    dec:    int; dabr:   int; ear:    int; pvr:    int
    # 603-family specific (included here to save round-trips)
    hid0:   int; hid1:   int; iabr:   int; dmiss:  int
    dcmp:   int; hash1:  int; hash2:  int; imuss:  int
    icmp:   int; rpa:    int

    def __str__(self):
        return "\n".join([
            f"  SDR1:  {self.sdr1 :08x};  ASR:   {self.asr  :08x};  DAR:   {self.dar  :08x};  DSISR: {self.dsisr:08x}",
            f"  SPRG0: {self.sprg0:08x};  SPRG1: {self.sprg1:08x};  SPRG2: {self.sprg2:08x};  SPRG3: {self.sprg3:08x}",
            f"  SRR0:  {self.srr0 :08x};  SRR1:  {self.srr1 :08x};  TBL:   {self.tbl  :08x};  TBU:   {self.tbu:08x}",
            f"  DEC:   {self.dec  :08x};  DABR:  {self.dabr :08x};  EAR:   {self.ear  :08x};  PVR:   {self.pvr:08x}",
            f"  HID0:  {self.hid0 :08x};  HID1:  {self.hid1 :08x};  IABR:  {self.iabr :08x};  DMISS: {self.dmiss:08x}",
            f"  DCMP:  {self.dcmp :08x};  HASH1: {self.hash1:08x};  HASH2: {self.hash2:08x};  IMUSS: {self.imuss:08x}",
            f"  ICMP:  {self.icmp :08x};  RPA:   {self.rpa  :08x}",
        ])

@dataclass
class DebugE300Context:
    pc:  int; lr:  int; msr: int; cr:  int; ctr: int; xer: int
    r0:  int; r1:  int; r2:  int; r3:  int; r4:  int; r5:  int; r6:  int; r7:  int
    r8:  int; r9:  int; r10: int; r11: int; r12: int; r13: int; r14: int; r15: int
    r16: int; r17: int; r18: int; r19: int; r20: int; r21: int; r22: int; r23: int
    r24: int; r25: int; r26: int; r27: int; r28: int; r29: int; r30: int; r31: int
    tr0: int; tr1: int; tr2: int; tr3: int # temporarily remapped GPRs (TGPR)
    fpu: DebugE300FPUContext = None
    seg: DebugE300SegmentContext = None
    bat: DebugE300BATContext = None
    oea: DebugE300SystemContext = None

    def __str__(self):
        def maybe(unit):
            return ((str(unit),) if unit else ()),
        s = "\n".join([
            f"  PC:  {self.pc :08x};  LR:  {self.lr   :08x};  MSR: {self.msr:08x};  CR:  {self.cr :08x}",
            f"  CTR: {self.ctr:08x};  XER: {self.xer  :08x}",
            f"  r0:  {self.r0 :08x};  r1:  {self.r1   :08x};  r2:  {self.r2 :08x};  r3:  {self.r3 :08x}",
            f"  r4:  {self.r4 :08x};  r5:  {self.r5   :08x};  r6:  {self.r6 :08x};  r7:  {self.r7 :08x}",
            f"  r8:  {self.r8 :08x};  r9:  {self.r9   :08x};  r10: {self.r10:08x};  r11: {self.r11:08x}",
            f"  r12: {self.r12:08x};  r13: {self.r13  :08x};  r14: {self.r14:08x};  r15: {self.r15:08x}",
            f"  r16: {self.r16:08x};  r17: {self.r17  :08x};  r18: {self.r18:08x};  r19: {self.r19:08x}",
            f"  r20: {self.r20:08x};  r21: {self.r21  :08x};  r22: {self.r22:08x};  r23: {self.r23:08x}",
            f"  r24: {self.r24:08x};  r25: {self.r25  :08x};  r26: {self.r26:08x};  r27: {self.r27:08x}",
            f"  r28: {self.r28:08x};  r29: {self.r29  :08x};  r30: {self.r30:08x};  r31: {self.r31:08x}",
        ])
        if self.fpu: s += "\n" + str(self.fpu)
        if self.seg: s += "\n" + str(self.seg)
        if self.bat: s += "\n" + str(self.bat)
        if self.oea: s += "\n" + str(self.oea)
        return s


class DebugE300Interface(GDBRemote):
    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self.soc     = None
        self.core    = None
        self._tgpr   = None

    async def connect(self):
        idcode_value, pvr = await self.identify()
        idcode = DR_IDCODE.from_int(idcode_value)
        mfg_name = jedec_mfg_name_from_bank_num(idcode.mfg_id >> 7,
                                                idcode.mfg_id & 0x7f) or "unknown"
        self._logger.info("JTAG ID: %08x (%s)", idcode_value, mfg_name)

        self.core = core = core_by_pvr(pvr)
        core_name = core.name if core else "unknown"
        self._logger.info("Core: %s (PVR=%08x)", core_name, pvr)

        if core.debug_style == None:
            raise DebugE300Error("Core has unknown debugging style")
        if core.debug_style != DebugStyle.e300:
            raise DebugE300Error(f"Processor has unsupported debugging style {Core.debug_style}")

        svr = await self.get_svr()
        soc = soc_by_svr(svr)
        svr_name = soc.name if soc else "unknown"
        self._logger.info("SoC: %s (SVR=%08x)", svr_name, svr)
        if svr_name.startswith("MPC83"):
            self.soc = MPC83xx(self, svr_name)

    def _log(self, message, *args):
        self._logger.log(self._level, message, *args)

    async def write_ir(self, new_ir):
        if isinstance(new_ir, int):
            new_ir = bits(new_ir, 8)
        old_ir = await self.lower.exchange_ir(new_ir)
        self._log("status %s, new IR %s", old_ir, new_ir)

    async def write_dr(self, dr):
        await self.lower.write_dr(dr)

    async def prime(self, value: bits):
        await self.write_ir(IR_PRIME)
        await self.lower.write_dr(value)

    async def set_hide(self, yes: int):
        if yes:
            await self.prime(bits('10000000'))
        else:
            await self.prime(bits('01000000'))

    async def get_pvr(self):
        await self.write_ir(IR_PVR)
        pvr = await self.lower.read_dr(32)
        return int(pvr)

    async def identify(self):
        await self.lower.test_reset()
        await self.lower.test_reset()
        idcode = await self.lower.read_dr(32)

        await self.set_hide(0) # necessary in order for PVR to be readable
        pvr = await self.get_pvr()
        return int(idcode), int(pvr)

    async def get_svr(self):
        await self.write_ir(IR_SVR)
        svr = await self.lower.read_dr(32)
        return int(svr)

    async def status(self) -> int:
        await self.write_ir(IR_NOP)
        status = await self.lower.exchange_ir(IR_NOP)
        return int(status)

    async def _halt(self):
        await self.lower.write_ir(IR_HALT)
        await self.lower.write_ir(IR_NOP)
        # TODO: verify outcome

    async def _run(self):
        await self.lower.write_ir(IR_RUN)
        await self.lower.write_ir(IR_NOP)
        # TODO: verify outcome

    # FIXME: doesn't work as such
    async def set_stop(self, yes):
        if yes:
            await self.prime(bits('00100000'))
        else:
            await self.prime(bits('01000000'))
        #assert (await self.status()).STOP == yes

    async def write_coreacc_ir(self, value):
        await self.write_ir(IR_COREACC_IR)
        await self.lower.write_dr(value)

    async def write_coreacc_dr(self, value):
        await self.write_ir(IR_COREACC_DR)
        await self.lower.write_dr(value)

    async def read_coreacc_dr(self, length):
        await self.write_ir(IR_COREACC_DR)
        await self.lower.read_dr(length) # dummy read (won't always have the right result)
        return await self.lower.read_dr(length)

    async def write_regsel(self, regsel):
        await self.write_coreacc_ir(COREACC_WRITE_REGSEL)
        await self.write_coreacc_dr(regsel.to_bits())

    async def read_regdata(self, length: int):
        await self.write_coreacc_ir(COREACC_READ_REGDATA)
        value = await self.read_coreacc_dr(length)
        return int(value)

    async def write_regdata(self, value: bits):
        await self.write_coreacc_ir(COREACC_WRITE_REGDATA)
        await self.write_coreacc_dr(value)

    async def _reg_read(self, ty: RegType, idx: int) -> int:
        await self.set_stop(0)
        regsel = REGSEL(major=ty.value, minor=idx, detail=0x202000, mode=1)
        await self.write_regsel(regsel)
        return await self.read_regdata(ty.dr_len())

    async def _reg_write(self, ty: RegType, idx: int, value: int):
        await self.set_stop(0)
        regsel = REGSEL(major=ty.value, minor=idx, detail=0x204000, mode=0)
        await self.write_regsel(regsel)
        await self.write_regdata(bits(value, ty.dr_len()))

    async def _get_pc(self):
        await self.write_ir(IR_PC)
        pc = await self.lower.read_dr(32)
        return int(pc)

    async def sap_cmd(self, addr: int, width: int, write: bool):
        match width:
            case  8: size = 0
            case 16: size = 1
            case 32: size = 2
            case 64: size = 3
            case _: raise DebugE300Error(f"Invalid width for SAP transfer: {width} bits")

        await self.set_stop(1) # TODO: only when necessary
        await self.write_ir(bits(IR_SAP))
        await self.write_ir(bits(IR_SAP | 1))
        command = SAPCommand(
            mode=write,
            size=size,
            magic1=0b00010000,
            addr=addr,
            magic2=1,
        )
        await self.write_dr(command.to_bits())

    async def sap_start(self):
        while status := int(await self.lower.exchange_ir(bits(IR_SAP | 2))):
            if status & 0xe0:
                raise DebugE300Error(f"Error starting SAP transfer: {status:02x}")
            if status & 0x18:
                break

    async def sap_complete(self):
        while status := await self.status():
            if status & 0xe0:
                raise DebugE300Error(f"Error completing SAP transfer: {status:02x}")
            if (status & 0x04) == 4:
                break

    async def sap_data(self, value: int, flag: int) -> SAPData:
        i = SAPData(value=value, flag=flag)
        o = await self.lower.exchange_dr(i.to_bits())
        return SAPData.from_bits(o)

    async def sap_exit(self):
        await self.write_ir(bits(IR_SAP))
        await self.set_stop(0)

    async def sap_read(self, addr: int, width: int) -> int:
        await self.sap_cmd(addr, width, 0)
        await self.sap_start()
        data = await self.sap_data(0, 0)
        await self.sap_exit()
        return data.value & ((1 << width) - 1)

    async def sap_write(self, addr: int, width: int, value: int):
        await self.sap_cmd(addr, width, 1)
        await self.lower.write_ir(bits(IR_SAP | 2))
        data = await self.sap_data(value << (64 - width), 1)
        await self.sap_complete()
        await self.sap_exit()

    async def _exec_insn(self, insn: int):
        await self.write_ir(bits('00001110'))
        regsel = REGSEL(major=RegType.MEM, minor=0, detail=0x18c800, mode=0)
        await self.write_regsel(regsel)
        await self.write_coreacc_ir(COREACC_WRITE_CPUINSN)
        await self.write_coreacc_dr(bits(insn, 32) + bits('10'))
        await self.lower.run_test_idle(1)
        await self.write_ir(bits('00001111'))

    async def tgpr(self) -> bool:
        if self._tgpr is None:
            # to find out whether MSR[TGPR] is set, we can't just read MSR
            # (we'd need a GPR for that), we have to change what the CPU
            # considers as r0 (or r1-r3), and see what actually changes
            gpr0 = await self.reg_read(RegType.GPR, 1)
            tgpr0 = await self.reg_read(RegType.GPR, 33)
            await self.exec_insn(ADDI(1, 1, 1))
            if await self.reg_read(RegType.GPR, 1) == gpr0 + 1:
                self._tgpr = False
            elif await self.reg_read(RegType.GPR, 33) == tgpr0 + 1:
                self._tgpr = True
            else:
                raise DebugE300Error(f"Failed to determine whether TGPRs are in use")
        return self._tgpr

    async def banked_gpr_read(self, r: int) -> int:
        if await self.tgpr():
            assert r <= 3
            return await self.reg_read(RegType.GPR, r + 32)
        else:
            return await self.reg_read(RegType.GPR, r)

    async def msr_read(self) -> MSR:
        await self.tgpr()
        await self.exec_insn(MFMSR(0))  # mfmsr r0
        return await self.banked_gpr_read(0)


    # GDB interface

    def gdb_log(self, level, message, *args):
        self._logger.log(level, "GDB: " + message, *args)

    def target_word_size(self):
        return 4

    def target_endianness(self):
        return self._endian

    def target_triple(self):
        return "powerpc-none-eabi"

    def target_features(self):
        return dict()

    def target_running(self) -> bool:
        return 42 # TODO

    async def target_stop(self):
        raise "i don't know how"

    async def target_continue(self):
        raise "i don't know how"

    async def target_single_step(self):
        raise "single step"

    async def target_detach(self):
        raise "detach"

    class GDBRegister(enum.IntEnum):
        # Note: This is based on GDB's powerpc-603.xml, and lacks e300-specific registers
        r0  =  0; r1  =  1; r2  =  2; r3  =  3; r4  =  4; r5  =  5; r6  =  6; r7  =  7
        r8  =  8; r9  =  9; r10 = 10; r11 = 11; r12 = 12; r13 = 13; r14 = 14; r15 = 15
        r16 = 16; r17 = 17; r18 = 18; r19 = 19; r20 = 20; r21 = 21; r22 = 22; r23 = 23
        r24 = 24; r25 = 25; r26 = 26; r27 = 27; r28 = 28; r29 = 29; r30 = 30; r31 = 31

        f0  = 32; f1  = 33; f2  = 34; f3  = 35; f4  = 36; f5  = 37; f6  = 38; f7  = 39
        f8  = 40; f9  = 41; f10 = 42; f11 = 43; f12 = 44; f13 = 45; f14 = 46; f15 = 47
        f16 = 48; f17 = 49; f18 = 50; f19 = 51; f20 = 52; f21 = 53; f22 = 54; f23 = 55
        f24 = 56; f25 = 57; f26 = 58; f27 = 59; f28 = 60; f29 = 61; f30 = 62; f31 = 63

        pc  = 64; msr = 65; cr  = 66; lr  = 67; ctr = 68; xer = 69; fpscr = 70

        sr0 = 71; sr1 = 72; sr2 = 73; sr3 = 74; sr4 = 75; sr5 = 76; sr6 = 77; sr7 = 78
        sr8 = 79; sr9 = 80; sr10= 81; sr11= 82; sr12= 83; sr13= 84; sr14= 85; sr15= 86

        pvr = 87

        ibat0u =  88; ibat0l =  89; ibat1u =  90; ibat1l =  91
        ibat2u =  92; ibat2l =  93; ibat3u =  94; ibat3l =  95
        dbat0u =  96; dbat0l =  97; dbat1u =  98; dbat1l =  99
        dbat2u = 100; dbat2l = 101; dbat3u = 102; dbat3l = 103

        sdr1   = 104; asr    = 105; dar    = 106; dsisr  = 107
        sprg0  = 108; sprg1  = 109; sprg2  = 110; sprg3  = 111
        srr0   = 112; srr1   = 113; tbl    = 114; tbu    = 115
        dec    = 116; dabr   = 117; ear    = 118
        hid0   = 119; hid1   = 120; iabr   = 121

        dmiss  = 124; dcmp   = 125; hash1  = 126; hash2  = 127
        imiss  = 128; icmp   = 129; rpa    = 130

    async def target_get_registers(self):
        assert self._is_halted
        reg = self.GDBRegister(number)
        return [
            getattr(self._context, self.GDBRegister(number).name)
            for number in range(max(self.GDBRegister) + 1)
        ]

    async def target_set_registers(self, values):
        raise "set regs"

    async def target_get_register(self, number):
        raise "get one reg"

    async def target_set_register(self, number, value):
        raise "set one reg"

    async def target_read_memory(self, address, length):
        raise "read mem"

    async def target_write_memory(self, address, data):
        raise "write mem"

    async def target_set_software_breakpt(self, address: int, kind: int):
        raise "set software bp"

    async def target_clear_software_breakpt(self, address: int, kind: int):
        raise "clr software bp"

    async def target_set_instr_breakpt(self, address: int, kind: int):
        raise "set instr bp"

    async def target_clear_instr_breakpt(self, address: int, kind: int):
        raise "clr instr bp"

class DebugE300Applet(JTAGProbeApplet):
    logger = logging.getLogger(__name__)
    help = "debug PowerPC processors via JTAG"
    description = """
    Debug PowerPC e300 processors via the JTAG/COP interface.
    These processors appear in the MPC83xx and MPC5121e series of SoCs.

    This applet has been tested on an MPC83xx SoC.
    """
    requires_tap = True
    requires_test_reset = True

    async def setup(self, args):
        await super().setup(args)
        self.e300_iface = DebugE300Interface(self.tap_iface, self.logger)

    @classmethod
    def add_run_arguments(cls, parser):
        pass

    async def run(self, args):
        await self.e300_iface.connect()
        await self.e300_iface._halt()

        await self.e300_iface._reg_write(RegType.GPR, 10, 0x00133700)
        for r in range(4):
            await self.e300_iface._reg_write(RegType.GPR, r, 0x7000_0000+r)

        await self.e300_iface._exec_insn(LIS(3, 0x1234))
        await self.e300_iface._exec_insn(ADDI(3, 3, 0x5678))
        await self.e300_iface._exec_insn(LI(1, 0xdddd))
        await self.e300_iface._exec_insn(LI(1, 0xdddd))

        for r in range(4):
            self.logger.info(" r%d: %08x", r, await self.e300_iface._reg_read(RegType.GPR, r))
        for r in range(4):
            self.logger.info("tr%d: %08x", r, await self.e300_iface._reg_read(RegType.GPR, r+32))
        for r in range(2):
            self.logger.info("f%d: %018x", r, await self.e300_iface._reg_read(RegType.FPR, r))

    async def repl(self, args):
        await self.e300_iface.connect()
        await super().repl(args)

    @classmethod
    def tests(cls):
        from . import test
        return test.DebugE300AppletTestCase
