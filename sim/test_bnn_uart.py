from dataclasses import dataclass
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge
from cocotb_test.simulator import run
import numpy as np

from test_utils.cocotb_helpers import Tick
from test_utils.general import get_files


@cocotb.test()
async def run_test(dut):
    height = dut.i_bnn.C_INPUT_HEIGHT.value.integer
    width = dut.i_bnn.C_INPUT_WIDTH.value.integer
    classes = dut.i_bnn.C_OUTPUT_CHANNEL.value.integer

    # input_image = np.random.randint(0, 255, (1, height, width, 1), dtype=np.uint8)
    input_image = np.full((1, height, width, 1), 0, dtype=np.uint8)

    # initialize the test
    clock_period = 40  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.clk_25mhz, clock_period, units="ns").start())

    dut.ftdi_txd <= 1
    dut.btn <= 127
    await tick.wait()
    dut.btn <= 0

    freq = dut.C_QUARTZ_FREQ.value.integer  # Hz
    baudrate = 115200  # words / s
    cycles_per_bit = freq // baudrate

    for pixel in input_image.flat:
        # start bit
        dut.ftdi_txd <= 0
        await tick.wait_multiple(cycles_per_bit)

        # data bits
        for bit_index in range(8):
            dut.ftdi_txd <= int(bin(pixel)[2:].zfill(8)[bit_index])
            await tick.wait_multiple(cycles_per_bit)

        # stop bit
        dut.ftdi_txd <= 1
        await tick.wait_multiple(cycles_per_bit)

    await FallingEdge(dut.ftdi_rxd)
    await tick.wait_multiple(cycles_per_bit * 12 * classes)

    # TODO: Add automated checks.


def test_bnn_uart():
    generics = {"C_QUARTZ_FREQ": 115200 * 4}  # 4 cycles per bit for faster simulation
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        )
        + get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src" / "interface",
            "*.vhd",
        ),
        toplevel="bnn_uart",
        module="test_bnn_uart",
        compile_args=["--work=bnn_lib", "--std=08"],
        parameters=generics,
    )
