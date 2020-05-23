#!/usr/bin/env python3

from nmigen import *

from .modules import *


class Program(Elaboratable):

    def __init__(self):
        pass

    def elaborate(self, platform):

        m = Module()

        #
        # NAND FSM Module
        #
        nand_fsm = NandFSM()
        m.submodules += nand_fsm

        #
        # Status LED
        #
        blink_led = platform.request("led", 0)
        blinker = Blinker(blink_led, 0.5)
        m.submodules += blinker

        busy_led = platform.request("led", 1)
        m.d.comb += busy_led.eq(~nand_fsm.busy)

        #
        # FTDI FIFO Module
        #
        ftdi_fifo = FtdiFifo()
        m.submodules += ftdi_fifo

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
        # Writer state machine
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
                    m.next = "READ_ADDR"
                    m.d.sync += counter.eq(0)
                with m.Else():
                    m.d.sync += counter.eq(counter + 1)

            #
            # Read address from FTDI FIFO
            #

            with m.State("READ_ADDR"):
                with m.If(counter != 3):
                    with m.If(ftdi_fifo.rx_buffer.r_rdy):
                        m.d.sync += page_address[counter].eq(
                            ftdi_fifo.rx_buffer.r_data)
                        m.d.comb += ftdi_fifo.rx_buffer.r_en.eq(1)
                        m.d.sync += counter.eq(counter+1)
                with m.Else():
                    m.next = "CMD1"

            #
            # Send the page program command
            #

            with m.State("CMD1"):
                with m.If(~nand_fsm.busy):
                    # Start by sending the 0x80 CMD
                    m.d.sync += nand_fsm.i_data.eq(0x80)
                    m.d.sync += nand_fsm.send_cmd.eq(1)
                    m.d.sync += counter.eq(0)
                    m.next = "ADDR"

            with m.State("ADDR"):
                # Send the 5 bytes of the address
                m.d.sync += nand_fsm.send_cmd.eq(0)
                with m.If(~nand_fsm.busy):
                    with m.If(counter != 5):
                        m.d.sync += nand_fsm.i_data.eq(address[counter])
                        m.d.sync += nand_fsm.send_address.eq(1)
                        m.d.sync += counter.eq(counter+1)
                    with m.Else():
                        m.d.sync += nand_fsm.send_address.eq(0)
                        m.d.sync += counter.eq(0)
                        m.next = "DATA"

            #
            # Move data from the FTDI FIFO to the NAND Bus
            #

            with m.State("DATA"):
                with m.If(~nand_fsm.busy):
                    with m.If(counter != 0x880):
                        with m.If(ftdi_fifo.rx_buffer.r_rdy):
                            m.d.sync += nand_fsm.i_data.eq(
                                ftdi_fifo.rx_buffer.r_data)
                            m.d.comb += ftdi_fifo.rx_buffer.r_en.eq(1)
                            m.d.sync += nand_fsm.send_data.eq(1)
                            m.d.sync += counter.eq(counter+1)
                        with m.Else():
                            m.d.sync += nand_fsm.send_data.eq(0)
                    with m.Else():
                        m.d.sync += nand_fsm.send_data.eq(0)
                        m.next = "CMD2"

            #
            # Terminate the prgram page command
            #

            with m.State("CMD2"):
                # Finish with the 0x10 CMD
                with m.If(~nand_fsm.busy):
                    m.d.sync += nand_fsm.i_data.eq(0x10)
                    m.d.sync += nand_fsm.send_cmd.eq(1)
                    m.d.sync += counter.eq(0)
                    m.next = "SEND_ADDR"

            #
            # Send back the address to FTDI FIFO
            # (acknowledge the erase command)
            # and loop back
            #

            with m.State("SEND_ADDR"):
                m.d.sync += nand_fsm.send_cmd.eq(0)
                with m.If(counter != 3):
                    with m.If(ftdi_fifo.tx_buffer.w_rdy):
                        m.d.comb += ftdi_fifo.tx_buffer.w_data.eq(
                            page_address[counter])
                        m.d.comb += ftdi_fifo.tx_buffer.w_en.eq(1)
                        m.d.sync += counter.eq(counter+1)
                with m.Else():
                    m.d.sync += counter.eq(0)
                    m.next = "READ_ADDR"

        return m
