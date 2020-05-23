#!/usr/bin/env python3

from enum import Enum

from nmigen import *
from nmigen.back import pysim


class WriteType(Enum):
    CMD = 0
    ADDR = 1
    DATA = 2


class NandFSM(Elaboratable):
    """
    NAND FSM Implementation, used to drive a NAND Flash bus

    Attributes
    ----------
    busy : Signal
        FSM is busy when equals to '1'
    i_data : Signal
        Data to write on the bus
    o_data : Signal
        Data read on the bus
    send_cmd : Signal
        Set to '1' if data to be sent is a command
    send_address : Signal
        Set to '1' if data to be sent is an address
    send_data : Signal
        Set to '1' if data to be sent is data
    read_data : Signal
        Set to '1' to request a data read
    """

    def __init__(self):

        # Control signals
        self.busy = Signal(reset=1)
        self.i_data = Signal(8)
        self.o_data = Signal(8)
        self.send_cmd = Signal()
        self.send_address = Signal()
        self.send_data = Signal()
        self.read = Signal()

    def elaborate(self, platform):

        m = Module()

        # External signals
        io_nand = platform.request("io_nand", 0)
        self.io_o = io_nand.o
        self.io_i = io_nand.i
        self.io_oe = io_nand.oe

        self.we = platform.request("we_nand", 0)
        self.re = platform.request("re_nand", 0)
        self.cle = platform.request("cle_nand", 0)
        self.ale = platform.request("ale_nand", 0)
        self.ce = platform.request("ce_nand", 0)
        self.ryby = platform.request("ryby_nand", 0)

        # Internal signals
        i_data_buff = Signal(8)
        write_type = Signal(2)

        # Keep the NAND activated
        m.d.comb += self.ce.eq(0)

        #
        # Main FSM
        #
        with m.FSM() as fsm:

            with m.State("IDLE"):
                with m.If(self.ryby):  # Make sure the NAND Flash is ready

                    # Check which command to run
                    with m.If(self.send_data):
                        m.d.sync += [write_type.eq(WriteType.DATA),
                                     self.ale.eq(0),
                                     self.cle.eq(0)]
                        m.next = "WRITE"

                    with m.Elif(self.send_cmd):
                        m.d.sync += [write_type.eq(WriteType.CMD),
                                     self.ale.eq(0)]
                        m.next = "WRITE"

                    with m.Elif(self.send_address):
                        m.d.sync += [write_type.eq(WriteType.ADDR),
                                     self.cle.eq(0)]
                        m.next = "WRITE"

                    with m.Elif(self.read):
                        m.d.sync += [self.cle.eq(0),
                                     self.ale.eq(0)]
                        m.next = "READ"

                    with m.Else():
                        m.d.sync += [self.cle.eq(0), self.ale.eq(0)]

                with m.Else():
                    m.d.sync += [self.cle.eq(0), self.ale.eq(0)]

                # When IDLE, keep we and re high & keep busy up
                # to date
                m.d.comb += self.busy.eq(self.ryby == 0)
                m.d.sync += [self.we.eq(1), self.re.eq(1)]

                # Sample input data
                m.d.sync += i_data_buff.eq(self.i_data)

            with m.State("WRITE"):
                # Write data to the bus
                m.d.sync += [self.io_o.eq(i_data_buff),
                             self.we.eq(0),
                             self.io_oe.eq(1)]

                # Set cle or ale if necessary
                with m.Switch(write_type):
                    with m.Case(WriteType.CMD):
                        m.d.sync += self.cle.eq(1)
                    with m.Case(WriteType.ADDR):
                        m.d.sync += self.ale.eq(1)

                m.next = "WRITE_HOLD"

            with m.State("WRITE_HOLD"):
                m.d.sync += [self.we.eq(1)]
                m.next = "IDLE"

            with m.State("READ"):
                m.d.sync += [self.re.eq(0),
                             self.io_oe.eq(0)]
                m.next = "READ_SAMPLE"

            with m.State("READ_SAMPLE"):
                m.d.sync += [self.o_data.eq(self.io_i),
                             self.re.eq(1)]
                m.next = "IDLE"

        return m
