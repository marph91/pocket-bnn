from dataclasses import dataclass
import math
from random import randint
from typing import Dict, List, Optional


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
    def __init__(self, name, parameter):
        super().__init__(name, parameter)

        self.control_signal = Parameter(f"sl_valid_{self.info['name']}", "std_logic")
        self.signals = [self.control_signal]

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

        # weights
        kernel_size = int(self.constants["C_KERNEL_SIZE"].value)
        input_channel = previous_layer_info["channel"]
        output_channel = self.info["channel"]
        bitwidth = input_channel * output_channel * kernel_size ** 2
        weights = "".join([str(randint(0, 1)) for _ in range(bitwidth)])
        self.constants["C_WEIGHTS"] = Parameter(
            f"C_WEIGHTS_{self.info['name'].upper()}",
            f"std_logic_vector({bitwidth} - 1 downto 0)",
            f'"{weights}"',
        )

        # thresholds
        input_channel_bitwidth = previous_layer_info["bitwidth"]
        bitwidth = (
            math.ceil(
                math.log2(input_channel * input_channel_bitwidth * kernel_size ** 2 + 1)
            )
            * output_channel
        )
        thresholds = "".join([str(randint(0, 1)) for _ in range(bitwidth)])
        self.constants["C_THRESHOLDS"] = Parameter(
            f"C_THRESHOLDS_{self.info['name'].upper()}",
            f"std_logic_vector({bitwidth} - 1 downto 0)",
            f'"{thresholds}"',
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

    def get_instance(self):
        return f"""
i_convolution_{self.info["name"]} : entity cnn_lib.window_convolution_activation
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
i_maximum_pooling_{self.info["name"]} : entity cnn_lib.window_maximum_pooling
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


class BatchNormalization(Layer):
    def __init__(self, name, parameter):
        super().__init__(name, parameter)

        self.constants = {}
        self.control_signal = Parameter(f"sl_valid_{self.info['name']}", "std_logic")
        self.data_signal = Parameter(
            f"slv_data_{self.info['name']}", "std_logic_vector(1 - 1 downto 0)"
        )
        self.signals = [self.data_signal, self.control_signal]

    def update(self, previous_layer_info):
        self.previous_name = previous_layer_info["name"]

    def get_instance(self):
        return f"""
i_batch_normalization_{self.info["name"]} : entity cnn_lib.batch_normalization
  generic map (
    C_POST_CONVOLUTION_BITWIDTH => 8
  )
  port map (
    isl_clk        => isl_clk,
    isl_valid      => sl_valid_{self.previous_name},
    islv_data      => slv_data_{self.previous_name},
    islv_threshold => "10000000",
    oslv_data      => {self.data_signal.name},
    osl_valid      => {self.control_signal.name}
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
            "name": "in",
            "channel": input_channel,
            "bitwidth": input_bitwidth,
            "width": image_width,
            "height": image_height,
        }

        # TODO: input_channel
        self.input_data_signal = Parameter(
            f"slv_data_{self.previous_layer_info['name']}",
            f"std_logic_vector(8 - 1 downto 0)",
        )
        self.input_control_signal = Parameter(
            f"sl_valid_{self.previous_layer_info['name']}", "std_logic"
        )

        self.libraries = """
library ieee;
  use ieee.std_logic_1164.all;

library cnn_lib;
library util;"""

        # TODO: input_channel
        self.entity = f"""
entity bnn is
  generic (
    C_INPUT_CHANNEL : integer := {self.previous_layer_info["channel"]};
    C_INPUT_CHANNEL_BITWIDTH : integer := {self.previous_layer_info["bitwidth"]}
  );
  port (
    isl_clk    : in    std_logic;
    isl_start  : in    std_logic;
    isl_valid  : in    std_logic;
    islv_data  : in    std_logic_vector(C_INPUT_CHANNEL * C_INPUT_CHANNEL_BITWIDTH - 1 downto 0);
    oslv_data  : out   std_logic_vector({self.output_bitwidth} - 1 downto 0);
    osl_valid  : out   std_logic;
    osl_finish : out   std_logic
  );
end entity bnn;
"""

    def add_layer(self, layer):
        self.layers.append(layer)

    def to_vhdl(self):
        output = []
        declarations = []
        implementation = []

        declarations.append("-- input signals")
        declarations.append(
            parameter_to_vhdl(
                "signal", [self.input_data_signal, self.input_control_signal]
            )
        )
        declarations.append("")

        # connect input signals
        implementation.append(f"{self.input_control_signal.name} <= isl_valid;")
        implementation.append(f"{self.input_data_signal.name} <= islv_data;")

        # append the output serializer
        self.layers.append(Serializer("output", []))

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
        assert self.output_classes == self.previous_layer_info["channel"]
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


if __name__ == "__main__":
    input_channel = 1
    input_channel_bitwidth = 8
    output_channel = 8
    output_channel_bitwidth = 8
    b = Bnn(
        8,
        8,
        input_channel,
        input_channel_bitwidth,
        output_channel,
        output_channel_bitwidth,
    )
    c = Convolution(
        "aaa",
        [
            Parameter("C_KERNEL_SIZE", "integer range 1 to 7", "3"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "8"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    m = MaximumPooling(
        "ggg",
        [
            Parameter("C_KERNEL_SIZE", "integer range 1 to 7", "2"),
            Parameter("C_STRIDE", "integer", "2"),
        ],
    )
    b.add_layer(m)
    c = Convolution(
        "bbb",
        [
            Parameter("C_KERNEL_SIZE", "integer range 1 to 7", "3"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "16"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    c = Convolution(
        "ccc",
        [
            Parameter("C_KERNEL_SIZE", "integer range 1 to 7", "1"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "32"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    c = Convolution(
        "ddd",
        [
            Parameter("C_KERNEL_SIZE", "integer range 1 to 7", "1"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", "64"),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", "1"),
        ],
    )
    b.add_layer(c)
    c = Convolution(
        "eee",
        [
            Parameter("C_KERNEL_SIZE", "integer range 1 to 7", "1"),
            Parameter("C_STRIDE", "integer", "1"),
            Parameter("C_OUTPUT_CHANNEL", "integer", output_channel),
            Parameter("C_OUTPUT_CHANNEL_BITWIDTH", "integer", output_channel_bitwidth),
        ],
    )
    b.add_layer(c)

    vhdl = b.to_vhdl()
    print(vhdl)
    with open("../src/bnn.vhd", "w") as outfile:
        outfile.write(vhdl)
