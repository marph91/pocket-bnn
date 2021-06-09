from dataclasses import dataclass
import math
from random import randint
from typing import Dict, List, Optional

from bitstring import Bits
import larq as lq
import numpy as np
import tensorflow as tf

# TODO: copied from test_utils.general
def to_fixedint(number: int, bitwidth: int, is_unsigned: bool = True):
    """Convert signed int to fixed int."""
    if is_unsigned:
        number_dict = {"uint": number, "length": bitwidth}
    else:
        number_dict = {"int": number, "length": bitwidth}
    return int(Bits(**number_dict).bin, 2)


@dataclass
class Parameter:
    name: str
    datatype: str
    value: Optional[str] = None


class Layer:
    def __init__(self, name, parameter: List[Parameter]):
        self.info = {"name": name}
        self.constants = {
            par.name: Parameter(f"{par.name}_{name.upper()}", par.datatype, par.value)
            for par in parameter
        }
        self.signals = []
        self.previous_layer_info = None

    def get_constants(self) -> List[Parameter]:
        return list(self.constants.values())

    def get_signals(self) -> List[Parameter]:
        return self.signals

    def update(self, previous_layer_info):
        pass

    def get_info(self):
        return self.info

    def get_instance(self):
        pass


class Convolution(Layer):
    def __init__(self, name, input_channel, input_channel_bitwidth, parameter):
        super().__init__(name, parameter)

        self.control_signal = Parameter(f"sl_valid_{self.info['name']}", "std_logic")
        self.signals = [self.control_signal]

        self.input_channel = input_channel
        self.input_channel_bitwidth = input_channel_bitwidth

    def update(self, previous_layer_info):
        self.previous_name = previous_layer_info["name"]

        self.data_signal = Parameter(
            f"slv_data_{self.info['name']}",
            f"std_logic_vector(C_OUTPUT_CHANNEL_{self.info['name'].upper()} * C_OUTPUT_CHANNEL_BITWIDTH_{self.info['name'].upper()} - 1 downto 0)",
        )
        self.signals.append(self.data_signal)

        # channel
        self.info["channel"] = int(self.constants["C_OUTPUT_CHANNEL"].value)
        self.info["bitwidth"] = int(self.constants["C_OUTPUT_CHANNEL_BITWIDTH"].value)
        self.constants["C_INPUT_CHANNEL"] = Parameter(
            f"C_INPUT_CHANNEL_{self.info['name'].upper()}",
            "integer",
            previous_layer_info["channel"],
        )
        self.constants["C_INPUT_CHANNEL_BITWIDTH"] = Parameter(
            f"C_INPUT_CHANNEL_BITWIDTH_{self.info['name'].upper()}",
            "integer",
            previous_layer_info["bitwidth"],
        )

        # calculate new image size
        self.constants["C_IMG_WIDTH"] = Parameter(
            f"C_IMG_WIDTH_{self.info['name'].upper()}",
            "integer",
            str(previous_layer_info["width"]),
        )
        self.constants["C_IMG_HEIGHT"] = Parameter(
            f"C_IMG_HEIGHT_{self.info['name'].upper()}",
            "integer",
            str(previous_layer_info["height"]),
        )

        self.info["width"] = new_size(
            previous_layer_info["width"],
            int(self.constants["C_KERNEL_SIZE"].value),
            int(self.constants["C_STRIDE"].value),
        )
        self.info["height"] = new_size(
            previous_layer_info["height"],
            int(self.constants["C_KERNEL_SIZE"].value),
            int(self.constants["C_STRIDE"].value),
        )

    def add_weights(self, weights=None):
        kernel_size = int(self.constants["C_KERNEL_SIZE"].value)
        output_channel = int(self.constants["C_OUTPUT_CHANNEL"].value)
        bitwidth = output_channel * self.input_channel * kernel_size ** 2

        if weights is None:
            slv_weights = "".join([str(randint(0, 1)) for _ in range(bitwidth)])
        else:
            # TODO: sanity checks
            # https://docs.larq.dev/larq/api/quantizers/#stesign
            # TODO: Weights are somehow reversed. Check why.
            slv_weights = "".join(["0" if t < 0 else "1" for t in weights])

        self.constants["C_WEIGHTS"] = Parameter(
            f"C_WEIGHTS_{self.info['name'].upper()}",
            f"std_logic_vector({bitwidth} - 1 downto 0)",
            f'"{slv_weights}"',
        )

    def add_thresholds(self, thresholds=None):
        kernel_size = int(self.constants["C_KERNEL_SIZE"].value)
        output_channel = int(self.constants["C_OUTPUT_CHANNEL"].value)
        threshold_bitwidth = (
            self.input_channel_bitwidth
            + math.ceil(math.log2(self.input_channel * kernel_size ** 2 + 1))
            + 1
        )
        total_bitwidth = output_channel * threshold_bitwidth
        if thresholds is None:
            # TODO: Random option for signed?
            slv_thresholds = "".join(
                [str(randint(0, 1)) for _ in range(total_bitwidth)]
            )
        else:
            # TODO: sanity checks
            slv_thresholds_list = []
            for t in thresholds:
                t_fixedint = to_fixedint(
                    int(t),
                    threshold_bitwidth,
                    is_unsigned=self.input_channel_bitwidth == 1,
                )
                slv_thresholds_list.append(
                    bin(t_fixedint)[2:].zfill(threshold_bitwidth)
                )
            # TODO: Thresholds are somehow reversed. Check why.
            slv_thresholds = "".join(slv_thresholds_list)
            assert all([bit in ["0", "1"] for bit in slv_thresholds]), slv_thresholds
        self.constants["C_THRESHOLDS"] = Parameter(
            f"C_THRESHOLDS_{self.info['name'].upper()}",
            f"std_logic_vector({total_bitwidth} - 1 downto 0)",
            f'"{slv_thresholds}"',
        )

    def get_instance(self):
        return f"""
i_convolution_{self.info["name"]} : entity bnn_lib.window_convolution_activation
  generic map (
    C_KERNEL_SIZE => {self.constants["C_KERNEL_SIZE"].name},
    C_STRIDE      => {self.constants["C_STRIDE"].name},

    C_INPUT_CHANNEL           => {self.constants["C_INPUT_CHANNEL"].name},
    C_INPUT_CHANNEL_BITWIDTH  => {self.constants["C_INPUT_CHANNEL_BITWIDTH"].name},
    C_OUTPUT_CHANNEL          => {self.constants["C_OUTPUT_CHANNEL"].name},
    C_OUTPUT_CHANNEL_BITWIDTH => {self.constants["C_OUTPUT_CHANNEL_BITWIDTH"].name},

    C_IMG_WIDTH  => {self.constants["C_IMG_WIDTH"].name},
    C_IMG_HEIGHT => {self.constants["C_IMG_HEIGHT"].name}
  )
  port map (
    isl_clk        => isl_clk,
    isl_start      => isl_start,
    isl_valid      => sl_valid_{self.previous_name},
    islv_data      => slv_data_{self.previous_name},
    islv_weights   => {self.constants["C_WEIGHTS"].name},
    islv_threshold => {self.constants["C_THRESHOLDS"].name},
    oslv_data      => {self.data_signal.name},
    osl_valid      => {self.control_signal.name}
  );"""


