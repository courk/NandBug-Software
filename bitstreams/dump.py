#!/usr/bin/env python3

from nmigen import *

from .modules import *


class Dump(Elaboratable):

    def __init__(self):
        pass

    def elaborate(self, platform):

        m = Module()

        #
        # Status LED Module
        #
        blink_led = platform.request("led", 0)
        blinker = Blinker(blink_led, 0.5)
        m.submodules += blinker

        #
        # FTDI FIFO Module
        #
        ftdi_fifo = FtdiFifo()
        m.submodules += ftdi_fifo

        #
        # NAND FSM Module
        #
        nand_fsm = NandFSM()
        m.submodules += nand_fsm

        #
        # Internal signals
        #
        page_address = Array([Signal(8) for _ in range(3)])
        column_address = Array([Signal(8) for _ in range(2)])
        address = Array([Signal(8) for _ in range(5)])

        # Multi-purpose counter, large enough
        # to count bytes in a page
        counter = Signal(range(0, 2177))

        # Wire address to column_adrress + page_address
        m.d.comb += Cat(*address).eq(Cat(*column_address, *page_address))

        #
        # Dump flash state machine
        #
        with m.FSM() as fsm:

            #
            # RESET the NAND Flash to a clean state
            #

            with m.State("RESET"):
                # Send RESET command (0xFF)
                with m.If(~nand_fsm.busy):
                    m.d.sync += nand_fsm.i_data.eq(0xFF)
                    m.d.sync += nand_fsm.send_cmd.eq(1)
                    m.d.sync += counter.eq(0)
                    m.next = "WAIT_RESET"

            with m.State("WAIT_RESET"):
                m.d.sync += nand_fsm.send_cmd.eq(0)
                with m.If(counter == 500):
                    m.next = "CMD1"
                    m.d.sync += counter.eq(0)
                with m.Else():
                    m.d.sync += counter.eq(counter + 1)

            #
            # Read each page
            # the 0x30 command is used
            #

            with m.State("CMD1"):
                # Start by sending the 0x00 CMD
                with m.If(~nand_fsm.busy):
                    m.d.sync += nand_fsm.i_data.eq(0x00)
                    m.d.sync += nand_fsm.send_cmd.eq(1)
                    m.d.sync += counter.eq(0)
                    m.next = "ADDR"

            with m.State("ADDR"):
                # Send the 5 bytes of the address
                m.d.sync += nand_fsm.send_cmd.eq(0)
                with m.If(~nand_fsm.busy):
                    with m.If(counter < 5):
                        m.d.sync += nand_fsm.i_data.eq(address[counter])
                        m.d.sync += nand_fsm.send_address.eq(1)
                        m.d.sync += counter.eq(counter+1)
                        m.next = "ADDR"
                    with m.Else():
                        m.d.sync += nand_fsm.send_address.eq(0)
                        m.next = "CMD2"

            with m.State("CMD2"):
                # Finish with the 0x30 CMD
                with m.If(~nand_fsm.busy):
                    m.d.sync += nand_fsm.i_data.eq(0x30)
                    m.d.sync += nand_fsm.send_cmd.eq(1)
                    m.d.sync += counter.eq(0)
                    m.next = "WAIT"

            with m.State("WAIT"):
                m.d.sync += nand_fsm.send_cmd.eq(0)
                with m.If(counter == 500):
                    m.next = "READ"
                    m.d.sync += counter.eq(0)
                with m.Else():
                    m.d.sync += counter.eq(counter + 1)

            #
            # Read the NAND Bus
            # and fill the FTDI FIFO
            #

            with m.State("READ"):
                # Request a READ from the NAND FSM
                m.d.sync += ftdi_fifo.tx_buffer.w_en.eq(0)
                with m.If(~nand_fsm.busy):
                    m.d.sync += ftdi_fifo.tx_buffer.w_en.eq(0)
                    m.d.sync += nand_fsm.read.eq(1)
                    m.next = "END_READ"

            with m.State("END_READ"):
                m.d.sync += nand_fsm.read.eq(0)
                m.next = "FIFO"

            with m.State("FIFO"):
                # Send the read data to the FTDI FIFO
                with m.If(counter < 2176):
                    with m.If(~nand_fsm.busy):
                        with m.If(ftdi_fifo.tx_buffer.w_rdy):
                            m.d.sync += ftdi_fifo.tx_buffer.w_en.eq(1)
                            m.d.sync += counter.eq(counter+1)
                            m.next = "READ"
                with m.Else():
                    m.d.sync += ftdi_fifo.tx_buffer.w_en.eq(0)
                    m.d.sync += counter.eq(0)
                    m.next = "INC_ADDR"

            #
            # Increment address, loop back
            #

            with m.State("INC_ADDR"):
                # If needed, increment the page address and loop back
                with m.If(Cat(*page_address) < 64 * 2048 - 1):
                    m.d.sync += Cat(*page_address).eq(Cat(*page_address) + 1)
                    m.next = "CMD1"
                with m.Else():
                    m.next = "IDLE"

            with m.State("IDLE"):
                pass

        # FTDI FIFO input always connected to NAND FSM output
        m.d.comb += ftdi_fifo.tx_buffer.w_data.eq(nand_fsm.o_data)

        return m
