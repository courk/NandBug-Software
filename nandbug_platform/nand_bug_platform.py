#!/usr/bin/env python3

from nmigen.build import *
from nmigen.vendor.lattice_ice40 import *
from nmigen_boards.resources import *

from .ice_ftdi import NandBugFtdiProgrammer


__all__ = ["NandBugPlatform"]


class NandBugPlatform(LatticeICE40Platform):
    device = "iCE40HX1K"
    package = "TQ144"
    default_clk = "clk60"
    resources = [
        Resource("clk60", 0, Pins("49", dir="i"),
                 Clock(60e6), Attrs(GLOBAL=True, IO_STANDARD="SB_LVCMOS")),

        *LEDResources(pins="10 11 12", attrs=Attrs(IO_STANDARD="SB_LVCMOS")),

        Resource("io_cpu", 0, Pins(
            "136 137 135 134 138 139 128 129", dir="io")),
        Resource("io_nand", 0, Pins("22 23 24 25 31 29 28 26", dir="io")),

        Resource("wp_cpu", 0, Pins("118", dir="i")),
        Resource("ale_cpu", 0, Pins("119", dir="i")),
        Resource("ce_cpu", 0, Pins("141", dir="i")),
        Resource("we_cpu", 0, Pins("142", dir="i")),
        Resource("re_cpu", 0, Pins("117", dir="i")),
        Resource("cle_cpu", 0, Pins("122", dir="i")),
        Resource("ryby_cpu", 0, Pins("143", dir="o")),

        Resource("wp_nand", 0, Pins("2", dir="o")),
        Resource("ale_nand", 0, Pins("8", dir="o")),
        Resource("ce_nand", 0, Pins("4", dir="o")),
        Resource("we_nand", 0, Pins("3", dir="o")),
        Resource("re_nand", 0, Pins("7", dir="o")),
        Resource("cle_nand", 0, Pins("9", dir="o")),
        Resource("ryby_nand", 0, Pins("1", dir="i"), Attrs(PULLUP=1)),

        Resource("cpu_detect", 0, Pins("144", dir="i")),

        Resource("ftdi_data", 0, Pins("62 61 60 58 56 52 50 48", dir="io")),
        Resource("ftdi_oe", 0, Pins("41", dir="o")),
        Resource("ftdi_siwua", 0, Pins("42", dir="o")),
        Resource("ftdi_wr", 0, Pins("43", dir="o")),
        Resource("ftdi_rd", 0, Pins("44", dir="o")),
        Resource("ftdi_txe", 0, Pins("45", dir="i")),
        Resource("ftdi_rxf", 0, Pins("47", dir="i")),
    ]

    connectors = []

    def toolchain_program(self, products, name):
        bitstream_data = products.get(f"{name}.bin")
        prog = NandBugFtdiProgrammer()
        prog.program(bitstream_data)
        prog.close()


if __name__ == "__main__":
    from nmigen_boards.test.blinky import *
    NandBugPlatform().build(Blinky(), do_program=True)
