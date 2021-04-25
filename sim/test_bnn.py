from dataclasses import dataclass
import pathlib
from random import randint
import sys
from typing import List

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import Timer
from cocotb_test.simulator import run
import larq as lq
import numpy as np
import tensorflow as tf

from test_utils.cocotb_helpers import ImageMonitor, Tick
from test_utils.general import get_files

np.set_printoptions(threshold=sys.maxsize)
# https://stackoverflow.com/questions/2891790/how-to-pretty-print-a-numpy-array-without-scientific-notation-and-with-given-pre
np.set_printoptions(suppress=True)


@cocotb.test()
async def run_test(dut):
    height = dut.C_INPUT_HEIGHT.value.integer
    width = dut.C_INPUT_WIDTH.value.integer
    input_image = [i % 255 for i in range(height * width)]

    model = tf.keras.models.load_model("../../models/test")
    lq.models.summary(model)
    data = np.reshape(np.array(input_image), (1, height, width, 1))

    # https://keras.io/getting_started/faq/#how-can-i-obtain-the-output-of-an-intermediate-layer-feature-extraction
    extractor = tf.keras.Model(
        inputs=model.inputs, outputs=[layer.output for layer in model.layers]
    )
    features = extractor(data)
    class_scores_pos = list(features[-2].numpy().flat)
    class_scores = [
        round((score + features[-4].shape[-1]) / 2) for score in class_scores_pos
    ]

    output_bitwitdh = dut.C_OUTPUT_CHANNEL_BITWIDTH.value.integer
    output_mon = ImageMonitor(
        "output",
        dut.oslv_data,
        dut.osl_valid,
        dut.isl_clk,
        1,
        output_bitwitdh,
    )

    # initialize the test
    clock_period = 10  # ns
    tick = Tick(clock_period=clock_period)
    cocotb.fork(Clock(dut.isl_clk, clock_period, units="ns").start())
    dut.isl_valid <= 0
    await tick.wait()

    for pixel in input_image:
        dut.isl_valid <= 1
        dut.islv_data <= pixel
        await tick.wait()
        dut.isl_valid <= 0
        await tick.wait()
        await tick.wait()

    await tick.wait_multiple(height * width)

    print(class_scores_pos)
    print(class_scores)
    print(output_mon.output)
    print(features)
    assert output_mon.output == class_scores


def test_bnn():
    generics = {}
    run(
        vhdl_sources=get_files(
            pathlib.Path(__file__).parent.absolute() / ".." / "src", "*.vhd"
        ),
        toplevel="bnn",
        module="test_bnn",
        compile_args=["--work=cnn_lib", "--std=08"],
        parameters=generics,
    )