class MaximumPooling(Layer):
    def __init__(self, name, parameter):
        super().__init__(name, parameter)

        self.control_signal = Parameter(f"sl_valid_{self.info['name']}", "std_logic")
        self.data_signal = Parameter(
            f"slv_data_{self.info['name']}",
            f"std_logic_vector(C_CHANNEL_{self.info['name']} - 1 downto 0)",
        )
        self.signals = [self.data_signal, self.control_signal]

    def update(self, previous_layer_info):
        self.previous_name = previous_layer_info["name"]

        self.constants["C_CHANNEL"] = Parameter(
            f"C_CHANNEL_{self.info['name']}", "integer", previous_layer_info["channel"]
        )

        # calculate new image size
        self.constants["C_IMG_WIDTH"] = Parameter(
            f"C_IMG_WIDTH_{self.info['name']}",
            "integer",
            str(previous_layer_info["width"]),
        )
        self.constants["C_IMG_HEIGHT"] = Parameter(
            f"C_IMG_HEIGHT_{self.info['name']}",
            "integer",
            str(previous_layer_info["height"]),
        )

        self.info["width"] = new_size(
            previous_layer_info["width"],
            int(self.constants["C_KERNEL_SIZE"].value),
            int(self.constants["C_STRIDE"].value),
        )
        self.info["height"] = new_size(
            previous_layer_info["height"],
            int(self.constants["C_KERNEL_SIZE"].value),
            int(self.constants["C_STRIDE"].value),
        )

    def get_instance(self):
        return f"""
i_maximum_pooling_{self.info["name"]} : entity bnn_lib.window_maximum_pooling
  generic map (
    C_KERNEL_SIZE => {self.constants["C_KERNEL_SIZE"].name},
    C_STRIDE      => {self.constants["C_STRIDE"].name},

    C_CHANNEL  => {self.constants["C_CHANNEL"].name},

    C_IMG_WIDTH  => {self.constants["C_IMG_WIDTH"].name},
    C_IMG_HEIGHT => {self.constants["C_IMG_HEIGHT"].name}
  )
  port map (
    isl_clk   => isl_clk,
    isl_start => isl_start,
    isl_valid => sl_valid_{self.previous_name},
    islv_data => slv_data_{self.previous_name},
    oslv_data => {self.data_signal.name},
    osl_valid => {self.control_signal.name}
  );"""


