from dataclasses import dataclass
import math
import pathlib
import random
from random import choice, randint
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import pytest

import larq as lq
import numpy as np
import tensorflow as tf

from test_utils.cocotb_helpers import ImageMonitor, Tick
from test_utils.general import (
    concatenate_channel,
    concatenate_integers,
    get_files,
)

random.seed(100)  # TODO: fixture


def tensor_to_list(tensor):
    return list(tensor.numpy().astype("uint8").flat)


@cocotb.test()
async def run_test(dut):
    # layer parameter
    bitwidth = 1
    kernel_size = (dut.C_KERNEL_SIZE.value.integer,) * 2
    stride = (dut.C_STRIDE.value.integer,) * 2
    image_shape = (
        dut.C_IMG_WIDTH.value.integer,
        dut.C_IMG_HEIGHT.value.integer,
        dut.C_INPUT_CHANNEL.value.integer,
    )
    output_channel = dut.C_OUTPUT_CHANNEL.value.integer

    # define the reference model
    batch_shape = (1,) + image_shape
    input_ = tf.keras.Input(batch_shape=batch_shape, name="img")
    x = lq.layers.QuantConv2D(
        output_channel,
        kernel_size,
        strides=stride,
        use_bias=False,
        name="test_conv",
    )(input_)
    x = tf.keras.layers.BatchNormalization(name="test_batchnorm")(x)
    output_ = lq.quantizers.SteHeaviside()(x)
    model = tf.keras.Model(inputs=input_, outputs=output_)

    # TODO: Try to set realistic batchnorm parameter.
    # beta=offset, gamma=scale, mean, variance
    # original_batch_weights = model.get_layer("test_batchnorm").get_weights()
    ## np.array([kernel_size[0] ** 2 * image_shape[2] / 2]
    # model.get_layer("test_batchnorm").set_weights(
    # [
    # original_batch_weights[0],
    # original_batch_weights[1],
    # np.array([16] * output_channel),
    # original_batch_weights[3],
    # ]
    # )

    # define the testcases
    @dataclass
    class Testcase:
        input_image: List[int]
        weights: List[int]

        @staticmethod
        def replace_minus(values):
            """Convert from LARQ format [-1, 1] to pocket-bnn format [0, 1].
            This gets compensated by batchnorm/activation later.
            """
            return [0 if v == -1 else v for v in values]

        @property
        def input_data(self) -> int:
            # send all channels (i. e. one pixel) at a time
            return concatenate_channel(
                self.replace_minus(self.input_image), image_shape[2], bitwidth
            )

        @property
        def output_data(self) -> int:
            # inference
            image_tensor = tf.convert_to_tensor(self.input_image)
            reshaped_tensor = tf.reshape(image_tensor, batch_shape)
            result = model(reshaped_tensor)
            result_list = list(result.numpy().astype("uint8").flat)
            return concatenate_channel(result_list, output_channel, bitwidth)

        def get_weights(self):
            return concatenate_integers(
                self.replace_minus(self.weights), bitwidth=bitwidth
            )

        def get_threshold(self):
            threshold = []
            batchnorm_params = [
                a.tolist() for a in model.get_layer("test_batchnorm").get_weights()
            ]
            for gamma, beta, mean, variance in zip(*batchnorm_params):
                # TODO: Could be wrong order.

                epsilon = 0.001  # prevent division by 0

                # use batch normalization as activation
                # see also: https://arxiv.org/pdf/1612.07119.pdf, 4.2.2 Batchnorm-activation as Threshold
                threshold_batchnorm = mean - (beta / (variance * epsilon - gamma))

                # Conversion from LARQ format [-1, 1] to pocket-bnn format [0, 1] (positive only):
                # make the threshold compatible to positive only values
                fan_in = kernel_size[0] ** 2 * image_shape[2]  # max value
                # get the following formula by solving:
                # x - y = fan_in; x + y = threshold
                threshold_pos = (threshold_batchnorm + fan_in) / 2
                threshold.append(int(threshold_pos))

            return concatenate_integers(
                self.replace_minus(threshold),
                bitwidth=math.ceil(math.log2(kernel_size[0] ** 2 * image_shape[2] + 1)),
            )

    cases = (
        # zero activations, zero weights -> result should be all zeros
        Testcase(
            [-1] * math.prod(image_shape),
            [-1] * (image_shape[2] * output_channel * kernel_size[0] ** 2),
        ),
        # one activations, one weights -> result should be all zeros
        Testcase(
            [1] * math.prod(image_shape),
            [1] * (image_shape[2] * output_channel * kernel_size[0] ** 2),
        ),
        # one activations, zero weights -> result should be all ones
        Testcase(
            [1] * math.prod(image_shape),
            [-1] * (image_shape[2] * output_channel * kernel_size[0] ** 2),
        ),
        # zero activations, one weights -> result should be all ones
        Testcase(
            [-1] * math.prod(image_shape),
            [1] * (image_shape[2] * output_channel * kernel_size[0] ** 2),
        ),
        # mixed
        Testcase(
            [choice([-1, 1]) for _ in range(math.prod(image_shape))],
            [
                choice([-1, 1])
                for _ in range(image_shape[2] * output_channel * kernel_size[0] ** 2)
            ],
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
        bitwidth * output_channel,
    )
    dut.isl_valid <= 0
    dut.isl_start <= 0
    await tick.wait()

    # run the specific testcases
    for case in cases:
        # print("eee", model.get_layer("test_conv").get_weights()[0].shape)
        reshaped_weights = [
            np.array(case.weights).reshape(
                kernel_size + (image_shape[2], output_channel)
            )
        ]
        model.get_layer("test_conv").set_weights(reshaped_weights)
        # print("reshaped weights", reshaped_weights)
        # print("fff", model.get_layer("test_conv").get_weights()[0][:, :, :, 0])

        dut.islv_weights <= case.get_weights()
        dut.islv_threshold <= case.get_threshold()

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

        print("expected result:", case.output_data)
        print("actual result:", output_mon.output)
        assert output_mon.output == case.output_data
        output_mon.clear()


# Don't run the full test matrix. Only the most common configs.
@pytest.mark.parametrize(
    "kernel_size,stride,input_channel,output_channel",
    [
        (1, 1, 4, 8),
        (2, 1, 4, 8),
        (2, 2, 4, 8),
        (3, 1, 4, 8),
        (3, 1, 1, 4),
        (3, 1, 3, 8),
        (3, 1, 8, 16),
        (3, 2, 4, 8),
        (5, 1, 4, 8),
        (7, 1, 4, 8),
    ],
)
def test_window_convolution_activation(
    kernel_size, stride, input_channel, output_channel
):
    # TODO: Add test for output bitwidth /= 1.
    generics = {
        "C_KERNEL_SIZE": kernel_size,
        "C_STRIDE": stride,
        "C_INPUT_CHANNEL": input_channel,
        "C_OUTPUT_CHANNEL": output_channel,
        "C_IMG_WIDTH": 8,
        "C_IMG_HEIGHT": 8,
    }
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="window_convolution_activation",
        module="test_window_convolution_activation",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
    )
