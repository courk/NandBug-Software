#!/usr/bin/env python3

from nmigen import *
from nmigen.lib.fifo import AsyncFIFO, SyncFIFO


class FtdiFifo(Elaboratable):
    """
    FTDI FIFO Interface, to be used with a FTDI in Sync FIFO Mode

    Attributes
    ----------
    tx_buffer : SyncFIFO
        FIFO containing data to be written to the FTDI
    rx_buffer : SyncFIFO
        FIFO containing data read from the FTDI
    """

    def __init__(self):
        self.tx_buffer = SyncFIFO(width=8, depth=16)
        self.rx_buffer = SyncFIFO(width=8, depth=16)

    def elaborate(self, platform):

        m = Module()

        # Register tx and rx fifo as submodules
        m.submodules += self.tx_buffer
        m.submodules += self.rx_buffer

        # External signals
        txe = platform.request("ftdi_txe")
        wr = platform.request("ftdi_wr")
        rxf = platform.request("ftdi_rxf")
        oe = platform.request("ftdi_oe")
        rd = platform.request("ftdi_rd")
        data = platform.request("ftdi_data")

        write_operation = Signal()
        oe_ready = Signal()

        # Set data bus direction
        with m.If(write_operation):
            m.d.comb += [data.oe.eq(1), oe.eq(1)]
            m.d.sync += oe_ready.eq(0)  # Add one delay cycle
        with m.Else():
            m.d.comb += [data.oe.eq(0), oe.eq(0)]
            m.d.sync += oe_ready.eq(1)  # Add one delay cycle

        # Manage "write to FTDI" operations
        with m.If((txe == 0) & (self.tx_buffer.r_rdy)):
            m.d.comb += [write_operation.eq(1),
                         wr.eq(0),
                         self.tx_buffer.r_en.eq(1),
                         data.o.eq(self.tx_buffer.r_data)]
        with m.Else():
            m.d.comb += [wr.eq(1),
                         self.tx_buffer.r_en.eq(0)]

        # Manage "Read from FTDI" operations
        with m.If((rxf == 0) & (self.rx_buffer.w_rdy)
                  & (~write_operation) & oe_ready):
            m.d.comb += [rd.eq(0),
                         self.rx_buffer.w_en.eq(1),
                         self.rx_buffer.w_data.eq(data.i)]
        with m.Else():
            m.d.comb += [rd.eq(1),
                         self.rx_buffer.w_en.eq(0)]

        return m
