from dataclasses import dataclass
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run

from test_utils.cocotb_helpers import Tick
from test_utils.general import get_files


@cocotb.test()
async def run_test(dut):
    height = dut.C_INPUT_HEIGHT.value.integer
    width = dut.C_INPUT_WIDTH.value.integer

    # initialize the test
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    dut.isl_valid <= 0
    await tick.wait()

    for _ in range(height * width):
        dut.isl_valid <= 1
        dut.islv_data <= randint(0, 255)
        await tick.wait()
        dut.isl_valid <= 0
        await tick.wait()
        await tick.wait()

    await tick.wait_multiple(height * width)
    # assert (
    #     dut.oslv_data.value.integer == case.output_data
    # ), f"{dut.oslv_data.value.integer} /= {case.output_data}"


def test_bnn():
    generics = {}
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="bnn",
        module="test_bnn",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
    )
