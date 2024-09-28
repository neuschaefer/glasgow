# Ref: e300 Power Architecture™ Core Family Reference Manual
# Number: e300CORERM
# Accession: TODO

# Ref: PowerPC™ e500 Core Family Reference Manual
# Number: E500CORERM
# Accession: TODO

# Ref: e500mc Core Reference Manual
# Number: e500mcRM
# Accession: TODO

# Ref: e600 PowerPC™ Core Reference Manual
# Number: E600CORERM
# Accession: TODO

import enum

from collections import namedtuple

__all__ = [
    "PPCCore", "DebugStyle", "cores", "core_by_pvr",
    "PPCSoC", "socs", "soc_by_svr",
]

# the Processor Version Register (PVR) identifies the CPU core

PPCCore = namedtuple("PPCCore", ("pvr", "pvr_mask", "name", "debug_style"))

class DebugStyle(enum.Enum):
    # e300c1 is special because it doesn't seem to have IR_PC
    e300c1 = 1

    # Most e300 variants
    e300 = 2

cores = [
    #         PVR          (mask)       name                 debug style (None=unknown)
    PPCCore(0x0006_0010, 0xffff_0000, "MPC603e (PID6)",    None),
    PPCCore(0x0007_0100, 0xffff_f000, "MPC603e (PID7v)",   None),
    PPCCore(0x0007_1201, 0xffff_f000, "MPC603r (PID7)",    None),
    PPCCore(0x0081_0011, 0xffff_0000, "G2 (original)",     None),
    PPCCore(0x8081_1010, 0xffff_0000, "G2",                None),
    PPCCore(0x8082_1010, 0xffff_0000, "G2_LE",             None),
    PPCCore(0x8083_0010, 0xffff_0000, "e300c1",            DebugStyle.e300c1),
    PPCCore(0x8084_0010, 0xffff_0000, "e300c2",            DebugStyle.e300),
    PPCCore(0x8085_0010, 0xffff_0000, "e300c3",            DebugStyle.e300),
    PPCCore(0x8086_0010, 0xffff_f000, "e300c4 (MPC5121e)", DebugStyle.e300),
    PPCCore(0x8086_1010, 0xffff_f000, "e300c4 (MPC83xx)",  DebugStyle.e300),
    PPCCore(0x8020_0010, 0xffff_00f0, "e500v1 (SoC 1.0)",  None),
    PPCCore(0x8020_0020, 0xffff_00f0, "e500v2 (SoC 1.1)",  None),
    PPCCore(0x8021_0010, 0xffff_0000, "e500v2 (SoC 2.0)",  None),
    PPCCore(0x8043_0010, 0xffff_00f0, "e500mc (rev 1)",    None),
    PPCCore(0x8043_0020, 0xffff_00f0, "e500mc (rev 2)",    None),
    PPCCore(0x8043_0030, 0xffff_00f0, "e500mc (rev 3)",    None),
    PPCCore(0x8004_0010, 0xffff_ffff, "e600 (MPC86xx)",    None),
    PPCCore(0x8004_0100, 0xffff_ffff, "e600 (MPC74xx)",    None),
]

def core_by_pvr(pvr: int):
    assert(type(pvr) == int)
    for core in cores:
        if pvr & core.pvr_mask == core.pvr & core.pvr_mask:
            return core


# the System Version Register (SVR), if available, identifies the SoC

PPCSoC = namedtuple("PPCSoC", ("svr", "svr_mask", "name"))

socs = [
    # Ref: MPC8315E PowerQUICC II Pro Integrated Host Processor Family Reference Manual
    # Number: MPC8315ERM
    PPCSoC(0x80b4_0010, 0xffff_0000, "MPC8315E"),
    PPCSoC(0x80b5_0010, 0xffff_0000, "MPC8315"),
    PPCSoC(0x80b6_0010, 0xffff_0000, "MPC8314E"),
    PPCSoC(0x80b7_0010, 0xffff_0000, "MPC8314"),
]

def soc_by_svr(svr: int):
    assert(type(svr) == int)
    for soc in socs:
        if svr & soc.svr_mask == soc.svr & soc.svr_mask:
            return soc
