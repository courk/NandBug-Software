#!/usr/bin/env python3

from nmigen import *

from .modules import *


class Passthrough(Elaboratable):

    def __init__(self):
        pass

    def elaborate(self, platform):

        m = Module()

        #
        # Passthrough
        #
        io_cpu = platform.request("io_cpu", 0)
        io_nand = platform.request("io_nand", 0)

        cpu_detect = platform.request("cpu_detect")

        # src -> dst
        ctrl_signals = {}
        for signal in ["wp", "ale", "ce", "we", "re", "cle"]:
            ctrl_signals[signal] = (platform.request(f"{signal}_cpu"),
                                    platform.request(f"{signal}_nand"))

        ctrl_signals["ryby"] = (platform.request("ryby_nand"),
                                platform.request("ryby_cpu"))

        for signal in ctrl_signals:
            src, dst = ctrl_signals[signal]
            m.d.comb += dst.eq(src)

        m.d.comb += io_cpu.o.eq(io_nand.i)
        m.d.comb += io_nand.o.eq(io_cpu.i)

        with m.If(((ctrl_signals["we"][0] == 0) | (io_nand.oe == 1))
                  & (ctrl_signals["re"][0] == 1)):
            m.d.comb += io_nand.oe.eq(1)

        with m.If(((ctrl_signals["re"][0] == 0) | (io_nand.oe == 0))
                  & (ctrl_signals["we"][0] == 1)):
            m.d.comb += io_nand.oe.eq(0)

        m.d.comb += io_cpu.oe.eq(~io_nand.oe)

        #
        # Status LED Module
        #
        blink_led = platform.request("led", 0)
        blinker = Blinker(blink_led, 0.5)
        m.submodules += blinker

        act_led = platform.request("led", 1)
        m.d.comb += act_led.eq(~io_nand.oe)

        cpu_led = platform.request("led", 2)
        m.d.comb += cpu_led.eq(~cpu_detect)

        return m
