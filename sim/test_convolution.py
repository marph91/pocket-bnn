from dataclasses import dataclass
from math import log2
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import pytest

from test_utils.cocotb_helpers import Tick
from test_utils.general import (
    concatenate_integers,
    from_fixedint,
    to_fixedint,
    get_files,
)


@cocotb.test()
async def run_test(dut):
    input_channel = dut.C_INPUT_CHANNEL.value.integer
    window_size = dut.C_KERNEL_SIZE.value.integer ** 2
    input_length = input_channel * window_size

    # input is unsigned 1 or 8 bit, output is signed
    input_channel_bitwidth = dut.C_INPUT_CHANNEL_BITWIDTH.value.integer
    output_bitwidth = (
        input_channel_bitwidth + int(log2(window_size * input_channel)) + 1
    )

    @dataclass
    class Testcase:
        input_activations: List[int]
        input_weights: List[int]

        @property
        def input_activations_int(self) -> int:
            return concatenate_integers(
                self.input_activations, bitwidth=input_channel_bitwidth
            )

        @property
        def input_weights_int(self) -> int:
            return concatenate_integers(self.input_weights)

        @property
        def output_data(self) -> int:
            # 1 bit activations -> xnor, popcount
            if input_channel_bitwidth == 1:
                ones_count = 0
                for act, weight in zip(self.input_activations, self.input_weights):
                    ones_count = ones_count + (not (act ^ weight))
                return ones_count
            # >1 bit activations -> multiplication
            product = 0
            for act, weight in zip(self.input_activations, self.input_weights):
                product = product + act * (-1 if weight == 0 else 1)
            return product

    cases = (
        Testcase([0] * input_length, [0] * input_length),
        Testcase([0] * input_length, [1] * input_length),
        Testcase([1] * input_length, [0] * input_length),
        Testcase([1] * input_length, [1] * input_length),
        Testcase(
            [randint(0, 2 ** input_channel_bitwidth - 1) for _ in range(input_length)],
            [randint(0, 1) for _ in range(input_length)],
        ),
    )

    # initialize the test
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    dut.isl_valid <= 0
    await tick.wait()

    for case in cases:
        # TODO: test pipelining -> monitor output
        dut.isl_valid <= 1
        dut.islv_data <= case.input_activations_int
        dut.islv_weights <= case.input_weights_int
        await tick.wait()
        while dut.osl_valid.value.integer == 0:
            dut.isl_valid <= 0
            await tick.wait()

        output_int = from_fixedint(
            dut.oslv_data.value.integer, output_bitwidth, is_unsigned=False
        )
        assert output_int == case.output_data, f"{output_int} /= {case.output_data}"


@pytest.mark.parametrize("kernel_size", (1, 2, 3, 5, 7))
@pytest.mark.parametrize("input_channel", (1, 4, 9))
@pytest.mark.parametrize("input_channel_bitwidth", (1, 8))
def test_convolution(kernel_size, input_channel, input_channel_bitwidth):
    generics = {
        "C_KERNEL_SIZE": kernel_size,
        "C_INPUT_CHANNEL": input_channel,
        "C_INPUT_CHANNEL_BITWIDTH": input_channel_bitwidth,
    }
    run(
        toplevel="convolution",
        module="test_convolution",
        compile_args=["--work=bnn_lib", "--std=08"],
        parameters=generics,
    )
