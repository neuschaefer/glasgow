# Ref: e300 Power Architecture™ Core Family Reference Manual
# Document Number: e300CORERM
# Accession: TODO

import enum

from ....support.bits import *
from ....support.bitstruct import *

__all__ = [
    # IR values
    "IR_HALT", "IR_RUN", "IR_SAP", "IR_PC", "IR_PVR", "IR_SVR",
    "IR_COREACC_IR", "IR_COREACC_DR", "IR_PRIME", "IR_NOP", "IR_BYPASS",

    # STATUS values
    "STATUS",

    # COREACC_IR values
    "COREACC_WRITE_REGSEL", "COREACC_READ_REGDATA",
    "COREACC_WRITE_REGDATA", "COREACC_WRITE_CPUINSN",

    # Core registers
    "REGSEL", "RegType",

    # SAP registers
    "SAPCommand", "SAPData",
]


# IR values
#
# Generally, the LSB indicates whether a flag is set or cleared.
# Instructions take effect after leaving Update-IR, either towards
# Run-Test-Idle or towards Capture-DR/IR.
#
# Reading IR produces a status.

IR_HALT       = bits("00001100") # 0c
IR_RUN        = bits("00001101") # 0d
IR_SAP        = bits("00100000") # 20
IR_PC         = bits("00110001") # 31
IR_PVR        = bits("01111100") # 7c
IR_SVR        = bits("01111110") # 7e
IR_COREACC_IR = bits("11011110") # de
IR_COREACC_DR = bits("11011111") # df
IR_PRIME      = bits('11111010') # fa
IR_NOP        = bits("11111110") # fe
IR_BYPASS     = bits("11111111") # ff


STATUS = bitstruct("STATUS", 8, [
    (None,          2),
    ("STOP",        1),
    (None,          4),
    ("DEBUG",       1),
])

# COREACC_IR values

COREACC_WRITE_REGSEL  = bits("0101")
COREACC_READ_REGDATA  = bits("1010")
COREACC_WRITE_REGDATA = bits("1011")
COREACC_WRITE_CPUINSN = bits("1111")


REGSEL = bitstruct("REGSEL", 40, [
    ("mode",        2),
    ("minor",      12),
    ("detail",     22),
    ("major",       4),
])


class RegType(enum.IntEnum):
    MEM    =  0 # Memory access
    GPR    =  2 # General Purpose Registers and Temporarily remapped GPRs (TGPR)
    FPR    =  3 # Floating Point Registers
    ITAG   =  4 # Instruction cache tags(?)
    DTAG   =  5 # Data cache tags(?)
    ICACHE =  6 # Instruction cache entries
    DCACHE =  7 # Data cache entries
    ISEG   =  8 # Instruction segment registers
    DSEG   =  9 # Data segment registers
    ITLB   = 10 # Instruction Translation Lookaside buffer
    DTLB   = 11 # Data Translation Lookaside buffer
    IBAT   = 12 # Instruction Block Address Translation
    DBAT   = 13 # Data Block Address Translation

    def dr_len(self) -> [int, None]:
        match self:
            case RegType.GPR:       return 32
            case RegType.FPR:       return 70
            case RegType.ITAG:      return 32
            case RegType.DTAG:      return 32
            case RegType.ICACHE:    return 72
            case RegType.DCACHE:    return 72
            case RegType.ISEG:      return 32
            case RegType.DSEG:      return 32
            case RegType.ITLB:      return 32
            case RegType.DTLB:      return 32
            case RegType.IBAT:      return 32
            case RegType.DBAT:      return 32

# SAP

SAPCommand = bitstruct("SAPCommand", 65, [
    ("magic2",     13),
    ("addr",       36),
    ("magic1",      8),
    ("size",        4),
    ("mode",        4),
])

SAPData = bitstruct("SAPData", 65, [
    ("flag",        1),
    ("value",      64),
])
