# Ref: e300 Power Architecture™ Core Family Reference Manual
# e300CORERM

from glasgow.support.bitstruct import *

__all__ = [
    "MSR"
]

# Machine State Register layout
MSR = bitstruct("MSR", 32, [
    ("LE",          1), # Little-endian mode enable
    ("RI",          1), # Recoverable interrupt
    ("PMM",         1), # Performance monitor mark bit
    (None,          1),
    ("DR",          1), # Data address translation
    ("IR",          1), # Instruction address translation
    ("IP",          1), # Interrupt prefix
    ("CE",          1), # Critical interrupt enable
    ("FE1",         1), # Floating-point interrupt mode 1
    ("BE",          1), # Branch trace enable
    ("SE",          1), # Single-step trace enable
    ("FE0",         1), # Floating-point interrupt mode 0
    ("ME",          1), # Machine check enable
    ("FP",          1), # Floating-point available
    ("PR",          1), # Privilege level
    ("EE",          1), # External interrupt enable
    ("ILE",         1), # Interrupt little-endian mode
    ("TGPR",        1), # Temporary GPR remapping
    ("POW",         1), # Power management enable
    (None,         13),
])