class Serializer(Layer):
    def __init__(self, name, parameter):
        super().__init__(name, parameter)

        self.control_signal = Parameter(f"sl_valid_{self.info['name']}", "std_logic")
        self.signals = [self.control_signal]

    def update(self, previous_layer_info):
        self.previous_name = previous_layer_info["name"]

        self.constants["C_DATA_COUNT"] = Parameter(
            f"C_DATA_COUNT_{self.info['name'].upper()}",
            "integer",
            previous_layer_info["channel"],
        )
        self.constants["C_DATA_BITWIDTH"] = Parameter(
            f"C_DATA_BITWIDTH_{self.info['name'].upper()}",
            "integer",
            previous_layer_info["bitwidth"],
        )

        self.data_signal = Parameter(
            f"slv_data_{self.info['name']}",
            f"std_logic_vector({self.constants['C_DATA_BITWIDTH'].name} - 1 downto 0)",
        )
        self.signals.append(self.data_signal)

    def get_instance(self):
        return f"""
i_serializer_{self.info["name"]} : entity util.serializer
  generic map (
    C_DATA_COUNT    => {self.constants["C_DATA_COUNT"].name},
    C_DATA_BITWIDTH => {self.constants["C_DATA_BITWIDTH"].name}
  )
  port map (
    isl_clk        => isl_clk,
    isl_valid      => sl_valid_{self.previous_name},
    islv_data      => slv_data_{self.previous_name},
    oslv_data      => {self.data_signal.name},
    osl_valid      => {self.control_signal.name}
  );"""


