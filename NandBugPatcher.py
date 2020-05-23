#!/usr/bin/env python3

import argparse
import tempfile
import struct

from halo import Halo

import bchlib

from nandbug_platform import NandBugPlatform, NandBugFtdiFIFO
import bitstreams


def nibble_swap(data):
    result = bytearray()
    for c in data:
        result.append(((c & 0x0F) << 4) | ((c & 0xF0) >> 4))
    return result


def ecc_fix(infilename, outfilename):
    data = open(infilename, "rb").read()

    bch = bchlib.BCH(0x8003, 48)

    f = open(outfilename, "wb")

    total_flips = 0
    for offset in range(len(data)//0x880):
        page = data[offset*0x880:(offset+1)*0x880]
        page_data = nibble_swap(page[:0x820])
        page_ecc = nibble_swap(page[0x820:-6])
        page_padding = page[-6:]
        flips = bch.decode_inplace(page_data, page_ecc)
        if flips > 0:
            total_flips += flips
        f.write(nibble_swap(page_data) + nibble_swap(page_ecc) + page_padding)

    f.close()

    return total_flips


def get_modified_blocks(before_filename, after_filename):
    before_data = open(before_filename, "rb").read()
    after_data = open(after_filename, "rb").read()

    modified_blocks = []

    for page_index in range(0, len(before_data)//0x880):
        before_page = before_data[page_index*0x880:(page_index+1)*0x880]
        after_page = after_data[page_index*0x880:(page_index+1)*0x880]
        if before_page != after_page:
            block_index = page_index // 64
            if block_index not in modified_blocks:
                modified_blocks.append(block_index)

    return modified_blocks


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Patch the nand flash content")
    parser.add_argument("filename", help="input filename")
    parser.add_argument(
        "--last-dump",
        help="use this dump instead of reading the flash content")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        if not args.last_dump:
            last_dump = f"{tmpdir}/dump.bin"
            spinner = Halo(
                text="Configuring bitstream for dumping", spinner="dots")
            spinner.start()

            p = NandBugPlatform()
            p.build(bitstreams.Dump(), do_program=True)

            spinner.succeed()

            spinner = Halo(
                text=f"Dumping flash to {last_dump} (0 %)", spinner="dots")
            spinner.start()

            fifo = NandBugFtdiFIFO()

            f = open(last_dump, "wb")
            total_size = 0

            while total_size != 0x11000000:
                data = fifo.read(256)
                if data:
                    f.write(data)
                    total_size += len(data)
                    if total_size % (128 * 1024):
                        percent = int(total_size / 0x11000000 * 100)
                        spinner.text = f"Dumping flash to {last_dump} " + \
                                       f"({percent} %)"

            f.close()
            fifo.close()
            spinner.succeed()

            spinner = Halo(text="Performing error correction", spinner="dots")
            spinner.start()

            corrected_filename = f"{tmpdir}/dump_fixed.bin"

            flips = ecc_fix(last_dump, corrected_filename)
            spinner.succeed()

            print(f"Corrected {flips} errors")

            last_dump = corrected_filename

        else:
            last_dump = args.last_dump

        modified_blocks = get_modified_blocks(last_dump, args.filename)

    if len(modified_blocks) == 0:
        print("Nothing to patch")
        exit(0)

    print(f"{len(modified_blocks)} blocks will be modified")

    spinner = Halo(
        text="Configuring bitstream for erasing blocks", spinner="dots")
    spinner.start()

    p = NandBugPlatform()
    p.build(bitstreams.Erase(), do_program=True)

    spinner.succeed()

    spinner = Halo(text=f"Erasing blocks", spinner="dots")
    spinner.start()

    fifo = NandBugFtdiFIFO()

    for block_index in modified_blocks:
        addr = struct.pack("<I", block_index * 64)[:3]
        fifo.write(addr)
        while fifo.read(3) != addr:
            pass

    fifo.close()

    spinner.succeed()

    spinner = Halo(
        text="Configuring bitstream for programming pages", spinner="dots")
    spinner.start()

    p = NandBugPlatform()
    p.build(bitstreams.Program(), do_program=True)

    fifo = NandBugFtdiFIFO()

    spinner.succeed()

    spinner = Halo(text="Writing pages (0 %)", spinner="dots")
    spinner.start()

    data = open(args.filename, "rb").read()
    for i, block_index in enumerate(modified_blocks):
        for page_index in range(block_index*64, (block_index+1)*64):
            addr = struct.pack("<I", page_index)[:3]
            page_data = data[page_index*0x880:(page_index+1)*0x880]
            fifo.write(addr)
            for offset in range(0, 0x880//64):
                fifo.write(page_data[offset*64:(offset+1)*64])
            while fifo.read(3) != addr:
                pass
        percent = int((i+1) / len(modified_blocks) * 100.0)
        spinner.text = f"Writing pages ({percent} %)"

    spinner.succeed()
