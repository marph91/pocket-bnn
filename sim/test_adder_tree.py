from dataclasses import dataclass
from math import ceil, log2
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import pytest

from test_utils.cocotb_helpers import ImageMonitor, Tick
from test_utils.general import (
    concatenate_integers,
    from_fixedint,
    to_fixedint,
    get_files,
)


@cocotb.test()
async def run_test(dut):
    input_count = int(dut.C_INPUT_COUNT.value.integer)
    input_bitwidth = int(dut.C_INPUT_BITWIDTH.value.integer)
    is_unsigned = bool(dut.C_UNSIGNED.value.integer)
    output_bitwidth = int(dut.C_OUTPUT_BITWIDTH.value.integer)

    @dataclass
    class Testcase:
        input_data: List[int]

        @property
        def input_data_fixedint(self) -> int:
            input_data_fixedint = [
                to_fixedint(datum, input_bitwidth, is_unsigned)
                for datum in self.input_data
            ]
            return concatenate_integers(input_data_fixedint, bitwidth=input_bitwidth)

        @property
        def output_data(self) -> int:
            return sum(self.input_data)

    input_range = (
        (0, 2 ** input_bitwidth - 1)
        if is_unsigned
        else (-(2 ** (input_bitwidth - 1)), 2 ** (input_bitwidth - 1) - 1)
    )
    cases = (
        # minimum values
        Testcase([input_range[0]] * input_count),
        # maximum values
        Testcase([input_range[1]] * input_count),
        # random values
        Testcase([randint(*input_range) for _ in range(input_count)]),
    )

    # initialize the test
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    output_mon = ImageMonitor(
        "output", dut.oslv_data, dut.osl_valid, dut.isl_clk, 1, output_bitwidth,
    )
    dut.isl_valid <= 0
    await tick.wait()

    for case in cases:
        dut.isl_valid <= 1
        dut.islv_data <= case.input_data_fixedint
        await tick.wait()
    dut.isl_valid <= 0

    await tick.wait_multiple(ceil(log2(input_count)) + 1)  # number of stages
    assert dut.osl_valid.value.integer == 0

    for case, output in zip(cases, output_mon.output):
        output_int = from_fixedint(output, output_bitwidth, is_unsigned)
        assert output_int == case.output_data, f"{output_int} /= {case.output_data}"


@pytest.mark.parametrize("is_unsigned", (0, 1))
@pytest.mark.parametrize("input_bitwidth", (1, 4, 8))
def test_adder_tree(is_unsigned, input_bitwidth):
    generics = {
        "C_INPUT_COUNT": randint(1, 16),
        "C_INPUT_BITWIDTH": input_bitwidth,
        "C_UNSIGNED": is_unsigned,
    }
    generics["C_OUTPUT_BITWIDTH"] = generics["C_INPUT_BITWIDTH"] + ceil(
        log2(generics["C_INPUT_COUNT"])
    )
    run(
        toplevel="adder_tree",
        module="test_adder_tree",
        compile_args=["--work=util", "--std=08"],
        parameters=generics,
    )