class AveragePooling(Layer):
    def __init__(self, name, parameter):
        super().__init__(name, parameter)

        self.control_signal = Parameter(f"sl_valid_{self.info['name']}", "std_logic")
        self.signals = [self.control_signal]

    def update(self, previous_layer_info):
        self.previous_name = previous_layer_info["name"]

        self.constants["C_BITWIDTH"] = Parameter(
            f"C_BITWIDTH_{self.info['name'].upper()}",
            "integer",
            previous_layer_info["bitwidth"],
        )
        self.constants["C_CHANNEL"] = Parameter(
            f"C_CHANNEL_{self.info['name'].upper()}",
            "integer",
            previous_layer_info["channel"],
        )
        self.constants["C_IMG_WIDTH"] = Parameter(
            f"C_IMG_WIDTH_{self.info['name']}",
            "integer",
            str(previous_layer_info["width"]),
        )
        self.constants["C_IMG_HEIGHT"] = Parameter(
            f"C_IMG_HEIGHT_{self.info['name']}",
            "integer",
            str(previous_layer_info["height"]),
        )

        self.data_signal = Parameter(
            f"slv_data_{self.info['name']}",
            f"std_logic_vector({self.constants['C_BITWIDTH'].name} - 1 downto 0)",
        )
        self.signals.append(self.data_signal)

    def get_instance(self):
        return f"""
i_average_pooling_{self.info["name"]} : entity bnn_lib.average_pooling
  generic map (
    C_BITWIDTH   => {self.constants["C_BITWIDTH"].name},

    C_CHANNEL    => {self.constants["C_CHANNEL"].name},
    C_IMG_WIDTH  => {self.constants["C_IMG_WIDTH"].name},
    C_IMG_HEIGHT => {self.constants["C_IMG_HEIGHT"].name}
  )
  port map (
    isl_clk   => isl_clk,
    isl_start => isl_start,
    isl_valid => sl_valid_{self.previous_name},
    islv_data => slv_data_{self.previous_name},
    oslv_data => {self.data_signal.name},
    osl_valid => {self.control_signal.name}
  );"""


def parameter_to_vhdl(type_, parameter):
    vhdl = []
    for par in parameter:
        par_vhdl = f"{type_} {par.name} : {par.datatype}"
        if par.value is not None:
            par_vhdl += f" := {par.value}"
        par_vhdl += ";"
        vhdl.append(par_vhdl)
    return "\n".join(vhdl)


def indent(input_, spaces=2):
    return [" " * spaces + i for i in input_]


def new_size(prevous_size, kernel_size, stride, padding=0):
    return int((prevous_size + 2 * padding - kernel_size) / stride + 1)


class Bnn:
    def __init__(
        self,
        image_height,
        image_width,
        input_channel,
        input_bitwidth,
        output_classes,
        output_bitwidth,
    ):
        self.layers = []
        self.output_classes = output_classes
        self.output_bitwidth = output_bitwidth
        self.previous_layer_info = {
            "name": "in_deserialized",
            "channel": input_channel,
            "bitwidth": input_bitwidth,
            "width": image_width,
            "height": image_height,
        }

        self.input_data_signal_deserialized = Parameter(
            f"slv_data_{self.previous_layer_info['name']}",
            f"std_logic_vector(C_INPUT_CHANNEL * C_INPUT_CHANNEL_BITWIDTH - 1 downto 0)",
        )
        self.input_control_signal_deserialized = Parameter(
            f"sl_valid_{self.previous_layer_info['name']}", "std_logic"
        )

        self.libraries = """
library ieee;
  use ieee.std_logic_1164.all;

library bnn_lib;
library util;"""

        self.entity = f"""
entity bnn is
  generic (
    -- TODO: Height and width are only used for the testsuite.
    C_INPUT_HEIGHT : integer := {self.previous_layer_info["height"]};
    C_INPUT_WIDTH : integer := {self.previous_layer_info["width"]};
    C_INPUT_CHANNEL : integer := {self.previous_layer_info["channel"]};
    C_INPUT_CHANNEL_BITWIDTH : integer := {self.previous_layer_info["bitwidth"]};
    C_OUTPUT_CHANNEL : integer := {self.output_classes};
    C_OUTPUT_CHANNEL_BITWIDTH : integer := {self.output_bitwidth}
  );
  port (
    isl_clk    : in    std_logic;
    isl_start  : in    std_logic;
    isl_valid  : in    std_logic;
    islv_data  : in    std_logic_vector(C_INPUT_CHANNEL_BITWIDTH - 1 downto 0);
    oslv_data  : out   std_logic_vector(C_OUTPUT_CHANNEL_BITWIDTH - 1 downto 0);
    osl_valid  : out   std_logic;
    osl_finish : out   std_logic
  );
end entity bnn;
"""

    def add_layer(self, layer):
        self.layers.append(layer)

    def replace_last_layer(self, layer):
        self.layers[-1] = layer

    def to_vhdl(self):
        output = []
        declarations = []
        implementation = []

        declarations.append("-- input signals")
        declarations.append(
            parameter_to_vhdl(
                "signal",
                [
                    self.input_data_signal_deserialized,
                    self.input_control_signal_deserialized,
                ],
            )
        )
        declarations.append("")

        # connect input signals
        implementation.append(
            f"""
i_deserializer : entity util.deserializer
  generic map (
    C_DATA_COUNT    => C_INPUT_CHANNEL,
    C_DATA_BITWIDTH => C_INPUT_CHANNEL_BITWIDTH
  )
  port map (
    isl_clk   => isl_clk,
    isl_valid => isl_valid,
    islv_data => islv_data,
    oslv_data => {self.input_data_signal_deserialized.name},
    osl_valid => {self.input_control_signal_deserialized.name}
  );
"""
        )

        # parse the bnn
        for layer in self.layers:
            layer.update(self.previous_layer_info)
            self.previous_layer_info.update(layer.get_info())

            declarations.append(f"-- layer {layer.info['name']}")
            declarations.append(parameter_to_vhdl("constant", layer.get_constants()))
            declarations.append(parameter_to_vhdl("signal", layer.get_signals()))
            declarations.append("")
            implementation.append(layer.get_instance())

        # connect output signals
        if self.output_classes != self.previous_layer_info["channel"]:
            raise Exception(
                f"Output classes ({self.output_classes}) don't match channel of the last layer ({self.previous_layer_info['channel']})."
            )
        implementation.append("")
        implementation.append(f"osl_finish <= '0';")
        implementation.append(f"osl_valid <= {layer.control_signal.name};")
        implementation.append(f"oslv_data <= {layer.data_signal.name};")
        implementation.append("")

        # generate the output
        output.append(self.libraries)
        output.append(self.entity)
        output.append("architecture rtl of bnn is\n")
        output.extend(declarations)
        output.append("begin\n")
        output.extend(implementation)
        output.append("end rtl;\n")
        return "\n".join(output)


