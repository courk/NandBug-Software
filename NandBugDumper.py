#!/usr/bin/env python3

import argparse

from halo import Halo

from nandbug_platform import NandBugPlatform, NandBugFtdiFIFO
import bitstreams


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Dump the nand flash content")
    parser.add_argument("filename", help="output filename")
    args = parser.parse_args()

    spinner = Halo(text="Configuring bitstream for dumping", spinner="dots")
    spinner.start()

    p = NandBugPlatform()
    p.build(bitstreams.Dump(), do_program=True)

    spinner.succeed()

    spinner = Halo(
        text=f"Dumping flash to {args.filename} (0 %)", spinner="dots")
    spinner.start()

    fifo = NandBugFtdiFIFO()

    f = open(args.filename, "wb")
    total_size = 0

    while total_size != 0x11000000:

        data = fifo.read(256)

        if data:
            f.write(data)
            total_size += len(data)

            if total_size % (128 * 1024):
                percent = int(total_size / 0x11000000 * 100)
                spinner.text = f"Dumping flash to {args.filename} " + \
                               f"({percent} %)"

    f.close()
    spinner.succeed()
