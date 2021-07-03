"""Connect the BNN core to the other components."""

import nmigen as nm
from nmigen_stdio.serial import AsyncSerial


class Interface(nm.Elaboratable):
    def __init__(self):
        pass

    def elaborate(self, platform):
        divisor = int(25e6 // 115.2e3)
        uart_pins = platform.request("uart")

        m = nm.Module()
        m.submodules.serial = serial = AsyncSerial(divisor=divisor, pins=uart_pins)
        m.d.comb += [
            serial.tx.data.eq(serial.rx.data),
            serial.rx.ack.eq(1),
            serial.tx.ack.eq(serial.rx.rdy),
        ]

        return m
