# Instructions in e300-compatible prefetched format. Some of them are
# unmodified PowerPC instructions, many are not.
#
# * The positions of RS/RA fields are swapped to align with RT/RA: The source
#   register is always at bit 11 and the target register at bit 6 (in IBM bit
#   numbers, which count the MSB as bit 0 and the LSB as bit 31).
# * Some instructions with primary opcode 31 use a different primary opcode.
#   This is possible because several opcodes are not use by the PowerISA spec.
# * The encoding of MFSPR/MTSPR depends on the SPR
#
# Unmodified instructions are imported from powerpc.instr and re-exported,
# modified instructions are defined here.

from glasgow.arch.powerpc.instr import ADDI, ADDIS, LI, LIS, NOP, ISYNC, DCBT
from glasgow.arch.powerpc.e300.spr import SPR, PMR
import enum

__all__ = [
    "ADDI", "ADDIS", "LI", "LIS", "NOP", "ISYNC", "DCBT",
    "MTMSR", "MTMSR",
]

def MFMSR(rt: int):
    return 6 << 26 | rt << 21 | 83 << 1

def MTMSR(rs: int):
    return 6 << 26 | rs << 16 | 146 << 1

def MTSPR(rs: int, spr: SPR):
    if spr.is_bat() or spr is SPR.XER:
        # alternate opcode, swap RA and low half of SPR
        return  2 << 26 | spr.lo << 21 | rs << 16 | spr.hi << 11 | 467 << 1
    else:
        # swap RA and low half of SPR
        return 31 << 26 | spr.lo << 21 | rs << 16 | spr.hi << 11 | 467 << 1

def MFSPR(rt: int, spr: SPR):
    if spr.is_bat():
        # alternate opcode
        return  2 << 26 | rt << 21 | spr.lo << 16 | spr.hi << 11 | 339 << 1
    else:
        # standard format
        return 31 << 26 | rt << 21 | spr.lo << 16 | spr.hi << 11 | 339 << 1

def DCBF(ra: int, rb: int, l: int) -> int:
    return 2 << 26 | l << 21 | ra << 16 | rb << 11 | 86 << 1

def DCBZ(ra: int, rb: int) -> int:
    return 2 << 26 | ra << 16 | rb << 11 | 1014 << 1

def DCBST(ra: int, rb: int, l: int) -> int:
    return 2 << 26 | ra << 16 | rb << 11 | 54 << 1

def SYNC(l: int, e: int) -> int:
    return 2 << 26 | l << 21 | e << 16 | 598 << 1

def MTSR(rs: int, sr: int) -> int:
    return 2 << 26 | sr << 21 | rs << 16 | 210 << 1

def MFSR(rt: int, sr: int) -> int:
    return 2 << 26 | rt << 21 | sr << 16 | 595 << 1

def MTPMR(rs: int, pmr: PMR) -> int:
    return 31 << 26 | pmr.lo << 21 | rs << 16 | pmr.hi << 11 | 462 << 1

def MFPMR(rs: int, pmr: PMR) -> int:
    return 31 << 26 | rt << 21 | pmr.lo << 16 | pmr.hi << 11 | 334 << 1

def MFFS(frt: int) -> int:
    return 4 << 26 | frt << 21 | 583 << 1

def MTFSF(frb: int, flm=None, w=0):
    if flm is None:
        return 4 << 26 | frb << 11 | 711 << 1
    else:
        return 4 << 26 | 1 << 25 | flm << 17 | w << 16 | frb << 11 | 711 << 1
