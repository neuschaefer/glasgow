import unittest, os

from glasgow.applet import *
from glasgow.hardware.assembly import HardwareAssembly
from glasgow.arch.powerpc.jtag.e300 import *
from glasgow.arch.powerpc.e300.instr import *
from . import DebugE300Applet


class DebugE300AppletTestCase(GlasgowAppletV2TestCase, applet=DebugE300Applet):
    # DUT: e300c3 core, MPC8314E SoC, LANCOM NWAPP2 board
    #hardware_args = "-e big -V A=3.30,B=5.00 --tck A1 --tms A3 --tdi A2 --tdo A4 --trst A0"
    hardware_args = "-V3.3 --tck B0 --tms B1 --tdi B2 --tdo B3"

    @synthesis_test
    def test_build(self):
        self.assertBuilds()

    @unittest.skipUnless("DEBUG_PPC_E300_HARDWARE_TEST" in os.environ, "hardware unavailable")
    def test_on_hardware(self):
        self.run_on_hardware(self.do_test_on_hardware)

    async def do_test_on_hardware(self, iface):
        await iface.connect()
        await iface._halt()
        saved_gprs = [await iface._reg_read(RegType.GPR, i) for i in range(36)]

        await iface._exec_insn(LIS(0, 0x1234))
        await iface.lower.write_ir(IR_NOP)
        r0 = await iface._reg_read(RegType.GPR, 0)
        print(f"r0 = {r0:x}")
        assert r0 == 0x12340000

        for i, value in enumerate(saved_gprs):
            await self._reg_write(RegType.GPR, i, value)
        await iface._run()

    @async_test
    async def run_on_hardware(self, test_case, **test_kwargs):
        parsed_args = self._parse_args(self.hardware_args)
        assembly = HardwareAssembly()
        applet = self.applet_cls(assembly)
        applet.build(parsed_args)
        async with assembly:
            await applet.setup(parsed_args)
            await test_case(applet.e300_iface, **test_kwargs)