def custom_bnn():
    input_channel = 1
    input_channel_bitwidth = 8
    output_channel = 8
    output_channel_bitwidth = 8
    b = Bnn(
        22,
        22,
        input_channel,
        input_channel_bitwidth,
        output_channel,
        output_channel_bitwidth,
    )
    c = Convolution(
        "conv1",
        [
            Parameter("C_KERNEL_SIZE", "integer", "3"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "8"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    m = MaximumPooling(
        "max1",
        [
            Parameter("C_KERNEL_SIZE", "integer", "2"),
            Parameter("C_STRIDE", "integer", "2"),
        ],
    )
    b.add_layer(m)
    c = Convolution(
        "conv2",
        [
            Parameter("C_KERNEL_SIZE", "integer", "3"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "16"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    m = MaximumPooling(
        "max2",
        [
            Parameter("C_KERNEL_SIZE", "integer", "2"),
            Parameter("C_STRIDE", "integer", "2"),
        ],
    )
    b.add_layer(m)
    c = Convolution(
        "conv3",
        [
            Parameter("C_KERNEL_SIZE", "integer", "1"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "64"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    c = Convolution(
        "conv4",
        [
            Parameter("C_KERNEL_SIZE", "integer", "1"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", output_channel),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", output_channel_bitwidth),
        ],
    )
    b.add_layer(c)
    return b


def get_kernel_size(kernel_shape):
    ksize = kernel_shape[0]
    for ksize_ in kernel_shape:
        if ksize != ksize_:
            raise Exception(
                f"Only quadratic kernels are supported. Got kernel shape {kernel_shape}"
            )
    return ksize


def get_stride(strides):
    stride = strides[0]
    for stride_ in strides:
        if stride != stride_:
            raise Exception(
                f"Only same stride in each direction is supported. Got strides {strides}"
            )
    return stride


def bnn_from_larq(path: str) -> Bnn:
    model = tf.keras.models.load_model(path)
    lq.models.summary(model)

    input_channel = model.input.shape[-1]
    input_channel_bitwidth = 8
    output_channel_bitwidth = 8
    bnn = Bnn(
        *model.input.shape[1:],  # h x w x ch
        input_channel_bitwidth,
        *model.output.shape[1:],  # ch
        output_channel_bitwidth,
    )

    # Find last convolution layer for disabling batch normalization
    last_conv_layer_name = None
    for layer in model.layers:
        if isinstance(layer, lq.layers.QuantConv2D):
            last_conv_layer_name = layer.get_config()["name"]

    last_layer = None  # Only used for sanity checks.
    fan_in = None
    channel = input_channel
    channel_bw = input_channel_bitwidth

    for layer in model.layers:
        # Compare "filters" with layer.output.shape[-1]?
        parameter = layer.get_config()
        if isinstance(layer, lq.layers.QuantConv2D):
            print("conv")

            if parameter["name"] == last_conv_layer_name:
                channel_bw_out = (
                    output_channel_bitwidth  # dont append batchnorm at last layer
                )
            else:
                channel_bw_out = 1

            l = Convolution(
                parameter["name"],
                channel,
                channel_bw,
                [
                    Parameter(
                        "C_KERNEL_SIZE",
                        "integer",
                        get_kernel_size(parameter["kernel_size"]),
                    ),
                    Parameter("C_STRIDE", "integer", get_stride(parameter["strides"])),
                    Parameter("C_OUTPUT_CHANNEL", "integer", layer.output.shape[-1]),
                    Parameter(
                        "C_OUTPUT_CHANNEL_BITWIDTH",
                        "integer",
                        str(channel_bw_out)
                        if parameter["name"] == last_conv_layer_name
                        else "1",
                    ),
                ],
            )

            l.add_weights(layer.get_weights()[0].flat)
            l.add_thresholds()  # add dummy threshold for now -> gets overwritten if there is a batch norm layer
            bnn.add_layer(l)

            # used at the next batch norm
            fan_in = (
                get_kernel_size(parameter["kernel_size"]) ** 2 * channel * channel_bw
            )
            # used at the next conv
            channel = layer.output.shape[-1]
            channel_bw = channel_bw_out
        elif isinstance(layer, tf.keras.layers.BatchNormalization):
            print("batchnorm")
            if not isinstance(last_layer, lq.layers.QuantConv2D):
                raise Exception(
                    f"Batchnorm must follow convolution, not {type(last_layer)}"
                )
            # TODO: Check for last layer output bitwith == 1
            if l.info["name"] == last_conv_layer_name or channel_bw != 1:
                raise Exception()

            # calculate batch normalization threshold
            beta, mean, variance = layer.get_weights()
            threshold_batchnorm = mean - beta * np.sqrt(variance + 0.001)

            if l.input_channel_bitwidth == 1:  # unsigned
                threshold_pos = (threshold_batchnorm + fan_in) / 2
                l.add_thresholds(threshold_pos.tolist())
            else:  # signed
                l.add_thresholds(threshold_batchnorm.tolist())

            bnn.replace_last_layer(l)
        elif isinstance(layer, tf.keras.layers.MaxPooling2D):
            print("maxpooling")
            l = MaximumPooling(
                parameter["name"],
                [
                    Parameter(
                        "C_KERNEL_SIZE",
                        "integer",
                        get_kernel_size(parameter["pool_size"]),
                    ),
                    Parameter("C_STRIDE", "integer", get_stride(parameter["strides"])),
                ],
            )
            bnn.add_layer(l)
        elif isinstance(layer, tf.keras.layers.GlobalAveragePooling2D):
            print("average pooling")
            l = AveragePooling(parameter["name"], [])
            bnn.add_layer(l)
        elif isinstance(layer, tf.keras.layers.Flatten):
            print("flatten")  # ignore
        elif isinstance(layer, tf.keras.layers.Dense):
            print("dense")
        elif isinstance(layer, tf.keras.layers.Activation):
            print("activation")  # ignore
        else:
            raise Exception(f"Unsupported layer: {type(layer)}")
        last_layer = layer
    return bnn


if __name__ == "__main__":
    # bnn = custom_bnn()
    bnn = bnn_from_larq("../models/test")
    vhdl = bnn.to_vhdl()
    with open("../src/bnn.vhd", "w") as outfile:
        outfile.write(vhdl)
