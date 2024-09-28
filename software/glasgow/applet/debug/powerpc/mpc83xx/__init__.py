# TODO: remove


## glasgow run jtag-probe -V 3.3 --port B --pin-tck 2 --pin-tms 3 --pin-tdi 1 --pin-tdo 0 --pin-trst 4 scan
# I: g.device.hardware: generating bitstream ID b129291257e4c5d286905716952dec7c
# I: g.cli: running handler for applet 'jtag-probe'
# I: g.applet.interface.jtag_probe: port(s) B voltage set to 3.3 V
# I: g.applet.interface.jtag_probe: shifted 32-bit DR=<10111000000001101101000101100100>
# I: g.applet.interface.jtag_probe: shifted 8-bit IR=<10000100>
# I: g.applet.interface.jtag_probe: discovered 1 TAPs
# I: g.applet.interface.jtag_probe: TAP #0: IR[8] IDCODE=0x268b601d
# I: g.applet.interface.jtag_probe: manufacturer=0x00e (Freescale (Motorola)) part=0x68b6 version=0x2

from .....support.bits import *
from .....support.bitstruct import *
from ....interface.jtag_probe import JTAGProbeApplet
import enum
import logging


class MPC83xxDebugInterface:
    IR_ENTER      = bits("00001100")
    IR_EXIT       = bits("00001101")
    IR_PC         = bits("00110001")
    IR_IDCODE     = bits("01111100")
    IR_COREACC_IR = bits("11011110")
    IR_COREACC_DR = bits("11011111")
    IR_STATUS     = bits("11111110")
    IR_BYPASS     = bits("11111111")

    COREACC_WRITE_REGSEL  = bits("0101")
    COREACC_READ_REGDATA  = bits("1010")
    COREACC_WRITE_REGDATA = bits("1010")
    COREACC_WRITE_CPUINSN = bits("1111")

    IR_STOP_SEQ = [
        bits("10100111"),
        bits("10001001"),
        bits("10001010"),
        bits("00000110"),
        bits("10000010"),
        bits("10001110"),
    ]

    IR_INIT_SEQ = [
        bits("10100111"),
        bits("00001111"),
        bits("10001011"),
        bits("10001001"),
        bits("10001110"),
        bits("10000010"),
        bits("00001100"),
        bits("10000000"),
        bits("01000100"),
        bits("00000111"),
        bits("01000101"),
        bits("10000001"),
    ]

    def __init__(self, interface, logger):
        self.lower   = interface
        self._logger = logger
        self.rev_ir  = True

    async def discover(self):
        await self.lower.test_reset()
        print(await self.lower.read_dr(32))
        await self.lower.write_ir(self.IR_IDCODE)
        print(await self.lower.read_dr(32))
        await self.lower.write_ir(self.IR_IDCODE.reversed())
        print(await self.lower.read_dr(32))

    def _log(self, message, *args):
        self._logger.log(self._level, "MPC83xx: " + message, *args)

    async def write_ir(self, ir):
        if self.rev_ir: ir = ir.reversed()
        await self.lower.write_ir(ir)

    async def exchange_ir(self, ir):
        if self.rev_ir:
            return (await self.lower.exchange_ir(ir.reversed())).reversed()
        else:
            return await self.lower.exchange_ir(ir)

    async def read_ir(self):
        ir = await self.lower.read_ir()
        return ir.reversed() if self.rev_ir else ir

    async def perform_ir_sequence(self, seq):
        for ir in seq:
            await self.write_ir(ir)

    async def get_status(self):
        await self.write_ir(self.IR_STATUS)
        return await self.exchange_ir(self.IR_STATUS)

    def stop(self):
        pass

    async def set_coreacc_ir(self, ir):
        assert len(ir) == 4
        await self.write_ir(self.IR_COREACC_IR)
        await self.write_dr(ir)

    async def set_coreacc_dr(self, dr):
        await self.write_ir(self.IR_COREACC_DR)
        await self.write_dr(dr)

    async def get_coreacc_dr(self, length):
        await self.write_ir(self.IR_COREACC_DR)
        await self.read_dr(length)

    async def set_regsel(self, regsel):
        assert len(regsel) == 40
        await self.set_coreacc_ir(self.COREACC_WRITE_REGSEL)
        await self.set_coreacc_dr(regsel)

    async def set_regdata(self, regdata):
        await self.set_coreacc_ir(self.COREACC_WRITE_REGDATA)
        await self.set_coreacc_dr(regdata)

    async def get_regdata(self, length):
        await self.set_coreacc_ir(self.COREACC_READ_REGDATA)
        return await self.get_coreacc_dr(length)


class DebugMPC83xxApplet(JTAGProbeApplet):
    preview = True
    logger = logging.getLogger(__name__)
    help = "debug NXP MPC83xx processors via JTAG/COP"
    description = """
    TODO
    """

    @classmethod
    def add_run_arguments(cls, parser, access):
        super().add_run_arguments(parser, access)
        super().add_run_tap_arguments(parser)

    async def run(self, device, args):
        tap_iface = await self.run_tap(DebugMPC83xxApplet, device, args)
        return MPC83xxDebugInterface(tap_iface, self.logger)
