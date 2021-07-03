# https://github.com/nmigen/nmigen-boards/blob/master/nmigen_boards/ulx3s.py
# https://github.com/lawrie/blackicemx_nmigen_examples/blob/main/uart/uart_test.py

import nmigen as nm
from nmigen_boards.ulx3s import ULX3S_85F_Platform
from nmigen_stdio.serial import AsyncSerial

from src.maximum_pooling import MaximumPooling


if __name__ == "__main__":
    platform = ULX3S_85F_Platform()

    divisor = int(25e6 // 115.2e3)
    uart_pins = platform.request("uart")

    m = nm.Module()
    m.submodules.serial = serial = AsyncSerial(divisor=divisor, pins=uart_pins)
    m.d.comb += [
        serial.tx.data.eq(serial.rx.data),
        serial.rx.ack.eq(1),
        serial.tx.ack.eq(serial.rx.rdy),
    ]
    platform.build(m, do_program=True)
