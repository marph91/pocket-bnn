from dataclasses import dataclass
import math
import pathlib
import random
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import pytest
import tensorflow as tf

from test_utils.cocotb_helpers import ImageMonitor
from test_utils.general import concatenate_channel, get_files, record_waveform

random.seed(100)  # TODO: fixture


@cocotb.test()
async def run_test(dut):
    # layer parameter
    bitwidth = 1
    kernel_size = (dut.C_KERNEL_SIZE.value.integer,) * 2
    stride = (dut.C_STRIDE.value.integer,) * 2
    image_shape = (
        dut.C_IMG_WIDTH.value.integer,
        dut.C_IMG_HEIGHT.value.integer,
        dut.C_CHANNEL.value.integer,
    )

    # define the reference model
    batch_shape = (1,) + image_shape
    input_ = tf.keras.Input(batch_shape=batch_shape, name="img")
    output_ = tf.keras.layers.MaxPooling2D(pool_size=kernel_size, strides=stride)(
        input_
    )
    model = tf.keras.Model(inputs=input_, outputs=output_)

    # define the testcases
    @dataclass
    class Testcase:
        input_image: List[int]

        @property
        def input_data(self) -> int:
            # send all channels (i. e. one pixel) at a time
            return concatenate_channel(self.input_image, image_shape[2], bitwidth)

        @property
        def output_data(self) -> int:
            # inference
            image_tensor = tf.convert_to_tensor(self.input_image)
            result = model(tf.reshape(image_tensor, batch_shape))
            result_list = list(result.numpy().astype("uint8").flat)
            return concatenate_channel(result_list, image_shape[2], bitwidth)

    cases = (
        # all zeros
        Testcase([0] * math.prod(image_shape)),
        # all ones
        Testcase([2 ** bitwidth - 1] * math.prod(image_shape)),
        # mixed
        Testcase(
            [randint(0, 2 ** bitwidth - 1) for _ in range(math.prod(image_shape))]
        ),
    )

    # prepare coroutines
    clock_period = 10  # ns
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    output_mon = ImageMonitor("output", dut.oslv_data, dut.osl_valid, dut.isl_clk, 1)
    dut.isl_valid <= 0
    dut.isl_start <= 0
    await Timer(clock_period, units="ns")

    # run the specific testcases
    for case in cases:
        dut.isl_start <= 1
        await Timer(clock_period, units="ns")
        dut.isl_start <= 0
        await Timer(clock_period, units="ns")

        for datum in case.input_data:
            dut.isl_valid <= 1
            dut.islv_data <= datum
            await Timer(clock_period, units="ns")
            dut.isl_valid <= 0
            await Timer(clock_period, units="ns")

        dut.isl_valid <= 0
        await Timer(40 * clock_period, units="ns")

        print(case.output_data)
        print(output_mon.output)
        assert output_mon.output == case.output_data
        output_mon.clear()


@pytest.mark.parametrize("kernel_size", range(2, 3))  # range(2, 6)
def test_window_maximum_pooling(record_waveform, kernel_size):
    generics = {
        "C_KERNEL_SIZE": kernel_size,
        "C_STRIDE": 2,
        "C_CHANNEL": 8,
        "C_IMG_WIDTH": 4,
        "C_IMG_HEIGHT": 4,
    }
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="window_maximum_pooling",
        module="test_window_maximum_pooling",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
        sim_args=["--wave=window_maximum_pooling.ghw"] if record_waveform else None,
    )