#!/usr/bin/env python3

from nmigen import *

from halo import Halo

from nandbug_platform import NandBugPlatform, NandBugFtdiFIFO
import bitstreams


if __name__ == "__main__":

    spinner = Halo(
        text="Configuring bitstream for passthrough", spinner="dots")
    spinner.start()

    p = NandBugPlatform()
    p.build(bitstreams.Passthrough(), do_program=True,
            nextpnr_opts="--ignore-loops"  # Unfortunatly needed
            )

    fifo = NandBugFtdiFIFO()  # Just needed to enable 50MHz clock

    spinner.succeed()
