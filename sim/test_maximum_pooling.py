from dataclasses import dataclass
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import pytest

from test_utils.cocotb_helpers import Tick
from test_utils.general import get_files, record_waveform


def concatenate_integers(integer_list: List[int], bitwidth=1) -> int:
    concatenated_integer = 0
    for value in integer_list:
        if value > 2 ** bitwidth:
            raise ValueError(f"Value {value} exeeds range.")
        concatenated_integer = (concatenated_integer << bitwidth) + value
    return concatenated_integer


@cocotb.test()
async def run_test(dut):
    @dataclass
    class Testcase:
        input_window: List[List[int]]

        @property
        def input_data(self) -> list:
            return concatenate_integers(
                [concatenate_integers(ch) for ch in self.input_window],
                bitwidth=len(self.input_window[0]),
            )

        @property
        def output_data(self) -> list:
            return concatenate_integers(
                [int(any(ch)) for ch in zip(*self.input_window)]
            )

    window_size = dut.C_KERNEL_SIZE.value.integer ** 2
    channel = dut.C_CHANNEL.value.integer
    cases = (
        # all zeros
        Testcase([[0] * channel] * window_size),
        # all ones
        Testcase([[1] * channel] * window_size),
        # mixed
        Testcase([[randint(0, 1) for _ in range(channel)] for _ in range(window_size)]),
    )

    # prepare coroutines
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    await tick.wait()

    for case in cases:
        print(case.input_window)
        print(case.output_data)
        dut.isl_valid <= 1
        dut.islv_data <= case.input_data
        await tick.wait()
        assert dut.osl_valid.value.integer == 1
        assert (
            dut.oslv_data.value.integer == case.output_data
        ), f"{bin(dut.oslv_data.value.integer)[2:]} /= {bin(case.output_data)[2:]}"


@pytest.mark.parametrize("kernel_size", (2, 3))
@pytest.mark.parametrize("channel", (1, 6))
def test_maximum_pooling(record_waveform, kernel_size, channel):
    generics = {
        "C_KERNEL_SIZE": kernel_size,
        "C_CHANNEL": channel,
    }
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="maximum_pooling",
        module="test_maximum_pooling",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
        sim_args=["--wave=maximum_pooling.ghw"] if record_waveform else None,
    )
