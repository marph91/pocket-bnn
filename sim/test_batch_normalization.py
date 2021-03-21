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
    @dataclass
    class Testcase:
        input_data: int
        input_threshold: int

        @property
        def output_data(self) -> int:
            return int(self.input_data > self.input_threshold)

    cases = (
        Testcase(1, 3),
        Testcase(2, 2),
        Testcase(0, 0),
        Testcase(1, 0),
        Testcase(randint(0, 10), randint(0, 10)),
    )

    # initialize the test
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    dut.isl_valid <= 0
    await tick.wait()

    for case in cases:
        dut.isl_valid <= 1
        dut.islv_data <= case.input_data
        dut.islv_threshold <= case.input_threshold
        await tick.wait()
        assert (
            dut.oslv_data.value.integer == case.output_data
        ), f"{dut.oslv_data.value.integer} /= {case.output_data}"


def test_batch_normalization():
    generics = {}
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="batch_normalization",
        module="test_batch_normalization",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
    )
