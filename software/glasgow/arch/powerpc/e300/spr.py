# Ref: e300 Power Architecture™ Core Family Reference Manual
# Number: e300CORERM
# Accession: TODO

import enum

__all__ = [ "SPR", "PMR" ]

class SPR(enum.IntEnum):
    # Exception/link/counter registers
    XER     =    1
    LR      =    8
    CTR     =    9

    # System/processor version register
    SVR     =  286
    PVR     =  287

    # Hardware Implementation Dependent registers
    HID0    = 1008
    HID1    = 1009
    HID2    = 1011

    # Instruction/Data Block Address Translation
    IBAT0U  =  528
    IBAT0L  =  529
    IBAT1U  =  530
    IBAT1L  =  531
    IBAT2U  =  532
    IBAT2L  =  533
    IBAT3U  =  534
    IBAT3L  =  535
    IBAT4U  =  560
    IBAT4L  =  561
    IBAT5U  =  562
    IBAT5L  =  563
    IBAT6U  =  564
    IBAT6L  =  565
    IBAT7U  =  566
    IBAT7L  =  567
    DBAT0U  =  536
    DBAT0L  =  537
    DBAT1U  =  538
    DBAT1L  =  539
    DBAT2U  =  540
    DBAT2L  =  541
    DBAT3U  =  542
    DBAT3L  =  543
    DBAT4U  =  568
    DBAT4L  =  569
    DBAT5U  =  570
    DBAT5L  =  571
    DBAT6U  =  572
    DBAT6L  =  573
    DBAT7U  =  574
    DBAT7L  =  575

    # SPRs for general use
    SPRG0   =  272
    SPRG1   =  273
    SPRG2   =  274
    SPRG3   =  275
    SPRG4   =  276
    SPRG5   =  277
    SPRG6   =  278
    SPRG7   =  279

    # Critical Interrupt Registers
    CSRR0   =   58
    CSRR1   =   59

    # Memory Base Address Register
    MBAR    =  311

    # Data Storage Interrupt Status Register
    DSISR   =   18

    # Save and Restore Registers
    SRR0    =   26
    SRR1    =   27

    # Data Address Register
    DAR     =   19

    # Instruction/Data Access Breakpoint Registers
    IABR    = 1010
    IABR2   = 1018
    DABR    = 1013
    DABR2   =  317

    # Insturction/Data Address Breakpoint Control registers
    IBCR    =  309
    DBCR    =  310

    # Software Table Search Registers
    DMISS   =  976
    DCMP    =  977
    HASH1   =  978
    HASH2   =  979
    IMISS   =  980
    ICMP    =  981
    RPA     =  982

    # Storage Description Register 1
    SDR1    =   25

    # Decrementer
    DEC     =   22

    # Time Base Facility (for reading)
    TBL_rd  =  268
    TBU_rd  =  269

    # Time Base Facility (for writing)
    TBL_wr  =  284
    TBU_wr  =  285

    @property
    def lo(self) -> int:
        return self.value & 31

    @property
    def hi(self) -> int:
        return (self.value >> 5) & 31

    def is_bat(self) -> bool:
        return (self.value in range(self.IBAT0U.value, self.DBAT3L.value) or
                self.value in range(self.IBAT4U.value, self.DBAT7L.value))


class PMR(enum.IntEnum):
    # Supervisor Level Performance Monitor Registers
    PMC0    =   16
    PMC1    =   17
    PMC2    =   18
    PMC3    =   19
    PMLCa0  =  144
    PMLCa1  =  145
    PMLCa2  =  146
    PMLCa3  =  147
    PMGC0   =  400

    # User Level Performance Monitor Registers (read-only)
    UPMC0   =    0
    UPMC1   =    1
    UPMC2   =    2
    UPMC3   =    3
    UPMLCa0 =  128
    UPMLCa1 =  129
    UPMLCa2 =  130
    UPMLCa3 =  131
    UPMGC0  =  384

    @property
    def lo(self):
        return self.value & 31

    @property
    def hi(self):
        return (self.value >> 5) & 31
