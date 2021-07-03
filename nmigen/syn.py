# https://github.com/nmigen/nmigen-boards/blob/master/nmigen_boards/ulx3s.py
# https://github.com/lawrie/blackicemx_nmigen_examples/blob/main/uart/uart_test.py

import nmigen as nm
from nmigen_boards.ulx3s import ULX3S_85F_Platform

from src.interface import Interface


if __name__ == "__main__":
    platform = ULX3S_85F_Platform()

    platform.build(Interface(), do_program=True)
