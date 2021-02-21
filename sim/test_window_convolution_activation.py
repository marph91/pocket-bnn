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

from test_utils.cocotb_helpers import ImageMonitor
from test_utils.general import (
    concatenate_channel,
    concatenate_integers,
    get_files,
    record_waveform,
)

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
        dut.C_INPUT_CHANNEL.value.integer,
    )
    output_channel = dut.C_OUTPUT_CHANNEL.value.integer
    post_convolution_bitwidth = dut.C_POST_CONVOLUTION_BITWIDTH.value.integer

    # define the reference model
    batch_shape = (1,) + image_shape
    input_ = tf.keras.Input(batch_shape=batch_shape, name="img")
    x = lq.layers.QuantConv2D(
        output_channel, kernel_size, strides=stride, use_bias=False, name="test_conv"
    )(input_)
    x = tf.keras.layers.BatchNormalization(name="test_batchnorm")(x)
    output_ = lq.quantizers.SteHeaviside()(x)
    model = tf.keras.Model(inputs=input_, outputs=output_)

    # define the testcases
    @dataclass
    class Testcase:
        input_image: List[int]
        weights: List[int]
        threshold: List[int]

        @property
        def input_data(self) -> int:
            # send all channels (i. e. one pixel) at a time
            return concatenate_channel(self.input_image, image_shape[2], bitwidth)

        @property
        def output_data(self) -> int:
            # inference
            image_tensor = tf.convert_to_tensor(self.input_image)
            reshaped_tensor = tf.reshape(image_tensor, batch_shape)
            print("input reshaped", reshaped_tensor)
            result = model(reshaped_tensor)
            print("result", result)
            result_list = list(result.numpy().astype("uint8").flat)
            return concatenate_channel(result_list, output_channel, bitwidth)

    cases = (
        ## zero weights
        # Testcase(
        # [randint(0, 1) for _ in range(math.prod(image_shape))],
        # [0] * (image_shape[2] * output_channel * kernel_size[0] ** 2),
        # [randint(0, 2 ** post_convolution_bitwidth - 1) for _ in range(output_channel)],
        # ),
        ## zero activations
        # Testcase(
        # [0] * math.prod(image_shape),
        # [randint(0, 1) for _ in range(image_shape[2] * output_channel * kernel_size[0] ** 2)],
        # [randint(0, 2 ** post_convolution_bitwidth - 1) for _ in range(output_channel)],
        # ),
        ## # all ones
        ## Testcase([2 ** bitwidth - 1] * math.prod(image_shape)),
        # mixed
        Testcase(
            # choice([-1, 1])
            [randint(0, 1) for _ in range(math.prod(image_shape))],
            [
                randint(0, 1)
                for _ in range(image_shape[2] * output_channel * kernel_size[0] ** 2)
            ],
            [16] * output_channel,  # corresponds to batchnorm parameter (see formula)
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
        print("eee", model.get_layer("test_conv").get_weights()[0].shape)
        reshaped_weights = [
            np.array(case.weights).reshape(
                kernel_size + (image_shape[2], output_channel)
            )
        ]
        model.get_layer("test_conv").set_weights(reshaped_weights)
        print("reshaped weights", reshaped_weights)
        print("fff", model.get_layer("test_conv").get_weights()[0][:, :, :, 0])

        # TODO: Try to set realistic batchnorm parameter. For now just set the mean to an arbitrary value.
        # beta=offset, gamma=scale, mean, variance
        original_batch_weights = model.get_layer("test_batchnorm").get_weights()
        # np.array([kernel_size[0] ** 2 * image_shape[2] / 2]
        model.get_layer("test_batchnorm").set_weights(
            [
                original_batch_weights[0],
                original_batch_weights[1],
                np.array([16] * output_channel),
                original_batch_weights[3],
            ]
        )

        print(case.weights)

        def replace_minus(values):
            return [0 if v == -1 else v for v in values]

        print(replace_minus(case.weights))
        print(len(bin(concatenate_integers(case.weights, bitwidth=1))[2:]))
        dut.islv_weights <= concatenate_integers(case.weights, bitwidth=1)
        dut.islv_threshold <= concatenate_integers(
            case.threshold, bitwidth=post_convolution_bitwidth
        )

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

        print("expected result:", case.output_data)
        print(output_mon.output)
        assert output_mon.output == case.output_data
        # assert False
        output_mon.clear()


@pytest.mark.parametrize("kernel_size", range(3, 4))  # range(2, 6)
def test_window_convolution_activation(record_waveform, kernel_size):
    generics = {
        "C_KERNEL_SIZE": kernel_size,
        "C_STRIDE": 1,
        "C_INPUT_CHANNEL": 8,
        "C_OUTPUT_CHANNEL": 8,
        "C_IMG_WIDTH": 4,
        "C_IMG_HEIGHT": 4,
        "C_POST_CONVOLUTION_BITWIDTH": 8,
    }
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="window_convolution_activation",
        module="test_window_convolution_activation",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
        sim_args=["--wave=window_convolution_activation.ghw"]
        if record_waveform
        else None,
    )
