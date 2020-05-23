# The NandBug Software

## Overview

This software is part of the *NandBug* Project. Hardware files are available [here](https://github.com/courk/NandBug-Hardware).

*NandBug* is a small FPGA based board that I used in my [Running Custom Code on a Google Home Mini](https://courk.cc/running-custom-code-google-home-mini-part1) project.

The goal of *NandBug* is to make the NAND Flash of a *Google Home Mini* *In-System Programmable*. 

You can refer to the article for more background information and details.

## Dumping the Flash

`NandBugDumper.py` is used to dump the NAND Flash content.

```text
./NandBugDumper.py -h
usage: NandBugDumper.py [-h] filename

Dump the nand flash content

positional arguments:
  filename    output filename

optional arguments:
  -h, --help  show this help message and exit
```

This script will:

- Generate a *Dump* bitstream and upload it to the FPGA.
- Receive the NAND Flash data and write it to the output `filename`.

## Programming the Flash

`NandBugPatcher.py` is used to alter the NAND Flash content.

```text
./NandBugPatcher.py -h
usage: NandBugPatcher.py [-h] [--last-dump LAST_DUMP] filename

Patch the nand flash content

positional arguments:
  filename              input filename

optional arguments:
  -h, --help            show this help message and exit
  --last-dump LAST_DUMP
                        use this dump instead of reading the flash content
```

This script will:

- Generate a *Dump* bitstream and upload it to the FPGA.
- Receive the NAND Flash data and compare it to the content of `filename`.
- Generate a list of blocks to erase and pages to program. This step can optionally be skipped if a `LAST_DUMP` file is provided.
- Generate a *Erase Blocks* bitstream & upload it to the FPGA.
- Send a list of blocks to erase to the FPGA.
- Generate a *Program Pages* bitstream & upload it to the FPGA.
- Send the pages addresses and data to the FPGA.

## Passthrough

The `NandBugPassthrough.py` script will simply generate a *Passthrough* bitstream and upload it to the FPGA.

Effectively, this makes the NAND Flash directly connected to the *Google Home Mini*.

## Technical Details

- [nMigen](https://github.com/nmigen/nmigen) is used to generate bitstreams uploaded in the FPGA of *NandBug*.
- [pylibftdi](https://pylibftdi.readthedocs.io/en/0.15.0/) is used for configuring and communicating with *NandBug*.
- [bchlib](https://pypi.org/project/bchlib/) is used to perform error correction.
- For now, the code is very specific to the NAND Flash and *SoC* used by the *Google Home Mini* (memory size and layout, *ECC* scheme, ...) and shouldn't be used with anything else without a couple of modifications.
- Please note it's my first time using *nMigen* in a real project, so the code is likely suboptimal. A known issue is the absence of reliable testbenches for the HDL modules.
