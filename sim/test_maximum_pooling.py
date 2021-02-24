from dataclasses import dataclass
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import pytest

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
    clock_period = 10  # ns

    # prepare coroutines
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    await Timer(clock_period, units="ns")

    @dataclass
    class Testcase:
        input_window: List[List[int]]

        @property
        def input_data(self) -> list:
            return [concatenate_integers(ch) for ch in self.input_window]

        @property
        def output_data(self) -> list:
            return [int(any(ch)) for ch in self.input_window]

    window_size = dut.C_KERNEL_SIZE.value.integer ** 2
    channel = dut.C_CHANNEL.value.integer
    cases = (
        # all zeros
        Testcase([[0] * window_size] * channel),
        # all ones
        Testcase([[1] * window_size] * channel),
        # mixed
        Testcase([[randint(0, 1) for _ in range(window_size)] for _ in range(channel)]),
    )

    for case in cases:
        dut.isl_valid <= 1
        dut.islv_data <= case.input_data[0]
        await Timer(clock_period, units="ns")
        assert dut.osl_valid.value.integer == 1
        assert (
            dut.oslv_data.value.integer == case.output_data[0]
        ), f"{dut.oslv_data.value.integer} /= {case.output_data[0]}"


def test_maximum_pooling(record_waveform):
    generics = {
        "C_KERNEL_SIZE": 2,
        "C_CHANNEL": 1,
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
