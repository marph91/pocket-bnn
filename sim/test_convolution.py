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
    @dataclass
    class Testcase:
        input_activations: List[int]
        input_weights: List[int]

        @property
        def input_activations_int(self) -> int:
            return concatenate_integers(self.input_activations)

        @property
        def input_weights_int(self) -> int:
            return concatenate_integers(self.input_weights)

        @property
        def output_data(self) -> int:
            ones_count = 0
            for act, weight in zip(self.input_activations, self.input_weights):
                ones_count = ones_count + (
                    act and weight
                )  # TODO: should be xnor: (not (act ^ weight))
            return ones_count

    input_channel = dut.C_INPUT_CHANNEL.value.integer
    window_size = dut.C_KERNEL_SIZE.value.integer ** 2
    input_length = input_channel * window_size
    cases = (
        Testcase([0] * input_length, [0] * input_length),
        Testcase([0] * input_length, [1] * input_length),
        Testcase([1] * input_length, [0] * input_length),
        Testcase([1] * input_length, [1] * input_length),
        Testcase(
            [randint(0, 1) for _ in range(input_length)],
            [randint(0, 1) for _ in range(input_length)],
        ),
    )

    # initialize the test
    clock_period = 10  # ns
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    dut.isl_valid <= 0
    await Timer(clock_period, units="ns")

    for case in cases:
        # TODO: test pipelining -> monitor output
        dut.isl_valid <= 1
        dut.islv_data <= case.input_activations_int
        dut.islv_weights <= case.input_weights_int
        await Timer(clock_period, units="ns")
        while dut.osl_valid.value.integer == 0:
            dut.isl_valid <= 0
            await Timer(clock_period, units="ns")
        assert (
            dut.oslv_data.value.integer == case.output_data
        ), f"{dut.oslv_data.value.integer} /= {case.output_data}"


@pytest.mark.parametrize("kernel_size", range(2, 3))  # range(2, 7)
@pytest.mark.parametrize("input_channel", (4,))  # (1, 4, 9)
def test_convolution(record_waveform, kernel_size, input_channel):
    generics = {
        "C_KERNEL_SIZE": kernel_size,
        "C_INPUT_CHANNEL": input_channel,
    }
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="convolution",
        module="test_convolution",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
        sim_args=["--wave=convolution.ghw"] if record_waveform else None,
    )
