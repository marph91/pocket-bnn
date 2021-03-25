from dataclasses import dataclass
import math
import pathlib
from random import randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import numpy as np
import tensorflow as tf

from test_utils.cocotb_helpers import ImageMonitor, Tick
from test_utils.general import concatenate_channel, get_files


@cocotb.test()
async def run_test(dut):
    # layer parameter
    bitwidth = dut.C_BITWIDTH.value.integer
    image_shape = (
        dut.C_IMG_WIDTH.value.integer,
        dut.C_IMG_HEIGHT.value.integer,
        dut.C_CHANNEL.value.integer,
    )

    # define the reference model
    batch_shape = (1,) + image_shape
    input_ = tf.keras.Input(batch_shape=batch_shape, name="img")
    output_ = tf.keras.layers.GlobalAveragePooling2D()(input_)
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
            # TODO: Not bit accurate in corner cases.
            result_list = list(np.rint(result.numpy()).astype("uint8").flat)
            return result_list

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
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    output_mon = ImageMonitor(
        "output",
        dut.oslv_data,
        dut.osl_valid,
        dut.isl_clk,
        1,
        bitwidth * image_shape[2],
    )
    dut.isl_valid <= 0
    dut.isl_start <= 0
    await tick.wait()

    # run the specific testcases
    for case in cases:
        dut.isl_start <= 1
        await tick.wait()
        dut.isl_start <= 0
        await tick.wait()

        for datum in case.input_data:
            dut.isl_valid <= 1
            dut.islv_data <= datum
            await tick.wait()
            dut.isl_valid <= 0
            await tick.wait()

        dut.isl_valid <= 0
        await tick.wait_multiple(40)

        print("Expected output:", case.output_data)
        print("Actual output:", output_mon.output)
        assert all(
            [
                math.isclose(act, exp, abs_tol=1)
                for act, exp in zip(output_mon.output, case.output_data)
            ]
        )
        output_mon.clear()


def test_average_pooling():
    generics = {
        "C_BITWIDTH": 8,
        "C_CHANNEL": 6,
        "C_IMG_WIDTH": 6,
        "C_IMG_HEIGHT": 6,
    }
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="average_pooling",
        module="test_average_pooling",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
    )
