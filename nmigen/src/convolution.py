import math

import nmigen as nm


class AdderTree(nm.Elaboratable):
    def __init__(self, count, bitwidth_in, bitwidth_out):
        # Parameter
        self.count = count
        self.bitwidth_in = bitwidth_in
        self.bitwidth_out = bitwidth_out

        # Ports
        self.valid_in = nm.Signal()
        self.data_in = nm.Array(
            nm.Signal(bitwidth_in, name=f"in_{cnt}") for cnt in range(count)
        )
        self.valid_out = nm.Signal()
        self.data_out = nm.Signal(bitwidth_out)

    def elaborate(self, platform):
        m = nm.Module()

        stages = math.ceil(math.log2(self.count))
        inputs_first_stage = 2 ** stages
        sums = nm.Array(
            nm.Signal(self.bitwidth_out, name=f"sums_{cnt}")
            for cnt in range(2 * inputs_first_stage - 1)
        )
        active_stages = nm.Signal(stages)

        # other sums simply stay 0
        with m.If(self.valid_in):
            for input_index in range(self.count):
                m.d.comb += sums[input_index].eq(self.data_in[input_index])

        m.d.sync += active_stages.eq(active_stages << 1 | self.valid_in)

        start_index = 0
        for i, stage in enumerate(range(len(active_stages))):
            next_start_index = start_index + 2 ** (stages - i)
            with m.If(active_stages[stage]):
                for current_index in range(0, 2 ** (stages - i), 2):
                    m.d.sync += sums[next_start_index + current_index // 2].eq(
                        sums[start_index + current_index]
                        + sums[start_index + current_index + 1]
                    )
            start_index = next_start_index

        m.d.comb += self.valid_out.eq(active_stages[-1])
        m.d.comb += self.data_out.eq(sums[-1])

        return m


class ConvolutionOneOutput(nm.Elaboratable):
    """Three dimensional (height, width, channel) convolution for one output channel."""

    def __init__(self, channel, dim=2, bitwidth=1, batch_normalization=True):
        # Parameter
        if dim not in range(1, 4):
            raise ValueError("Only supported dim is 1-3 for now.")
        if bitwidth != 1:
            raise ValueError("Only supported bitwidth is 1 for now.")
        self.dim = dim
        self.channel = channel
        self.bitwidth = bitwidth
        self.batch_normalization = batch_normalization

        # Ports
        self.valid_in = nm.Signal()
        self.data_in = nm.Array(
            nm.Array(
                nm.Signal(bitwidth, name=f"data_in_{ch=}_{spatial_index=}")
                for spatial_index in range(dim ** 2)
            )
            for ch in range(channel)
        )
        self.weights = nm.Array(
            nm.Array(
                nm.Signal(bitwidth, name=f"weights_{ch=}_{spatial_index=}")
                for spatial_index in range(dim ** 2)
            )
            for ch in range(channel)
        )
        # TODO: check if bitwidth is sufficient
        if self.batch_normalization:
            output_bitwidth = 1
        else:
            output_bitwidth = bitwidth + math.ceil(math.log2(dim ** 2 * channel + 1))
        self.data_out = nm.Signal(output_bitwidth)
        self.valid_out = nm.Signal()

    def elaborate(self, platform):
        m = nm.Module()

        adder_tree = AdderTree(
            self.channel * self.dim ** 2, self.bitwidth, len(self.data_out)
        )
        m.submodules.adder_tree = adder_tree

        with m.If(self.valid_in):
            products = []
            for ch in range(self.channel):
                for spatial_index in range(self.dim ** 2):
                    products.append(
                        self.data_in[ch][spatial_index]
                        ^ self.weights[ch][spatial_index]
                    )

            for i in range(len(products)):
                m.d.comb += adder_tree.data_in[i].eq(products[i])
        m.d.comb += adder_tree.valid_in.eq(self.valid_in)

        if self.batch_normalization:
            # TODO: batchnorm
            raise ValueError("Batchnorm not yet supported.")
        else:
            m.d.comb += [
                self.valid_out.eq(adder_tree.valid_out),
                self.data_out.eq(adder_tree.data_out),
            ]

        return m


class Convolution(nm.Elaboratable):
    """Three dimensional (height, width, channel), including adder tree and batch normalization."""

    def __init__(
        self, channel_in, channel_out=1, dim=2, bitwidth=1, batch_normalization=True
    ):
        # Parameter
        if dim not in range(1, 4):
            raise ValueError("Only supported dim is 1-3 for now.")
        if bitwidth != 1:
            raise ValueError("Only supported bitwidth is 1 for now.")
        self.dim = dim
        self.channel_in = channel_in
        self.channel_out = channel_out
        self.bitwidth = bitwidth
        self.batch_normalization = batch_normalization

        # Ports
        self.valid_in = nm.Signal()
        self.data_in = nm.Array(
            nm.Array(
                nm.Signal(bitwidth, name=f"data_in_{ch=}_{spatial_index=}")
                for spatial_index in range(dim ** 2)
            )
            for ch in range(channel_in)
        )
        self.weights = nm.Array(
            nm.Array(
                nm.Array(
                    nm.Signal(
                        bitwidth, name=f"weights_{ch_out=}_{ch_in=}_{spatial_index=}"
                    )
                    for spatial_index in range(dim ** 2)
                )
                for ch_in in range(channel_in)
            )
            for ch_out in range(channel_out)
        )
        if self.batch_normalization:
            output_bitwidth = 1
        else:
            output_bitwidth = bitwidth + math.ceil(math.log2(dim ** 2 * channel_in + 1))
        self.data_out = nm.Array(
            nm.Signal(output_bitwidth, name=f"data_out_{ch_out=}")
            for ch_out in range(channel_out)
        )
        self.valid_out = nm.Signal()

    def elaborate(self, platform):
        m = nm.Module()

        for ch_out in range(len(self.weights)):
            m.submodules[f"conv_{ch_out}"] = ConvolutionOneOutput(
                self.channel_in,
                self.dim,
                self.bitwidth,
                batch_normalization=self.batch_normalization,
            )

        for ch_out in range(len(self.weights)):
            for ch_in in range(len(self.weights[0])):
                for spatial_index in range(len(self.weights[0][0])):
                    m.d.comb += (
                        m.submodules[f"conv_{ch_out}"]
                        .data_in[ch_in][spatial_index]
                        .eq(self.data_in[ch_in][spatial_index])
                    )
                    m.d.comb += (
                        m.submodules[f"conv_{ch_out}"]
                        .weights[ch_in][spatial_index]
                        .eq(self.weights[ch_out][ch_in][spatial_index])
                    )

            m.d.comb += [
                m.submodules[f"conv_{ch_out}"].valid_in.eq(self.valid_in),
                self.data_out[ch_out].eq(m.submodules[f"conv_{ch_out}"].data_out),
            ]
        m.d.comb += self.valid_out.eq(m.submodules["conv_0"].valid_out)

        return m
