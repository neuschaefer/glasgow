# Ref: Power ISA™ Version 2.07
# Accession: TODO

__all__ = [
    "ADDI", "ADDIS", "LI", "LIS", "ORI", "NOP", "XORI",
    "MFMSR", "MTMSR", "DCBZ", "ISYNC",
]

def ADDI(rt, ra, si):
    return 14 << 26 | rt << 21 | ra << 16 | si & 0xffff

def ADDIS(rt, ra, si):
    return 15 << 26 | rt << 21 | ra << 16 | si & 0xffff

def LI(rt, si):
    return ADDI(rt, 0, si)

def LIS(rt, si):
    return ADDIS(rt, 0, si)

def ORI(rs, ra, ui):
    return 24 << 26 | rs << 21 | ra << 16 | ui & 0xffff

def NOP():
    return ORI(0, 0, 0)

def XORI(rs, ra, ui):
    return 26 << 26 | rs << 21 | ra << 16 | ui & 0xffff

def MFMSR(rt):
    return 31 << 26 | rt << 21 | 83 << 1

def MTMSR(rt):
    return 31 << 26 | rt << 21 | 146 << 1

def DCBZ(ra, rb):
    return 31 << 26 | ra << 16 | rb << 11 | 1014 << 1

def DCBT(ra: int, rb: int, th: int) -> int:
    return 31 << 26 | th << 21 | ra << 16 | rb << 11 | 278 << 1

def ISYNC() -> int:
    return 19 << 26 | 150 << 1

