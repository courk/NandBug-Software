#!/usr/bin/env python3

import time
import pylibftdi as ftdi


__all__ = ["NandBugFtdiProgrammer", "NandBugFtdiFIFO"]


class NandBugFtdiProgrammer(object):
    """
    Configure a iCE40 FPGA in SPI slave mode
    based on iCE40ProgrammingandConfiguration.pdf
    """

    SPI_SCK = (1 << 0)
    SPI_SI = (1 << 1)
    SPI_SO = (1 << 2)
    SPI_SS = (1 << 3)
    CRESET_B = (1 << 4)
    CDONE = (1 << 5)

    def __init__(self):
        deva = ftdi.Device(interface_select=ftdi.INTERFACE_A)
        deva.ftdi_fn.ftdi_set_bitmode(0x00, 0x00)  # reset
        deva.close()

        self.dev = ftdi.Device(interface_select=ftdi.INTERFACE_B)
        self.dev.ftdi_fn.ftdi_set_bitmode(0x00, 0x00)  # reset
        self.dev.ftdi_fn.ftdi_set_bitmode(0x03, 0x02)  # MPSSE mode
        self.set_spi_clock(500e3)

    def set_spi_clock(self, hz):
        div = int((12000000 / (hz * 2)) - 1)
        self.ft_write((0x86, div % 256, div // 256))

    def ft_write(self, data):
        s = bytes(data)
        ret = self.dev.write(s)
        return ret

    def ft_write_cmd_bytes(self, cmd, data):
        n = len(data) - 1
        self.ft_write([cmd, n % 256, n // 256] + list(data))

    def ft_read(self, nbytes):
        s = self.dev.read(nbytes)
        return s

    def program(self, bitstream):
        # Set SPI_SCK, SPI_SI, CRESET_B and SPI_SS as output low
        output_mask = self.SPI_SCK | self.SPI_SI | self.CRESET_B | self.SPI_SS
        self.ft_write((0x80, self.SPI_SCK, output_mask))

        # Wait for 200us
        time.sleep(200e-6)

        # CRESET_B = 1
        self.ft_write((0x80, self.CRESET_B, output_mask))

        # Wait for 1200us
        time.sleep(1200e-6)

        # SPI_SS = 1
        self.ft_write((0x80, self.SPI_SS | self.CRESET_B, output_mask))

        # send dummy byte
        self.ft_write_cmd_bytes(0x11, b"\xff")

        # SPI_SS = 0
        self.ft_write((0x80, self.CRESET_B, output_mask))

        # Send bitsteam
        self.ft_write_cmd_bytes(0x11, bitstream)

        # SPI_SS = 1
        self.ft_write((0x80, self.SPI_SS | self.CRESET_B, output_mask))

        # Wait for 100 clocks
        self.ft_write_cmd_bytes(0x11, b"\xff" * 7)

        # Make sure CDONE=1
        self.ft_write((0x81,))
        ret = b""
        while not len(ret):
            ret = self.ft_read(1)
        if not ret[0] & self.CDONE:
            raise Exception("CDONE=0")

        # at least 49 more clocks
        self.ft_write_cmd_bytes(0x11, b"\xff" * 7)

    def close(self):
        self.dev.close()


class NandBugFtdiFIFO(object):
    """
    Communicate with a FT2232H in Sync FIFO Mode
    """

    def __init__(self):
        self.dev = ftdi.Device(interface_select=ftdi.INTERFACE_A)
        self.dev.ftdi_fn.ftdi_set_latency_timer(8)
        self.dev.ftdi_fn.ftdi_set_bitmode(0x00, 0x00)  # reset
        self.dev.ftdi_fn.ftdi_set_bitmode(0x02, 0x40)  # Sync FIFO mode

    def read(self, n=1):
        return self.dev.read(n)

    def write(self, data):
        return self.dev.write(data)

    def close(self):
        self.dev.close()
